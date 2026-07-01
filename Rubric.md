# Rubric chấm điểm — Lab 25: GPU FinOps Optimization

> **AICB · Phase 2 · Track 2 · Day 25**
> Tổng điểm: **100 điểm** · Thời hạn nộp: xem lịch khóa học

---

## Tổng quan thang điểm

| Thành phần | Điểm tối đa | Ghi chú |
|---|---|---|
| **A. Kiểm tra tự động** (`verify.py` 11/11) | 30 | Chạy được, đếm số check pass |
| **B. Unit tests** (`pytest` pass) | 20 | Tỷ lệ tests pass / 15 tests |
| **C. Báo cáo kỹ thuật** (`outputs/report.md`) | 30 | Đánh giá chất lượng và độ chính xác |
| **D. Phần mở rộng "Your Turn"** (≥2 extensions) | 20 | Mỗi extension tối đa 10 điểm |
| **Tổng** | **100** | |

---

## A. Kiểm tra tự động — 30 điểm

### Cách chấm

Chạy lệnh sau trong thư mục lab của sinh viên:

```bash
python verify.py
```

| Số check pass | Điểm |
|---|---|
| 11/11 | 30 |
| 10/11 | 25 |
| 9/11 | 20 |
| 8/11 | 15 |
| 7/11 | 10 |
| ≤ 6/11 | 5 |
| Không chạy được / lỗi import | 0 |

### Chi tiết 11 checks và ý nghĩa

| Check | Mission | Ý nghĩa giáo dục |
|---|---|---|
| M1 flags GPU-Util lie (gpu-h100-4) | M1 | Hiểu sự khác biệt GPU-Util vs MFU |
| M1 detects idle waste | M1 | Tính được chi phí GPU bỏ không |
| M2 $/1M-token drops after optimization | M2 | Hiểu đòn bẩy inference giảm chi phí |
| M2 savings in 60–95% band | M2 | Kết quả hợp lý (không quá thấp/cao) |
| M3 recommends a spot tier | M3 | Logic tier selection hoạt động đúng |
| M3 recommends a reserved tier | M3 | Logic tier selection đa dạng |
| M3 purchasing saves money | M3 | Tổng savings > 0 |
| M4 tag coverage 85–100% | M4 | Data đã được generate đúng |
| M4 chargeback gate is open | M4 | Coverage ≥ 80% → sẵn sàng chargeback |
| M5 total savings in 40–95% band | M5 | Báo cáo tổng hợp hợp lý |
| M5 report.md written | M5 | File output được tạo |

> **Lưu ý cho giảng viên:** Nếu sinh viên sửa code engine (`finops/`) theo hướng không đúng bản chất (ví dụ: hardcode kết quả), check sẽ pass nhưng phần C sẽ phản ánh vấn đề này.

---

## B. Unit Tests — 20 điểm

### Cách chấm

```bash
pytest -q
```

| Số tests pass | Điểm |
|---|---|
| 15/15 | 20 |
| 13–14/15 | 16 |
| 10–12/15 | 12 |
| 7–9/15 | 8 |
| 4–6/15 | 4 |
| ≤ 3/15 | 0 |

### Danh sách tests và nội dung

| File test | Tests | Kiểm tra gì |
|---|---|---|
| `test_metrics.py` | `test_mfu_basic`, `test_mbu_and_roofline`, `test_flag_util_lies`, `test_idle_waste` | Tính đúng MFU/MBU, phát hiện lies, tính lãng phí |
| `test_pricing.py` | `test_request_cost`, `test_dollars_per_million`, `test_discount_stack`, `test_break_even`, `test_recommend_tier` | Công thức chi phí, chiết khấu, tier selection |
| `test_allocation.py` | `test_cost_by_tag`, `test_tag_coverage`, `test_chargeback_ready`, `test_to_focus_rows` | Phân bổ chi phí và FOCUS export |
| `test_report.py` | `test_build_report` | Tạo báo cáo Markdown đúng format |
| `test_data_and_missions.py` | Integration tests M1–M5 | End-to-end pipeline hoạt động |

