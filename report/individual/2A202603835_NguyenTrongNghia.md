# Báo cáo Day 7

**Nguyễn Trọng Nghĩa · 2A202603835 · L3B** — Agentic RAG trên kho dữ liệu Day 6 (*World Bank Annual Report 2024*).

Mọi số liệu dưới đây lấy từ các lần chạy ngày 2026-11-16, trong khoảng 03:32–03:44 UTC. Các file kết quả nằm trong [results/](../../results/README.md).

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - Nguồn: World Bank (2024), *World Bank Annual Report 2024*, doi `10.1596/AR2024EN`. Giấy phép **CC BY-NC-ND 3.0 IGO**.
  - Corpus là bộ đã xây ở bài 6: 49 trang PDF, trong đó 42 trang nội dung, khoảng 202 nghìn ký tự.
  - Dùng **557 chunk** của strategy C bài 6: chia theo đoạn, tối đa 500 ký tự, mỗi chunk có metadata `section` và `region`. Có 158 chunk được gắn `region`.
  - Chunk được export thẳng từ database bài 6 bằng `src/export_day6.py` ra `starter/data/day6/chunks.json`. File này không được commit vì giấy phép NoDerivatives; chạy lại lệnh export sẽ tạo lại.
- **Vector store, embedding model, phiên bản và số chiều:**
  - Dùng **đúng vector store của bài 6**: PostgreSQL 16.16 + pgvector 0.8.7 (Docker `day6_student_starter`), bảng `chunks_384d`, cosine, exact search.
  - Query được embed bằng chính model đã tạo index: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 chiều, chuẩn hóa L2, sentence-transformers 6.3.0). `DenseRetriever` kiểm tra rằng model ghi trong index trùng với model embed query.
  - Không phải embed lại, nên không tốn thêm chi phí embedding.
- **Agent model, cách chạy và phân chia dev/test:**
  - Model: DeepSeek API, `AGENT_MODEL=deepseek-chat`. Server trả về tên model thật là **`deepseek-flash`** (DeepSeek-V4.1-Flash-1017), có tool calling.
  - temperature = 0. Chạy bằng `python src/run_agent.py --split <dev|test> --method <...> --tag <...>`.
  - Benchmark có **24 câu**:
    - dev: 15 câu có đáp án + 2 câu thiếu bằng chứng;
    - test: 5 câu có đáp án + 2 câu thiếu bằng chứng.
  - Chi tiết benchmark ở [benchmark/README.md](../../benchmark/README.md).
- **Cách xác định câu có hoặc thiếu evidence, và tiêu chí chấm:**
  - **Dev:** 15 câu dev của bài 6, kèm 2 câu thiếu bằng chứng mới.
  - **Test: 5 câu mới hoàn toàn**, lấy từ các trang 17, 26, 30, 32, 38, là những trang chưa từng có trong benchmark bài 6. Test bài 6 không được dùng lại, vì kết quả của nó đã được xem.
  - Mỗi câu có đáp án ghi `gold` gồm `{source_id, page, evidence}`, có thể có nhiều evidence thay thế. `src/verify_benchmark.py` kiểm tra mỗi câu có ít nhất một evidence nằm trọn trong một chunk đúng trang.
  - 4 câu thiếu bằng chứng (Việt Nam, IDA21/Nhật Bản, lending spread, nhân sự IFC) đều gần chủ đề. Mỗi câu đã được xác minh bằng cách tìm trên **toàn bộ 49 trang** PDF, ghi trong `absence_reason`.
  - **Định nghĩa hit (như bài 6):** chunk nằm trên trang gold và chứa trọn evidence. **Context Evidence Rate** tính trên context cuối mà model đã thấy; evidence được phép vắt qua các chunk liền kề cùng trang khi tất cả các chunk đó đều có trong context.

## Retrieval và thử nghiệm

