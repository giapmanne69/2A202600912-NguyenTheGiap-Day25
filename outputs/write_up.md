# Báo cáo Phân tích Tối ưu hóa Chi phí GPU & Trả lời Câu hỏi Lab 25

Báo cáo này chứa toàn bộ kết quả phân tích tối ưu hóa chi phí GPU của **NimbusAI** cùng câu trả lời chi tiết cho tất cả các câu hỏi lý thuyết, thực hành và câu hỏi phụ trong tài liệu hướng dẫn và chấm điểm (Guide, README, Rubric).

---

## Phần 1: Báo cáo Baseline vs. Optimized

* **Tổng chi phí GPU hàng tháng (Baseline vs. Optimized):**
  * **Baseline spend:** $27,133
  * **Optimized spend:** $15,385
  * **Tiết kiệm tổng cộng:** **$11,748** (tương đương giảm **43%** tổng hóa đơn).
* **Đơn vị Unit Economics hàng ngày (Inference $/1M-token):**
  * **Baseline $/1M-token:** $6.488 / 1M tokens
  * **Optimized $/1M-token:** $1.139 / 1M tokens
  * **Tỷ lệ tiết kiệm riêng phần inference:** **82.4%** nhờ áp dụng cascade routing, prompt caching (có chọn lọc) và Batch API.

---

## Phần 2: Phân tích từng đòn bẩy tiết kiệm

| Đòn bẩy (Lever) | Số tiền tiết kiệm hàng tháng | Phân tích đóng góp và nguyên nhân |
|---|---|---|
| **Purchasing (spot/reserved)** | **$9,284** (Đóng góp lớn nhất) | Đóng góp nhiều nhất vì các job training dài hạn có chi phí cực lớn. Việc chuyển đổi các job training (như `job-train-llm`, `job-train-embed`) sang spot instance kết hợp checkpoint giúp giảm giá giờ thuê tới 40-50%. Các job inference chạy 24/7 được cam kết reserved giúp hưởng chiết khấu 45%. |
| **Inference (cascade/cache/batch)** | **$1,209** | Cascade định tuyến 80% request đơn giản sang mô hình nhỏ (`small`). Batch API áp dụng chiết khấu 50% cho các request chạy offline của team `eval`. Caching giảm giá input 90% cho team `assistant` và `rag`. |
| **Right-size util-lies** | **$655** | Phát hiện các GPU đắt đỏ (H100) đang bị lãng phí do chạy tác vụ memory-bound và hạ cấp xuống A100. |
| **Kill idle GPUs** | **$600** | Tắt các GPU không hoạt động (như `gpu-h100-5` bị bỏ trống ban đêm) giúp cắt giảm chi phí lãng phí vô ích. |

---

## Phần 3: Hiện tượng "GPU-Util Lie"

* **Các GPU bị "nói dối" (Util >= 90% nhưng MFU < 30%):**
  * **`gpu-h100-4`** (Util: 98.2%, MFU: 19.4%)
  * **`gpu-a10g-1`** (Util: 96.9%, MFU: 26.8%)
* **Tại sao hiện tượng này xảy ra?**
  * Công cụ `nvidia-smi` truyền thống chỉ đo tỷ lệ thời gian mà các nhân đồ họa (clock) đang bận hoặc có lệnh trong hàng đợi. Nó không phản ánh được mức độ tính toán thực tế của Tensor Cores (đo bằng MFU - Model FLOPs Utilization).
  * Trong các tác vụ decode của LLM hoặc I/O bound, GPU thường xuyên bị "stall" (nghẽn) do phải chờ nạp trọng số từ bộ nhớ HBM (Memory-bandwidth bound). GPU vẫn báo bận 98% nhưng thực chất chỉ chạy ở 19% công suất tính toán tối đa.
* **Tác động tài chính:**
  * NimbusAI đang trả tiền cho cấu hình H100 đắt đỏ ($2.5/giờ) nhưng chỉ nhận lại hiệu năng thực tế tương đương cấu hình A100 ($1.79/giờ) hoặc thấp hơn. Bằng cách hạ cấp (right-sizing) các GPU này xuống dòng thấp hơn phù hợp, công ty đã tiết kiệm được **$655/tháng** mà không ảnh hưởng tới throughput.

---

## Phần 4: Các phần mở rộng đã thực hiện (Extensions)

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

## Phần 5: Khuyến nghị hành động cho NimbusAI

