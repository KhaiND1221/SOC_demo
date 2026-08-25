# PHÂN TÍCH & THIẾT KẾ ỨNG DỤNG — Task Manager

Tài liệu này gồm 2 phần: (A) cơ sở lý thuyết nền tảng về ứng dụng web,
áp dụng trực tiếp vào các quyết định thiết kế của ứng dụng trong repo
này; (B) bản phân tích & thiết kế tính năng của ứng dụng.

---

## PHẦN A — CƠ SỞ LÝ THUYẾT (áp dụng vào ứng dụng đã xây)

### A1. Cấu trúc của một ứng dụng web điển hình

| Lớp | Công nghệ phổ biến | Công nghệ dùng trong ứng dụng này | Vai trò |
|---|---|---|---|
| Frontend (trình duyệt client) | HTML, CSS, JS | HTML/CSS/JS thuần (`frontend/`) | Render UI, gọi REST API qua `fetch()`, không có business logic nhạy cảm (mọi validate/authZ thật đều nằm ở backend). |
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

**Ứng dụng này là web động**, cụ thể theo mô hình "trang tĩnh gọi API
động" (khác với web động truyền thống kiểu PHP nhúng HTML render sẵn ở
server):
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
- `Secure`: cookie chỉ được trình duyệt gửi qua kết nối HTTPS. Trong
  môi trường dev đang tắt (`SESSION_COOKIE_SECURE=false`) vì chạy HTTP
  trên localhost — phải bật lại khi có HTTPS thật (xem README mục 3, 6).
- `SameSite=Strict`: cookie không được gửi kèm khi request bắt nguồn từ
  site khác → giảm rủi ro CSRF.

**API**: thiết kế theo REST — dùng đúng HTTP method theo ý nghĩa thao tác
(GET đọc, POST tạo, PUT cập nhật, DELETE xoá), trả JSON, dùng đúng HTTP
status code (200/201/400/401/403/404/429/500). Toàn bộ endpoint liệt kê ở
mục B6 bên dưới.

Các loại log ứng dụng sinh ra khi vận hành (access log, application log,
authentication log, audit log database) và ý nghĩa của từng loại được
phân tích riêng ở [`LOGGING_MAP.md`](LOGGING_MAP.md).

---

## PHẦN B — PHÂN TÍCH & THIẾT KẾ TÍNH NĂNG

### B1. Mô tả bài toán

Xây dựng ứng dụng **quản lý công việc cá nhân (Task Manager)**: mỗi
người dùng có tài khoản riêng, tự tạo/theo dõi/cập nhật/xoá danh sách
công việc cần làm của chính mình (tiêu đề, mô tả, độ ưu tiên, trạng thái,
hạn hoàn thành). Không có vai trò quản trị/chia sẻ công việc giữa nhiều
người dùng — phạm vi tập trung vào việc dựng đúng kiến trúc web chuẩn 4
lớp (frontend/proxy/backend/database).

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
| FR6 | Xem/cập nhật hồ sơ cá nhân | Chỉ được xem/sửa hồ sơ của chính mình (chống truy cập trái phép) |
| FR7 | Tạo công việc | title, description, priority, status, due_date |
| FR8 | Xem danh sách/chi tiết công việc | Chỉ thấy công việc của chính mình |
| FR9 | Cập nhật công việc | Chỉ chủ sở hữu được sửa; ghi log giá trị cũ/mới từng field thay đổi |
| FR10 | Xoá công việc | Chỉ chủ sở hữu được xoá |
| FR11 | Ghi log đầy đủ | Mọi hành động ở FR1–FR10 đều để lại log ở đúng layer tương ứng (xem LOGGING_MAP.md) |
| FR12 | Gắn nhãn (category) & lọc công việc theo nhãn | Mỗi task có thể gắn 1 nhãn tự do (VD: `work`, `study`, `personal`); danh sách task lọc được theo nhãn. Bổ sung ở đợt nâng cấp 1 — xem [`VAN_HANH_NANG_CAP.md`](VAN_HANH_NANG_CAP.md). |
| FR13 | Ghi chú (comment) cho công việc | Mỗi task có thể có nhiều ghi chú theo thời gian; chỉ chủ sở hữu task mới xem/thêm/xoá được ghi chú của task đó. Bổ sung ở đợt nâng cấp 2 — xem [`VAN_HANH_NANG_CAP.md`](VAN_HANH_NANG_CAP.md). |

### B4. Thiết kế cơ sở dữ liệu

**Sơ đồ quan hệ (ERD dạng văn bản):**

