# Benchmark nâng cao — World Bank Annual Report 2022 (116 trang)


File [questions.json](questions.json) gồm **48 câu**, chia trước khi chạy bất kỳ cấu hình nào:

| Nhóm chính | Dev | Test | Tối thiểu test (ADVANCED) |
|---|---:|---:|---:|
| Bảng (`table`) | 4 | 6 | 6 |
| Ảnh, sơ đồ, bản đồ, infographic (`image_diagram`) | 3 | 5 | 5 |
| Biểu đồ (`chart`) | 3 | 5 | 5 |
| Multi-hop (`multi_hop`) | 2 | 4 | 4 |
| Text (`text`) | 3 | 4 | 4 |
| Thiếu bằng chứng (`no_evidence`) | 3 | 6 | 6 |
| **Tổng** | **18** | **30** | **30** |

**Mỗi câu có đáp án** ghi các trường sau:
- `expected_answer`;
- `evidence`: danh sách các mục `{page, kind, locator, values, quote}`. `page` là số trang PDF (1–116). `locator` chỉ ra bảng, hàng và cột, hoặc hình và lát cắt, hoặc ô chú thích. `values` là các con số đúng như in trên trang;
- `calc`: phép tính, nếu câu hỏi cần tính toán.

**Mỗi câu thiếu bằng chứng** ghi `absence_reason` (cách đã kiểm tra là tài liệu không có thông tin) và `near_topic_pages` (các trang gần chủ đề).

## Cách kiểm chứng

- **Kiểm tra tự động.** Chạy:
  ```bash
  python advanced/src/verify_benchmark.py
  ```
  Script đối chiếu với **lớp text của PDF gốc**, dùng hai bộ trích độc lập là PyMuPDF và pdfplumber, chứ không dựa vào nội dung do model tạo:
  - mọi `quote` phải có trên đúng trang;
  - mọi con số trong `values` phải xuất hiện trong lớp text của trang đó;
  - với câu thiếu bằng chứng, script chạy lại phép tìm kiếm và in ra mọi kết quả để người duyệt xem lại.
  - Kết quả hiện tại: **tất cả đều qua**.
- **Kiểm tra bằng mắt.** Có hai điều lớp text không chứng minh được: **nhãn nào đi với phần trăm nào** trong biểu đồ tròn, và **hướng mũi tên** trong sơ đồ. AI đã render và xem lại các trang 23, 27, 31, 35, 39, 43, 47 (biểu đồ tròn), 95, 105, 109 (sơ đồ), 4, 18, 19, 113 (infographic và bản đồ).

## Cách chia dev/test và rủi ro

- Dev và test không có câu nào trùng nội dung hoặc chỉ diễn đạt lại cùng một đáp án.
- **Có dùng chung nguồn:** một vài câu dev và test lấy từ cùng một bảng hoặc hình, nhưng khác hàng, khác lát cắt hoặc khác ô chú thích:
  - Table 18 và 24: dev hỏi Eastern and Southern Africa, test hỏi South Asia và Latin America and the Caribbean;
  - Figure 5 chỉ dùng cho dev;
  - bản đồ kết quả: dev hỏi ô 19, test hỏi ô 27;
  - trang 9: dev hỏi về IFC, test hỏi về MIGA.
- Không đưa đáp án, bảng gold hay vùng evidence vào pipeline khi chạy.
- Cấu hình sẽ được chọn trên dev và chốt trước khi chạy test. **Chấm test theo đạt hoặc không đạt:** cần ≥27/30.
