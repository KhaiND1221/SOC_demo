# Task Manager

Ứng dụng web quản lý công việc cá nhân: mỗi người dùng đăng ký tài
khoản riêng, tự tạo/xem/sửa/xoá danh sách công việc cần làm của mình
(tiêu đề, mô tả, độ ưu tiên, trạng thái, hạn hoàn thành).

Kiến trúc: Frontend tĩnh → Nginx (reverse proxy) → FastAPI (backend) →
PostgreSQL, mỗi thành phần một container Docker riêng.

Tài liệu phân tích & thiết kế tính năng (bài toán, đối tượng dùng,
chức năng, ERD, thiết kế API/màn hình) nằm ở
[`PHAN_TICH_THIET_KE.md`](PHAN_TICH_THIET_KE.md).

Báo cáo phân tích log sinh ra khi ứng dụng hoạt động (theo dõi luồng
hoạt động, sự kiện truy cập/đăng nhập/thao tác/lỗi ở từng layer) nằm ở
[`LOGGING_MAP.md`](LOGGING_MAP.md).

Tài liệu vận hành & nâng cấp mã nguồn (thêm tính năng mới vào ứng dụng
đang chạy, migration DB, các vấn đề cần quan tâm) nằm ở
[`VAN_HANH_NANG_CAP.md`](VAN_HANH_NANG_CAP.md).

Kịch bản quay video demo (từng bước thao tác + đối chiếu log đúng
phương pháp: bóc field + xác thực bằng bằng chứng ở layer thấp hơn) nằm
ở [`KICH_BAN_DEMO.md`](KICH_BAN_DEMO.md).

## 1. Cấu trúc thư mục

```
SOC_demo/
├── docker-compose.yml
├── .env.example
├── README.md
├── LOGGING_MAP.md
├── PHAN_TICH_THIET_KE.md
├── frontend/            # HTML/CSS/JS thuần, được Nginx serve trực tiếp
├── nginx/nginx.conf      # reverse proxy + custom access_log format
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/               # FastAPI: routers, models, logging, middleware
├── db/postgresql.conf    # log_statement=mod + logging_collector
├── db/migrations/        # migration SQL cho các đợt nâng cấp schema
└── logs/                 # bind-mount ra host: nginx/, app/, postgres/
```

## 2. Chạy ứng dụng

```powershell
Copy-Item .env.example .env
# (tuỳ chọn) sửa POSTGRES_PASSWORD trong .env

docker compose up -d --build
docker compose ps          # cả 3 container phải "healthy"/"running"

# seed vài user + task mẫu
docker compose exec backend python -m app.seed
```

Mở trình duyệt: `http://localhost:8080` (đổi `NGINX_PORT` trong `.env`
nếu 8080 đã bị chiếm).

Tài khoản demo sau khi seed: `alice` / `bob` / `carol`, mật khẩu chung
`Passw0rd!` (in ra console khi seed chạy xong).

Dừng ứng dụng: `docker compose down` (thêm `-v` nếu muốn xoá luôn
volume DB).

## 3. Biến môi trường (`.env.example`)

| Biến | Ý nghĩa |
|---|---|
| `POSTGRES_USER/PASSWORD/DB` | Thông tin kết nối Postgres. Không hardcode ở đâu trong code. |
| `NGINX_PORT` | Port host map vào Nginx (mặc định 8080). |
| `SESSION_COOKIE_NAME` | Tên cookie session (mặc định `session_id`). |
| `SESSION_TIMEOUT_MINUTES` | Thời gian sống tuyệt đối của session kể từ lúc login (mặc định 30). |
| `SESSION_COOKIE_SECURE` | `false` chỉ chấp nhận được khi chạy HTTP local. Khi deploy qua HTTPS phải đổi thành `true`, nếu không cookie session sẽ bị gửi qua cả kênh không mã hoá. |
| `SESSION_COOKIE_SAMESITE` | Mặc định `strict`. |
| `RATE_LIMIT_MAX_ATTEMPTS/WINDOW_MINUTES/LOCKOUT_MINUTES` | Ngưỡng khoá tài khoản sau nhiều lần login sai. |
| `LOG_LEVEL` | Mức log cho 2 logger `app` và `auth` (mặc định `INFO`). |

