# KỊCH BẢN DEMO (quay video)

Kịch bản này để bạn **vừa thao tác vừa quay màn hình**, trình bày đủ 3
mục yêu cầu: (1) ứng dụng đầy đủ chức năng, (2) log/theo dõi luồng hoạt
động, (3) vận hành/nâng cấp mã nguồn. Thời lượng ước tính: 12–15 phút.

**Nguyên tắc bắt buộc khi trình bày log** (áp dụng cho MỌI bước có log ở
Phần 2): không được dừng lại ở việc chỉ đọc tên `event`. Với mỗi bằng
chứng log, phải làm đủ 3 việc, theo đúng thứ tự:

1. **Đọc tên event** (nhãn tóm tắt) — ví dụ `task_create`.
2. **Bóc tách field cụ thể** trong dòng log đó — đọc to từng field quan
   trọng (`user_id`, `request_id`, `result`, field nghiệp vụ...), không
   chỉ nói "log hiện ra rồi".
3. **Đối chiếu với bằng chứng ở layer thấp hơn** (log Postgres —
   câu lệnh SQL thật) — chỉ ra đúng dòng SQL tương ứng, xác nhận
   field ở app.log/auth.log (layer cao, dễ bị code sai/giả) khớp với
   những gì thực sự được ghi xuống database (layer thấp, khó giả mạo
   hơn). Đây là bước **xác thực**, không phải chỉ "quan sát" — kết
   luận chỉ có giá trị khi 2 lớp khớp nhau.

## 0. Chuẩn bị trước khi quay (không quay phần này)

```powershell
cd C:\Users\khain\SOC_demo
docker compose ps                      # cả 3 container phải Up/healthy
```

Mở sẵn, xếp cạnh nhau trên màn hình (để trong lúc quay không phải
Alt+Tab lục tìm):
- **Cửa sổ 1**: trình duyệt, mở `http://localhost:8080`
- **Cửa sổ 2**: PowerShell, chạy `.\watch-logs.ps1` — đây là nguồn bằng
  chứng chính xuyên suốt buổi demo (gộp Nginx/App/Auth/DB theo đúng thời
  gian thực, xem `README.md` mục 5 nếu cần nhắc lại cách dùng).
- **Cửa sổ 3**: PowerShell/psql riêng, dùng khi cần `docker compose exec
  db psql ...` để đối chiếu dữ liệu thật (bước 2.6, phần vận hành).
- **Cửa sổ 4** (tuỳ chọn): file `VAN_HANH_NANG_CAP.md` mở sẵn cho Phần 3.

---

## PHẦN 1 — Giới thiệu + demo chức năng (Mục 1 đề bài)

**1.1. Giới thiệu kiến trúc (30s, nói trước camera, không cần thao tác)**
Nêu ngắn gọn: ứng dụng Task Manager, kiến trúc 4 lớp Frontend → Nginx →
FastAPI → PostgreSQL, mỗi lớp 1 container Docker riêng. Tài liệu phân
tích/thiết kế ở `PHAN_TICH_THIET_KE.md` (có thể lướt qua ERD 1 lần).

**1.2. Đăng ký + xác minh password KHÔNG lưu plaintext + Đăng nhập**
- Vào `/register.html`, tạo tài khoản mới (nhớ tên, dùng lại ở 2.2).
- **Trước khi đăng nhập**, chuyển sang cửa sổ 3, chạy:
  ```powershell
  docker compose exec db psql -U soclab -d soclab -c "SELECT username, password_hash FROM users ORDER BY created_at DESC LIMIT 1;"
  ```
  → chỉ ra `password_hash` là 1 chuỗi bcrypt (`$2b$...`), không phải mật khẩu gốc vừa gõ. Vì
  Postgres (`log_statement=mod`) ghi lại **toàn bộ giá trị literal** của câu `INSERT`, có thể mở
  thêm `logs\postgres\postgresql-<ngày>.log` để chỉ ra: ngay cả ở tầng audit log thấp nhất, giá
  trị xuất hiện cũng đã là bản hash — mật khẩu gốc (plaintext) không bao giờ chạm tới bất kỳ log
  hay bảng nào trong hệ thống, vì việc hash (`backend/app/security.py`, dùng `bcrypt`) xảy ra ở
  tầng ứng dụng trước khi câu SQL được gửi đi.
- Đăng nhập ở `/login.html` → tự chuyển về trang chủ.

**1.3. Quản lý task (CRUD + category)**
- Vào `/tasks.html`: chỉ ra 3 ô đếm Chưa làm/Đang làm/Hoàn thành ở đầu
  trang (tự cập nhật theo danh sách hiện có).