Nếu tôi là FinOps Lead tại NimbusAI, đây là 3 hành động đầu tiên tôi sẽ triển khai:
1. **Thực thi chính sách Tagging & Chargeback ngay lập tức:** Vì tag coverage hiện tại đã đạt **92%** (vượt ngưỡng an toàn 80%), chúng ta có thể chuyển từ Showback sang Chargeback thực tế để buộc các team tự chịu trách nhiệm về chi phí.
2. **Right-size các GPU chạy tác vụ Memory-bound:** Hạ cấp các workload LLM decode đang chạy trên H100 nhưng có MFU thấp xuống A100 hoặc L4.
3. **Thiết lập Carbon-aware / Cost-aware Scheduler:** Tự động lên lịch chạy các job offline (như training, nightly eval) vào các vùng giá rẻ/sạch như `us-east-wa` và `europe-north1` sử dụng Spot Instance và lưu trữ checkpoint định kỳ.

---

## Phần 6: Trả lời câu hỏi chi tiết từ Guide.md

### 1. Câu hỏi về Mission 1 (Kiểm toán hiệu quả GPU)
* **GPU nào có `GPU-Util` cao nhất? MFU của nó là bao nhiêu?**
  * GPU có `GPU-Util` cao nhất là `gpu-h100-4` với mức sử dụng báo cáo là **98.2%**. Tuy nhiên, hiệu quả tính toán thực tế (**MFU**) của nó chỉ đạt **19.4%** (rất thấp).
* **Lãng phí idle tính ra bao nhiêu/tháng? Chiếm bao nhiêu % tổng chi phí?**
  * Lãng phí do GPU trống (Idle waste) đạt **$20/ngày**, tương đương **$600/tháng**. Chiếm khoảng **3.9%** tổng chi phí tối ưu hóa.

### 2. Câu hỏi về Mission 2 (Đòn bẩy chi phí Inference)
* **Tại sao `discount_stack(batch=True, cache_hit_frac=1.0) = 0.05`?**
  * Các loại chiết khấu này có tính chất **nhân dồn** (multiplicative). Khi `cache_hit_frac = 1.0`, chi phí input chỉ còn `0.10` (chiết khấu 90%). Khi áp dụng tiếp Batch API (`batch = True`), chi phí giảm tiếp 50% (`0.50`). 
  * Công thức: $0.10 \times 0.50 = 0.05$ (tức là chỉ phải trả 5% giá gốc, tương đương tiết kiệm 95%).
* **Khi nào không nên dùng Batch API?**
  * Không nên dùng Batch API đối với các ứng dụng yêu cầu thời gian phản hồi thực tế (Real-time / Interactive) như Chatbot trò chuyện trực tiếp, autocomplete, vì Batch API thường có độ trễ lớn (latency từ vài phút đến 24 giờ).

### 3. Câu hỏi về Mission 3 (Chiến lược mua GPU)
* **Job nào được đề xuất dùng Spot? Tại sao?**
  * Các job training offline như `job-train-llm`, `job-train-embed`, `job-finetune` được đề xuất dùng Spot. Vì các job này có thể gián đoạn (`interruptible = 1`) và hệ thống có cơ chế lưu checkpoint để khôi phục công việc mà không sợ mất mát dữ liệu khi bị thu hồi tài nguyên.
* **Với Spot, "effective hours" cao hơn "job hours" thực tế — điều này nghĩa là gì?**
  * "Effective hours" (số giờ chạy thực tế) cao hơn là do tính thêm **thời gian rework** (chạy lại phần việc bị mất kể từ checkpoint gần nhất khi GPU bị thu hồi) và **overhead** (thời gian hệ thống ghi/đọc checkpoint định kỳ).

### 4. Câu hỏi về Mission 4 (Phân bổ chi phí)
* **Team nào tốn nhiều nhất? Tỷ lệ so với tổng là bao nhiêu?**
  * Team **assistant** tiêu tốn nhiều nhất với **$2.59/ngày**, chiếm khoảng **30.5%** tổng chi phí phân bổ.
* **Tag coverage là bao nhiêu %? Có đủ để chargeback không?**
  * Tag coverage đạt **92%**. Mức này hoàn toàn **đủ điều kiện để thực hiện chargeback** (ngưỡng an toàn tối thiểu là 80%).
