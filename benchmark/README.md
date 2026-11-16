# Benchmark Day 7 — World Bank Annual Report 2024

Corpus: 557 chunk của strategy C bài 6 (chia theo đoạn, tối đa 500 ký tự), trích từ `data/worldbank-report-2024.pdf` (CC BY-NC-ND 3.0 IGO). Lấy bằng lệnh `python src/export_day6.py`.

| Split | Có đáp án | Thiếu bằng chứng | Tổng |
|---|---:|---:|---:|
| dev | 15 (`q01`–`q15`) | 2 (`u01`, `u02`) | 17 |
| test | 5 (`t11`–`t15`) | 2 (`u03`, `u04`) | 7 |
| **Tổng** | **20** | **4** | **24** |

- [questions.json](questions.json): các câu có đáp án. Mỗi câu có `id`, `split`, `type`, `question`, `expected_answer`, `gold` (danh sách `{source_id, page, evidence}` là các evidence thay thế nhau) và `filter` nếu có.
- [cases.json](cases.json): toàn bộ 24 câu, có thêm `answerable`, `expected_behavior` và `absence_reason` cho câu thiếu bằng chứng.
- `page` là **số trang PDF (1–49)**, không phải số trang in.

Kiểm tra benchmark bằng lệnh:

```bash
python src/verify_benchmark.py
```

Lệnh này xác nhận mỗi câu có ít nhất một evidence nằm trọn trong một chunk đúng trang, giá trị filter tồn tại trong metadata và bao gồm trang gold, và số câu mỗi split đạt mức tối thiểu.

## Nguồn câu hỏi

**Dev (15 câu có đáp án):** lấy nguyên 15 câu dev của benchmark bài 6. Học viên đã duyệt các câu này ở bài 6. Có một thay đổi:
- `q01`: thêm evidence thay thế ở trang 6 ("the World Bank Group committed $117.5 billion"). Bài 6 cho thấy evidence gốc ở trang 8 bị tách qua hai chunk, nên không chunk nào chứa trọn nó.
- Đây là thay đổi trên **dev**, có ghi lại, và không đụng tới test.

**Test (5 câu có đáp án): viết mới cho Day 7.**
- Kết quả test của bài 6 (`t01`–`t05`) đã được xem và phân tích, nên không dùng lại làm holdout.
- Các câu mới lấy từ trang 17, 26, 30, 32 và 38. Không trang nào trong số này có trong benchmark bài 6, kể cả dev lẫn test.
- `t11` là câu filter: hỏi dân số hiện tại "của khu vực này" trong bảng regional snapshot, với filter `region=europe_central_asia`. Cả 7 khu vực đều có bảng cùng mẫu, nên không lọc thì dễ lấy nhầm khu vực. Câu này đồng thời là câu đọc số liệu từ bảng.

**Thiếu bằng chứng (4 câu):** đều gần chủ đề, xem `absence_reason`.

| ID | Split | Câu hỏi | Cách kiểm tra là tài liệu không có |
|---|---|---|---|
| `u01` | dev | Cam kết cho Việt Nam năm FY24 | Tìm "Viet Nam"/"Vietnam" trong cả 49 trang: chỉ thấy ví dụ dự án (trang 14, 15, 37, 42); không có trong bảng top borrower IBRD/IDA |
| `u02` | dev | Nhật Bản cam kết bao nhiêu cho IDA21 | "IDA21" chỉ được nhắc là đợt bổ sung vốn sắp tới, không có số tiền; "Japan" xuất hiện ở ngữ cảnh khác |
| `u03` | test | Lending spread của khoản vay linh hoạt IBRD | Từ "spread" không xuất hiện; "interest rate" chỉ có ở trang 27 và 37, không có giá trị |
| `u04` | test | IFC có bao nhiêu nhân viên năm FY24 | Bảng 16 (trang 40) chỉ có số liệu nhân sự IBRD/IDA |

Việc tìm kiếm chạy trên toàn bộ 49 trang PDF, kể cả các trang bị loại khỏi corpus. Câu thiếu bằng chứng **không được tính vào mẫu số của retrieval metrics**.

## Rủi ro rò rỉ

- `t11` dùng cùng kiểu câu filter theo region như `q13`–`q15`, nhưng hỏi bảng snapshot thay vì câu "approved … operations".
- Dev được dùng lại từ bài 6, nên kết quả dev của Day 7 có thể bị ảnh hưởng bởi những gì đã biết từ bài 6. Đây là chủ đích: dev dùng để chỉnh.
- Test chỉ có 5 + 2 câu. Mỗi câu có đáp án tương ứng 20 điểm phần trăm, nên kết quả test chỉ mang tính minh họa.

## Tiêu chí chọn cấu hình

Sẽ chốt trước khi chạy test, và ghi ở [../results/README.md](../results/README.md).
