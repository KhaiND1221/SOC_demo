# Phân tích log — Task Manager

Đây là báo cáo phân tích các sự kiện log sinh ra khi ứng dụng Task
Manager hoạt động: ai truy cập, đăng nhập, dùng tính năng nào, phát
sinh lỗi gì, và log đó nằm ở đâu, thuộc layer nào trong kiến trúc 4
lớp (Nginx / FastAPI / PostgreSQL / OS-container). Đây là công việc
theo dõi luồng hoạt động ứng dụng, thực hiện **sau khi** ứng dụng ở
[`PHAN_TICH_THIET_KE.md`](PHAN_TICH_THIET_KE.md) đã được xây xong và
chạy thật — không phải một tính năng của ứng dụng.

## Các loại log và ý nghĩa

| Loại log | Layer | Trả lời câu hỏi | Ví dụ |
|---|---|---|---|
| Access/error log của web server | Nginx | Ai gọi gì, từ đâu, kết quả HTTP nào, mất bao lâu? | `remote_addr, uri, status, request_time` |
| Application log (structured JSON) | FastAPI (`app.log`) | Hành động nghiệp vụ nào xảy ra, do ai, thành công hay thất bại? | `event=task_create, user_id, result` |
| Authentication log | FastAPI (`auth.log`, logger riêng) | Ai đăng nhập/đăng xuất, có ai đang bị brute-force không? | `event=ACCOUNT_LOCKED, fail_count` |
| Audit log của database | PostgreSQL | Dữ liệu nào **thực sự bị thay đổi** ở tầng thấp nhất, bất kể qua đường nào? | `INSERT INTO tasks ...` |

Log ở layer thấp hơn (DB) là bằng chứng khó giả mạo nhất nếu tầng
application bị lỗi/bị can thiệp; log ở layer cao hơn (app) giàu ngữ
cảnh nghiệp vụ hơn nhưng phụ thuộc code có log đúng hay không — cần cả
2 để có bức tranh đầy đủ khi điều tra một sự cố.

`request_id` là chìa khoá correlation xuyên layer: Nginx tự sinh
`$request_id`, forward xuống backend qua header `X-Request-ID`, backend
dùng lại đúng giá trị đó cho mọi dòng log trong request — nên 1 request
= 1 `request_id` giống nhau ở cả Nginx access log lẫn app.log/auth.log.

Quy ước field chung ở layer Application (`app.log`) — mọi dòng đều có:
`timestamp, level, logger, event, message, request_id, source_ip, user_id,
session_id, result` — các cột "Fields" bên dưới chỉ liệt kê field **thêm**
ngoài bộ field chung đó.

## Bảng mapping: Action → Event → Log location → Layer → Fields