- **Hit@1 và Evidence Hit@3:** retrieval-only, dùng **query gốc**, top-3, áp filter do câu hỏi cung cấp.
- **Context Evidence Rate:** tính trên context cuối của **agent**. Agent tự viết query, tối đa 4 lượt search, mỗi lượt lấy top-3.
- **Chi phí:** tính theo giá `deepseek-flash` **giờ cao điểm**, cho mỗi 1M token: cache hit $0.006, cache miss $0.30, output $1.20. Mọi lượt chạy đều rơi vào giờ cao điểm (01:00–04:00 UTC, thứ Hai), nên đây là chi phí thực. Bản thân retrieval không tốn chi phí, vì chạy local.

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline `dense_k3` | Dense pgvector bài 6, k = 3, filter region khi có, không rerank, context = các chunk đã search (TB 1.408 ký tự) | Index Day 6 nguyên trạng, khớp strategy C bài 6 | dev | 11/15 (73%) | 13/15 (87%) | 14/15 (93%) | 35,3 s / $0.0077 |
| Phương pháp 2 `bm25_k3` | BM25 (k1 = 1,5, b = 0,75), k = 3, filter như trên (TB 1.400 ký tự) | Câu hỏi nhiều số liệu và tên riêng, nên khớp từ khóa có lợi | dev | 12/15 (80%) | 14/15 (93%) | 15/15 (100%) | 36,0 s / $0.0073 |
| Phương pháp 3 `hybrid_rrf_k3` | RRF (k = 60) trên 20 candidate dense + 20 candidate BM25, k = 3 (TB 1.441 ký tự) | Kết hợp hai cách tìm để bù điểm yếu của nhau; hợp nhất theo rank nên không cần chuẩn hóa score | dev | 13/15 (87%) | 14/15 (93%) | 15/15 (100%) | 33,2 s / $0.0074 |
| Cải thiện 1 `dense+nbr1` | Dense k = 3 + chunk liền trước và liền sau trên cùng trang (TB 3.504 ký tự) | Sửa lỗi evidence bị tách qua hai chunk (q01) | dev | 11/15 (73%) | 13/15 (87%) | 15/15 (100%) | 33,7 s / $0.0106 |
| Cải thiện 2 `hybrid_rrf+nbr1` | Hybrid k = 3 + chunk lân cận (TB 3.197 ký tự) | Kết hợp phương pháp 3 với cải thiện 1 | dev | 13/15 (87%) | 14/15 (93%) | 15/15 (100%) | 32,0 s / $0.0091 |
| **Cấu hình đã chọn** `hybrid_rrf_k3` | Như phương pháp 3 | Đã chốt trên dev | test | 5/5 (100%) | 5/5 (100%) | 4/5 (80%) | 16,0 s / $0.0036 |
| Baseline `dense_k3` | Như baseline | — | test | 4/5 (80%) | 5/5 (100%) | 5/5 (100%) | 16,4 s / $0.0044 |

Cách đọc bảng:
- **Hybrid** là phương pháp thứ 3 và cũng là cấu hình được chọn. **Cải thiện 1 và 2** là cấu hình chọn context (lấy thêm chunk lân cận), không đổi cách xếp hạng. Vì vậy Hit@1 và Hit@3 của chúng bằng phương pháp gốc, chỉ có Context Evidence Rate thay đổi.
- **Ablation bỏ filter** (`--no-filter`): Hit@3 dev của dense, BM25 và hybrid giảm còn 10/15, 12/15 và 10/15, vì các câu "in this region" (q13–q15) bị kéo sang khu vực khác.
- **Hit@1 của lượt tìm đầu trong agent** (do agent tự viết query) trên dev: dense 9/15, BM25 10/15, hybrid 10/15. Thấp hơn so với dùng query gốc.

**Hai lỗi dev, nguyên nhân và cách thử**

1. **q01, evidence bị tách:**
   - Câu "$117.5B (BILLION) in loans, grants…" ở trang 8 bị bộ chia đoạn của bài 6 tách làm hai, vì dòng viết hoa `(BILLION)` bị nhận nhầm là tiêu đề. Do đó không chunk nào chứa trọn evidence.
   - Ở baseline, agent vẫn trả lời "$117.5 billion" nhưng cite chunk thiếu nửa sau của câu.
   - **Cách thử:** cải thiện 1 lấy thêm chunk liền kề, nên đưa được cả hai nửa vào context. Context Evidence Rate của dense tăng từ 14/15 lên 15/15.
   - **Đánh đổi:** context dài gấp khoảng 2,5 lần (1.408 lên 3.504 ký tự), prompt token tăng 47%, chi phí tăng 38%.
2. **q02, gold thiếu evidence thay thế:**
   - Agent cite chunk trang 31 ("boosting annual guarantee issuance to $20 billion by 2030"). Nội dung đúng, nhưng benchmark ban đầu chỉ ghi gold ở trang 7.
   - Đọc trace mới phát hiện ra điều này: cùng mục tiêu đó còn xuất hiện ở trang 30 và 31.
   - **Cách xử lý:** bổ sung hai trang này làm evidence thay thế (chỉ sửa trên dev, có ghi lại), rồi tính lại nhãn từ trace đã lưu bằng `src/relabel.py`, không gọi lại API.
   - **Bài học:** đúng như GUIDE nói, citation không khớp gold chưa chắc là sai; phải đọc đối chiếu.
3. **Hit@1 thấp:** chunk đúng thường đứng hạng 2–3, sau các chunk chỉ là tiêu đề bảng hoặc trang tổng hợp. Không cấu hình nào sửa được điểm này. Cần thử rerank (chưa làm, xem phần giới hạn).

