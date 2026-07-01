"""Pricing & purchasing economics — measure in $/1M-token, not $/GPU-hr.

Figures are June-2026 as-of snapshots from the deck's RESEARCH dossier; treat
live prices as fast-moving (re-baseline before each cohort).
"""
from __future__ import annotations


def request_cost(
    input_tok: int,
    output_tok: int,
    price_in_per_m: float,
    price_out_per_m: float,
    cached_in: int = 0,
    cache_discount: float = 0.10,   # Anthropic cached-read ~0.1x (=-90%)
    batch: bool = False,
    batch_discount: float = 0.50,   # Batch API ~ -50%
) -> float:
    """USD cost of a single request. Cached input billed at cache_discount x price."""
    cached_in = min(max(0, cached_in), input_tok)
    uncached_in = input_tok - cached_in
    cost = (
        (uncached_in / 1e6) * price_in_per_m
        + (cached_in / 1e6) * price_in_per_m * cache_discount
        + (output_tok / 1e6) * price_out_per_m
    )
    if batch:
        cost *= batch_discount
    return cost


def dollars_per_million(total_cost_usd: float, total_tokens: int) -> float:
    """Aggregate unit economics: $ per 1,000,000 tokens served."""
    if total_tokens <= 0:
        return 0.0
    return total_cost_usd / (total_tokens / 1e6)


def discount_stack(
    batch: bool = False,
    cache_hit_frac: float = 0.0,
    batch_discount: float = 0.50,
    cache_discount: float = 0.10,
) -> float:
    """Effective fraction of the naive bill after stacking discounts (input-heavy view).

    Discounts MULTIPLY: cache applies to the cached share of input, batch to the
    whole bill. batch + 100% cache-hit -> 0.5 * 0.1 = 0.05 (~95% off).
    """
    cache_mult = cache_hit_frac * cache_discount + (1.0 - cache_hit_frac)
    batch_mult = batch_discount if batch else 1.0
    return cache_mult * batch_mult


def break_even_utilization(discount_frac: float) -> float:
    """Utilization at which a commitment pays off ~= 1 - discount.

    A 45% reserved discount needs ~55% utilization (~13.2h/day) to beat on-demand.
    """
    return max(0.0, min(1.0, 1.0 - discount_frac))


def recommend_tier(
    hours_per_day: float,
    interruptible: bool,
    reserved_discount: float = 0.45,
    gpu_type: str | None = None,
    job_days: float | None = None,
) -> str:
    """Pick a purchasing tier from a workload's duty cycle + interruptibility.

    Enhanced policy:
      - Considers GPU-specific spot interruption rates (H100 spot has low ~2% risk, A10G has higher ~8% risk).
      - If interruption risk is high and duty cycle is high, we prefer reserved/on_demand.
      - If job_days is short (e.g. < 90 days), long-term commitments are restricted.
    """
    interrupt_rates = {
        "H100": 0.02,
        "A100": 0.04,
        "A10G": 0.08,
        "L4": 0.05,
    }
    duty = max(0.0, hours_per_day) / 24.0
    be = break_even_utilization(reserved_discount)
    
    # If the job duration is extremely short, reserved is not suitable
    effective_discount = reserved_discount
    if job_days is not None and job_days < 90:
        # Penalize reserved tier heavily for short term projects
        effective_discount = 0.0
    
    be = break_even_utilization(effective_discount)

    if interruptible and hours_per_day < 24:
        ir = interrupt_rates.get(gpu_type or "", 0.05)
        # High risk spot + high duty cycle -> prefer reserved/on_demand
        if ir >= 0.08 and hours_per_day > 18:
            return "reserved" if duty >= be else "on_demand"
        return "spot"
    if duty >= be:
        return "reserved"
    return "on_demand"


def cache_is_worth_it(
    avg_cache_reads: float,     # Average times a cached prefix is read back
    write_cost_per_m: float,    # Cost to write cache (standard input price)
    read_discount: float = 0.10 # 10% = 90% off
) -> bool:
    """Cache only saves money when the total savings from reads exceeds the cost of writing/establishing the cache.
    
    Without caching, N accesses cost: N * write_cost_per_m.
    With caching, N accesses cost: 1 * write_cost_per_m + (N - 1) * read_discount * write_cost_per_m.
    
    So caching saves money if:
      1 + (N - 1) * read_discount < N
      => (N - 1) * read_discount < N - 1
      => Since N = 1 + avg_cache_reads, this is equivalent to:
         avg_cache_reads * read_discount < avg_cache_reads
         which is always true for read_discount < 1.0, provided avg_cache_reads > 0.
         
    However, if there is a cache write overhead or a threshold requirement (e.g., cache creation fee),
    we can define that the savings must be greater than a certain threshold or avg_cache_reads * (1 - read_discount) > 1.0.
    """
    return avg_cache_reads * (1.0 - read_discount) > 1.0



def spot_checkpoint_cost(
    job_hours: float,
    spot_hr: float,
    on_demand_hr: float,
    interrupt_rate: float = 0.05,      # per-hour chance (H100 spot ~<5%)
    ckpt_overhead_frac: float = 0.03,  # steady cost of writing checkpoints
    rework_hours_per_interrupt: float = 0.5,
) -> dict:
    """Effective cost of running a checkpointable job on spot vs on-demand.

    Interruptions waste the compute since the last checkpoint (rework); checkpointing
    adds a small steady overhead. Spot still wins for interruptible jobs.
    """
    expected_interrupts = job_hours * interrupt_rate
    rework_hours = expected_interrupts * rework_hours_per_interrupt
    effective_hours = job_hours * (1.0 + ckpt_overhead_frac) + rework_hours
    spot_cost = effective_hours * spot_hr
    on_demand_cost = job_hours * on_demand_hr
    savings_pct = (1.0 - spot_cost / on_demand_cost) * 100.0 if on_demand_cost > 0 else 0.0
    return {
        "spot_effective_hours": round(effective_hours, 2),
        "spot_cost": round(spot_cost, 2),
        "on_demand_cost": round(on_demand_cost, 2),
        "savings_pct": round(savings_pct, 1),
    }
