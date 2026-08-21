# SOC Logging Lab

Web app tối giản, đầy đủ logging, dùng để đào tạo SOC Tier 3 về log
correlation. **Không phải để chạy production.** Kiến trúc: Frontend tĩnh
→ Nginx (reverse proxy) → FastAPI (backend) → PostgreSQL, mỗi thành phần
một container Docker riêng.

Bảng mapping chi tiết đầy đủ (Action → Event → Log location → Layer →
Fields → Ghi chú SOC) nằm ở [`LOGGING_MAP.md`](LOGGING_MAP.md) — đọc file
đó khi bạn cần đối chiếu trực tiếp với tài liệu lý thuyết.

## 1. Cấu trúc thư mục

```
soc-logging-lab/
├── docker-compose.yml
├── .env.example
├── README.md
├── LOGGING_MAP.md
├── frontend/            # HTML/CSS/JS thuần, được Nginx serve trực tiếp
├── nginx/nginx.conf      # reverse proxy + custom access_log format
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/               # FastAPI: routers, models, logging, middleware
├── db/postgresql.conf    # log_statement=mod + logging_collector
└── logs/                 # bind-mount ra host: nginx/, app/, postgres/
```

## 2. Chạy lab

```powershell
Copy-Item .env.example .env
# (tuỳ chọn) sửa POSTGRES_PASSWORD trong .env

docker compose up -d --build
docker compose ps          # cả 3 container phải "healthy"/"running"

# seed vài user + order mẫu
docker compose exec backend python -m app.seed
```

Mở trình duyệt: `http://localhost:8080` (đổi `NGINX_PORT` trong `.env`
nếu 8080 đã bị chiếm).

Tài khoản demo sau khi seed: `alice` / `bob` / `carol`, mật khẩu chung
`Passw0rd!` (in ra console khi seed chạy xong).

Dừng lab: `docker compose down` (thêm `-v` nếu muốn xoá luôn volume DB).

## 3. Biến môi trường (`.env.example`)

| Biến | Ý nghĩa |
|---|---|
| `POSTGRES_USER/PASSWORD/DB` | Thông tin kết nối Postgres. Không hardcode ở đâu trong code. |
| `NGINX_PORT` | Port host map vào Nginx (mặc định 8080). |
| `SESSION_COOKIE_NAME` | Tên cookie session (mặc định `session_id`). |
| `SESSION_TIMEOUT_MINUTES` | Thời gian sống tuyệt đối của session kể từ lúc login (mặc định 30). |
| `SESSION_COOKIE_SECURE` | **`false` chỉ chấp nhận được vì lab chạy HTTP local.** Nếu bạn từng deploy lab này qua HTTPS (kể cả staging), phải đổi thành `true` trước — nếu không cookie session sẽ bị gửi qua cả kênh không mã hoá. |
| `SESSION_COOKIE_SAMESITE` | Mặc định `strict`. |
| `RATE_LIMIT_MAX_ATTEMPTS/WINDOW_MINUTES/LOCKOUT_MINUTES` | Ngưỡng khoá tài khoản sau nhiều lần login sai. |
| `LOG_LEVEL` | Mức log cho 2 logger `app` và `auth` (mặc định `INFO`). |

## 4. Bảng mapping (rút gọn — bản đầy đủ ở LOGGING_MAP.md)

| Endpoint | Action | Log chính | Layer |
|---|---|---|---|
| `POST /api/auth/register` | Đăng ký | `event=register` → `app.log` | Application |
| `POST /api/auth/login` | Đăng nhập | `LOGIN_SUCCESS`/`LOGIN_FAIL`/`ACCOUNT_LOCKED` → `auth.log`; `login_success`/`login_fail` → `app.log` | Authentication + Application |
| `POST /api/auth/logout` | Đăng xuất | `LOGOUT` → `auth.log`; UPDATE `sessions.revoked_at` → Postgres log | Authentication + Database |
| `GET/PUT /api/users/{id}` | Xem/sửa profile | `profile_read`/`profile_update`/`authorization_denied` → `app.log` | Application |
| `POST /api/orders` | Tạo order | `order_create` → `app.log`; INSERT → Postgres log | Application + Database |
| `GET /api/orders`, `GET /api/orders/{id}` | Đọc order(s) | `order_read` → `app.log` (KHÔNG có gì ở Postgres log — SELECT không audit) | Application |
| `PUT /api/orders/{id}` | Sửa order | `order_update` (kèm `changed_fields`) → `app.log`; UPDATE → Postgres log | Application + Database |
| `DELETE /api/orders/{id}` | Xoá order | `order_delete` → `app.log`; DELETE → Postgres log | Application + Database |
| Mọi request không hợp lệ | — | `validation_error` → `app.log`, HTTP 400 | Application |
| `GET /api/debug/crash` | Gây exception | `unhandled_exception` (kèm stack trace) → `app.log`, HTTP 500 (client chỉ thấy `request_id`) | Application |
| Mọi request | — | 1 dòng access log JSON (kèm `session_id` cookie) → `nginx access.log` | Reverse Proxy |

