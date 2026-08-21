# PHÂN TÍCH & THIẾT KẾ ỨNG DỤNG — Task Manager (SOC Logging Lab)

Tài liệu này gồm 2 phần: (A) trả lời các câu hỏi lý thuyết nền tảng về
ứng dụng web, áp dụng trực tiếp vào ứng dụng đã xây dựng trong repo này;
(B) bản phân tích & thiết kế tính năng của ứng dụng theo đúng yêu cầu đề
bài ("Lập trình và triển khai cài đặt 1 ứng dụng web").

---

## PHẦN A — LÝ THUYẾT NỀN TẢNG (áp dụng vào ứng dụng đã xây)

### A1. Cấu trúc của một ứng dụng web điển hình

| Lớp | Công nghệ phổ biến (đề bài liệt kê) | Công nghệ dùng trong lab này | Vai trò trong lab |
|---|---|---|---|
| Frontend (trình duyệt client) | HTML, CSS | HTML/CSS/JS thuần (`frontend/`) | Render UI, gọi REST API qua `fetch()`, không có business logic nhạy cảm (mọi validate/authZ thật đều nằm ở backend). |
| Backend | PHP, Python, .NET | Python — FastAPI (`backend/app/`) | Chứa toàn bộ business logic: auth, session, CRUD task, log. |
| Web server | IIS, Apache, Tomcat | Nginx (`nginx/nginx.conf`) | Vừa là web server (serve file tĩnh của frontend) vừa là reverse proxy (forward `/api/*` sang FastAPI), là nơi TLS sẽ termination nếu triển khai HTTPS thật. |
| Database | MS SQL, MySQL, MongoDB | PostgreSQL (`db/`) | RDBMS mã nguồn mở, cùng nhóm quan hệ (relational) với MS SQL/MySQL — phù hợp vì dữ liệu có quan hệ khoá ngoại rõ ràng (users → sessions, users → tasks). |

Sơ đồ luồng:

```
Browser (HTML/CSS/JS)
      |  HTTP request
      v
Nginx (web server + reverse proxy)  -- serve static frontend
      |  proxy /api/* -> backend:8000
      v
FastAPI (backend, business logic + session auth)
      |  SQL (SQLAlchemy)
      v
PostgreSQL (users, sessions, tasks, login_attempts)
```

### A2. Phân loại ứng dụng web: web tĩnh vs web động

- **Web tĩnh**: server chỉ trả về đúng nguyên file có sẵn (HTML/CSS/JS/ảnh),
  không xử lý logic, không truy vấn database, mọi người truy cập cùng 1
  URL đều nhận cùng nội dung.
- **Web động**: nội dung được server sinh ra tuỳ theo request (tham số,
  người dùng đăng nhập, dữ liệu trong DB), có xử lý logic phía server.

**Ứng dụng trong lab là web động**, cụ thể theo mô hình "trang tĩnh gọi
API động" (khác với web động truyền thống kiểu PHP nhúng HTML render
sẵn ở server):
- Các file `.html/.css/.js` trong `frontend/` bản thân chúng là tĩnh —
  Nginx trả về y nguyên, không đổi theo user.
- Nhưng **dữ liệu hiển thị bên trong** (danh sách task, thông tin
  profile) được JavaScript phía client gọi `fetch()` tới FastAPI
  (`/api/tasks`, `/api/users/{id}`...) — FastAPI xử lý logic, truy vấn
  PostgreSQL, trả JSON **khác nhau tuỳ theo user nào đang đăng nhập**
  (nhờ session cookie) → đây chính là tính "động" của ứng dụng.

### A3. Cơ chế web session, cookie, API

**Session (session-based authentication, không dùng JWT):**
1. User gửi `POST /api/auth/login` với username/password.
2. Backend xác thực password (bcrypt), nếu đúng thì tạo **1 bản ghi mới
   trong bảng `sessions`** ở PostgreSQL (`id` là UUID ngẫu nhiên,
   `user_id`, `created_at`, `expires_at = now + SESSION_TIMEOUT_MINUTES`).