- Bấm nút **"+ Thêm việc"** để mở form tạo task (form mặc định đang ẩn).
- Tạo 2–3 task, gắn category khác nhau (vd `work`, `study`).
- Thử tạo 1 task **trùng tiêu đề** với task vừa tạo → chỉ ra hộp thoại
  cảnh báo hiện ra trước khi cho tạo (tính năng chống nhầm lẫn).
- Lọc theo category → chỉ hiện đúng task thuộc nhãn đó, đồng thời 3 ô
  đếm ở trên cũng đổi theo đúng bộ lọc.
- Sửa trạng thái 1 task (`todo` → `doing`) ngay trên dropdown ở bảng.
- Bấm "Xem" để mở modal chi tiết task.
- Xoá 1 task.

**1.4. Hồ sơ cá nhân**
- Vào `/profile.html`, đổi email → lưu → thấy cập nhật ngay.

*(Phần 1 chỉ cần thao tác mượt, chưa cần nhìn log — log sẽ được đối
chiếu lại ở Phần 2.)*

---

## PHẦN 2 — Theo dõi luồng hoạt động qua log (Mục 2 đề bài)

Chuyển sang cửa sổ `watch-logs.ps1`. Từng bước dưới đây: **làm hành
động → dừng lại → áp dụng đúng quy trình 3 bước ở đầu file**.

### 2.1. Đăng nhập thành công
- Hành động: đăng nhập lại (hoặc dùng tài khoản vừa tạo).
- Bóc field: dòng `[AUTH] ... LOGIN_SUCCESS` — đọc to `username`,
  `user_id`, `session_id`, `ip_address`, `result=success`. Chỉ thêm dòng
  `[APP] ... login_success` (log kép, 2 nguồn cho cùng 1 sự kiện).
- Đối chiếu lớp thấp: dòng `[DB] INSERT sessions` cùng thời điểm —
  chứng minh 1 bản ghi session **thật sự** được tạo trong Postgres,
  không phải chỉ có cookie phía trình duyệt.

### 2.2. Tạo task
- Hành động: tạo 1 task mới có category.
- Bóc field: `[APP] ... task_create` — đọc `task_id`, `title`,
  `priority`, `category`, `user_id`.
- Đối chiếu lớp thấp: `[DB] INSERT tasks` trên `watch-logs.ps1` (dòng rút
  gọn) — đối chiếu `task_id` trùng khớp với `task_id` vừa đọc ở app.log.
- **Soi thêm raw DB log** (giống cách đã làm với password hash): mở
  `logs\postgres\postgresql-<ngày hôm nay>.log` bằng Notepad, tìm dòng
  `INSERT INTO tasks (...) VALUES (...)` mới nhất — chỉ ra câu SQL đầy đủ
  (title, priority, category, user_id...) khớp với những gì vừa nhập trên
  UI, chứng minh `watch-logs.ps1` không "bịa" — đây là câu SQL thật do
  Postgres tự ghi lại.

### 2.2b. Xoá task — đối chiếu DB log
- Hành động: xoá 1 task vừa tạo (task không có comment, để tránh nhầm với
  demo cascade ở 2.4).
- Bóc field: `[APP] ... task_delete` — đọc `task_id`.
- Đối chiếu lớp thấp: `[DB] DELETE tasks` trên `watch-logs.ps1`. Sau đó mở
  lại `logs\postgres\postgresql-<ngày hôm nay>.log`, cuộn xuống dòng mới
  nhất, chỉ ra câu `DELETE FROM tasks WHERE id = '<task_id>'` — đúng
  `task_id` vừa đọc ở app.log, chứng minh task đã bị xoá thật trong DB,
  không chỉ biến mất khỏi giao diện.

### 2.3. Cập nhật task
- Hành động: đổi status của task vừa tạo.
- Bóc field: `[APP] ... task_update` — đọc field `changed_fields`, chỉ
  rõ giá trị **old** và **new** (vd `{"status":{"old":"todo","new":"doing"}}`).
- Đối chiếu lớp thấp: `[DB] UPDATE tasks` — xác nhận Postgres cũng nhận
  đúng giá trị mới đó (`SET status='doing'`), khớp với `new` ở app.log.