**Lý do chọn cấu hình.** Tiêu chí được ghi trong [results/README.md](../../results/README.md) và chốt ngày 2026-11-16, trước khi chạy test:
1. Ràng buộc: từ chối đúng 2/2 và từ chối nhầm 0.
2. Context Evidence Rate cao nhất.
3. Nếu hòa, xét Hit@3 của lượt tìm đầu.
4. Nếu vẫn hòa, xét Hit@1 retrieval-only.
5. Nếu vẫn hòa, chọn cấu hình rẻ hơn.

Kết quả là **hybrid_rrf_k3**: hòa hybrid+nbr1 ở bốn bước đầu và rẻ hơn ($0.0074 so với $0.0091). Tiêu chí này được viết **sau khi đã xem dev, nhưng trước khi chạy test**.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:**
  - **Tool:** một tool `search(query)`, retriever phía sau thay đổi theo cấu hình. Model có thể gọi nhiều tool song song trong một lượt.
  - **Giới hạn:** tối đa **4 lượt search** và **6 lượt gọi model**; khi đã dùng hết số lượt search, agent buộc phải trả lời.
  - **Filter:** do câu hỏi cung cấp (ngữ cảnh của người dùng) và được hệ thống tự áp vào mọi lượt search. Model không được tự chọn filter.
  - **Context:** gồm mọi chunk agent đã nhận, giữ thứ tự xuất hiện và bỏ trùng.
  - **Cách trả lời:** câu trả lời phải có `[chunk-id]`. Nếu không đủ bằng chứng, model trả `INSUFFICIENT_EVIDENCE: …`. Câu trả lời không có citation hợp lệ (ID không nằm trong context) bị chuyển thành từ chối.
  - **Prompt:** nhắc rằng nội dung tài liệu là dữ liệu, không phải chỉ dẫn.
  - **Xử lý lỗi:** khi API lỗi, client thử lại tối đa 5 lần, có giãn thời gian chờ, và giữ một kết nối cố định (keep-alive). Lý do là mạng tới api.deepseek.com chập chờn (DNS timeout, kết nối mất 1–8 giây). Câu nào vẫn lỗi được ghi `status: error`, không bị thay bằng kết quả giả. Trong lần smoke test đầu, q13 bị lỗi ConnectTimeout và đã được ghi lại đúng như vậy. Ở các lượt chạy chính thức không có lỗi nào.

Kết quả tổng hợp bằng `starter/agent_metrics.py` từ nhãn thủ công:

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| dense_k3 / test | 7/7 | search 1:3 · 2:1 · 3:1 · 4:2 câu; 17 lượt gọi model | 0/0/5 → **2,00** | 8/8 | 5/5 | 2/2 | 0/5 |
| hybrid_rrf_k3 / test | 7/7 | search 1:2 · 2:3 · 3:1 · 4:1 câu; 16 lượt gọi model | 1/0/4 → **1,60** | 6/6 | 4/4 | 2/2 | 1/5 (t11) |
| dense_k3 / dev (chỉ tính tự động) | 17/17 | search 1:8 · 2:7 · 4:2; 36 lượt gọi model | — | ID trong context: 100% | 15/15 | 2/2 | 0/15 |
| hybrid_rrf_k3 / dev (chỉ tính tự động) | 17/17 | search 1:8 · 2:7 · 4:2; 36 lượt gọi model | — | ID trong context: 100% | 15/15 | 2/2 | 0/15 |