```
users (1) ──────< sessions   (1 user có nhiều session, mỗi session thuộc 1 user)
users (1) ──────< tasks      (1 user có nhiều task, mỗi task thuộc 1 user)
tasks (1) ──────< task_comments  (1 task có nhiều comment; ON DELETE CASCADE
                                    — xoá task thì xoá theo comment, xem 3.2
                                    trong VAN_HANH_NANG_CAP.md)
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
| category | varchar(50), nullable | Nhãn tự do (VD: `work`/`study`/`personal`); thêm ở đợt nâng cấp, xem `VAN_HANH_NANG_CAP.md` |
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

**Bảng `task_comments`** (thêm ở đợt nâng cấp 2)

| Cột | Kiểu | Ghi chú |
|---|---|---|
| id | UUID (PK) | |
| task_id | UUID (FK → tasks.id, `ON DELETE CASCADE`) | Xoá task thì xoá theo comment — quyết định thiết kế có chủ đích, giải thích đầy đủ ở `VAN_HANH_NANG_CAP.md` mục 3.2 |
| user_id | UUID (FK → users.id) | Người viết ghi chú |
| content | varchar(1000) | |
| created_at | timestamptz | Không có `updated_at` — comment không hỗ trợ sửa, chỉ tạo/xoá |

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
| GET | `/api/tasks?category=` | Danh sách task của mình, lọc theo nhãn (query param `category` optional) | Cần session | 200 |
| GET | `/api/tasks/{id}` | Chi tiết 1 task (chỉ chủ sở hữu) | Cần session | 200 |
| PUT | `/api/tasks/{id}` | Cập nhật task (chỉ chủ sở hữu) | Cần session | 200 |
| DELETE | `/api/tasks/{id}` | Xoá task (chỉ chủ sở hữu) | Cần session | 204 |
| POST | `/api/tasks/{id}/comments` | Thêm ghi chú cho task (chỉ chủ sở hữu) | Cần session | 201 |
| GET | `/api/tasks/{id}/comments` | Danh sách ghi chú của task (chỉ chủ sở hữu) | Cần session | 200 |
| DELETE | `/api/tasks/{id}/comments/{comment_id}` | Xoá 1 ghi chú (chỉ chủ sở hữu task) | Cần session | 204 |
| GET | `/api/health` | Health check cho container | Không | 200 |

Mã lỗi dùng chung: `400` (validation), `401` (chưa đăng nhập/session hết
hạn), `403` (không phải chủ sở hữu), `404` (không tồn tại), `429` (bị
khoá do đăng nhập sai nhiều lần), `500` (lỗi hệ thống, không lộ stack
trace).

### B7. Thiết kế giao diện

| Trang | File | Nội dung chính |
|---|---|---|
| Trang chủ | `index.html` | Trạng thái đăng nhập, nút logout |
| Đăng ký | `register.html` | Form username/email/password |
| Đăng nhập | `login.html` | Form username/password, redirect về trang chủ khi thành công |
| Hồ sơ | `profile.html` | Xem/sửa hồ sơ của người đang đăng nhập |
| Công việc | `tasks.html` | Danh sách task dạng bảng (đổi trạng thái inline), form tạo mới, xem chi tiết/xoá theo từng dòng; modal chi tiết có thêm khu vực ghi chú (xem/thêm/xoá comment) |

Luồng điều hướng chính: `Register → Login → (Home / Profile / Tasks)`.
Mọi trang sau Login đều gọi API với cookie session có sẵn trong trình
duyệt (`credentials: same-origin`); nếu session hết hạn, API trả 401 và
UI hiển thị lỗi trực tiếp.

### B8. Thiết kế logging

Xem chi tiết đầy đủ (Action → Event → Log location → Layer → Fields →
ý nghĩa khi phân tích sự cố) tại [`LOGGING_MAP.md`](LOGGING_MAP.md).
Nguyên tắc thiết kế cốt lõi:
- Mỗi action nghiệp vụ có ít nhất 1 dòng log ở layer Application, có
  `request_id` để correlate ngược lên Nginx access log.
- Hành động liên quan xác thực (login/logout) được log **kép**: 1 lần ở
  `app.log` (event thường), 1 lần ở `auth.log` (event auth chuyên biệt,
  logger riêng) — mô phỏng tình huống 2 team khác nhau sở hữu 2 nguồn log.
- Chỉ hành động **ghi** dữ liệu (INSERT/UPDATE/DELETE) mới xuất hiện
  trong log Postgres (`log_statement=mod`) — hành động đọc (SELECT) chỉ
  thấy được qua `app.log`, không có ở DB layer.