> **Lưu ý thứ tự — đọc trước khi quay:** cơ chế khoá tài khoản kiểm tra
> theo **username HOẶC IP** (xem `backend/app/routers/auth.py`). Toàn bộ
> traffic demo đều xuất phát từ cùng 1 máy → cùng 1 IP. Nếu làm bước
> "login sai 5 lần" (2.5) TRƯỚC bước IDOR (2.4), IP sẽ bị khoá 5 phút và
> tài khoản B ở bước 2.4 **không login được nữa** dù mật khẩu đúng (nhận
> 429 thay vì 200) — đã tự kiểm chứng lỗi này khi test thử. Vì vậy thứ tự
> bên dưới **bắt buộc theo đúng số** (2.4 trước 2.5), không đảo được.
> Đây cũng là điểm hay để nói trong video: khoá theo IP-OR-username nghĩa
> là 1 IP bị khoá sẽ ảnh hưởng đến MỌI tài khoản đăng nhập từ IP đó, kể
> cả tài khoản chưa từng đăng nhập sai lần nào.

### 2.4. Truy cập trái phép (IDOR) — làm trước bước khoá tài khoản
- Hành động: đăng nhập bằng tài khoản B (vd `bob`, đăng ký ở tab ẩn danh),
  vào Tasks, dán Task ID của tài khoản A (`vcsTest`) vào ô "Tra cứu theo
  ID" → bấm "Xem theo ID".
- Bóc field: `[APP] authorization_denied` — đọc `resource`,
  `resource_id`, `owner_id`, `requester_id` — chỉ rõ `owner_id !=
  requester_id` bằng mắt.
- Đối chiếu lớp thấp: **không có** dòng `[DB]` nào tương ứng xuất hiện —
  NHƯNG đây **không phải** vì request bị chặn trước khi chạm database.
  Code thực tế (`backend/app/routers/tasks.py:16-23`, hàm
  `get_owned_task`) vẫn chạy `db.get(Task, task_id)` — một câu `SELECT`
  thật — trước khi so `owner_id`. Dòng `[DB]` không xuất hiện đơn giản vì
  Postgres (`log_statement=mod`) không audit `SELECT`, đúng blind spot đã
  chứng minh ở bước đọc task (2.7). Điểm cần nói: request IDOR **vẫn thực
  sự chạm DB**, chỉ là audit log DB không thấy được — nên việc chặn IDOR
  bắt buộc phải nằm ở tầng ứng dụng (kiểm tra `owner_id` rồi trả 403),
  không thể trông cậy "DB tự chặn".