> **Lưu ý:** Sinh viên **không được sửa file test**. Nếu phát hiện test bị sửa để hardcode kết quả, trừ toàn bộ điểm phần B.

---

## C. Báo cáo kỹ thuật — 30 điểm

### Cách đánh giá

Mở và đọc `outputs/report.md` + xem `outputs/savings.png`.

### C.1 — Nội dung bắt buộc (15 điểm)

| Tiêu chí | Điểm | Không đạt |
|---|---|---|
| Có đủ: baseline spend, optimized spend, % tiết kiệm tổng | 5 | Thiếu bất kỳ số liệu nào |
| Bảng phân tích từng lever với số tiền tiết kiệm cụ thể | 5 | Chỉ có tổng, không có breakdown |
| Phần Sustainability: năng lượng/truy vấn, carbon, vùng tốt nhất | 5 | Thiếu hoặc sai vùng tốt nhất |

### C.2 — Phân tích chất lượng (10 điểm)

| Tiêu chí | Điểm | Mô tả |
|---|---|---|
| Giải thích tại sao GPU-Util là "lie" và ý nghĩa với chi phí | 3 | Không chỉ nêu MFU thấp, phải giải thích cơ chế |
| Đề xuất hành động cụ thể, có độ ưu tiên | 4 | Ưu tiên lever nào trước? Tại sao? |
| Có nhận xét về tính bền vững (carbon, vùng triển khai) | 3 | Liên kết carbon với chi phí thực tế |

### C.3 — Hình thức (5 điểm)

| Tiêu chí | Điểm | Mô tả |
|---|---|---|
| `savings.png` có mặt và đọc được | 2 | Waterfall chart hiển thị đúng 4 levers |
| Số liệu nhất quán giữa report.md và output của missions | 3 | Không có số liệu copy-paste sai |

### Thang điểm tham khảo C.2

**9–10/10 (Xuất sắc):** Giải thích rõ nguyên nhân gốc rễ của từng vấn đề (ví dụ: GPU-Util lie xảy ra do memory stall hoặc kernel launch overhead). Đề xuất hành động theo thứ tự ROI. Liên kết carbon với chi phí điện cụ thể.

**7–8/10 (Tốt):** Nêu đúng các vấn đề và đề xuất hợp lý, nhưng giải thích cơ chế còn đơn giản.

**5–6/10 (Đạt):** Có phân tích nhưng chủ yếu diễn giải lại output của script, không có insight thêm.

**<5/10 (Cần cải thiện):** Báo cáo chỉ là copy-paste output terminal, không có phân tích.

---

## D. Phần mở rộng "Your Turn" — 20 điểm

Sinh viên chọn **ít nhất 2** trong 5 extensions. Mỗi extension tối đa **10 điểm**.

> Nếu làm ≥3 extensions và chất lượng tốt, điểm tối đa vẫn là 20. Không có điểm cộng thêm trên 20.

### Thang điểm cho mỗi Extension

| Điểm | Tiêu chí |
|---|---|
| **9–10** | Code chạy được, có kết quả đo lường cụ thể (con số), so sánh trước/sau có ý nghĩa, giải thích insight rõ ràng |
| **7–8** | Code chạy được, có kết quả đo lường, nhưng giải thích còn sơ sài hoặc so sánh chưa rõ ý nghĩa |
| **5–6** | Code có lỗi nhỏ nhưng logic đúng hướng, hoặc không có kết quả đo lường định lượng |
| **3–4** | Code chưa hoàn thiện hoặc chạy không được, nhưng thể hiện hiểu đúng hướng |
| **0–2** | Chỉ viết comment ý định, không có code thực sự |

### D.1 — Extension 1: Cải thiện `recommend_tier()`

**Vị trí:** `finops/pricing.py` — hàm `recommend_tier()`

**Kỳ vọng tối thiểu (7–8 điểm):**
- Thêm ít nhất 1 yếu tố mới (interruption rate theo GPU type, hoặc so sánh 1yr vs 3yr reserved)
- Chạy lại M3, in ra `savings_pct` mới so với cũ