* **Tại sao chuẩn FOCUS lại quan trọng khi công ty dùng nhiều cloud provider?**
  * FOCUS (FinOps Open Cost & Usage Specification) cung cấp một định dạng dữ liệu hóa đơn chung, chuẩn hóa các thuật ngữ và cột dữ liệu (như `BilledCost`, `BillingAccountId`, `ProviderName`) giữa AWS, Azure, GCP và các nhà cung cấp GPU Cloud chuyên dụng. Điều này giúp đội FinOps hợp nhất dữ liệu chi phí dễ dàng mà không cần viết các parser riêng cho từng cloud.

---

## Phần 7: Câu hỏi kiểm tra hiểu biết (Oral Check từ Rubric.md)

### 1. "GPU-Util 98% có nghĩa là GPU đang làm việc hiệu quả không? Tại sao?"
* **Không.** GPU-Util chỉ đo xem các clock của GPU có đang bận xử lý hay không. Nếu GPU bị stall do I/O, CPU nghẽn cổ chai hoặc chờ dữ liệu từ RAM/HBM (memory-bandwidth bound), GPU-Util vẫn báo 98% nhưng Tensor Cores (nhân tính toán LLM) hoàn toàn không chạy, dẫn đến hiệu suất tính toán thực tế (MFU) cực kỳ thấp (~20%).

### 2. "Tại sao cần >= 80% tag coverage mới dám chargeback?"
* Nếu tag coverage thấp (ví dụ 50%), một nửa số tiền hóa đơn sẽ là "vô chủ" (untagged). Khi thực hiện chargeback (trừ tiền trực tiếp vào ngân sách của các team), việc phân bổ bừa bãi phần chi phí vô chủ này sẽ dẫn đến sự bất công, gây tranh cãi giữa các phòng ban và làm mất lòng tin vào hệ thống FinOps. Ngưỡng $\ge 80\%$ đảm bảo phần lớn chi phí đã được xác thực chính xác.

### 3. "Nếu công ty bạn có 70% workload interruptible, bạn sẽ tối ưu purchasing như thế nào?"
* Tôi sẽ áp dụng mô hình **Spot-First**. Thuê khoảng 60% Spot Instance cho các job training/batch và thiết lập hệ thống ghi checkpoint tự động thật tối ưu (ví dụ mỗi 30 phút). 10% còn lại của phần interruptible và toàn bộ spiky workload sẽ được bù đắp bằng các nhóm Reserved có thời hạn ngắn (1-year) hoặc On-demand để đảm bảo tính ổn định tối thiểu.

### 4. "Đo bằng $/GPU-hr vs $/1M-token — khi nào con số này cho kết quả trái ngược nhau?"
* Khi ta nâng cấp từ GPU dòng cũ (như A10G giá $1.0/giờ) lên GPU siêu cấp (H100 giá $2.5/giờ). 
  * Nhìn theo **`$/GPU-hr`**, chi phí tăng lên **2.5 lần** (trông có vẻ lãng phí).
  * Nhưng vì H100 xử lý nhanh hơn 10 lần nhờ kiến trúc Tensor Core và băng thông lớn, nó phục vụ được lượng token gấp 10 lần trong cùng một giờ. Do đó, **`$/1M-token`** của H100 sẽ rẻ hơn đáng kể so với A10G.

### 5. "Tại sao LLM decode là memory-bound còn prefill là compute-bound?"
* **Prefill Phase (Input):** LLM xử lý toàn bộ prompt đầu vào cùng lúc, thực hiện các phép nhân ma trận song song cực lớn trên toàn bộ token đầu vào. Tỷ lệ số phép tính (FLOPs) trên mỗi byte dữ liệu tải từ bộ nhớ rất cao $\rightarrow$ **Compute-bound**.
* **Decode Phase (Output):** LLM sinh từng token một cách tuần tự (autoregressive). Với mỗi token mới sinh ra, nó bắt buộc phải load toàn bộ trọng số mô hình (weights) và KV Cache từ bộ nhớ HBM lên các thanh ghi đăng ký của GPU chỉ để tính toán cho đúng 1 token đó $\rightarrow$ Tỷ lệ tính toán/byte nạp cực thấp $\rightarrow$ **Memory-bandwidth bound**.

---

## Phần 8: Câu hỏi phụ từ các phần mở rộng (Extensions)