| Action (user thao tác) | Event | Log location | Layer | Fields quan trọng | Ghi chú khi phân tích |
|---|---|---|---|---|---|
| Truy cập trang web (bất kỳ trang tĩnh nào) | (access log line, không có `event` riêng) | `logs/nginx/access.log` | Reverse Proxy / Web | `remote_addr, request_method, uri, status, request_time, http_user_agent, session_id, request_id` | Baseline traffic. So khớp `remote_addr` + `http_user_agent` để phát hiện scanner/bot. |
| Gọi bất kỳ API nào (mọi request) | `http_request` | `logs/app/app.log` (stdout + file) | Application | `method, path, status_code, duration_ms` | Access-log tầng app; correlate với dòng Nginx cùng `request_id`. `duration_ms` cao bất thường → khả năng slow query/DoS. |
| Đăng ký tài khoản thành công | `register` | `logs/app/app.log` | Application | `user_id, username` | Đối chiếu username mới tạo hàng loạt cùng 1 `source_ip` → dấu hiệu account farming. |
| Đăng ký thất bại (trùng username/email) | `register` (`result=fail`) | `logs/app/app.log` | Application | `username, email` | Nhiều lần fail liên tiếp cùng IP → dò username tồn tại (enumeration). |
| Đăng nhập đúng | `login_success` | `logs/app/app.log` | Application | `user_id, session_id` | — |
| Đăng nhập đúng | `LOGIN_SUCCESS` | `logs/app/auth.log` | Authentication | `username, user_id, session_id, ip_address` | Log kép có chủ đích: cùng 1 sự kiện login xuất hiện ở cả `app.log` (event thường) và `auth.log` (event auth chuyên biệt, field giàu hơn) — mô phỏng tình huống 2 team khác nhau sở hữu 2 nguồn log. |
| Đăng nhập đúng | (INSERT vào bảng `sessions`) | `logs/postgres/postgresql-*.log` | Database | câu lệnh `INSERT INTO sessions ...` | `log_statement=mod` nên statement này CÓ xuất hiện — đối chiếu timestamp với `LOGIN_SUCCESS`. |
| Đăng nhập sai (chưa đạt ngưỡng khoá) | `login_fail` | `logs/app/app.log` | Application | `username, reason` | — |
| Đăng nhập sai (chưa đạt ngưỡng khoá) | `LOGIN_FAIL` | `logs/app/auth.log` | Authentication | `username, ip_address, reason (user_not_found / bad_password), fail_count` | `reason` cho biết sai mật khẩu hay username không tồn tại — 2 tín hiệu khác nhau khi build rule phát hiện brute-force/credential stuffing. |
| Lần login sai thứ 5 trong 5 phút (cùng IP hoặc username) | `ACCOUNT_LOCKED` | `logs/app/auth.log` | Authentication | `username, ip_address, fail_count, window_minutes, lockout_minutes` | Event chính để phát hiện brute-force. Chỉ log 1 lần tại thời điểm vượt ngưỡng, không lặp lại mỗi request tiếp theo trong lúc còn khoá. |
| Login khi đang bị khoá | `LOGIN_FAIL` (`reason=account_locked`) | `logs/app/auth.log` | Authentication | `username, ip_address, reason=account_locked, fail_count` | HTTP status trả về là 429 — xem thêm ở dòng `http_request`/Nginx cùng `request_id`. |
| Đăng xuất | `logout` | `logs/app/app.log` | Application | `user_id` | — |
| Đăng xuất | `LOGOUT` | `logs/app/auth.log` | Authentication | `user_id, session_id` | Session bị revoke thật ở DB (`revoked_at` được set), không chỉ xoá cookie — kiểm chứng bằng UPDATE statement bên dưới. |
| Đăng xuất | (UPDATE bảng `sessions`, set `revoked_at`) | `logs/postgres/postgresql-*.log` | Database | `UPDATE sessions SET revoked_at = ...` | Bằng chứng session bị huỷ phía server, không phải chỉ client xoá cookie. |
| Dùng session đã hết hạn (gọi API bất kỳ sau khi quá `SESSION_TIMEOUT_MINUTES`) | `SESSION_EXPIRED` | `logs/app/auth.log` | Authentication | `session_id, user_id` | Phát hiện kiểu **lazy**: chỉ log khi có request thực sự dùng session hết hạn đó, không có background job quét định kỳ. |
| Xem profile của chính mình | `profile_read` | `logs/app/app.log` | Application | `user_id` | SELECT tương ứng ở Postgres **không** xuất hiện trong log DB vì `log_statement=mod` chỉ log ghi, không log đọc — đây chính là điểm đối chiếu "có audit vs không audit". |
| Truy cập profile của người khác (bị chặn) | `authorization_denied` | `logs/app/app.log` | Application | `resource=user, resource_id, owner_id, requester_id` | HTTP 403. `requester_id != owner_id` là bằng chứng trực tiếp của một nỗ lực truy cập trái phép (IDOR). |
| Cập nhật profile của chính mình | `profile_update` | `logs/app/app.log` | Application | `changed_fields` (old/new; password bị mask thành `***`) | — |
| Cập nhật profile người khác (bị chặn) | `authorization_denied` | `logs/app/app.log` | Application | như trên | HTTP 403, không có UPDATE nào chạy ở DB. |
| Tạo task | `task_create` | `logs/app/app.log` | Application | `task_id, title, priority, category` | `category` là nullable — có thể là `null` nếu user không gắn nhãn. |
| Tạo task | (INSERT bảng `tasks`) | `logs/postgres/postgresql-*.log` | Database | `INSERT INTO tasks ...` | — |
| Xem danh sách task, có/không lọc theo category | `task_read` | `logs/app/app.log` | Application | `count, category_filter` | `category_filter=null` nghĩa là xem toàn bộ, không lọc. Dùng để phân biệt user đang duyệt hết task hay tìm theo 1 nhãn cụ thể. |
| Xem chi tiết 1 task (của chính mình) | `task_read` | `logs/app/app.log` | Application | `task_id` | Không có gì tương ứng trong log Postgres (SELECT không được audit) — tương phản có chủ đích với `task_create/update/delete`. |
| Xem/sửa/xoá task của người khác (bị chặn) | `authorization_denied` | `logs/app/app.log` | Application | `resource=task, resource_id, owner_id, requester_id` | HTTP 403. Surface thứ 2 của cùng loại lỗi authorization, độc lập với profile. |
| Cập nhật task (của chính mình) | `task_update` | `logs/app/app.log` | Application | `task_id, changed_fields` (mỗi field: `{old, new}`) | Ví dụ đổi `status` từ `todo` → `doing` sẽ log `changed_fields: {"status": {"old": "todo", "new": "doing"}}`. |
| Cập nhật task | (UPDATE bảng `tasks`) | `logs/postgres/postgresql-*.log` | Database | `UPDATE tasks SET ...` | Đối chiếu field/giá trị mới với `changed_fields` ở app.log. |
| Xoá task (của chính mình) | `task_delete` | `logs/app/app.log` | Application | `task_id, cascaded_comments_deleted` | `cascaded_comments_deleted` đếm số comment bị xoá theo (cascade) — **bù cho điểm mù** của Postgres (xem ghi chú thiết kế #4 bên dưới). |
| Xoá task | (DELETE bảng `tasks`) | `logs/postgres/postgresql-*.log` | Database | `DELETE FROM tasks WHERE id = ...` | Chỉ có đúng 1 dòng, dù task có comment con hay không — xem ghi chú #4. |
| Thêm ghi chú (comment) cho task (của chính mình) | `comment_create` | `logs/app/app.log` | Application | `task_id, comment_id` | Log ghi SAU KHI `db.commit()` thành công ("log on commit"), không log ngay khi nhận request — xem `VAN_HANH_NANG_CAP.md` mục 3.3. |
| Thêm comment | (INSERT bảng `task_comments`) | `logs/postgres/postgresql-*.log` | Database | `INSERT INTO task_comments ...` | — |
| Xem danh sách comment của 1 task (của chính mình) | `comment_read` | `logs/app/app.log` | Application | `task_id, count` | Không có gì tương ứng ở Postgres log (SELECT không audit) — cùng nguyên tắc với `task_read`. |
| Thêm/xem/xoá comment trên task của người khác (bị chặn) | `authorization_denied` | `logs/app/app.log` | Application | `resource=task, resource_id, owner_id, requester_id` | HTTP 403 — dùng chung hàm kiểm tra quyền sở hữu với task (`get_owned_task`), vì comment luôn đi kèm 1 task cụ thể. |
| Xoá 1 comment (của chính mình) | `comment_delete` | `logs/app/app.log` | Application | `task_id, comment_id` | — |
| Xoá comment | (DELETE bảng `task_comments`) | `logs/postgres/postgresql-*.log` | Database | `DELETE FROM task_comments WHERE id = ...` | Đây là DELETE do client gọi trực tiếp (không phải cascade) nên CÓ xuất hiện — khác với trường hợp #4 bên dưới. |
| Gửi request sai định dạng/thiếu field bắt buộc | `validation_error` | `logs/app/app.log` | Application | `path, errors` (chi tiết lỗi pydantic) | HTTP 400. Không có stack trace vì đây là lỗi input hợp lệ về mặt xử lý, không phải exception. |
| Lỗi server ngoài dự kiến (bug thật trong code, không phải input sai) | `unhandled_exception` | `logs/app/app.log` | Application | `path, exception_type, stack_trace` | HTTP 500 trả về **chỉ** `{"detail": "...", "request_id": ...}` — KHÔNG có stack trace ra client. Stack trace đầy đủ chỉ nằm trong file/stdout server-side (xử lý ở `app/main.py::unhandled_exception_handler`, áp dụng cho mọi exception không được bắt riêng, không cần một endpoint riêng để gây ra). |
| Bất kỳ hành động nào ở trên | tương ứng | `docker logs soclab-nginx` / `docker logs soclab-backend` / `docker logs soclab-db` | OS / Container | toàn bộ stdout của từng container | Tương đương "OS layer" — xem README mục 5. |

## Ghi chú thiết kế quan trọng

1. **Vì sao có 2 logger (`app` và `auth`) log trùng sự kiện login/logout?**
   Đây là chủ đích: `app.log` đóng vai trò nhật ký hành động tổng quát
   (dùng `event` chữ thường, ví dụ `login_success`), còn `auth.log` là log
   chuyên biệt layer xác thực (dùng `event` chữ HOA, ví dụ `LOGIN_SUCCESS`,
   field auth-specific như `reason`, `fail_count`). Trong thực tế, 2 nguồn
   này có thể được 2 team khác nhau sở hữu (AppSec vs IAM) — cần biết
   correlate hai log riêng biệt của cùng một sự kiện nghiệp vụ.

2. **Vì sao SELECT không xuất hiện trong log Postgres?**
   `log_statement = 'mod'` chỉ audit INSERT/UPDATE/DELETE. Đây là cấu hình
   Postgres thực tế phổ biến (log toàn bộ SELECT quá tốn dung lượng). Hệ
   quả: mọi hành động "đọc" (`profile_read`, `task_read`) chỉ có thể quan
   sát được qua `app.log`, không có ở DB layer — một giới hạn quan trọng
   của audit log DB cần biết khi điều tra sự cố.

3. **`ACCOUNT_LOCKED` chỉ log một lần tại thời điểm vượt ngưỡng**, không
   lặp lại ở mỗi request tiếp theo trong lúc còn bị khoá (những request đó
   chỉ tạo ra `LOGIN_FAIL` với `reason=account_locked`). `ACCOUNT_LOCKED` =
   tín hiệu "đã khoá", còn chuỗi `LOGIN_FAIL` liên tiếp trước đó = tín hiệu
   "đang bị brute-force".

4. **CASCADE DELETE là điểm mù (blind spot) của log Postgres.** Khi xoá 1
   task có comment con (`ON DELETE CASCADE` trên `task_comments.task_id`),
   log Postgres **chỉ** có 1 dòng `DELETE FROM tasks ...` — **không có**
   dòng `DELETE FROM task_comments` nào, dù comment con thực sự đã bị xoá.
   Lý do: cascade là hành động **nội bộ** Postgres tự thực hiện để giữ
   ràng buộc khoá ngoại, không phải câu lệnh SQL do client gửi lên, nên
   `log_statement=mod` (chỉ ghi lại câu lệnh client gửi) không thấy được.
   Đây là giới hạn thật của Postgres, không sửa được ở tầng DB — đã bù lại
   bằng cách log tường minh `cascaded_comments_deleted` ở tầng Application
   (xem dòng `task_delete` ở bảng trên, và giải thích đầy đủ ở
   `VAN_HANH_NANG_CAP.md` mục 3.4). Bài học: khi phát hiện 1 layer có điểm
   mù, phải chủ động bù bằng layer khác mình kiểm soát được — không được
   để trống, vì mentor/SOC analyst hoàn toàn có thể hỏi thẳng "dữ liệu đó
   biến mất đi đâu, ai xoá, xoá khi nào" và log phải trả lời được.

## Phụ lục: kịch bản thao tác để tự sinh ra các log trên

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
curl.exe -b cookies.txt http://localhost:8080/api/tasks
```
→ xem: `logs/app/app.log` (`task_read`). Kiểm tra Postgres log cùng thời
điểm — sẽ **không** có gì (SELECT không audit), đối lập với bước 7-9.

**7. Create**
```powershell
curl.exe -b cookies.txt -X POST http://localhost:8080/api/tasks `
  -H "Content-Type: application/json" `
  -d '{"title":"Viết báo cáo tuần","priority":"high","status":"todo","due_date":"2026-08-25"}'
```
→ xem: `logs/app/app.log` (`task_create`) + Postgres log (`INSERT INTO
tasks`). Lưu lại `id` trả về để dùng ở bước 8-9.

**8. Update**
```powershell
curl.exe -b cookies.txt -X PUT http://localhost:8080/api/tasks/<task_id> `
  -H "Content-Type: application/json" `
  -d '{"status":"doing"}'
```
→ xem: `logs/app/app.log` (`task_update`, có `changed_fields` với
old/new) + Postgres log (`UPDATE tasks`).

**9. Delete**
```powershell
curl.exe -b cookies.txt -X DELETE http://localhost:8080/api/tasks/<task_id>
```
→ xem: `logs/app/app.log` (`task_delete`) + Postgres log (`DELETE FROM
tasks`).

**10. Request không hợp lệ**
```powershell
curl.exe -X POST http://localhost:8080/api/auth/register `
  -H "Content-Type: application/json" -d '{"username":"x"}'
```
→ xem: `logs/app/app.log` — `event="validation_error"`, HTTP 400.

**11. Kiểm tra authorization (đăng nhập bằng bob, thử đọc profile/task của alice bằng ID của alice)**

Đây là bước kiểm thử bảo mật (không phải chức năng của app) để xác nhận
authorization theo quyền sở hữu dữ liệu hoạt động đúng — quan trọng vì
đây là control chính bảo vệ dữ liệu người dùng trong ứng dụng này.

```powershell
curl.exe -c bob.txt -b bob.txt -X POST http://localhost:8080/api/auth/login `
  -H "Content-Type: application/json" -d '{"username":"bob","password":"Passw0rd!"}'

curl.exe -b bob.txt http://localhost:8080/api/users/<alice_user_id>
curl.exe -b bob.txt http://localhost:8080/api/tasks/<alice_task_id>
```
→ cả hai trả HTTP 403, và `logs/app/app.log` có `event=
"authorization_denied"` với `owner_id != requester_id` — bằng chứng trực
tiếp cho một nỗ lực truy cập trái phép (IDOR).