3. Backend trả `id` đó về client qua header `Set-Cookie`.
4. Mọi request sau đó, trình duyệt tự động đính kèm cookie này; backend
   tra bảng `sessions` theo `id` để biết request thuộc user nào, còn hạn
   hay không (implement ở `backend/app/deps.py::get_current_user`).
5. Logout: backend **cập nhật `revoked_at`** trong bảng `sessions` (huỷ
   session thật ở server), không chỉ xoá cookie phía client.

Đây là điểm khác biệt cố ý so với JWT: session id là chuỗi ngẫu nhiên vô
nghĩa (opaque token), toàn bộ trạng thái (còn hạn/đã bị revoke) nằm ở
server (bảng `sessions`) — cho phép huỷ session tức thời bất cứ lúc nào,
điều JWT stateless không làm được nếu không có thêm blacklist.

**Cookie** (`session_id`, set trong `backend/app/routers/auth.py`):
- `HttpOnly`: JavaScript phía client không đọc được cookie này → giảm
  rủi ro bị đánh cắp qua XSS.
- `Secure`: cookie chỉ được trình duyệt gửi qua kết nối HTTPS. **Trong
  lab đang tắt** (`SESSION_COOKIE_SECURE=false`) vì chạy HTTP trên
  localhost — phải bật lại khi có HTTPS thật (xem README mục 8).
- `SameSite=Strict`: cookie không được gửi kèm khi request bắt nguồn từ
  site khác → giảm rủi ro CSRF.

**API**: thiết kế theo REST — dùng đúng HTTP method theo ý nghĩa thao tác
(GET đọc, POST tạo, PUT cập nhật, DELETE xoá), trả JSON, dùng đúng HTTP
status code (200/201/400/401/403/404/429/500). Toàn bộ endpoint liệt kê ở
mục B6 bên dưới.

### A4. Các loại log trên ứng dụng web và ý nghĩa

Ứng dụng ghi log ở đúng 4 lớp độc lập, mỗi lớp phục vụ một góc nhìn khác
nhau khi điều tra sự cố (bảng đầy đủ + ý nghĩa SOC ở
[`LOGGING_MAP.md`](LOGGING_MAP.md)):

| Loại log | Layer | Trả lời câu hỏi | Ví dụ |
|---|---|---|---|
| Access/error log của web server | Nginx | Ai gọi gì, từ đâu, kết quả HTTP nào, mất bao lâu? | `remote_addr, uri, status, request_time` |
| Application log (structured JSON) | FastAPI (`app.log`) | Hành động nghiệp vụ nào xảy ra, do ai, thành công hay thất bại? | `event=task_create, user_id, result` |
| Authentication log | FastAPI (`auth.log`, logger riêng) | Ai đăng nhập/đăng xuất, có ai đang bị brute-force không? | `event=ACCOUNT_LOCKED, fail_count` |
| Audit log của database | PostgreSQL | Dữ liệu nào **thực sự bị thay đổi** ở tầng thấp nhất, bất kể qua đường nào? | `INSERT INTO tasks ...` |

Log ở layer thấp hơn (DB) là bằng chứng khó giả mạo nhất nếu tầng
application bị compromise; log ở layer cao hơn (app) giàu ngữ cảnh nghiệp
vụ hơn nhưng phụ thuộc code có log đúng hay không — đây là lý do một hệ
thống SOC trưởng thành cần cả 2, không chỉ 1.

---

## PHẦN B — PHÂN TÍCH & THIẾT KẾ TÍNH NĂNG

### B1. Mô tả bài toán

Xây dựng ứng dụng **quản lý công việc cá nhân (Task Manager)**: mỗi
người dùng có tài khoản riêng, tự tạo/theo dõi/cập nhật/xoá danh sách
công việc cần làm của chính mình (tiêu đề, mô tả, độ ưu tiên, trạng thái,
hạn hoàn thành). Không có vai trò quản trị/chia sẻ công việc giữa nhiều
người dùng — phạm vi tập trung vào việc dựng đúng kiến trúc web chuẩn 4
lớp (frontend/proxy/backend/database) và ghi log đầy đủ ở từng lớp.

### B2. Đối tượng sử dụng

