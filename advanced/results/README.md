# Kết quả thử thách nâng cao

Tài liệu: World Bank Annual Report 2022 (116 trang, xem [../manifest.json](../manifest.json)). Benchmark ở [../benchmark/](../benchmark/README.md).

Cấu hình chung:
- **Agent và vision:** `deepseek-flash`, temperature = 0.
- **Index:** 877 chunk, gồm 816 chunk text và 61 chunk hình. Tìm bằng hybrid RRF (dense MiniLM trên pgvector `adv_chunks_384d` + BM25), lấy top-5.
- **Tool:** `search` (tối đa 5 lượt) và `view_page` (tối đa 4 lượt), tối đa 10 lượt gọi model.
- **"Đạt tự động"** chỉ là ước lượng sơ bộ: câu trả lời chứa đủ các con số trong evidence **và** cite đúng các trang evidence; câu thiếu bằng chứng thì phải được từ chối. Kết quả chính thức là nhãn thủ công đạt/không đạt.

## Dev (18 câu): các lượt thử

| Lượt chạy | Thay đổi / giả thuyết | Đạt tự động | Chi phí ≤ | Thời gian |
|---|---|---|---|---|
| `dev_base` | Pipeline ban đầu | 17/18 | $0.036 | 143 s |
| — | **Sửa benchmark:** d11, t17, t20 không phải multi-hop thật (một bảng của khu vực đã đủ để trả lời), nên được thay bằng câu cần hai nguồn; bổ sung evidence thay thế cho d01, t02. Sửa trước khi chạy test lần nào | — | — | — |
| `dev_base_v2` | Pipeline ban đầu, benchmark đã sửa | 17/18 (d12: hết lượt search nhưng vẫn gọi tiếp, kết thúc không có câu trả lời) | $0.033 | 154 s |
| `dev_loopfix` (C1) | Gỡ tool đã hết lượt, dành lượt cuối để trả lời | 18/18 | $0.030 | 164 s |
| `dev_loopfix_r2` / `_r3` | Chạy lặp C1 | 17/18 / 17/18 (d12: lượt cuối không có tool, model in cú pháp gọi tool thô `<｜DSML｜ calls>`, nên bị chuyển thành từ chối) | $0.039 / $0.035 | 170 / 152 s |
| `dev_loopfix_catalog` (C2) | C1 + mục lục 45 bảng và hình (nhãn, tiêu đề, trang) trong prompt, lấy từ index chứ không từ gold | 18/18 | $0.027 | 112 s |
| `dev_loopfix_catalog_r2` / `_r3` | Chạy lặp C2 | 18/18 / 18/18 | $0.030 / $0.036 | 162 / 178 s |

**Tiêu chí chọn** (đặt trước khi chạy lặp và trước khi chạy test):
1. Tỷ lệ đạt trung bình qua 3 lần chạy dev cao nhất.
2. Nếu hòa, chọn cấu hình có lần chạy kém nhất cao hơn.
3. Nếu vẫn hòa, chọn cấu hình rẻ hơn và nhanh hơn.

C1 đạt trung bình 17,33/18, lần kém nhất 17. C2 đạt trung bình 18,00/18, lần kém nhất 18.

→ **Chốt C2** (`--loop-fix --catalog`) ngày **2026-11-16**, trước khi chạy test. 

Lệnh chạy test:

```bash
python advanced/src/run_adv.py --split test --tag final --loop-fix --catalog
```

## Test (30 câu): `test_final`, chạy lúc 05:55 UTC ngày 2026-11-16

Mỗi câu được chấm thủ công đạt hoặc không đạt theo ADVANCED.md, bằng cách đối chiếu câu trả lời và citation với bản gốc. Nhãn và lý do từng câu nằm ở [test_final/labels.csv](test_final/labels.csv); trace ở [test_final/traces.json](test_final/traces.json).

| Nhóm | Đạt / tổng | Tỷ lệ |
|---|---|---|
| Bảng | 6/6 | 100% |
| Ảnh, sơ đồ | 5/5 | 100% |
| Biểu đồ | 5/5 | 100% |
| Multi-hop | 4/4 | 100% |
| Text | 4/4 | 100% |
| Thiếu bằng chứng | 6/6 | 100% |
| **Toàn bộ** | **30/30** | **100%** (ngưỡng là ≥27/30) |

- **Lỗi hệ thống / timeout:** 0.
- **Thời gian:** 192 giây (trung bình 6,4 giây mỗi câu).
- **Chi phí:** $0.047 theo giá cao điểm (mức trần). Lượt chạy diễn ra ngoài giờ cao điểm, nên chi phí thực khoảng một nửa.
- **Token:**
  - agent: 215.663 token prompt (trong đó 169.856 cache hit) và 6.304 token output;
  - vision (`view_page`): 33.465 token prompt và 12.043 token output.
- **Số lượt `view_page` mỗi câu:** 0 lượt 5 câu; 1 lượt 19 câu; 2 lượt 5 câu; 4 lượt 1 câu.
- **Ghi chú khi chấm:**
  - `t13` và `t20` nêu thêm tổng số tiền in ở tiêu đề biểu đồ trên trang được cite; câu hỏi không yêu cầu con số này.
  - `t23` có citation thứ hai (trang 12), cũng chứa số $4,9 tỷ của MIGA.
  - Các câu từ chối không chứa khẳng định sai nào.
- **Giới hạn:**
  - Mỗi câu chỉ chạy một lần, mà trên dev kết quả có dao động giữa các lần chạy (C1), nên 30/30 có biên sai số.
  - Nhãn do tác giả pipeline duyệt.