### 1. Extension 1: "Savings thay đổi như thế nào? Tại sao policy mới cho kết quả khác?"
* **Thay đổi:** Tổng chi phí tối ưu hóa tăng nhẹ từ $14,626 (phương án cũ) lên **$15,385** (phương án mới).
* **Nguyên nhân:** Chính sách mới hoạt động an toàn và thực tế hơn. Nó phát hiện ra job `job-infer-chat` chạy trên `A10G` là tác vụ có rủi ro bị gián đoạn rất cao (spot interruption rate $\ge 8\%$) và chạy với duty cycle cao ($24/24$). Chạy Spot ở đây sẽ khiến hệ thống liên tục bị sập và mất thời gian phục hồi KV Cache, do đó chính sách mới đã chủ động đề xuất chuyển sang **Reserved** thay vì Spot. Sự tăng chi phí này là cần thiết để bảo vệ chất lượng dịch vụ (SLA).

### 2. Extension 2: "Tại sao không chỉ chọn GPU rẻ nhất theo $/GPU-hr?"
* Vì GPU rẻ nhất theo `$/GPU-hr` (ví dụ L4 giá $0.8/giờ) có dung lượng VRAM và băng thông bộ nhớ (peak bandwidth) rất hạn chế. Nếu chạy các mô hình lớn hoặc Batch size lớn trên L4, thời gian xử lý sẽ bị kéo dài gấp nhiều lần hoặc bị tràn bộ nhớ (Out of Memory - OOM), khiến tổng chi phí trên 1 triệu token (`$/1M-token`) cuối cùng đắt hơn nhiều so với việc thuê một GPU H100 đắt tiền nhưng hoàn thành công việc nhanh chóng.

### 3. Extension 3: "Cần đọc lại bao nhiêu lần để cache có lợi? Dataset của chúng ta có đạt ngưỡng này không?"
* Theo công thức tính toán: $avg\_cache\_reads \times (1 - read\_discount) > 1.0$. Với `read_discount = 0.10` ( Anthropic Prompt Caching giảm giá 90%), ta cần:
  $$avg\_cache\_reads > \frac{1.0}{0.90} \approx 1.11 \text{ lần}$$
* **Dataset của chúng ta:** Đạt ngưỡng đối với các nhóm `assistant` (chat) và `rag` (đọc tài liệu) do các nhóm này sử dụng chung hệ thống prompt tĩnh/văn bản hướng dẫn dài lặp đi lặp lại ($avg\_cache\_reads \approx 5.0$). Ngược lại, các tác vụ tìm kiếm (`search`) và đánh giá (`eval`) có prompt thay đổi liên tục ($avg\_cache\_reads \approx 0.5$) nên không đạt ngưỡng và không được hệ thống áp dụng cache.

### 4. Extension 4: "Reasoning traffic chiếm bao nhiêu % tổng? Tại sao nó lại tốn năng lượng ~80× nhiều hơn?"
* **Tỷ lệ traffic:** Reasoning traffic chiếm khoảng **25%** tổng lượng request trong nhóm `eval` (tập trung ở team eval).
* **Lý do tiêu thụ điện gấp 80 lần:** Mô hình reasoning (như OpenAI o1/o3, DeepSeek-R1) sinh ra một lượng rất lớn các token suy nghĩ nội bộ (Chain-of-Thought) ẩn trước khi đưa ra câu trả lời cuối cùng. Số lượng token thực tế xử lý trong quá trình suy nghĩ này lớn gấp hàng chục đến hàng trăm lần so với số token output hiển thị cho người dùng, dẫn đến thời gian GPU hoạt động hết công suất lâu hơn $\rightarrow$ Tiêu tốn năng lượng vượt trội.

### 5. Extension 5: "Vùng nào là 'tối ưu' thực sự? Phụ thuộc vào ưu tiên nào của công ty?"
* **Vùng tối ưu thực sự phụ thuộc vào chiến lược của doanh nghiệp:**
  * **Ưu tiên Chi phí tối đa:** Chọn **`us-east-wa`** với giá điện rẻ nhất ($0.055/kWh).
  * **Ưu tiên Carbon thấp nhất:** Chọn **`europe-north1`** (Na Uy) với nguồn điện thủy điện sạch (chỉ phát thải 30 gCO2/kWh, giảm 92% carbon).
  * **Ưu tiên Cân bằng (SLA + Green):** Chọn **`us-west-2`** (Oregon) với giá điện trung bình thấp ($0.07/kWh) và nguồn điện tương đối sạch (120 gCO2/kWh từ thủy điện sông Columbia). Vùng này vẫn gần thị trường Mỹ hơn Na Uy, đảm bảo độ trễ (latency) thấp cho khách hàng.