## 5. Xem log — từng layer

```powershell
# Nginx (Reverse Proxy / Web layer)
Get-Content .\logs\nginx\access.log -Tail 50 -Wait
Get-Content .\logs\nginx\error.log -Tail 50 -Wait

# FastAPI (Application layer) — 2 logger riêng: app.log và auth.log
Get-Content .\logs\app\app.log -Tail 50 -Wait
Get-Content .\logs\app\auth.log -Tail 50 -Wait

# PostgreSQL (Database layer) — chỉ có INSERT/UPDATE/DELETE (log_statement=mod)
Get-Content .\logs\postgres\postgresql-<ngày>.log -Tail 50 -Wait

# OS / Container layer (tương đương docker logs cho từng service)
docker logs -f soclab-nginx
docker logs -f soclab-backend
docker logs -f soclab-db
```

`docker logs soclab-backend` và `docker logs soclab-nginx` cho ra đúng nội
dung với file trong `logs/` (stdout được ghi song song với file, theo yêu
cầu của lab) — dùng cái nào tuỳ bạn muốn thực hành thu log qua Docker
logging driver hay đọc file trực tiếp.

## 6. Walkthrough 10 kịch bản

Giả sử `NGINX_PORT=8080`. Dùng `curl` với `-c cookies.txt -b cookies.txt`
để giữ session giữa các lệnh (PowerShell: dùng `curl.exe`, không phải
alias `Invoke-WebRequest`).

**1. Truy cập web**
```powershell
curl.exe http://localhost:8080/index.html
```
→ xem: `logs/nginx/access.log` (1 dòng mới, status 200).

**2. Đăng ký (đã có thể làm qua UI `/register.html`)**
```powershell
curl.exe -X POST http://localhost:8080/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{"username":"dave","email":"dave@example.com","password":"Passw0rd!"}'
```
→ xem: `logs/app/app.log`, `event="register"`.

**3. Login đúng**
```powershell
curl.exe -c cookies.txt -X POST http://localhost:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"alice","password":"Passw0rd!"}'
```
→ xem: `logs/app/auth.log` (`LOGIN_SUCCESS`), `logs/app/app.log`
(`login_success`), `logs/nginx/access.log` (cookie `session_id` xuất
hiện trong response `Set-Cookie`, và trong các request tiếp theo).

**4. Login sai (5 lần liên tiếp để kích hoạt khoá)**
```powershell
1..5 | ForEach-Object {
  curl.exe -X POST http://localhost:8080/api/auth/login `
    -H "Content-Type: application/json" `
    -d '{"username":"alice","password":"wrong"}'
}
```
→ xem: `logs/app/auth.log` — 4 dòng `LOGIN_FAIL` (`reason=bad_password`),
dòng thứ 5 có thêm `ACCOUNT_LOCKED`. Lần thử thứ 6 trở đi trong 5 phút
tiếp theo sẽ nhận HTTP 429 và `LOGIN_FAIL` với `reason=account_locked`.

**5. Logout**
```powershell
curl.exe -c cookies.txt -b cookies.txt -X POST http://localhost:8080/api/auth/logout
```
→ xem: `logs/app/auth.log` (`LOGOUT`), và trong Postgres log một dòng
`UPDATE sessions SET revoked_at = ...` — bằng chứng session bị huỷ thật ở
server chứ không chỉ xoá cookie.

**6. Query (đọc dữ liệu)**
```powershell
curl.exe -b cookies.txt http://localhost:8080/api/orders
```
→ xem: `logs/app/app.log` (`order_read`). Kiểm tra Postgres log cùng thời
điểm — sẽ **không** có gì (SELECT không audit), đối lập với bước 7-9.

