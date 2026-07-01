"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing

DAYS = 30


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        # Pass gpu_type and job_days (from j["days"]) to advanced recommend_tier
        job_days = num(j["days"])
        tier = pricing.recommend_tier(hpd, interruptible, gpu_type=gtype, job_days=job_days)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")

    # Run carbon-aware scheduling analysis
    carbon_results = run_carbon_scheduling_analysis(verbose=verbose)

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_analysis": carbon_results}


def run_carbon_scheduling_analysis(verbose: bool = True) -> dict:
    from finops.sustainability import REGION_CARBON, REGION_PRICE_KWH
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    
    interruptible_jobs = [j for j in jobs if bool(int(num(j["interruptible"])))]
    total_baseline_carbon = 0.0
    total_cleanest_carbon = 0.0
    
    results = []
    for j in interruptible_jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        c = cat[gtype]
        watts = num(c["watts"])
        
        wh_monthly = watts * hpd * ngpu * DAYS
        kwh_monthly = wh_monthly / 1000.0
        
        region_metrics = {}
        for region in REGION_CARBON:
            intensity = REGION_CARBON[region]
            elec_price = REGION_PRICE_KWH[region]
            
            carbon_footprint = kwh_monthly * intensity
            elec_cost = kwh_monthly * elec_price
            
            region_metrics[region] = {
                "carbon_g": carbon_footprint,
                "cost_usd": elec_cost
            }
        
        baseline_carbon = region_metrics["us-east-1"]["carbon_g"]
        cleanest_carbon = region_metrics["europe-north1"]["carbon_g"]
        
        total_baseline_carbon += baseline_carbon
        total_cleanest_carbon += cleanest_carbon
        
        results.append({
            "job_id": j["job_id"],
            "gpu_type": gtype,
            "kwh_monthly": kwh_monthly,
            "regions": region_metrics
        })
        
    carbon_saved = total_baseline_carbon - total_cleanest_carbon
    saved_pct = (carbon_saved / total_baseline_carbon * 100.0) if total_baseline_carbon > 0 else 0.0
    
    if verbose:
        print("\n== Extension 5: Carbon-Aware Scheduling Analysis ==")
        print(f"Analyzing {len(interruptible_jobs)} interruptible jobs (can run in any region):")
        for r in results:
            print(f"Job: {r['job_id']} ({r['gpu_type']}) - {r['kwh_monthly']:.1f} kWh/month")
            print(f"  - us-east-1 (baseline): {r['regions']['us-east-1']['carbon_g']/1000:.2f} kgCO2e, ${r['regions']['us-east-1']['cost_usd']:.2f}")
            print(f"  - europe-north1 (cleanest): {r['regions']['europe-north1']['carbon_g']/1000:.2f} kgCO2e, ${r['regions']['europe-north1']['cost_usd']:.2f}")
            
        print(f"\nPotential Carbon Savings by routing to europe-north1: {carbon_saved/1000:.2f} kgCO2e ({saved_pct:.1f}% reduction)")
        
        print("\nRegional Comparison Matrix (Avg across all interruptible jobs):")
        print(f"{'Region':20}{'gCO2/kWh':10}{'$/kWh':8}{'Avg Carbon (kg)':18}{'Avg Elec Cost ($)':20}")
        for reg in REGION_CARBON:
            avg_carbon = sum(r["regions"][reg]["carbon_g"] for r in results) / len(results) / 1000.0 if results else 0.0
            avg_cost = sum(r["regions"][reg]["cost_usd"] for r in results) / len(results) if results else 0.0
            print(f"{reg:20}{REGION_CARBON[reg]:<10}{REGION_PRICE_KWH[reg]:<8.3f}{avg_carbon:<18.2f}${avg_cost:<19.2f}")
            
        print("\nDecision Recommendations:")
        print("  - Re nhat ($): us-east-wa ($0.055/kWh)")
        print("  - Sach nhat (CO2): europe-north1 (30 gCO2/kWh)")
        print("  - Can bang nhat: us-west-2 (120 gCO2/kWh, $0.07/kWh)")
        print("  - Trade-off Latency: europe-north1 (Norway) may introduce higher latency for US-based end-users, but for offline training jobs, this latency is negligible.")

    return {
        "carbon_saved_g": carbon_saved,
        "saved_pct": saved_pct,
        "results": results
    }


if __name__ == "__main__":
    run()