## 4. Các chức năng chính

| Endpoint | Chức năng |
|---|---|
| `POST /api/auth/register` | Đăng ký tài khoản |
| `POST /api/auth/login` | Đăng nhập |
| `POST /api/auth/logout` | Đăng xuất |
| `GET/PUT /api/users/{id}` | Xem/sửa hồ sơ cá nhân |
| `POST /api/tasks` | Tạo công việc |
| `GET /api/tasks`, `GET /api/tasks/{id}` | Xem danh sách/chi tiết công việc |
| `PUT /api/tasks/{id}` | Cập nhật công việc |
| `DELETE /api/tasks/{id}` | Xoá công việc |
| `GET /api/debug/crash` | **Chỉ phục vụ demo/quay video** — cố tình gây lỗi 500 để minh hoạ kịch bản "phát sinh exception" (xem `KICH_BAN_DEMO.md` bước 2.6). Không phải chức năng nghiệp vụ thật. |

Chi tiết thiết kế API/màn hình đầy đủ ở
[`PHAN_TICH_THIET_KE.md`](PHAN_TICH_THIET_KE.md).

## 5. Xem log của ứng dụng

```powershell
# Nginx (Reverse Proxy / Web layer)
Get-Content .\logs\nginx\access.log -Tail 50 -Wait
Get-Content .\logs\nginx\error.log -Tail 50 -Wait

# FastAPI (Application layer) — 2 logger riêng: app.log và auth.log
Get-Content .\logs\app\app.log -Tail 50 -Wait
Get-Content .\logs\app\auth.log -Tail 50 -Wait

# PostgreSQL (Database layer) — chỉ có INSERT/UPDATE/DELETE (log_statement=mod)
Get-Content .\logs\postgres\postgresql-<ngày>.log -Tail 50 -Wait

# Docker logging driver (tương đương stdout container)
docker logs -f soclab-nginx
docker logs -f soclab-backend
docker logs -f soclab-db
```

Xem trực tiếp dữ liệu trong Postgres (không phải log, mà là data thật):
```powershell
docker compose exec db psql -U soclab -d soclab -c "\dt"
docker compose exec db psql -U soclab -d soclab -c "SELECT * FROM tasks;"
```

Phân tích chi tiết từng loại sự kiện log (đăng nhập, thao tác task,
lỗi...) và ý nghĩa của chúng nằm ở
[`LOGGING_MAP.md`](LOGGING_MAP.md) — tài liệu đó bao gồm cả bộ kịch bản
thao tác mẫu để tự tay tạo ra các sự kiện log tương ứng.

## 6. Giới hạn phạm vi hiện tại

- `SESSION_COOKIE_SECURE=false` trong `.env.example` chỉ phù hợp khi
  chạy HTTP trên `localhost`. Bật lại `true` ngay khi có HTTPS.
- Chưa có TLS, CI/CD, hay test coverage tự động.
- `uvicorn` chạy đúng 1 worker (`--workers 1`) để logic đếm login-fail
  và session (đọc/ghi trực tiếp Postgres, không cache) luôn nhất quán —
  đây là lựa chọn đơn giản hoá, có thể mở rộng sau.

## 7. Troubleshooting nhanh

- Container `db` không lên "healthy": kiểm tra `logs/postgres/` có ghi
  được không — trên một số máy, quyền ghi bind-mount cho user `postgres`
  bên trong container có thể cần chỉnh (`icacls`/chạy Docker Desktop với
  WSL2 backend thường không gặp vấn đề này).
- Đổi port 8080: sửa `NGINX_PORT` trong `.env`, chạy lại
  `docker compose up -d`.
- Nếu vừa `git pull`/đổi code frontend mà trình duyệt vẫn hiện bản cũ:
  nhấn Ctrl+Shift+R để hard-refresh (trình duyệt cache file tĩnh theo
  mặc định vì Nginx không set `Cache-Control` tường minh).