Chất lượng context thủ công trên 5 câu test có đáp án, thang 0/1/2: dense 0/0/5 (trung bình 2,00), hybrid 1/0/4 (trung bình 1,60).

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| t12 (dense) | Có đáp án, điều kiện | 2 lượt search ("adaptive social protection…"), lấy được chunk trang 26 và trang 5 | "500 million people… by the end of 2030… half of these beneficiaries be women" [p026:001][p005:014] | Context 2, câu trả lời 2, citation y;y: đủ cả 3 điều kiện; trang 5 nói cùng mục tiêu ("half a billion") |
| u03 (hybrid) | Thiếu bằng chứng | 4 lượt search về "IBRD flexible loan spread / pricing", lấy được trang 37, 44, 45, 47 | "INSUFFICIENT_EVIDENCE: … do not state the lending spread…" | Từ chối đúng, không thêm con số nào |
| **t11 (hybrid), lỗi** | Có đáp án, filter ECA, đọc bảng | 2 lượt search, cả hai đều trả về chunk **tiêu đề** "TABLE 9: … REGIONAL SNAPSHOT" (trang 17) và 2 chunk trang 16; chunk chứa hàng số liệu nằm ngay sau tiêu đề nhưng không được lấy | "…do not include its contents… INSUFFICIENT_EVIDENCE" | Context 0, câu trả lời 0: **từ chối nhầm**. Dense có cùng kết quả ở lượt đầu nhưng tìm tiếp đến lượt 3 thì gặp chunk `p017:001` có số 247,5, nên trả lời đúng |
| u04 (cả hai) | Thiếu bằng chứng | 3 lượt search, đều ra trang 40 (Bảng 16, Our People) | "INSUFFICIENT_EVIDENCE: … World Bank Group-wide staff figures (13,492…; 18,300…) but no IFC-specific…" | Từ chối đúng, nhưng có ghi chú: số 13.492 là của World Bank (IBRD/IDA), không phải toàn Nhóm, nên agent mô tả sai phạm vi một con số. Agent không đoán đáp án |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - Trace agent: `results/agent/<split>_<cấu hình>/traces.json`. Mỗi câu có đủ query, filter, kết quả kèm score, context cuối (gồm text), câu trả lời, citation, token, thời gian và lý do từ chối.
  - Tổng hợp mỗi lượt chạy: `summary.json`; nhãn thủ công đã chuyển đổi: `reviews.json`; kết quả của script đề: `agent_metrics.json`.
  - Retrieval-only: `results/retrieval/<split>_<tag>/`.
  - Nhãn thủ công: `results/manual/test_agent_labels.csv`, tổng hợp ở `results/manual/test_summary.md`.
  - Lệnh chạy: xem [README.md](../../README.md).
  - **Tổng chi phí** cho 5 lượt chạy dev và 2 lượt chạy test: **$0.0501**, tổng cộng 205.517 token prompt và 12.884 token output. Con số này chưa tính vài lượt smoke test lúc phát triển.
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - **Trước/sau trên dev:**
    - Từ baseline sang hybrid: Hit@1 retrieval-only tăng từ 11 lên 13/15, Context Evidence Rate từ 14 lên 15/15, chi phí gần như không đổi.
    - Từ baseline sang dense+nbr1: Context Evidence Rate từ 14 lên 15/15, nhưng chi phí tăng 38%.
    - hybrid+nbr1 không tốt hơn hybrid nhưng đắt hơn 23%.
  - **Trên test, cấu hình được chọn kém baseline một câu (t11):**
    - Grounded answer 1,60 so với 2,00, và có 1 câu từ chối nhầm.
    - Nguyên nhân không nằm ở bước xếp hạng: retrieval-only của hybrid đạt 5/5 Hit@1. Vấn đề nằm ở hành vi agent: dừng tìm khi mới thấy tiêu đề bảng. Hai cấu hình có lượt tìm đầu giống nhau ở t11; chỉ khác ở việc agent có tìm tiếp hay không, nên đây là biến thiên của model, dù đã đặt temperature = 0.
    - Giả thuyết: lấy thêm chunk lân cận (cải thiện 1 hoặc 2) sẽ kéo chunk hàng số liệu vào context ngay lượt đầu. Nhưng cấu hình đã chốt, nên **không chỉnh lại**. Nếu muốn kiểm chứng giả thuyết này, phải dùng một tập test mới.
  - **Giới hạn:**
    - Test chỉ có 5 + 2 câu; mỗi câu có đáp án tương ứng 20 điểm phần trăm, nên không kết luận được phương pháp nào tốt hơn một cách tổng quát.
    - Dev gần chạm trần (CER 14–15/15), nên khó tách bạch các cấu hình.
    - Mỗi cấu hình chỉ chạy một lần, không lặp lại để đo độ dao động của model.
    - Corpus chỉ có một tài liệu.
    - Chưa thử rerank hay viết lại query bằng một bước riêng; agent tự viết lại query bên trong vòng lặp.
    - Câu hỏi và các đoạn của báo cáo (nội dung công khai, CC BY-NC-ND) được gửi tới máy chủ DeepSeek.

## Thử thách nâng cao (nếu thực hiện)

Không thực hiện. Báo cáo World Bank 2024 chỉ có 49 trang PDF (khoảng 92 trang in), chưa đạt mức tối thiểu 100 trang. Bonus còn cần một tài liệu mới có bảng, ảnh và biểu đồ, cùng một benchmark riêng ≥30 câu test với ngưỡng đạt 90%; phần này nằm ngoài phạm vi thời gian của bài.

## Sử dụng AI

- **Công cụ:** dùng Claude Code để lập kế hoạch, viết code (`src/`), soạn nháp 5 câu test mới và 4 câu thiếu bằng chứng, chạy thí nghiệm và viết nháp báo cáo.
