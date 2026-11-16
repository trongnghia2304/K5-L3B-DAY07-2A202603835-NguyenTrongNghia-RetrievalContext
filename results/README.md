# Kết quả Day 7

## Điều kiện chung (mọi cấu hình)

- **Corpus:** 557 chunk của strategy C bài 6.
- **Dense retrieval:** pgvector 0.8.7, bảng `chunks_384d`, embedding `paraphrase-multilingual-MiniLM-L12-v2` (384 chiều), cosine, exact search.
- **BM25:** `rank-bm25` 0.2.2 (k1 = 1,5, b = 0,75), tách từ thành token chữ và số, có bỏ stopword.
- **Hybrid:** RRF với k = 60, mỗi retriever lấy 20 candidate.
- **Filter:** chỉ dùng `filter` do câu hỏi cung cấp (q13–q15 ở dev), hệ thống tự áp vào mọi lượt search. Không dùng gold.
- **Agent:** `deepseek-chat`, server trả về tên model thật là `deepseek-flash` (DeepSeek-V4.1-Flash-1017). temperature = 0, tối đa 4 lượt search và 6 lượt gọi model. Mỗi lượt search lấy top-3; câu trả lời có `[chunk-id]` hoặc `INSUFFICIENT_EVIDENCE`.
- **Chi phí:** tính theo giá cao điểm của `deepseek-flash`, tức là mức trần (ngoài giờ cao điểm chỉ bằng một nửa). Cache hit $0.006, cache miss $0.30, output $1.20, tính trên mỗi 1M token. Nguồn: https://api-docs.deepseek.com/quick_start/pricing, xem ngày 2026-11-16.
- **Định nghĩa hit (như bài 6):** chunk nằm trên trang gold **và** chứa trọn evidence của một trong các gold thay thế.
- **Context Evidence Rate:** tính trên context cuối mà model đã thấy. Evidence được phép nằm vắt qua các chunk liền kề cùng trang, miễn là tất cả các chunk đó đều có trong context.

## Dev: retrieval-only (query gốc, top-3, không gọi LLM)

Lệnh chạy: `python src/eval_retrieval.py --split dev --methods dense,bm25,hybrid_rrf,dense+nbr1,hybrid_rrf+nbr1 --budget 100000 --tag filter_unbudgeted`

| Phương pháp | Hit@1 | Evidence Hit@3 | Context có evidence | Trượt @3 |
|---|---|---|---|---|
| dense (baseline, giống strategy C bài 6) | 11/15 | 13/15 | 13/15 | q01, q02 |
| bm25 | 12/15 | 14/15 | 14/15 | q01 |
| hybrid_rrf | 13/15 | 14/15 | 14/15 | q01 |
| dense+nbr1 | 11/15 | 13/15 | 14/15 | q01, q02 |
| hybrid_rrf+nbr1 | 13/15 | 14/15 | 15/15 | q01 |

Khi bỏ filter (`--no-filter`), dense, bm25 và hybrid chỉ còn Hit@3 lần lượt 10/15, 12/15 và 10/15: các câu filter q13–q15 bị kéo sang khu vực khác.

## Dev: agent (17 câu = 15 có đáp án + 2 thiếu bằng chứng)