- **Người dùng cá nhân**: đăng ký tài khoản, quản lý công việc của riêng
  mình. Một vai trò duy nhất (không phân admin/user) — việc phân quyền
  chính trong hệ thống là **authorization theo quyền sở hữu dữ liệu**
  (user A không được xem/sửa/xoá task hay profile của user B), không phải
  phân quyền theo role.

### B3. Danh sách chức năng (functional requirements)

| Mã | Chức năng | Mô tả |
|---|---|---|
| FR1 | Đăng ký tài khoản | username, email, password (bcrypt hash, không lưu plaintext) |
| FR2 | Đăng nhập | Session-based, tạo cookie `session_id` HttpOnly |
| FR3 | Đăng xuất | Huỷ session thật ở server (`revoked_at`), không chỉ xoá cookie |
| FR4 | Hết hạn phiên tự động | Session hết hạn sau `SESSION_TIMEOUT_MINUTES` (mặc định 30) kể từ lúc login |
| FR5 | Khoá tài khoản tạm thời | 5 lần đăng nhập sai liên tiếp trong 5 phút (cùng IP hoặc username) → khoá 5 phút |
| FR6 | Xem/cập nhật hồ sơ cá nhân | Chỉ được xem/sửa hồ sơ của chính mình (authorization rõ ràng, chống IDOR) |
| FR7 | Tạo công việc | title, description, priority, status, due_date |
| FR8 | Xem danh sách/chi tiết công việc | Chỉ thấy công việc của chính mình |
| FR9 | Cập nhật công việc | Chỉ chủ sở hữu được sửa; ghi log giá trị cũ/mới từng field thay đổi |
| FR10 | Xoá công việc | Chỉ chủ sở hữu được xoá |
| FR11 | Ghi log đầy đủ | Mọi hành động ở FR1–FR10 đều để lại log ở đúng layer tương ứng (xem LOGGING_MAP.md) |

### B4. Thiết kế cơ sở dữ liệu

**Sơ đồ quan hệ (ERD dạng văn bản):**

```
users (1) ──────< sessions   (1 user có nhiều session, mỗi session thuộc 1 user)
users (1) ──────< tasks      (1 user có nhiều task, mỗi task thuộc 1 user)
users (0..1) ───< login_attempts  (liên kết lỏng qua "username" — vẫn ghi
                                    nhận cả lần thử với username không tồn tại,
                                    nên không đặt khoá ngoại cứng tới users.id)
```

**Bảng `users`**

| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | UUID (PK) | |
| username | varchar(50), unique | |
| email | varchar(255), unique | |
| password_hash | varchar(255) | bcrypt, không bao giờ trả về client |
| created_at / updated_at | timestamptz | |

**Bảng `sessions`**

| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | UUID (PK) | Chính là giá trị cookie `session_id` |
| user_id | UUID (FK → users.id) | |
| created_at | timestamptz | |
| expires_at | timestamptz | Absolute timeout = created_at + SESSION_TIMEOUT_MINUTES |
| revoked_at | timestamptz, nullable | Set khi logout hoặc khi phát hiện hết hạn (lazy expiry) |
| ip_address, user_agent | varchar | Ngữ cảnh phục vụ điều tra |

**Bảng `tasks`**

| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → users.id) | Chủ sở hữu — mọi authorization check dựa vào cột này |
| title | varchar(255) | Bắt buộc |
| description | varchar(2000), nullable | |
| priority | varchar(20) | `low` / `medium` / `high` |
| status | varchar(20) | `todo` / `doing` / `done` |
| due_date | date, nullable | |
| created_at / updated_at | timestamptz | |

**Bảng `login_attempts`**

| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | UUID (PK) | |
| username | varchar(50), nullable | Có thể là username không tồn tại (cố tình dò) |
| ip_address | varchar(64) | |
| success | boolean | |
| created_at | timestamptz, indexed | Dùng để đếm số lần fail trong cửa sổ trượt 5 phút |

### B5. Thiết kế kiến trúc triển khai

4 container Docker riêng biệt, mỗi container 1 trách nhiệm, giao tiếp qua
1 network nội bộ (`lab_net`) — chi tiết xem `docker-compose.yml`:

