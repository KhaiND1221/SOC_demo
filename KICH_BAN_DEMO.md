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
cd C:\Users\ANM-KHAIND8\soc-logging-lab
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

**1.2. Đăng ký + Đăng nhập**
- Vào `/register.html`, tạo tài khoản mới (nhớ tên, dùng lại ở 2.2).
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
- Đối chiếu lớp thấp: `[DB] INSERT tasks` — đối chiếu `task_id` trong
  câu SQL trùng khớp với `task_id` vừa đọc ở app.log.

### 2.3. Cập nhật task
- Hành động: đổi status của task vừa tạo.
- Bóc field: `[APP] ... task_update` — đọc field `changed_fields`, chỉ
  rõ giá trị **old** và **new** (vd `{"status":{"old":"todo","new":"doing"}}`).
- Đối chiếu lớp thấp: `[DB] UPDATE tasks` — xác nhận Postgres cũng nhận
  đúng giá trị mới đó (`SET status='doing'`), khớp với `new` ở app.log.

### 2.4. Đăng nhập sai 5 lần liên tiếp (khoá tạm thời)
```powershell
1..5 | ForEach-Object {
  curl.exe -X POST http://localhost:8080/api/auth/login `
    -H "Content-Type: application/json" -d '{"username":"alice","password":"wrong"}'
}
```
- Bóc field: 4 dòng `[AUTH] LOGIN_FAIL` (`reason=bad_password`,
  `fail_count` tăng dần 1→4), dòng thứ 5 có thêm `[AUTH] ACCOUNT_LOCKED`
  (đọc `fail_count`, `window_minutes`, `lockout_minutes`).
- Đối chiếu lớp thấp: `[DB] INSERT login_attempts` — mỗi lần thử đều có
  1 dòng ghi `success=false` tương ứng trong Postgres, không chỉ là log
  ứng dụng "nói suông" — số dòng `INSERT` phải đúng bằng số lần login sai.

### 2.5. Truy cập trái phép (IDOR)
- Hành động: đăng nhập bằng tài khoản B, thử `GET /api/tasks/<id của
  task tài khoản A>`.
- Bóc field: `[APP] authorization_denied` — đọc `resource`,
  `resource_id`, `owner_id`, `requester_id` — chỉ rõ `owner_id !=
  requester_id` bằng mắt.
- Đối chiếu lớp thấp: **không có** dòng `[DB]` nào tương ứng xuất hiện —
  đây chính là bằng chứng request bị chặn *trước khi* chạm tới database,
  không phải app chỉ "ẩn" kết quả sau khi đã đọc dữ liệu.

### 2.6. Phát sinh exception (lỗi 500)
```powershell
curl.exe -s -w "`nHTTP:%{http_code}" http://localhost:8080/api/debug/crash
```
- Bóc field: `[APP] unhandled_exception`, `level=ERROR` — đọc
  `exception_type`, và chỉ ra `request_id` trong response JSON trả về
  client **trùng khớp** với `request_id` trong dòng log — client chỉ
  thấy thông báo chung chung, KHÔNG thấy `stack_trace` (mở rộng dòng log
  để cho thấy `stack_trace` đầy đủ chỉ nằm ở server).
- Đối chiếu lớp thấp: đây là trường hợp **không có** thao tác ghi DB nào
  (lỗi xảy ra trước khi chạm DB) — điểm đối chiếu ở đây là log Nginx
  (`[NGINX] GET /api/debug/crash 500`) để xác nhận lỗi được ghi nhận
  đồng thời ở cả tầng web server lẫn tầng application, cùng 1
  `request_id`.

### 2.7. Đọc dữ liệu — điểm tương phản quan trọng
- Hành động: `GET /api/tasks` (xem danh sách).
- Bóc field: `[APP] task_read`, field `count`.
- Đối chiếu lớp thấp: **không có** dòng `[DB]` nào cả — vì
  `log_statement=mod` trong Postgres chỉ audit INSERT/UPDATE/DELETE,
  không audit SELECT. Đây là điểm cần nói rõ trong video: hành động đọc
  chỉ quan sát được qua app log, đây là giới hạn thật của audit log DB
  cần biết khi điều tra sự cố.

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
