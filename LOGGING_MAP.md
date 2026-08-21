# LOGGING_MAP.md — Action → Event → Log Location → Layer → Fields → SOC Notes

Dùng file này để đối chiếu trực tiếp với tài liệu lý thuyết
`Fresher_SOC_Tier3_Web_Application_Training.md`. Mỗi hàng là một sự kiện có
thể log ra khi bạn thao tác trên lab.

Quy ước field chung ở layer Application (`app.log`) — mọi dòng đều có:
`timestamp, level, logger, event, message, request_id, source_ip, user_id,
session_id, result` — các cột "Fields" bên dưới chỉ liệt kê field **thêm**
ngoài bộ field chung đó.

`request_id` là chìa khoá correlation xuyên layer: Nginx tự sinh
`$request_id`, forward xuống backend qua header `X-Request-ID`, backend
dùng lại đúng giá trị đó cho mọi dòng log trong request — nên 1 request
= 1 `request_id` giống nhau ở cả Nginx access log lẫn app.log/auth.log.

| Action (user thao tác) | Event | Log location | Layer | Fields quan trọng | Ghi chú SOC |
|---|---|---|---|---|---|
| Truy cập trang web (bất kỳ trang tĩnh nào) | (access log line, không có `event` riêng) | `logs/nginx/access.log` | Reverse Proxy / Web | `remote_addr, request_method, uri, status, request_time, http_user_agent, session_id, request_id` | Baseline traffic. So khớp `remote_addr` + `http_user_agent` để phát hiện scanner/bot. |
| Gọi bất kỳ API nào (mọi request) | `http_request` | `logs/app/app.log` (stdout + file) | Application | `method, path, status_code, duration_ms` | Access-log tầng app; correlate với dòng Nginx cùng `request_id`. `duration_ms` cao bất thường → khả năng DoS/slow query. |
| Đăng ký tài khoản thành công | `register` | `logs/app/app.log` | Application | `user_id, username` | Đối chiếu username mới tạo hàng loạt cùng 1 `source_ip` → dấu hiệu account farming. |
| Đăng ký thất bại (trùng username/email) | `register` (`result=fail`) | `logs/app/app.log` | Application | `username, email` | Nhiều lần fail liên tiếp cùng IP → dò username tồn tại (enumeration). |
| Đăng nhập đúng | `login_success` | `logs/app/app.log` | Application | `user_id, session_id` | — |
| Đăng nhập đúng | `LOGIN_SUCCESS` | `logs/app/auth.log` | Authentication | `username, user_id, session_id, ip_address` | Log kép có chủ đích: cùng 1 sự kiện login xuất hiện ở cả `app.log` (event thường) và `auth.log` (event auth chuyên biệt, field giàu hơn). Dùng để luyện correlation 2 nguồn. |
| Đăng nhập đúng | (INSERT vào bảng `sessions`) | `logs/postgres/postgresql-*.log` | Database | câu lệnh `INSERT INTO sessions ...` | `log_statement=mod` nên statement này CÓ xuất hiện — đối chiếu timestamp với `LOGIN_SUCCESS`. |
| Đăng nhập sai (chưa đạt ngưỡng khoá) | `login_fail` | `logs/app/app.log` | Application | `username, reason` | — |
| Đăng nhập sai (chưa đạt ngưỡng khoá) | `LOGIN_FAIL` | `logs/app/auth.log` | Authentication | `username, ip_address, reason (user_not_found / bad_password), fail_count` | `reason` cho biết sai mật khẩu hay username không tồn tại — 2 tín hiệu khác nhau khi build rule phát hiện brute-force/credential stuffing. |
| Lần login sai thứ 5 trong 5 phút (cùng IP hoặc username) | `ACCOUNT_LOCKED` | `logs/app/auth.log` | Authentication | `username, ip_address, fail_count, window_minutes, lockout_minutes` | Đây là **event chính** để viết detection rule brute-force trong bài lab. Chỉ log 1 lần tại thời điểm vượt ngưỡng, không lặp lại mỗi request tiếp theo trong lúc còn khoá. |
| Login khi đang bị khoá | `LOGIN_FAIL` (`reason=account_locked`) | `logs/app/auth.log` | Authentication | `username, ip_address, reason=account_locked, fail_count` | HTTP status trả về là 429 — xem thêm ở dòng `http_request`/Nginx cùng `request_id`. |
| Đăng xuất | `logout` | `logs/app/app.log` | Application | `user_id` | — |
| Đăng xuất | `LOGOUT` | `logs/app/auth.log` | Authentication | `user_id, session_id` | Session bị revoke thật ở DB (`revoked_at` được set), không chỉ xoá cookie — kiểm chứng bằng UPDATE statement bên dưới. |
| Đăng xuất | (UPDATE bảng `sessions`, set `revoked_at`) | `logs/postgres/postgresql-*.log` | Database | `UPDATE sessions SET revoked_at = ...` | Bằng chứng session bị huỷ phía server, không phải chỉ client xoá cookie. |
| Dùng session đã hết hạn (gọi API bất kỳ sau khi quá `SESSION_TIMEOUT_MINUTES`) | `SESSION_EXPIRED` | `logs/app/auth.log` | Authentication | `session_id, user_id` | Phát hiện kiểu **lazy**: chỉ log khi có request thực sự dùng session hết hạn đó, không có background job quét định kỳ (thiết kế có chủ đích, tránh nhiễu log). |
| Xem profile của chính mình | `profile_read` | `logs/app/app.log` | Application | `user_id` | SELECT tương ứng ở Postgres **không** xuất hiện trong log DB vì `log_statement=mod` chỉ log ghi, không log đọc — đây chính là điểm đối chiếu "có audit vs không audit". |
| Xem profile người khác (IDOR) | `authorization_denied` | `logs/app/app.log` | Application | `resource=user, resource_id, owner_id, requester_id` | HTTP 403. `requester_id != owner_id` là bằng chứng trực tiếp của một nỗ lực IDOR. |
| Cập nhật profile của chính mình | `profile_update` | `logs/app/app.log` | Application | `changed_fields` (old/new; password bị mask thành `***`) | — |
| Cập nhật profile người khác (IDOR) | `authorization_denied` | `logs/app/app.log` | Application | như trên | HTTP 403, không có UPDATE nào chạy ở DB. |
| Tạo task | `task_create` | `logs/app/app.log` | Application | `task_id, title, priority` | — |
| Tạo task | (INSERT bảng `tasks`) | `logs/postgres/postgresql-*.log` | Database | `INSERT INTO tasks ...` | — |
| Xem danh sách / chi tiết task (của chính mình) | `task_read` | `logs/app/app.log` | Application | `task_id` (chi tiết) hoặc `count` (danh sách) | Không có gì tương ứng trong log Postgres (SELECT không được audit) — tương phản có chủ đích với `task_create/update/delete`. |
| Xem/sửa/xoá task của người khác (IDOR) | `authorization_denied` | `logs/app/app.log` | Application | `resource=task, resource_id, owner_id, requester_id` | HTTP 403. Đây là surface IDOR thứ 2 trong lab, độc lập với profile. |
| Cập nhật task (của chính mình) | `task_update` | `logs/app/app.log` | Application | `task_id, changed_fields` (mỗi field: `{old, new}`) | Ví dụ đổi `status` từ `todo` → `doing` sẽ log `changed_fields: {"status": {"old": "todo", "new": "doing"}}`. |
| Cập nhật task | (UPDATE bảng `tasks`) | `logs/postgres/postgresql-*.log` | Database | `UPDATE tasks SET ...` | Đối chiếu field/giá trị mới với `changed_fields` ở app.log. |
| Xoá task (của chính mình) | `task_delete` | `logs/app/app.log` | Application | `task_id` | — |
| Xoá task | (DELETE bảng `tasks`) | `logs/postgres/postgresql-*.log` | Database | `DELETE FROM tasks WHERE id = ...` | — |
| Gửi request sai định dạng/thiếu field bắt buộc | `validation_error` | `logs/app/app.log` | Application | `path, errors` (chi tiết lỗi pydantic) | HTTP 400. Không có stack trace vì đây là lỗi input hợp lệ về mặt xử lý, không phải exception. |
| Gọi `GET /api/debug/crash` | `unhandled_exception` | `logs/app/app.log` | Application | `path, exception_type, stack_trace` | HTTP 500 trả về **chỉ** `{"detail": "...", "request_id": ...}` — KHÔNG có stack trace ra client. Stack trace đầy đủ chỉ nằm trong file/stdout server-side. Dùng `request_id` trong response để grep đúng dòng log. |
| Bất kỳ hành động nào ở trên | tương ứng | `docker logs soclab-nginx` / `docker logs soclab-backend` / `docker logs soclab-db` | OS / Container | toàn bộ stdout của từng container | Tương đương "OS layer" trong bài lab — xem README mục "Xem log container". |

