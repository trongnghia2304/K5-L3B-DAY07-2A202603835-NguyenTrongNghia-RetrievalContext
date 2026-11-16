# Day 7 — Agentic RAG

> ## Bài làm — Nguyễn Trọng Nghĩa (2A202603835, L3B)
>
> - **Dữ liệu:** dùng lại corpus, chunk (strategy C), pgvector và embedding MiniLM của [bài Day 6](https://github.com/trongnghia2304/K5-L3B-DAY06-2A202603835-DataIngestion).
> - **Agent:** DeepSeek `deepseek-chat`; server trả về tên model thật là `deepseek-flash`.
> - **Retrieval:** dense (baseline), BM25, hybrid RRF; cấu hình chọn là hybrid_rrf, top-3.
> - **Báo cáo:** [report/individual/2A202603835_NguyenTrongNghia.md](report/individual/2A202603835_NguyenTrongNghia.md).
> - **Kết quả:** [results/README.md](results/README.md).
> - **Benchmark:** [benchmark/README.md](benchmark/README.md).
>
> **Cách chạy** (Python 3.11, Windows PowerShell; trên macOS/Linux đổi đường dẫn venv cho phù hợp):
>
> ```bash
> # 1. Bật Postgres + pgvector của Day 6 (đã ingest; chạy trong thư mục starter/ của repo Day 6)
> docker compose -p day6_student_starter up -d --wait
> # 2. Môi trường Day 7
> python -m venv .venv
> .venv\Scripts\python -m pip install -r requirements.txt
> Copy-Item .env.example .env        # rồi điền DEEPSEEK_API_KEY vào .env
> # 3. Dữ liệu và benchmark
> .venv\Scripts\python src/export_day6.py
> .venv\Scripts\python src/verify_benchmark.py
> # 4. Retrieval-only (không gọi LLM)
> .venv\Scripts\python src/eval_retrieval.py --split dev --methods dense,bm25,hybrid_rrf,dense+nbr1,hybrid_rrf+nbr1 --budget 100000 --tag filter_unbudgeted
> # 5. Agent (gọi DeepSeek API, có tốn phí)
> .venv\Scripts\python src/run_agent.py --split dev --method hybrid_rrf --top-k 3 --tag hybrid_rrf_k3
> .venv\Scripts\python src/run_agent.py --split test --method hybrid_rrf --top-k 3 --tag hybrid_rrf_k3
> # 6. Chấm thủ công: tạo bảng chấm, điền nhãn, rồi tổng hợp qua starter/agent_metrics.py
> .venv\Scripts\python src/review_sheet.py summarize
> # Unit test của starter (cần chế độ UTF-8 trên Windows)
> $env:PYTHONUTF8=1; .venv\Scripts\python -m unittest discover -s tests -v
> ```
>
> `starter/data/` (toàn văn các chunk, giấy phép NoDerivatives) không được commit; bước 3 sẽ tạo lại. Không commit `.env`.
>
> **Thử thách nâng cao (bonus):** *World Bank Annual Report 2022* (116 trang). Test đạt **30/30**. Chi tiết trong [advanced/results/README.md](advanced/results/README.md).
>
> Cần thêm thư viện `pymupdf` và `pdfplumber`, và file `AR2022EN.pdf` (tải từ Open Knowledge Repository của World Bank, đặt vào `advanced/data/`):
>
> ```bash
> .venv\Scripts\python -m pip install pymupdf pdfplumber
> .venv\Scripts\python advanced/src/ingest.py              # text theo trang + manifest
> .venv\Scripts\python advanced/src/describe_visuals.py    # vision mô tả bảng và hình (gọi API)
> .venv\Scripts\python advanced/src/describe_visuals.py --recheck   # đối chiếu số liệu với lớp text
> .venv\Scripts\python advanced/src/build_index.py         # chunk + pgvector adv_chunks_384d
> .venv\Scripts\python advanced/src/make_benchmark.py; .venv\Scripts\python advanced/src/verify_benchmark.py
> .venv\Scripts\python advanced/src/run_adv.py --split dev --tag loopfix_catalog --loop-fix --catalog
> .venv\Scripts\python advanced/src/run_adv.py --split test --tag final --loop-fix --catalog
> ```

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.