**Kỳ vọng xuất sắc (9–10 điểm):**
- Thêm cả interruption rate VÀ duration comparison
- Đề xuất bảng tier recommendation theo matrix (GPU type × duty cycle × interruptible)
- Có test tự viết cho logic mới

**Câu hỏi chấm điểm:** "Savings thay đổi như thế nào? Tại sao policy mới cho kết quả khác?"

### D.2 — Extension 2: Right-sizing theo MBU

**Vị trí:** `missions/m1_efficiency_audit.py`

**Kỳ vọng tối thiểu (7–8 điểm):**
- Tính `$/GB-VRAM` cho các GPU trong catalog
- Với GPU memory-bound (MBU thấp), in ra GPU thay thế rẻ hơn và % savings

**Kỳ vọng xuất sắc (9–10 điểm):**
- Bảng so sánh: GPU hiện tại vs. GPU đề xuất, với lý do chọn dựa trên `peak_bw_tbs` và `$/GB-VRAM`
- Tính được monthly savings nếu right-size tất cả memory-bound GPUs

**Câu hỏi chấm điểm:** "Tại sao không chỉ chọn GPU rẻ nhất theo `$/GPU-hr`?"

### D.3 — Extension 3: `cache_is_worth_it()`

**Vị trí:** `finops/pricing.py` + `missions/m2_inference_levers.py`

**Kỳ vọng tối thiểu (7–8 điểm):**
- Hàm `cache_is_worth_it(avg_reads, write_cost, read_discount)` hoạt động đúng
- Applied trong M2: chỉ tính savings cache khi hàm trả về True

**Kỳ vọng xuất sắc (9–10 điểm):**
- Tính break-even số lần đọc cho từng model tier (nhỏ vs. lớn)
- So sánh với `avg_cache_reads` thực tế trong `token_usage.csv`
- Có test đơn vị cho `cache_is_worth_it()`

**Câu hỏi chấm điểm:** "Cần đọc lại bao nhiêu lần để cache có lợi? Dataset của chúng ta có đạt ngưỡng này không?"

### D.4 — Extension 4: Ngân sách Reasoning

**Vị trí:** `missions/m2_inference_levers.py` và/hoặc `missions/m5_report.py`

**Kỳ vọng tối thiểu (7–8 điểm):**
- Tách riêng chi phí `$` và `Wh` cho `is_reasoning=1` vs `is_reasoning=0`
- In ra: reasoning chiếm bao nhiêu % tổng chi phí với bao nhiêu % tổng traffic

**Kỳ vọng xuất sắc (9–10 điểm):**
- Đề xuất routing rule cụ thể (ví dụ: "chỉ dùng reasoning khi độ phức tạp task > X")
- Ước lượng: nếu cap reasoning xuống 10% traffic thay vì hiện tại, tiết kiệm bao nhiêu `$` và `Wh`

**Câu hỏi chấm điểm:** "Reasoning traffic chiếm bao nhiêu % tổng? Tại sao nó lại tốn năng lượng ~80× nhiều hơn?"

### D.5 — Extension 5: Carbon-aware Scheduling

**Vị trí:** `missions/m3_purchasing.py` hoặc file mới

**Kỳ vọng tối thiểu (7–8 điểm):**
- Với mỗi job `interruptible=1`: tính carbon tại `us-east-1` vs. vùng sạch nhất
- In ra tổng gCO2e tiết kiệm nếu chuyển toàn bộ sang vùng sạch nhất

**Kỳ vọng xuất sắc (9–10 điểm):**
- Bảng so sánh tất cả 5 vùng: `$/kWh`, `gCO2/kWh`, chi phí điện thực tế, carbon thực tế
- Đề xuất vùng tối ưu theo từng tiêu chí (rẻ nhất `$`, sạch nhất `CO2`, cân bằng nhất)
- Có nhận xét về trade-off latency (vùng sạch nhất có thể xa users nhất)

**Câu hỏi chấm điểm:** "Vùng nào là 'tối ưu' thực sự? Phụ thuộc vào ưu tiên nào của công ty?"

---

## Hướng dẫn sử dụng Rubric này