| Cấu hình | Giả thuyết | Hit@1 lượt tìm đầu | Hit@3 lượt tìm đầu | Context Evidence Rate | Từ chối đúng | Từ chối nhầm | Số lượt search (số câu) | Ký tự context TB | Token (prompt + output) | Chi phí ≤ | Thời gian |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dense_k3 (**baseline**) | Index bài 6 | 9/15 | 14/15 | 14/15 | 2/2 | 0/15 | 1:8, 2:7, 4:2 | 1.408 | 30.008 + 2.212 | $0.0077 | 35,3 s |
| bm25_k3 (phương pháp 2) | Câu hỏi nhiều số liệu và tên riêng, nên khớp từ khóa có lợi | 10/15 | 13/15 | 15/15 | 2/2 | 0/15 | 1:7, 2:8, 3:1, 4:1 | 1.400 | 30.532 + 2.234 | $0.0073 | 36,0 s |
| hybrid_rrf_k3 (phương pháp 3) | Gộp hai cách tìm để bù điểm yếu của nhau | 10/15 | 14/15 | 15/15 | 2/2 | 0/15 | 1:8, 2:7, 4:2 | 1.441 | 30.284 + 2.157 | $0.0074 | 33,2 s |
| dense+nbr1 (cải thiện 1) | Thêm chunk lân cận để sửa lỗi evidence bị tách ở q01 | 9/15 | 14/15 | 15/15 | 2/2 | 0/15 | 1:8, 2:8, 4:1 | 3.504 | 44.245 + 2.182 | $0.0106 | 33,7 s |
| hybrid_rrf+nbr1 (cải thiện 2) | Kết hợp hybrid với chunk lân cận | 10/15 | 14/15 | 15/15 | 2/2 | 0/15 | 1:8, 2:9 | 3.197 | 39.202 + 2.101 | $0.0091 | 32,0 s |

Tất cả 5 cấu hình đều gọi search ở 17/17 câu, không có câu nào lỗi, và không có citation ID nào ngoài context.

## Phân tích lỗi dev

1. **q01 (evidence bị tách, lỗi chunking từ bài 6):**
   - Chunk trang 8 kết thúc bằng "$117.5B", còn "(BILLION) in loans, grants…" nằm ở chunk kế tiếp. Không chunk nào chứa trọn evidence, nên q01 trượt Hit@3 ở mọi phương pháp.
   - Ở dense_k3, agent vẫn trả lời "$117.5 billion" nhưng cite chunk thiếu nửa sau của câu.
   - **Cải thiện 1** (lấy thêm chunk lân cận) đưa cả hai nửa vào context, nên CER của dense tăng từ 14/15 lên 15/15. Đổi lại, context dài gấp khoảng 2,5 lần và chi phí tăng khoảng 38%.
2. **q02 (gold ban đầu thiếu evidence thay thế):**
   - Agent cite chunk trang 31, có câu "boosting annual guarantee issuance to $20 billion by 2030". Đây là bằng chứng hợp lệ, nhưng benchmark ban đầu chỉ ghi trang 7.
   - Đã bổ sung trang 30 và 31 làm evidence thay thế (thay đổi trên dev, có ghi lại) và tính lại nhãn từ trace bằng `src/relabel.py`, không gọi lại API.
3. **Hit@1 của lượt tìm đầu thấp (9–10/15):** chunk đúng thường đứng hạng 2–3, sau tiêu đề bảng hoặc trang tổng hợp. Không cấu hình nào cải thiện được điểm này.
4. **Chất lượng trên dev đã gần chạm trần:** CER đạt 14–15/15. Vì vậy dev 15 câu khó tách bạch các cấu hình; chênh lệch nằm ở một câu (q01) và ở chi phí.

## Tiêu chí chọn cấu hình (đề xuất, chốt trước khi chạy test)

1. **Ràng buộc:** từ chối đúng 2/2 và từ chối nhầm 0 trên dev.
2. Context Evidence Rate của agent trên dev cao nhất.
3. Nếu hòa: Hit@3 của lượt tìm đầu trong agent.
4. Nếu vẫn hòa: Hit@1 retrieval-only trên dev.
5. Nếu vẫn hòa: chi phí thấp hơn.

Áp dụng:
- Bước 2: còn bm25, hybrid, dense+nbr1, hybrid+nbr1 (đều CER 15/15).
- Bước 3: còn hybrid, dense+nbr1, hybrid+nbr1 (đều 14/15).
- Bước 4: còn hybrid và hybrid+nbr1 (đều 13/15).
- Bước 5: hybrid_rrf_k3 rẻ hơn ($0.0074 so với $0.0091).

→ **Cấu hình chọn: `hybrid_rrf`, top-3, không lấy chunk lân cận.** Test sẽ chạy **baseline dense_k3** và **hybrid_rrf_k3**.

Note: Tiêu chí này được viết **sau khi đã xem kết quả dev, nhưng trước khi chạy test**.