### 2.5. Đăng nhập sai 5 lần liên tiếp (khoá tạm thời) — làm SAU CÙNG
Làm bước này sau bước 2.4, vì nó khoá IP 5 phút (xem lưu ý ở trên). Chạy
trong PowerShell **gốc** (không phải Git Bash) — chú ý dấu `\"` bên trong
(escape bắt buộc, nếu để `"` thường thì PowerShell làm hỏng JSON khi
forward cho `curl.exe`, dẫn tới lỗi `Validation error` thay vì
`LOGIN_FAIL` thật):
```powershell
1..5 | ForEach-Object {
  curl.exe -k -X POST https://localhost:8443/api/auth/login `
    -H "Content-Type: application/json" -d '{\"username\":\"carol\",\"password\":\"wrong\"}'
}
```
- Bóc field: **5** dòng `[AUTH] LOGIN_FAIL` (`reason=bad_password`,
  `fail_count` tăng dần 1→5), và dòng thứ 5 có thêm **1 dòng riêng**
  `[AUTH] ACCOUNT_LOCKED` cùng `request_id` với lần thử thứ 5 (đọc
  `fail_count`, `window_minutes`, `lockout_minutes`).
- Đối chiếu lớp thấp: `[DB] INSERT login_attempts` — mỗi lần thử đều có
  1 dòng ghi `success=false` tương ứng trong Postgres, không chỉ là log
  ứng dụng "nói suông" — số dòng `INSERT` phải đúng bằng 5, khớp số lần
  login sai.

### 2.6. Phát sinh exception (lỗi 500)
```powershell
curl.exe -k -s -w "`nHTTP:%{http_code}" https://localhost:8443/api/debug/crash
```
- Bóc field: `[APP] unhandled_exception`, `level=ERROR` — đọc
  `exception_type`, và chỉ ra `request_id` trong response JSON trả về
  client **trùng khớp** với `request_id` trong dòng log — client chỉ
  thấy thông báo chung chung, KHÔNG thấy `stack_trace`. Dòng này bị
  `watch-logs.ps1` rút gọn, phải mở trực tiếp `logs\app\app.log` bằng
  Notepad mới thấy `stack_trace` đầy đủ.
- Đối chiếu lớp thấp: đây là trường hợp **thực sự không có** thao tác ghi
  DB nào — route `/api/debug/crash` (`backend/app/routers/debug.py`)
  không nhận tham số `db`, hoàn toàn không đụng Postgres (khác với IDOR ở
  2.4, nơi có SELECT nhưng không bị audit). Điểm đối chiếu ở đây là log
  Nginx (`[NGINX] GET /api/debug/crash 500`) để xác nhận lỗi được ghi
  nhận đồng thời ở cả tầng web server lẫn tầng application, cùng 1
  `request_id`. Đây cũng khác hẳn lỗi 502 hạ tầng ở mục 2.8 bên dưới: 500
  = backend còn sống nhưng code exception, 502 = backend chết hẳn.

### 2.7. Đọc dữ liệu — điểm tương phản quan trọng
- Hành động: `GET /api/tasks` (xem danh sách).
- Bóc field: `[APP] task_read`, field `count`.
- Đối chiếu lớp thấp: **không có** dòng `[DB]` nào cả — vì
  `log_statement=mod` trong Postgres chỉ audit INSERT/UPDATE/DELETE,
  không audit SELECT. Đây là điểm cần nói rõ trong video: hành động đọc
  chỉ quan sát được qua app log, đây là giới hạn thật của audit log DB
  cần biết khi điều tra sự cố.

### 2.8. Lỗi hạ tầng (502) — backend chết hẳn, phân biệt với lỗi 500 ở 2.6
```powershell
docker compose stop backend
curl.exe -k -s -o NUL -w "status: %{http_code}, time: %{time_total}s`n" https://localhost:8443/api/health
```
- Kỳ vọng: mất khoảng **20–40 giây** mới trả về `status: 502` (Nginx cố
  kết nối tới IP container backend đã chết, nhận lỗi "Host is
  unreachable" — chậm hơn nhiều so với bị từ chối kết nối ngay lập tức).
- Bóc field: `[NGINX-ERR] connect() failed (113: Host is unreachable)
  ... upstream: "http://<ip container>:8000/..."`. Mở trực tiếp
  `logs\nginx\error.log` bằng Notepad để đối chiếu nguyên văn.
- Đối chiếu: khôi phục lại bằng `docker compose start backend`, gọi lại
  `/api/health` → về `200` bình thường. Nhấn mạnh: đây là lỗi **hạ tầng**
  (không có process nào lắng nghe), khác bản chất với lỗi 500 ở 2.6 (có
  process, nhưng code bên trong tự văng exception).

---

## PHẦN 3 — Vận hành / nâng cấp mã nguồn (Mục 3 đề bài)

Mở `VAN_HANH_NANG_CAP.md`, trình bày theo đúng tài liệu đã viết:

**3.1. Tính năng vừa thêm**: gắn nhãn (`category`) cho task + lọc theo
nhãn — đã demo chức năng ở bước 1.3.

**3.2. Vấn đề migration DB** — mở `db/migrations/0001_add_task_category.sql`,
giải thích: `Base.metadata.create_all()` không tự `ALTER TABLE`, nên phải
chạy migration SQL thủ công **trước** khi deploy code mới, nếu không mọi
request tới `/api/tasks` sẽ lỗi `column "category" does not exist`.

Chứng minh bằng lệnh thật (chạy trực tiếp trên camera):
```powershell
docker compose exec db psql -U soclab -d soclab -c "\d tasks"
```
→ chỉ ra cột `category` đã tồn tại trong bảng thật, đối chiếu với dòng
`ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category VARCHAR(50);` trong
file migration.

**3.3. Backward compatibility**: mở `GET /api/tasks` của 1 task tạo
**trước** khi có tính năng category (nếu còn) → chỉ ra `category: null`,
không lỗi — chứng minh dữ liệu cũ không bị phá khi thêm field mới.

**3.4. Thứ tự triển khai + rollback**: đọc tóm tắt 2 mục "Thứ tự triển
khai" và "Rollback plan" trong `VAN_HANH_NANG_CAP.md`, giải thích ngắn
gọn vì sao phải migrate trước-deploy sau, và vì sao rollback code thì an
toàn nhưng rollback schema (`DROP COLUMN`) thì nguy hiểm nếu đã có dữ
liệu thật.

---

## PHẦN 4 — Kết thúc

Tóm tắt 1 câu: ứng dụng đủ 4 lớp kiến trúc, log đầy đủ và đã được xác
thực chéo qua nhiều layer (không chỉ tin nhãn event), và có quy trình
nâng cấp mã nguồn an toàn, có tài liệu hoá.

Dừng quay.