**7. Create**
```powershell
curl.exe -b cookies.txt -X POST http://localhost:8080/api/orders `
  -H "Content-Type: application/json" `
  -d '{"product_name":"Monitor","quantity":1,"unit_price":199.99,"status":"pending"}'
```
→ xem: `logs/app/app.log` (`order_create`) + Postgres log (`INSERT INTO
orders`). Lưu lại `id` trả về để dùng ở bước 8-9.

**8. Update**
```powershell
curl.exe -b cookies.txt -X PUT http://localhost:8080/api/orders/<order_id> `
  -H "Content-Type: application/json" `
  -d '{"status":"paid"}'
```
→ xem: `logs/app/app.log` (`order_update`, có `changed_fields` với
old/new) + Postgres log (`UPDATE orders`).

**9. Delete**
```powershell
curl.exe -b cookies.txt -X DELETE http://localhost:8080/api/orders/<order_id>
```
→ xem: `logs/app/app.log` (`order_delete`) + Postgres log (`DELETE FROM
orders`).

**10. Request không hợp lệ + gây exception**
```powershell
# thiếu field bắt buộc -> 400
curl.exe -X POST http://localhost:8080/api/auth/register `
  -H "Content-Type: application/json" -d '{"username":"x"}'

# gây lỗi 500 có chủ đích
curl.exe http://localhost:8080/api/debug/crash
```
→ xem: `logs/app/app.log` — dòng đầu `event="validation_error"`, dòng
sau `event="unhandled_exception"` kèm `stack_trace` đầy đủ. Response của
lệnh `debug/crash` chỉ có `detail` chung chung + `request_id` — dùng
`request_id` đó để `grep`/`Select-String` đúng dòng log tương ứng ở cả
`app.log` lẫn `logs/nginx/access.log`.

**Bonus — test IDOR** (điểm nhấn của lab):
```powershell
# Login bằng bob, thử đọc profile hoặc order của alice bằng ID của alice
curl.exe -c bob.txt -b bob.txt -X POST http://localhost:8080/api/auth/login `
  -H "Content-Type: application/json" -d '{"username":"bob","password":"Passw0rd!"}'

curl.exe -b bob.txt http://localhost:8080/api/users/<alice_user_id>
curl.exe -b bob.txt http://localhost:8080/api/orders/<alice_order_id>
```
→ cả hai trả HTTP 403, và `logs/app/app.log` có `event=
"authorization_denied"` với `owner_id != requester_id` — bằng chứng trực
tiếp cho detection rule IDOR.

## 7. Seed dữ liệu mẫu

```powershell
docker compose exec backend python -m app.seed
```
Tạo 3 user (`alice`, `bob`, `carol`, mật khẩu `Passw0rd!`) và vài order
mẫu gắn với `alice`/`bob`. Script idempotent — chạy lại không tạo trùng
user đã tồn tại.

## 8. Ghi chú bảo mật cho lab này (đọc trước khi làm gì khác ngoài local)

- `SESSION_COOKIE_SECURE=false` trong `.env.example` là **có chủ đích**,
  chỉ vì lab chạy HTTP trên `localhost`. Bật lại `true` ngay khi có HTTPS.
- Endpoint `GET /api/debug/crash` cố tình không cần auth và cố tình gây
  lỗi — không bao giờ đưa endpoint kiểu này vào code thật.
- Không có TLS, không có CI/CD, không có test coverage — đúng như phạm vi
  yêu cầu (lab học logging/kiến trúc, không phải sản phẩm thật).
- `uvicorn` chạy đúng 1 worker (`--workers 1`) để logic đếm login-fail và
  session (đọc/ghi trực tiếp Postgres, không cache) nhất quán và dễ dò
  log 1-1 với hành động — không phải giới hạn kỹ thuật, mà là lựa chọn
  đơn giản hoá cho mục đích đào tạo.

## 9. Troubleshooting nhanh

- Container `db` không lên "healthy": kiểm tra `logs/postgres/` có ghi
  được không — trên một số máy, quyền ghi bind-mount cho user `postgres`
  bên trong container có thể cần chỉnh (`icacls`/chạy Docker Desktop với
  WSL2 backend thường không gặp vấn đề này).
- Đổi port 8080: sửa `NGINX_PORT` trong `.env`, chạy lại
  `docker compose up -d`.
