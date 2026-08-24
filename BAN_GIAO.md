# Bàn giao / Trạng thái dự án (đọc file này trước khi làm tiếp)

File này dành cho **phiên Claude Code khác** (ví dụ ở máy nhà) đọc để
nắm bối cảnh ngay, không cần user giải thích lại từ đầu. Cũng hữu ích để
chính user đọc lại khi quên đã làm tới đâu.

## Dự án là gì

Web app **Task Manager** (quản lý công việc cá nhân) — bài tập lớn theo
đề: (1) xây app đủ chức năng, (2) theo dõi log/luồng hoạt động, (3) vận
hành/nâng cấp mã nguồn. Kiến trúc 4 lớp: Frontend tĩnh → Nginx (reverse
proxy) → FastAPI (backend) → PostgreSQL, mỗi lớp 1 container Docker.

Đọc theo thứ tự để hiểu toàn bộ:
1. [`README.md`](README.md) — chạy app, biến môi trường, xem log
2. [`PHAN_TICH_THIET_KE.md`](PHAN_TICH_THIET_KE.md) — phân tích & thiết kế
3. [`LOGGING_MAP.md`](LOGGING_MAP.md) — bảng mapping event → log
4. [`VAN_HANH_NANG_CAP.md`](VAN_HANH_NANG_CAP.md) — nâng cấp mã nguồn (đợt thêm category)
5. [`KICH_BAN_DEMO.md`](KICH_BAN_DEMO.md) — kịch bản quay video demo, đã test full qua tay user

## Quan trọng: 2 máy KHÔNG tự đồng bộ Docker/DB

User làm việc trên 2 máy (công ty + nhà), cùng đăng nhập 1 tài khoản
Docker Hub và 1 repo GitHub (`https://github.com/KhaiND1221/SOC_demo`,
private). **Chỉ có code qua git là đồng bộ 2 máy.** Các thứ sau là
**local riêng từng máy, không tự sync dù cùng account Docker**:
- Image tự build (`soc-logging-lab-backend`)
- Volume dữ liệu Postgres (`pgdata`) — 2 máy là 2 database khác nhau
- Container đang chạy
- Chứng chỉ HTTPS self-signed (`nginx/ssl/*.key`, `*.crt` — bị gitignore
  có chủ đích, mỗi máy tự generate riêng, xem README mục 5b)

Vì vậy ở máy mới (nhà), sau khi `git pull`, luôn phải tự làm:
```powershell
Copy-Item .env.example .env    # nếu chưa có .env
docker compose up -d --build
docker compose exec backend python -m app.seed   # DB trống, cần seed lại
```
Và nếu cần HTTPS, tự generate cert theo lệnh ở README mục 5b (chưa có
sẵn cert vì không commit private key vào git).

## Việc đã làm ở phiên này (máy công ty, gần đây nhất trước)

Bối cảnh trước đó: máy nhà đã "reframe" dự án từ SOC-lab thuần lý thuyết
thành Task Manager thật (xoá `/api/debug/crash`, thêm tính năng
`category`, redesign UI dark/indigo). Phiên này (máy công ty) đồng bộ
theo bản đó rồi làm tiếp:

- Đã pull bản redesign từ nhà, chạy migration DB (`0001_add_task_category.sql`)
  đúng thứ tự trước khi rebuild code, verify không phá dữ liệu cũ.
- **Fix bug**: `request_id` bị mất (null) trong response lỗi 500 — do
  `RequestContextMiddleware` reset contextvar quá sớm, trước khi
  `ServerErrorMiddleware` (nằm ngoài middleware stack) kịp đọc. Xem
  `backend/app/middleware.py`.
- **Thêm lại** `/api/debug/crash` (đã bị xoá ở bản nhà) — cần cho kịch
  bản demo "phát sinh exception" theo đúng yêu cầu đề bài. Đánh dấu rõ
  "chỉ phục vụ demo" trong code + README.
- **Fix UI `tasks.html`**: lỗi tạo task trùng (do form không tự xoá sau
  khi tạo, dễ bấm nhầm 2 lần) — giờ nút tự khoá lúc gửi + form tự xoá
  sau khi tạo thành công. Thêm 3 ô đếm Chưa làm/Đang làm/Hoàn thành, nút
  "+ Thêm việc" ẩn/hiện form tạo, cảnh báo xác nhận khi tạo task trùng
  tiêu đề, hiện ID task trong modal + ô "Tra cứu theo ID" để test IDOR
  ngay trên UI (không cần curl/DevTools).
- **Viết `watch-logs.ps1`**: script PowerShell gộp + tô màu + sắp xếp
  đúng thời gian thật cả 4 nguồn log (Nginx/App/Auth/DB) vào 1 cửa sổ,
  UTF-8 an toàn (tiếng Việt hiện đúng), tự hiện lịch sử gần nhất khi mở.
  Đây là công cụ chính dùng khi quay demo.
- **Thêm HTTPS**: self-signed cert, Nginx nghe cả port 80 (HTTP,
  `NGINX_PORT=8080`) và 443 (HTTPS, `NGINX_HTTPS_PORT=8443`). Log Nginx
  giờ có field `"scheme":"http"/"https"` để phân biệt rõ, `watch-logs.ps1`
  hiện tag `[HTTP]`/`[HTTPS]` màu khác nhau.
- **Viết `KICH_BAN_DEMO.md`**: kịch bản quay video 4 phần, đã tự tay
  test hết Phần 2 (7 bước log-correlation) qua UI thật, xác nhận đúng.
  **Lưu ý quan trọng đã phát hiện khi test**: cơ chế khoá tài khoản
  match theo `username HOẶC IP` — nếu test "login sai 5 lần" TRƯỚC khi
  test IDOR (cần login tài khoản khác), tài khoản đó sẽ bị khoá lây theo
  IP. Kịch bản đã sửa đúng thứ tự (IDOR trước, khoá-tài-khoản sau cùng),
  đừng đảo lại.

## Trạng thái hiện tại

- App chạy tốt, đã test end-to-end nhiều lần (CRUD, auth, lockout, IDOR,
  exception, category, HTTPS).
- **Chưa quay video demo thật** — kịch bản đã sẵn sàng và đã verify, chỉ
  còn bước user tự quay theo `KICH_BAN_DEMO.md`.
- Tài khoản demo: `alice`/`bob`/`carol`, mật khẩu chung `Passw0rd!`
  (seed qua `python -m app.seed`).

## Ghi chú vận hành máy công ty (có thể không áp dụng ở nhà)

- Docker Desktop trên máy này từng tự tắt giữa chừng vài lần (không rõ
  nguyên nhân — có thể do máy sleep). Nếu `docker ps`/`docker compose`
  báo lỗi "cannot connect to the Docker API", mở lại Docker Desktop và
  đợi ~30-60s cho engine sẵn sàng rồi thử lại.
- Máy công ty ban đầu chưa có Docker/Git/GitHub CLI/WSL2 — đã cài đủ
  trong phiên trước, không cần cài lại trừ khi là máy khác.