| Container | Trách nhiệm | Log xuất ra |
|---|---|---|
| `soclab-nginx` | Serve frontend tĩnh + reverse proxy `/api/*` | `logs/nginx/access.log`, `error.log` |
| `soclab-backend` | Business logic, session auth, REST API | `logs/app/app.log`, `logs/app/auth.log` |
| `soclab-db` | Lưu trữ dữ liệu quan hệ | `logs/postgres/postgresql-*.log` |

### B6. Thiết kế API

| Method | Endpoint | Chức năng | Auth | Status thành công |
|---|---|---|---|---|
| POST | `/api/auth/register` | Đăng ký | Không | 201 |
| POST | `/api/auth/login` | Đăng nhập | Không | 200 |
| POST | `/api/auth/logout` | Đăng xuất | Cần session | 204 |
| GET | `/api/users/{id}` | Xem hồ sơ (chỉ chính mình) | Cần session | 200 |
| PUT | `/api/users/{id}` | Sửa hồ sơ (chỉ chính mình) | Cần session | 200 |
| POST | `/api/tasks` | Tạo task | Cần session | 201 |
| GET | `/api/tasks` | Danh sách task của mình | Cần session | 200 |
| GET | `/api/tasks/{id}` | Chi tiết 1 task (chỉ chủ sở hữu) | Cần session | 200 |
| PUT | `/api/tasks/{id}` | Cập nhật task (chỉ chủ sở hữu) | Cần session | 200 |
| DELETE | `/api/tasks/{id}` | Xoá task (chỉ chủ sở hữu) | Cần session | 204 |
| GET | `/api/debug/crash` | Gây lỗi 500 có chủ đích (phục vụ luyện tập) | Không | — (luôn 500) |
| GET | `/api/health` | Health check cho container | Không | 200 |

Mã lỗi dùng chung: `400` (validation), `401` (chưa đăng nhập/session hết
hạn), `403` (không phải chủ sở hữu — IDOR bị chặn), `404` (không tồn
tại), `429` (bị khoá do đăng nhập sai nhiều lần), `500` (lỗi hệ thống,
không lộ stack trace).

### B7. Thiết kế giao diện

| Trang | File | Nội dung chính |
|---|---|---|
| Trang chủ | `index.html` | Trạng thái đăng nhập, nút logout, khu vực test kịch bản crash 500 |
| Đăng ký | `register.html` | Form username/email/password |
| Đăng nhập | `login.html` | Form username/password, redirect về trang chủ khi thành công |
| Hồ sơ | `profile.html` | Xem/sửa hồ sơ theo `user_id` nhập tay (phục vụ test IDOR) |
| Công việc | `tasks.html` | Danh sách task dạng bảng, form tạo mới, tra cứu/sửa/xoá theo `task_id` nhập tay (phục vụ test IDOR) |

Luồng điều hướng chính: `Register → Login → (Home / Profile / Tasks)`.
Mọi trang sau Login đều gọi API với cookie session có sẵn trong trình
duyệt (`credentials: same-origin`); nếu session hết hạn, API trả 401 và
UI hiển thị lỗi trực tiếp (không có redirect tự động về Login trong lab
này — cố ý giữ đơn giản để bạn thấy rõ lỗi 401/`SESSION_EXPIRED` thay vì
bị che đi bởi 1 redirect im lặng).

### B8. Thiết kế logging

Xem chi tiết đầy đủ (Action → Event → Log location → Layer → Fields →
Ghi chú SOC) tại [`LOGGING_MAP.md`](LOGGING_MAP.md). Nguyên tắc thiết kế
cốt lõi:
- Mỗi action nghiệp vụ có ít nhất 1 dòng log ở layer Application, có
  `request_id` để correlate ngược lên Nginx access log.
- Hành động liên quan xác thực (login/logout) được log **kép**: 1 lần ở
  `app.log` (event thường), 1 lần ở `auth.log` (event auth chuyên biệt,
  logger riêng) — mô phỏng tình huống 2 team khác nhau sở hữu 2 nguồn log.
- Chỉ hành động **ghi** dữ liệu (INSERT/UPDATE/DELETE) mới xuất hiện
  trong log Postgres (`log_statement=mod`) — hành động đọc (SELECT) chỉ
  thấy được qua `app.log`, không có ở DB layer.
