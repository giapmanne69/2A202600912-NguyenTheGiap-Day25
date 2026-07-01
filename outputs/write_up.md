# Báo cáo Phân tích Tối ưu hóa Chi phí GPU (GPU FinOps Write-up)

Báo cáo này trả lời đầy đủ 5 câu hỏi trong Rubric chấm điểm của Lab 25 để làm tài liệu chứng minh kết quả tối ưu hóa chi phí GPU của **NimbusAI**.

---

## 1. Baseline vs. Optimized

* **Tổng chi phí GPU hàng tháng (Baseline vs. Optimized):**
  * **Baseline spend:** $27,133
  * **Optimized spend:** $15,385
  * **Tiết kiệm tổng cộng:** **$11,748** (tương đương giảm **43%** tổng hóa đơn).
* **Đơn vị Unit Economics hàng ngày (Inference $/1M-token):**
  * **Baseline $/1M-token:** $6.488 / 1M tokens
  * **Optimized $/1M-token:** $1.139 / 1M tokens
  * **Tỷ lệ tiết kiệm riêng phần inference:** **82.4%** nhờ áp dụng cascade routing, prompt caching (có chọn lọc) và Batch API.

---

## 2. Phân tích từng đòn bẩy tiết kiệm

| Đòn bẩy (Lever) | Số tiền tiết kiệm hàng tháng | Phân tích đóng góp và nguyên nhân |
|---|---|---|
| **Purchasing (spot/reserved)** | **$9,284** (Đóng góp lớn nhất) | Đóng góp nhiều nhất vì các job training dài hạn có chi phí cực lớn. Việc chuyển đổi các job training (như `job-train-llm`, `job-train-embed`) sang spot instance kết hợp checkpoint giúp giảm giá giờ thuê tới 40-50%. Các job inference chạy 24/7 được cam kết reserved giúp hưởng chiết khấu 45%. |
| **Inference (cascade/cache/batch)** | **$1,209** | Cascade định tuyến 80% request đơn giản sang model nhỏ (giá rẻ hơn 15 lần). Batch API áp dụng chiết khấu 50% cho các request chạy offline của team `eval`. Caching giảm giá input 90% cho team `assistant` và `rag`. |
| **Right-size util-lies** | **$655** | Phát hiện các GPU đắt đỏ (H100) đang bị lãng phí do chạy tác vụ memory-bound và hạ cấp xuống A100. |
| **Kill idle GPUs** | **$600** | Tắt các GPU không hoạt động (như `gpu-h100-5` bị bỏ trống ban đêm) giúp cắt giảm chi phí lãng phí vô ích. |

---

## 3. Hiện tượng "GPU-Util Lie"

* **Các GPU bị "nói dối" (Util >= 90% nhưng MFU < 30%):**
  * **`gpu-h100-4`** (Util: 98.2%, MFU: 19.4%)
  * **`gpu-a10g-1`** (Util: 96.9%, MFU: 26.8%)
* **Tại sao hiện tượng này xảy ra?**
  * Công cụ `nvidia-smi` truyền thống chỉ đo tỷ lệ thời gian mà các nhân đồ họa (clock) đang bận hoặc có lệnh trong hàng đợi. Nó không phản ánh được mức độ tính toán thực tế của Tensor Cores (đo bằng MFU - Model FLOPs Utilization).
  * Trong các tác vụ decode của LLM hoặc I/O bound, GPU thường xuyên bị "stall" (nghẽn) do phải chờ nạp trọng số từ bộ nhớ HBM (Memory-bandwidth bound). GPU vẫn báo bận 98% nhưng thực chất chỉ chạy ở 19% công suất tính toán tối đa.
* **Tác động tài chính:**
  * NimbusAI đang trả tiền cho cấu hình H100 đắt đỏ ($2.5/giờ) nhưng chỉ nhận lại hiệu năng thực tế tương đương cấu hình A100 ($1.79/giờ) hoặc thấp hơn. Bằng cách hạ cấp (right-sizing) các GPU này xuống dòng thấp hơn phù hợp, công ty đã tiết kiệm được **$655/tháng** mà không ảnh hưởng tới throughput.

---

## 4. Các phần mở rộng đã thực hiện (Extensions)

### Extension 1: Cải thiện chính sách `recommend_tier()`
* **Mô tả:** Thay vì chỉ dựa vào duty cycle đơn thuần, chúng tôi đã đưa vào yếu tố tỷ lệ gián đoạn (interruption rate) đặc thù của từng loại GPU (H100 spot ít bị gián đoạn ~2% hơn so với A10G ~8%). Nếu một job có rủi ro bị ngắt quãng cao (A10G) và chạy cường độ lớn (>18h/ngày), hệ thống sẽ chủ động khuyến nghị dùng reserved để tránh rủi ro mất mát dữ liệu và rework. Đồng thời, hạn chế đề xuất reserved đối với các job ngắn hạn dưới 90 ngày.
* **Đo lường:** Đảm bảo độ ổn định hệ thống cao hơn, giảm số giờ rework của spot instance.

### Extension 3: Tối ưu kinh tế học của Prompt Caching (`cache_is_worth_it`)
* **Mô tả:** Viết hàm `cache_is_worth_it()` để xác định xem việc ghi cache có thực sự mang lại lợi nhuận kinh tế hay không (dựa trên tần suất đọc lại trung bình `avg_cache_reads`). Prompt Caching chỉ được áp dụng khi `avg_cache_reads * (1 - read_discount) > 1.0`.
* **Đo lường:** Áp dụng caching có chọn lọc cho các nhóm `assistant` và `rag` (nơi có hệ thống prompt tĩnh lớn được tái sử dụng nhiều lần), loại bỏ lãng phí ghi cache cho team `search`/`eval`.

### Extension 5: Carbon-Aware Scheduling
* **Mô tả:** Phân tích lượng khí thải carbon của 5 workloads có thể gián đoạn khi chạy ở các vùng cloud khác nhau.
* **Đo lường:**
  * Chuyển các job training sang vùng **`europe-north1`** (Na Uy) giúp giảm lượng phát thải từ **1,606.3 kgCO2e** xuống còn **126.9 kgCO2e** (giảm tới **92.1%** carbon) do vùng này sử dụng năng lượng sạch (thủy điện).
  * Vùng rẻ nhất về giá điện là **`us-east-wa`** ($0.055/kWh), vùng sạch nhất là **`europe-north1`** (30 gCO2/kWh), và vùng cân bằng nhất là **`us-west-2`** ($0.07/kWh, 120 gCO2/kWh).

---

## 5. Khuyến nghị hành động cho NimbusAI

Nếu tôi là FinOps Lead tại NimbusAI, đây là 3 hành động đầu tiên tôi sẽ triển khai:
1. **Thực thi chính sách Tagging & Chargeback ngay lập tức:** Vì tag coverage hiện tại đã đạt **92%** (vượt ngưỡng an toàn 80%), chúng ta có thể chuyển từ Showback sang Chargeback thực tế để buộc các team tự chịu trách nhiệm về chi phí.
2. **Right-size các GPU chạy tác vụ Memory-bound:** Hạ cấp các workload LLM decode đang chạy trên H100 nhưng có MFU thấp xuống A100 hoặc L4.
3. **Thiết lập Carbon-aware / Cost-aware Scheduler:** Tự động lên lịch chạy các job offline (như training, nightly eval) vào các vùng giá rẻ/sạch như `us-east-wa` và `europe-north1` sử dụng Spot Instance và lưu trữ checkpoint định kỳ.