## Ghi chú thiết kế quan trọng (đọc trước khi đối chiếu lý thuyết)

1. **Vì sao có 2 logger (`app` và `auth`) log trùng sự kiện login/logout?**
   Đây là chủ đích: `app.log` đóng vai trò nhật ký hành động tổng quát
   (dùng `event` chữ thường, ví dụ `login_success`), còn `auth.log` là log
   chuyên biệt layer xác thực (dùng `event` chữ HOA, ví dụ `LOGIN_SUCCESS`,
   field auth-specific như `reason`, `fail_count`). Trong thực tế, 2 nguồn
   này có thể được 2 team khác nhau sở hữu (AppSec vs IAM) — bài lab mô
   phỏng đúng tình huống bạn phải correlate hai log riêng biệt của cùng
   một sự kiện nghiệp vụ.

2. **Vì sao SELECT không xuất hiện trong log Postgres?**
   `log_statement = 'mod'` chỉ audit INSERT/UPDATE/DELETE. Đây là cấu hình
   Postgres thực tế phổ biến (log toàn bộ SELECT quá tốn dung lượng). Hệ
   quả: mọi hành động "đọc" (`profile_read`, `task_read`) chỉ có thể quan
   sát được qua `app.log`, không có ở DB layer — một điểm dạy quan trọng
   về giới hạn của audit log DB.

3. **`ACCOUNT_LOCKED` chỉ log một lần tại thời điểm vượt ngưỡng**, không
   lặp lại ở mỗi request tiếp theo trong lúc còn bị khoá (những request đó
   chỉ tạo ra `LOGIN_FAIL` với `reason=account_locked`). Khi viết detection
   rule, `ACCOUNT_LOCKED` = tín hiệu "đã khoá", còn chuỗi `LOGIN_FAIL`
   liên tiếp trước đó = tín hiệu "đang bị brute-force".