### Quy trình chấm điểm đề xuất

1. **Chạy tự động trước** — `python verify.py` và `pytest -q` để lấy điểm A và B khách quan.
2. **Đọc `outputs/report.md`** — chấm C theo từng tiêu chí riêng biệt.
3. **Review code extension** — tìm file bị sửa và chạy thử để chấm D.
4. **Cross-check** — đảm bảo số liệu trong report khớp với output của missions.

### Dấu hiệu cần điều tra thêm

- `verify.py` pass 11/11 nhưng `pytest` fail nhiều → có thể sinh viên chỉ sửa missions, không sửa engine
- Kết quả savings quá cao (>95%) → kiểm tra có hardcode không
- Report có số liệu khác output terminal → copy-paste từ bài khác hoặc chỉnh tay

### Phân loại học lực tham khảo

| Tổng điểm | Phân loại | Đặc điểm |
|---|---|---|
| 90–100 | Xuất sắc | Pass tự động, test sạch, report có insight sâu, ≥3 extensions chất lượng |
| 80–89 | Tốt | Pass tự động, test sạch, report đủ nội dung, ≥2 extensions hoạt động |
| 70–79 | Khá | Pass tự động hoặc gần pass, pytest >10/15, report đủ số liệu |
| 60–69 | Đạt | verify.py ≥8/11, pytest >7/15, report có đủ cấu trúc |
| <60 | Cần cải thiện | Chưa hoàn thành flow cơ bản |

---

## Phụ lục: Câu hỏi kiểm tra hiểu biết (Oral Check)

Dùng để phân biệt sinh viên hiểu bản chất vs. chỉ chạy script:

1. **"GPU-Util 98% có nghĩa là GPU đang làm việc hiệu quả không? Tại sao?"**
   - **Không.** GPU-Util chỉ đo xem các clock của GPU có đang hoạt động hay không. Nếu GPU bị nghẽn cổ chai bộ nhớ (Memory-bandwidth bound) hoặc nghẽn I/O, GPU-Util vẫn báo 98% nhưng Tensor Cores (nhân tính toán LLM) hoàn toàn không chạy, dẫn đến hiệu suất tính toán thực tế (MFU) cực kỳ thấp (~20%).
2. **"Tại sao cần ≥ 80% tag coverage mới dám chargeback?"**
   - Để đảm bảo tính công bằng và chính xác khi trừ tiền trực tiếp vào ngân sách của các team. Nếu tag coverage thấp, một lượng lớn chi phí "vô chủ" (untagged) sẽ bị phân bổ không chính xác, gây tranh chấp giữa các phòng ban.
3. **"Nếu công ty bạn có 70% workload interruptible, bạn sẽ tối ưu purchasing như thế nào?"**
   - Áp dụng chiến lược **Spot-First**. Thuê khoảng 60% Spot Instance cho các job training/batch và thiết lập hệ thống checkpoint tự động (ví dụ mỗi 30 phút). Các job spiky hoặc ngắn hạn còn lại sẽ chạy On-demand để tối ưu chi phí và độ ổn định.
4. **"Đo bằng $/GPU-hr vs $/1M-token — khi nào con số này cho kết quả trái ngược nhau?"**
   - Khi nâng cấp lên GPU thế hệ mới hơn (như A10G lên H100). Chi phí theo giờ (`$/GPU-hr`) tăng gấp nhiều lần, nhưng vì GPU mới xử lý nhanh hơn vượt trội, chi phí trên một triệu token (`$/1M-token`) thực tế lại rẻ hơn đáng kể.
5. **"Tại sao LLM decode là memory-bound còn prefill là compute-bound?"**
   - **Prefill (Input):** Xử lý song song tất cả các token đầu vào cùng lúc, tính toán ma trận khổng lồ $\rightarrow$ **Compute-bound**.
   - **Decode (Output):** Sinh token tuần tự từng cái một, bắt buộc phải tải lại toàn bộ weights của mô hình và KV Cache từ bộ nhớ HBM lên registers cho mỗi token mới $\rightarrow$ **Memory-bandwidth bound**.

