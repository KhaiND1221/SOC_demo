# WEB APPLICATION SPECIFICATION — rút ra từ `demo_web_2.mp4`

**Nguồn bằng chứng và phương pháp (đọc trước khi dùng tài liệu này):**

Môi trường phân tích không có khả năng giải mã audio (không có speech-to-text),
nên phần audio/narration của video **không được phân tích** — mọi kết luận dưới
đây chỉ dựa trên hình ảnh. Để tối đa độ chính xác, tài liệu này dùng 3 nguồn
bằng chứng, đánh dấu rõ trong từng mục:

- `[OBSERVED]` — nhìn thấy trực tiếp trong khung hình video (video dài
  **00:07:32**, độ phân giải gốc 1920×1024, 30fps, có audio nhưng không phân
  tích; trích xuất 226 khung hình cách nhau 2 giây bằng ffmpeg để dựng timeline).
- `[FROM_SOURCE_CODE]` — lấy trực tiếp, nguyên văn từ mã nguồn thật của chính
  ứng dụng đang được quay demo (`frontend/*.html`, `frontend/js/api.js`,
  `frontend/css/style.css`, `backend/app/**/*.py`) — **chính xác tuyệt đối**,
  không phải suy đoán từ pixel. Đây là ứng dụng thật đang chạy trong video, nên
  mã nguồn là bằng chứng mạnh hơn quan sát hình ảnh mờ.
- `[FROM_LOGS]` — lấy từ log thật của backend/nginx/Postgres phát sinh **trong
  chính phiên quay video này**. Đã xác nhận khớp thời gian tuyệt đối: video có
  `creation_time = 2026-08-25T08:52:35Z`, dài 452.47s → kết thúc
  `2026-08-25T09:00:07Z`; toàn bộ request trong `logs/nginx/access.log`,
  `logs/app/app.log`, `logs/app/auth.log`, `logs/postgres/postgresql-2026-08-25.log`
  trong đúng khung giờ này (08:52:35–09:00:07) đối chiếu 1-1 với hành động thấy
  trên màn hình (số lượng, thứ tự, khoảng cách thời gian giữa các thao tác đều
  khớp). Vì vậy log này được dùng làm nguồn dữ liệu chính xác cho giá trị nhập
  liệu thật (title, email, ưu tiên...), timestamp chính xác đến mili-giây, và
  request/response thật.
- `[INFERRED]` — suy luận hợp lý, không có bằng chứng trực tiếp.
- `[NOT VISIBLE]` — video/log không cho biết.

Không có mục nào trong tài liệu bị bỏ qua chỉ vì khó quan sát: phần log/terminal
chiếm hơn nửa thời lượng video và được phân tích đầy đủ ở mục 9.

---

## 1. PHÂN TÍCH TỔNG QUAN APPLICATION

- **Ứng dụng dùng để làm gì**: "Task Manager" — ứng dụng quản lý công việc cá
  nhân (todo/task list) nhiều người dùng, có tài khoản riêng, mỗi task có ưu
  tiên/trạng thái/danh mục/hạn chót, và có thể đính "ghi chú" (comment) vào
  từng task. `[FROM_SOURCE_CODE]` — footer mọi trang: "Task Manager — ứng dụng
  quản lý công việc cá nhân".
- **Đối tượng sử dụng**: cá nhân tự quản lý việc cần làm của mình (không có
  khái niệm assign việc cho người khác, không có team/workspace — mỗi user chỉ
  thấy task của chính mình). `[FROM_SOURCE_CODE]`
- **Điểm đặc biệt**: ứng dụng được cố ý trang bị thêm 2 tính năng phục vụ mục
  đích lab bảo mật/logging, không phải tính năng sản phẩm thông thường:
  1. Ô "Tra cứu theo ID" trên trang Tasks — dán ID bất kỳ (kể cả không phải
     task của mình) để test IDOR/authorization. `[FROM_SOURCE_CODE]`
  2. Endpoint `GET /api/debug/crash` cố ý ném exception không bắt, chỉ để demo
     log lỗi 500 — có comment trong code "Not a real feature - never do this
     in a production route". `[FROM_SOURCE_CODE]`
- **Các chức năng chính**: Đăng ký, Đăng nhập, Đăng xuất, Dashboard tổng quan,
  CRUD Task (tiêu đề/mô tả/ưu tiên/trạng thái/danh mục/hạn chót), lọc task theo
  danh mục, CRUD Ghi chú (comment) trên task, tra cứu task theo ID (IDOR test),
  xem/sửa hồ sơ cá nhân (email, mật khẩu). `[FROM_SOURCE_CODE]`
- **Các màn hình/trang tồn tại**: Login, Register, Home (Dashboard), Tasks,
  Profile. `[OBSERVED]` + `[FROM_SOURCE_CODE]` (5 file HTML trong `frontend/`)
- **Navigation giữa các màn hình**: thanh nav cố định trên cùng (sticky top)
  chỉ xuất hiện ở 3 trang Home/Tasks/Profile (không có ở Login/Register).
  Logo "Task Manager" bên trái → về Home. 3 link Home/Tasks/Profile ở giữa,
  link đang active có gạch chân màu tím. Vùng user-area bên phải: nếu chưa
  đăng nhập hiện "Login · Register"; nếu đã đăng nhập hiện avatar (2 chữ cái
  đầu username viết hoa) + username + nút "Logout". `[FROM_SOURCE_CODE]` +
  `[OBSERVED]`
- **User flow tổng thể** `[OBSERVED, khớp FROM_LOGS]`: mở `/login.html` → bấm
  link sang `/register.html` → điền form đăng ký → bấm Register (không tự
  chuyển trang) → tự tay quay lại `/login.html` → đăng nhập → tự động chuyển
  về `/index.html` (Home) → xem dashboard → vào `/tasks.html` → tạo/xem/sửa/xoá
  task và ghi chú → (video này không thao tác Logout qua UI ở phiên đầu, xem
  timeline mục 11) → dùng tài khoản thứ 2 để test IDOR → Logout tài khoản 2 ở
  cuối không được quan sát rõ trong video này.
- **Chức năng cần authentication** `[FROM_SOURCE_CODE]`: mọi API `/api/tasks/*`,
  `/api/users/{id}` (profile), dữ liệu dashboard trên Home. Cơ chế: cookie
  `session_id` (httponly, `samesite=strict`) — thiếu/sai cookie → `401`.
- **Chức năng truy cập được khi CHƯA đăng nhập** `[FROM_SOURCE_CODE]`:
  `/login.html`, `/register.html`, khung sườn trang `/index.html` (hiện
  "guest-card" thay vì dashboard), `POST /api/auth/register`,
  `POST /api/auth/login`, `GET /api/health`, `GET /api/debug/crash` (route này
  không có dependency `get_current_user` nên hoàn toàn không cần đăng nhập —
  đúng là một lỗ hổng cố ý cho mục đích demo).

---

## 2. LIỆT KÊ TOÀN BỘ CÁC TRANG / SCREEN

### 2.1. Trang Login

- **Tên trang**: Login — `[OBSERVED]` tiêu đề tab trình duyệt "Login - Task Manager"
- **URL/route**: `/login.html` `[OBSERVED]` + `[FROM_SOURCE_CODE]`
- **Layout**: không có header/nav. Toàn trang là 1 khối `auth-shell` căn giữa
  màn hình theo cả chiều ngang lẫn dọc (`min-height:100vh; display:flex;
  align-items:center; justify-content:center`), bên trong là 1 "card" rộng tối
  đa 400px, bo góc 18px, nền `--bg-elevated` (#13131e), viền 1px màu #24243a.
  `[FROM_SOURCE_CODE]`
- **UI elements**:

| Element | Loại | Text hiển thị | Behavior |
|---|---|---|---|
| icon-badge | icon tròn/vuông bo góc (svg checkmark trong vòng tròn) | (không có text) | trang trí, căn giữa phía trên form |
| h1 | heading | "Welcome Back" | tĩnh |
| subtitle | paragraph, màu nhạt | "Đăng nhập để tiếp tục quản lý công việc." | tĩnh |
| label + input#username | text input | label "Username" | `autocomplete="username"` |
| label + input#password | password input | label "Password" | `autocomplete="current-password"` |
| button#login-btn | button, full-width | "Sign In" | click → gọi `POST /api/auth/login` |
| p#msg | text thông báo | (rỗng ban đầu) | class đổi `message success` (xanh #4ade80) hoặc `message error` (đỏ #f87171) |
| ghi chú nhỏ | text 12px, màu nhạt, căn giữa | "Sau 5 lần đăng nhập sai liên tiếp trong 5 phút, tài khoản sẽ tạm thời bị khoá." | tĩnh, cảnh báo trước |
| auth-footer | text + link | "Chưa có tài khoản? Đăng ký" | link "Đăng ký" → `/register.html` |

  `[FROM_SOURCE_CODE]` (toàn bộ text trích nguyên văn từ `frontend/login.html`)

- **Visual design** `[FROM_SOURCE_CODE]` (biến CSS `:root` trong `style.css`):
  nền tổng thể `--bg:#0a0a0f` (gần đen), card nền `--bg-elevated:#13131e`,
  chữ chính `--text:#f2f2f6`, chữ phụ `--text-dim:#a1a1b8`, màu nhấn (accent,
  dùng cho link/nút chính/icon) `--accent:#6366f1` (tím-xanh, hover
  `#7b7ef6`), bo góc lớn 14px / nhỏ 8px, font `"Segoe UI", -apple-system,
  Roboto, Arial, sans-serif`. Input: nền `--bg`, viền `--border-light:#33334d`,
  khi focus viền chuyển màu accent + có glow (`box-shadow` accent nhạt). Nút
  chính: nền accent, chữ trắng, bo góc 8px, hover sáng hơn. `[OBSERVED]` xác
  nhận tông màu tối/tím giống mô tả code.

### 2.2. Trang Register

- **Tên trang**: Register — tab "Register - Task Manager" `[FROM_SOURCE_CODE]`
- **URL/route**: `/register.html`
- **Layout**: giống hệt khung Login (cùng class `auth-shell`/`auth-card`),
  chỉ khác icon (icon "add person") và nội dung form.
- **UI elements**:

| Element | Loại | Text hiển thị | Behavior/Validation |
|---|---|---|---|
| h1 | heading | "Create Account" | |
| subtitle | text | "Đăng ký để bắt đầu quản lý công việc." | |
| label+input#username | text | "Username" | server validate: 3–50 ký tự `[FROM_SOURCE_CODE: schemas.py UserCreate]` |
| label+input#email | email | "Email" | server validate: định dạng email hợp lệ (Pydantic `EmailStr`) |
| label+input#password | password | "Password (min 8 chars)" | server validate: 8–128 ký tự |
| button#register-btn | button full-width | "Register" | client không tự validate — mọi validate ở server; sai → hiện message lỗi |
| p#msg | message | rỗng | thành công: `"Registered user '{username}'. You can now log in."` (xanh); lỗi: `"Error {status}: {JSON detail}"` (đỏ) |
| auth-footer | text+link | "Đã có tài khoản? Đăng nhập" | → `/login.html` |

  `[FROM_SOURCE_CODE]`

- **Sau khi đăng ký thành công**: **KHÔNG tự động chuyển trang** — chỉ hiện
  message xanh, người dùng phải tự bấm link "Đăng nhập" để sang Login.
  `[FROM_SOURCE_CODE]`, khớp `[OBSERVED]` (video thấy dừng lại ở trang Register
  sau khi submit, người dùng tự điều hướng sang Login).

### 2.3. Trang Home / Dashboard

- **Tên trang**: Home — tab "Home - Task Manager" `[FROM_SOURCE_CODE]`
- **URL/route**: `/index.html`
- **Layout**: có `topnav` (xem mục 1). Nội dung chính (`main.page`, max-width
  1180px căn giữa): 1 nhãn nhỏ in hoa màu accent "DASHBOARD", `h1` chào mừng,
  subtitle, rồi tuỳ trạng thái đăng nhập hiện 1 trong 2 khối:
  - **Chưa đăng nhập** — `guest-card`: "Bạn chưa đăng nhập. **Đăng nhập** để
    xem công việc của bạn." (link "Đăng nhập" → `/login.html`)
  - **Đã đăng nhập** — `dashboard`: 3 thẻ thống kê dạng lưới (`stat-grid`,
    responsive `repeat(auto-fit, minmax(200px,1fr))`) rồi 1 card "Bắt đầu"
- **UI elements** (trạng thái đã đăng nhập):

| Element | Loại | Text | Behavior |
|---|---|---|---|
| h1#greeting | heading | `"Chào mừng trở lại, {username}!"` | username lấy từ localStorage sau login |
| stat-card #1 | thẻ số liệu | label "Tổng công việc", value = tổng số task | tính từ toàn bộ `GET /api/tasks` |
| stat-card #2 | thẻ số liệu | label "Ưu tiên cao", value = số task `priority=high` | |
| stat-card #3 | thẻ số liệu | label "Đến hạn hôm nay", value = số task có `due_date=hôm nay` và `status≠done` | |
| card "Bắt đầu" | card | h3 "Bắt đầu", p "Xem, tạo và cập nhật công việc trong trang Tasks." | button "Xem danh sách công việc" → `/tasks.html` |

  `[FROM_SOURCE_CODE]`. **Lưu ý**: trong phiên video này, sau khi tạo 3 task
  rồi mới rời khỏi trang Home lần đầu, giá trị 3 thẻ này không được quan sát
  lại lần 2 sau khi có task — `[NOT VISIBLE]` giá trị số cụ thể của 3 thẻ ở
  Home tại thời điểm có task (chỉ chắc chắn "0 mọi giá trị" lúc tài khoản mới
  tạo, vì tasks rỗng — `[OBSERVED + FROM_LOGS]`).

### 2.4. Trang Tasks

- **Tên trang**: Tasks — tab "Tasks - Task Manager" `[FROM_SOURCE_CODE]`
- **URL/route**: `/tasks.html`
- **Layout**: có `topnav`. `page-header` (flex, 2 đầu): bên trái nhãn "CÔNG
  VIỆC CỦA TÔI" + `h1` "Tasks" + subtitle "Quản lý và theo dõi công việc cần
  làm."; bên phải nút "+ Thêm việc". Dưới đó: 3 stat-card (Chưa làm/Đang
  làm/Hoàn thành). Rồi 1 `card` chính chứa: tiêu đề "Danh sách", thanh filter
  (select danh mục + nút "Làm mới"), bảng task (`table-scroll` overflow-x
  auto), rồi message dòng cuối. Cuối cùng 1 `card` riêng cho "Tra cứu theo ID".
  2 modal ẩn mặc định (`detail-modal`, `create-modal`) chỉ hiện khi kích hoạt.
- **UI elements — vùng danh sách**:

| Element | Loại | Text | Behavior |
|---|---|---|---|
| button#add-task-toggle-btn | button | "+ Thêm việc" | mở modal tạo task |
| stat #stat-todo/doing/done | số liệu | label "Chưa làm"/"Đang làm"/"Hoàn thành" | tự tính lại mỗi lần load danh sách (đúng theo filter đang áp dụng) |
| select#filter-category | dropdown | option: "Tất cả danh mục" (rỗng), "work", "study", "personal" | đổi → gọi lại danh sách có `?category=` |
| button#refresh-btn | button secondary | "Làm mới" | gọi lại `GET /api/tasks` |
| table#tasks-table thead | table header | "Tiêu đề · Ưu tiên · Trạng thái · Danh mục · Hạn chót · Thao tác" | tĩnh |
| mỗi row | table row | tiêu đề task, badge ưu tiên, dropdown trạng thái, badge danh mục (hoặc "-"), ngày hạn chót (+ badge "Quá hạn" đỏ nếu overdue), 2 nút | xem chi tiết bên dưới |
| button "Xem" | button secondary, nhỏ | "Xem" | mở modal chi tiết task đó |
| button "Xoá" | button danger, nhỏ | "Xoá" | **xoá ngay, KHÔNG có modal xác nhận** `[FROM_SOURCE_CODE]` — điểm khác biệt quan trọng so với giả định thông thường |
| p#list-msg | message | `"Đã tải {n} công việc."` (thành công) hoặc `"Error {status}"` | |

  `[FROM_SOURCE_CODE]`

- **UI elements — badge màu** `[FROM_SOURCE_CODE, CSS]`:
  - Ưu tiên: `high` = nền đỏ nhạt/chữ đỏ hồng ("#fca5a5" trên nền
    `rgba(239,68,68,.15)"`), `medium` = nền vàng/chữ vàng, `low` = nền
    xanh lá/chữ xanh lá. Label hiển thị: Cao/Trung bình/Thấp.
  - Trạng thái (dropdown ngay trong ô, không phải text tĩnh): `todo` = nền xám
    nhạt trong suốt, `doing` = nền tím nhạt/chữ tím, `done` = nền xanh
    lá nhạt/chữ xanh lá. Label: Chưa làm/Đang làm/Hoàn thành. **Đổi giá trị
    dropdown này gửi PUT ngay lập tức, không cần nút Lưu riêng.**
  - Danh mục: badge xám viền, hiển thị nguyên văn category (không dịch), hoặc
    dấu "-" nếu không có category.
  - Quá hạn: badge đỏ "Quá hạn" chỉ hiện khi `due_date < hôm nay` VÀ
    `status ≠ done`.

- **UI elements — vùng IDOR lookup**:

| Element | Loại | Text | Behavior |
|---|---|---|---|
| h3 | heading | "Tra cứu theo ID (test truy cập trái phép / IDOR)" | |
| p muted | text | "Dán ID của 1 task (kể cả task không phải của bạn) để thử xem — dùng để kiểm tra authorization: chỉ chủ sở hữu mới được xem, người khác sẽ nhận lỗi 403." | |
| label+input#lookup-id | text | label "Task ID", placeholder "vd: 6d137c2e-d870-430d-960c-854428acf066" | |
| button#lookup-btn | button secondary | "Xem theo ID" | gọi `GET /api/tasks/{id}` |
| p#lookup-msg | message | rỗng nếu chưa nhập: "Nhập ID trước đã." (đỏ); thành công: "Truy cập được — bạn là chủ sở hữu task này." (mở luôn modal chi tiết); lỗi: `"HTTP {status}: {JSON detail}"` | |

  `[FROM_SOURCE_CODE]`

- **Modal "Tạo công việc mới"** (`create-modal`, ẩn mặc định, class `hidden`
  toggled): overlay nền đen mờ 60%, card trắng-tối căn giữa, max-width 460px.

| Element | Loại | Text/Default | Ghi chú |
|---|---|---|---|
| h3 | heading | "Tạo công việc mới" | |
| button "✕" | close | (icon ✕) | đóng modal, hoặc click ra ngoài overlay, hoặc phím Escape |
| label+input#c-title | text | "Tiêu đề" | bắt buộc (server: 1–255 ký tự) |
| label+input#c-description | text | "Mô tả" | optional (server: tối đa 2000 ký tự) |
| label+select#c-priority | select | "Ưu tiên" — option Thấp/**Trung bình (mặc định)**/Cao | |
| label+select#c-status | select | "Trạng thái" — option **Chưa làm (mặc định)**/Đang làm/Hoàn thành | |
| label+input#c-category | text | "Danh mục (không bắt buộc)", placeholder "work / study / personal" | optional, server tối đa 50 ký tự |
| label+input#c-due | date picker | "Hạn chót (không bắt buộc)" | optional |
| button#create-btn | button | "Thêm task" → đổi thành "Đang thêm..." + disabled trong lúc gửi | xem logic duplicate-check bên dưới |
| p#create-msg | message | | |

  `[FROM_SOURCE_CODE]`. **Logic đặc biệt khi bấm "Thêm task"** (nguyên văn từ
  code, rất quan trọng để tái tạo đúng): (1) khoá nút, đổi label "Đang thêm...";
  (2) gọi `GET /api/tasks` (không filter) để lấy TOÀN BỘ task hiện có của user;
  (3) so title (đã trim + lowercase) — nếu trùng với 1 task đã tồn tại, bật
  `confirm()` của trình duyệt với nội dung
  `Đã có công việc tên "{title}". Bạn vẫn muốn tạo thêm một cái trùng tên?`
  — Cancel → dừng lại, hiện `"Đã huỷ - trùng tên với công việc đã có."` (đỏ);
  OK → tiếp tục; (4) `POST /api/tasks`; (5) thành công → message "Đã tạo công
  việc.", reset toàn bộ field về mặc định, load lại danh sách, và **tự đóng
  modal sau 500ms**; (6) `finally` luôn mở khoá nút + trả lại label gốc.

- **Modal "Chi tiết task"** (`detail-modal`):

| Element | Loại | Text | Ghi chú |
|---|---|---|---|
| h3#detail-title | heading | tiêu đề task | |
| button "✕" | close | | đóng modal (Escape cũng đóng cả 2 modal) |
| detail-row × 9 | cặp label/value | ID · Chủ sở hữu (user_id) · Mô tả · Ưu tiên (badge) · Trạng thái · Danh mục · Hạn chót · Tạo lúc · Cập nhật lúc | ID và user_id có `user-select:all` (click 1 phát bôi đen để copy); "Tạo lúc"/"Cập nhật lúc" format `toLocaleString("vi-VN")` |
| h3 "Ghi chú" | heading trong modal | "Ghi chú" | mở section comment, xem mục 5 |

  `[FROM_SOURCE_CODE]`

### 2.5. Trang Profile

- **Tên trang**: Profile — tab "Profile - Task Manager" `[FROM_SOURCE_CODE]`.
  **Không được thao tác trong video này** `[FROM_LOGS: không có PUT
  /api/users/* nào trong toàn bộ cửa sổ thời gian video]` — mô tả dưới đây
  hoàn toàn từ source code.
- **URL/route**: `/profile.html`
- **Layout**: có `topnav`. Nhãn "TÀI KHOẢN", `h1` "Hồ sơ cá nhân". Lưới 2 cột
  (`profile-grid`, 260px + phần còn lại, chuyển 1 cột nếu màn hình <760px):
  cột trái là card avatar tròn lớn (chữ cái đầu username) + username + ngày
  tham gia; cột phải gồm 2 card: "Thông tin tài khoản" (chỉ đọc) và "Cập nhật
  thông tin" (form sửa).

| Element | Loại | Text | Behavior |
|---|---|---|---|
| avatar-lg | avatar tròn 76px | 2 ký tự đầu username viết hoa | |
| h2#disp-username | text | username | |
| p#disp-created | text | `"Tham gia {ngày tạo, vi-VN}"` | |
| input#disp-username-field | text, `disabled` | giá trị = username | chỉ đọc |
| input#disp-email | text, `disabled` | giá trị = email | chỉ đọc |
| label+input#email | email | "Email mới (để trống nếu không đổi)" | optional |
| label+input#password | password | "Mật khẩu mới (để trống nếu không đổi)" | optional, server: 8–128 ký tự nếu có nhập |
| button#save-btn | button | "Lưu thay đổi" | `PUT /api/users/{id}` chỉ gửi field nào có nhập |
| p#save-msg | message | thành công "Profile updated." (xanh); lỗi `"Error {status}: ..."` | sau thành công: 2 ô input xoá trắng, load lại profile |

  `[FROM_SOURCE_CODE]`

---

## 3. AUTHENTICATION FLOW

### 3.1. Registration `[FROM_SOURCE_CODE + FROM_LOGS + OBSERVED]`

- Field: Username (text), Email (email), Password (password).
- Label chính xác: "Username", "Email", "Password (min 8 chars)".
- Placeholder: không có placeholder trên form Register (chỉ có label).
- Validation (100% phía server, client không tự validate trước khi gửi):
  username 3–50 ký tự; email đúng định dạng; password 8–128 ký tự. Vi phạm →
  HTTP 400 (username/password quá ngắn/dài, hoặc email sai định dạng, do
  Pydantic tạo `RequestValidationError` → response
  `{"detail":"Validation error","request_id":"..."}` với status 400 — **không
  trả về danh sách lỗi field cụ thể cho client**, chỉ 1 message chung).
- Không có Confirm Password field. `[FROM_SOURCE_CODE — xác nhận không tồn tại]`
- Button: "Register".
- Success state: message xanh `"Registered user '{username}'. You can now log
  in."`; **không tự chuyển trang**.
- Error state: message đỏ `"Error {status}: {JSON.stringify(detail)}"`. Case
  cụ thể quan sát được qua code: username hoặc email đã tồn tại → 400
  `"Username or email already registered"`.
- Sau đăng ký thành công: ở lại trang Register, người dùng tự bấm "Đăng nhập"
  để sang `/login.html`.
- Dữ liệu thật đã nhập trong video `[FROM_LOGS]`: user 1 — username=`vcstest`,
  email=`kkkk@gmail.com` (08:52:53); user 2 — username=`bob`,
  email=`aaa@gmail.com` (08:56:55). Mật khẩu không log dạng plaintext ở bất kỳ
  đâu (xem mục 9).

### 3.2. Login `[FROM_SOURCE_CODE + FROM_LOGS]`

- Field: Username (text), Password (password). **Không có "Remember me".**
- Button: "Sign In".
- Link tới Register: "Chưa có tài khoản? Đăng ký".
- Error message: `"Error {status}: {JSON.stringify(detail)}"` — case cụ thể:
  sai username/password → 401 `"Invalid username or password"` (client
  **không phân biệt được** "user không tồn tại" và "sai mật khẩu" — cùng 1
  message, dù server nội bộ có log 2 reason khác nhau, xem mục 9); bị khoá do
  đăng nhập sai nhiều lần → 429 `"Account temporarily locked due to repeated
  failed logins"`.
- Success behavior: lưu `{id, username}` vào `localStorage` key `tm_user`,
  hiện message xanh `"Logged in as {username}. Redirecting..."`, sau 500ms
  redirect sang `/index.html`.
- Session behavior `[FROM_SOURCE_CODE]`: server tạo bản ghi `sessions` trong
  Postgres (không phải JWT) — `expires_at` = login-time + 30 phút, set cookie
  `session_id` (httponly, `samesite=strict`, `secure` theo config). Mỗi
  request tới API cần cookie có session hợp lệ, chưa hết hạn, chưa revoke.
  Hết hạn được phát hiện "lazy" — chỉ khi có request dùng session đó sau khi
  đã hết hạn (không có background job quét).
- Dữ liệu thật `[FROM_LOGS]`: login vcstest lúc 08:53:08 → session
  `181fb52e-f4ef-4f22-b666-2c1eb1326c27`; login bob lúc 08:57:03 → session
  `783644b3-f100-48a2-8039-62b2ccbfd553`.

### 3.3. Logout `[FROM_SOURCE_CODE]`

- Vị trí: nút "Logout" trong `user-area` ở góc phải thanh nav — **chỉ hiện
  khi đã đăng nhập** (thay thế cặp link Login/Register).
- Khi click: `POST /api/auth/logout` → server set `revoked_at` cho session
  hiện tại (nếu chưa revoke) và ghi log `LOGOUT`/`logout`; response `204 No
  Content`; xoá cookie `session_id` phía server (`delete_cookie`). Client:
  `clearStoredUser()` (xoá `tm_user` khỏi localStorage) rồi
  `window.location.href = "/login.html"`.
- Redirect: luôn về `/login.html`, kể cả khi không có cookie hợp lệ lúc gọi.
- **Không quan sát được thao tác Logout qua UI trong video này**
  `[NOT VISIBLE trực tiếp qua click]` — nhưng có 1 lần chuyển từ trạng thái
  "đã đăng nhập vcstest" sang màn hình đăng ký tài khoản mới (~04:04–04:10) mà
  không có sự kiện `LOGOUT` tương ứng trong log ở khung giờ đó
  `[FROM_LOGS: không có LOGOUT event nào trong toàn bộ video]` → đây có thể là
  logout không thành công ghi log (ví dụ do lỗi client) hoặc thao tác diễn ra
  ngoài log — đánh dấu `[INFERRED — không chắc chắn]`, không khẳng định cơ chế
  logout đã thực sự chạy trong video, chỉ khẳng định cơ chế đúng theo code.

### 3.4. Failed Login / Security `[OBSERVED + FROM_LOGS + FROM_SOURCE_CODE]`

- Video có demo trực tiếp qua PowerShell + `curl.exe` (không qua UI):
  ```
  1..5 | ForEach-Object {
    curl.exe -k -X POST https://localhost:8443/api/auth/login `
      -H "Content-Type: application/json" -d '{"username":"carol","password":"wrong"}'
  }
  ```
- Kết quả thật `[FROM_LOGS]`: 5 request `POST /api/auth/login` lúc
  `08:59:32.406 / .442 / .474 / .506 / .539` UTC (video ~06:57), **mỗi lần
  cách nhau ~32–37ms** (loop chạy gần như liên tục, không có delay), tất cả
  trả **401** (không phải 429 — vì đây là 5 lần *đầu tiên*, chưa vượt
  ngưỡng). `fail_count` trong `auth.log` tăng dần đúng 1→2→3→4→5.
  `reason="user_not_found"` cho cả 5 lần (tài khoản `carol` không tồn tại
  trong CSDL của lần chạy demo này).
- Dòng thứ 5 kèm theo 1 sự kiện riêng `ACCOUNT_LOCKED` (cùng `request_id` với
  lần thử thứ 5): `fail_count=5, window_minutes=5, lockout_minutes=5`.
- Ngưỡng khoá `[FROM_SOURCE_CODE, config.py]`: **5 lần** sai trong cửa sổ
  **5 phút** → khoá **5 phút**. Khoá theo **username HOẶC ip_address** (OR
  logic) — 1 IP bị khoá ảnh hưởng mọi username đăng nhập từ IP đó.
- **Video KHÔNG có lần thử thứ 6** để thấy phản hồi 429 thật trên màn hình —
  hành vi 429 là suy ra từ code (`auth.py`), đánh dấu `[FROM_SOURCE_CODE,
  không phải OBSERVED]`.
- Thông báo UI: không quan sát được UI login thật hiển thị lỗi này (vì test
  chạy bằng `curl` ngoài UI) — nếu làm qua UI, message sẽ là
  `"Error 429: {"detail":"Account temporarily locked due to repeated failed
  logins"}"` theo đúng cơ chế hiển thị lỗi chung ở mục 3.2. `[INFERRED từ code]`

---

## 4. TASK MANAGEMENT

### 4.1. Task list `[FROM_SOURCE_CODE + OBSERVED]`

Bảng 6 cột: Tiêu đề, Ưu tiên (badge màu), Trạng thái (dropdown màu, sửa được
tại chỗ), Danh mục (badge hoặc "-"), Hạn chót (ngày ISO `YYYY-MM-DD`, kèm badge
"Quá hạn" nếu áp dụng), Thao tác (nút Xem + Xoá). 3 thẻ đếm Chưa
làm/Đang làm/Hoàn thành phía trên bảng, **tự tính lại theo đúng tập dữ liệu
đang hiển thị** (tức là bị ảnh hưởng bởi filter danh mục). Filter theo danh
mục qua dropdown (`work`/`study`/`personal`/rỗng="Tất cả"), có nút "Làm mới"
gọi lại API. **Không có search theo tên, không có sort, không có
pagination.** `[FROM_SOURCE_CODE — xác nhận các tính năng này không tồn tại]`

### 4.2. Create Task `[FROM_SOURCE_CODE + FROM_LOGS, dữ liệu thật từ video]`

Trình tự chính xác: (1) User click "+ Thêm việc" → modal mở. (2) Điền form.
(3) Click "Thêm task". (4) Client fetch toàn bộ `/api/tasks` để check trùng
tên (case-insensitive). (5) Nếu trùng → `confirm()` dialog. (6) `POST
/api/tasks`. (7) Thành công → message + reset form + load lại bảng + đóng
modal sau 500ms.

Field bắt buộc: chỉ **Tiêu đề** (server: 1–255 ký tự, không rỗng). Mọi field
khác optional, có default (`priority=medium`, `status=todo`).

3 task thật đã tạo trong video `[FROM_LOGS, chính xác tuyệt đối]`:

| # | title | priority | category | due_date | task_id (UUID) | thời điểm tạo (UTC) |
|---|---|---|---|---|---|---|
| 1 | `làm lab` | low | study | 2026-02-09 | `33be5c43-e682-425f-882d-8cd948a8f70c` | 08:54:29.625 |
| 2 | `quay demo` | high | work | 2026-02-10 | `18c151cc-fee5-4be5-9981-9b10dcfc678b` | 08:54:55.207 |
| 3 | `nấu ăn` | low | personal | 2028-02-22 | `9cab0c2f-0c53-47e8-8b61-04c245a653f4` | 08:55:18.091 |

Mô tả (`description`) để trống ở cả 3 task (`NULL` trong DB) `[FROM_LOGS,
Postgres INSERT statement]`. Không quan sát được thao tác gõ description
trong video ở bước tạo 3 task này.

UI thay đổi sau khi tạo thành công: bảng có thêm 1 dòng mới, 3 thẻ đếm cập
nhật (thẻ "Chưa làm" +1 vì mặc định `todo`), modal tự đóng sau 0.5s.

Error behavior: nếu tiêu đề rỗng → server trả 400 validation error (thông
qua handler chung, không có message field cụ thể) — **không quan sát được**
việc tạo task rỗng trong video này `[NOT VISIBLE]`.

### 4.3. Read Task `[FROM_SOURCE_CODE + OBSERVED]`

2 cách vào chi tiết: (a) bấm nút "Xem" trên 1 dòng của bảng chính (chỉ xem
được task của chính mình vì bảng chỉ liệt kê task của user hiện tại); (b) dán
ID vào ô "Tra cứu theo ID" rồi bấm "Xem theo ID" (có thể là ID của người khác
— dùng để test IDOR, xem mục 9).

Task detail hiển thị (trong modal): ID, user_id chủ sở hữu, Mô tả, Ưu tiên
(badge), Trạng thái (text, không phải dropdown ở đây), Danh mục, Hạn chót, Tạo
lúc, Cập nhật lúc (2 mốc thời gian này định dạng theo locale `vi-VN`), và
section Ghi chú (load riêng bằng 1 API call thứ 2 sau khi modal mở).

### 4.4. Update Task `[FROM_SOURCE_CODE + FROM_LOGS]`

**Chỉ có 1 cách sửa task trong toàn bộ UI: đổi dropdown Trạng thái ngay trong
bảng danh sách.** Không có form "Edit" đầy đủ để sửa title/description/
priority/category/due_date qua UI (dù API `PUT /api/tasks/{id}` hỗ trợ sửa
mọi field — chỉ là frontend không có form gọi tới các field khác).
`[FROM_SOURCE_CODE — xác nhận giới hạn này]`

3 lần đổi trạng thái thật trong video `[FROM_LOGS]`:

| task | old → new | thời điểm (UTC) |
|---|---|---|
| `nấu ăn` (9cab0c2f) | todo → done | 08:56:09.074 |
| `làm lab` (33be5c43) | todo → doing | 08:56:11.012 |
| `quay demo` (18c151cc) | todo → doing | 08:56:12.903 |

Đổi dropdown → gửi PUT ngay (không có nút Lưu, không có xác nhận) → class CSS
của dropdown đổi màu ngay theo trạng thái mới → **không tự động load lại 3
thẻ đếm phía trên cho tới lần load bảng tiếp theo** (vì hàm đổi trạng thái chỉ
PUT, không gọi lại `loadTasks()`) `[FROM_SOURCE_CODE — chi tiết hành vi
frontend, cần tái tạo đúng]`.

### 4.5. Delete Task `[FROM_SOURCE_CODE + FROM_LOGS]`

**Không có modal xác nhận.** Nút "Xoá" (style `danger`, nền đỏ nhạt) trên mỗi
dòng → click → gọi `DELETE /api/tasks/{id}` ngay lập tức → load lại toàn bộ
danh sách. Task `nấu ăn` bị xoá lúc `08:56:15.783` (sau khi đã set `done` ở
bước trước) — không có comment nào gắn với task này nên
`cascaded_comments_deleted=0`.

---

## 5. COMMENT SYSTEM (UI gọi là "Ghi chú", không phải "Bình luận")

`[FROM_SOURCE_CODE + FROM_LOGS]`

### View comments

Nằm trong modal chi tiết task, dưới đường kẻ ngang, heading "Ghi chú". Mỗi
comment hiển thị: nội dung + timestamp (`toLocaleString("vi-VN")`) bên dưới
bằng chữ nhỏ màu nhạt, và 1 nút "Xoá" nhỏ bên phải. Không hiển thị username
tác giả (vì 1 task chỉ owner mới truy cập được nên hiển nhiên tác giả comment
= chính user đó, UI không cần ghi thêm). Nếu chưa có comment: "Chưa có ghi
chú nào." Nếu API lỗi: "Không tải được ghi chú (HTTP {status})."

### Add comment

Input placeholder: "VD: đã liên hệ khách hàng lúc 15h". Button "Thêm ghi chú"
(style secondary). Validation: nội dung không được rỗng (client chặn trước:
"Nhập nội dung ghi chú trước đã." nếu rỗng; server: 1–1000 ký tự). Thành công:
input xoá trắng, message "Đã thêm ghi chú.", danh sách comment load lại.

Comment thật trong video: nội dung `"cần làm gấp"`, gắn vào task `quay demo`
(18c151cc), tạo lúc `08:55:56.094` UTC, `comment_id =
dd137b9e-de72-4fb6-9ea3-44d367bfe0cc`.

### Delete comment

**Ai có quyền xoá**: về mặt code, bất kỳ ai mở được task đó (tức chỉ chủ sở
hữu task, vì `get_owned_task` chặn từ đầu) đều xoá được **bất kỳ comment nào**
trên task đó — không có kiểm tra "chỉ tác giả comment mới được xoá" (vì trong
model này chỉ có 1 người viết được comment lên task của chính mình, nên không
có tình huống nhiều người bình luận chung). **Không có modal xác nhận.** Click
"Xoá" → `DELETE .../comments/{id}` ngay → load lại danh sách.

Comment `cần làm gấp` bị xoá ngay sau đó, lúc `08:56:02.420` UTC.

---

## 6. USER INTERACTION FLOW — trình tự thật, dựng lại từ video + log

Mốc thời gian: `mm:ss` = tính từ đầu video; giờ UTC = thời điểm thật trong
log (video bắt đầu đúng `08:52:35 UTC`). `[OBSERVED + FROM_LOGS]`

1. `00:00` — Desktop trống, chuẩn bị quay.
2. `~00:02` — Mở `/login.html` ("Welcome Back").
3. `~00:08` — Chuyển sang `/register.html` ("Create Account").
4. `~00:12–00:18` — Điền username=`vcstest`, email=`kkkk@gmail.com`, password
   → bấm "Register" → **08:52:53.657** `POST /api/auth/register` → 201.
5. `~00:24` — Tự tay quay lại `/login.html`.
6. `~00:32` — Điền username/password, bấm "Sign In" → **08:53:08.494**
   `POST /api/auth/login` → 200 → sau 500ms redirect `/index.html`.
7. `~00:34` — Home hiện "Chào mừng trở lại, vcstest!", 3 thẻ đều 0 (task
   rỗng — **08:53:09.046** `GET /api/tasks` → `count:0`).
8. `~01:26` — Chuyển sang `/tasks.html`.
9. `~01:28–01:58` — Mở modal "+ Thêm việc", tạo task 1 "làm lab" (low/study,
   hạn 2026-02-09) → **08:54:29.625** tạo thành công, đếm = 1.
10. `~02:18–02:22` — Tạo task 2 "quay demo" (high/work, hạn 2026-02-10) →
    **08:54:55.207**, đếm = 2.
11. `~02:42–02:46` — Tạo task 3 "nấu ăn" (low/personal, hạn 2028-02-22) →
    **08:55:18.091**, đếm = 3.
12. `~02:46–03:00` — Bấm "Xem" mở chi tiết 1 task (33be5c43 "làm lab" —
    **08:55:22.590**), xem section Ghi chú rỗng.
13. `~03:10–03:16` — Bấm "Xem" mở chi tiết task "quay demo" (18c151cc —
    **08:55:51.532**).
14. `~03:20` — Gõ ghi chú "cần làm gấp", bấm "Thêm ghi chú" →
    **08:55:56.099**, đếm ghi chú = 1.
15. `~03:26` — Bấm "Xoá" trên ghi chú vừa tạo → **08:56:02.424**, đếm ghi chú
    về 0.
16. `~03:34` — Đổi dropdown trạng thái task "nấu ăn": Chưa làm → Hoàn thành →
    **08:56:09.078**.
17. `~03:36` — Đổi trạng thái "làm lab": Chưa làm → Đang làm →
    **08:56:11.017**.
18. `~03:38` — Đổi trạng thái "quay demo": Chưa làm → Đang làm →
    **08:56:12.907**.
19. `~03:41` — Bấm "Xoá" trên task "nấu ăn" (đã Hoàn thành) →
    **08:56:15.787**, `cascaded_comments_deleted:0`. Đếm còn lại: Chưa làm=0,
    Đang làm=2, Hoàn thành=0.
20. `~04:04–04:20` — Chuyển sang đăng ký tài khoản thứ 2: username=`bob`,
    email=`aaa@gmail.com` → **08:56:55.354** `POST /api/auth/register` → 201.
    (Không thấy sự kiện Logout tương ứng trong log ở bước chuyển từ vcstest
    sang màn hình đăng ký này — xem lưu ý ở mục 3.3.)
21. `~04:28` — Đăng nhập `bob` → **08:57:03.127** → 200 → về Home, "Chào mừng
    trở lại, bob!", 0 task.
22. `~04:30–04:32` — Sang `/tasks.html`, danh sách rỗng (task của bob = 0).
23. `~04:34–04:36` — Dán ID của task "làm lab" (33be5c43, thuộc về vcstest)
    vào ô "Tra cứu theo ID", bấm "Xem theo ID" → **08:57:11.078**
    `authorization_denied` (`owner_id=4a64ba5c... requester_id=a4b3835a...`) →
    HTTP **403**, message hiện `"HTTP 403: {"detail":"Not allowed to access
    this task"}"`.
24. `~05:02–05:11` — Chuyển sang cửa sổ PowerShell, chạy
    `curl.exe -k -s -w "\nHTTP:%{http_code}" https://localhost:8443/api/debug/crash`
    → **08:57:45.979** → HTTP **500**. Mở `logs\app\app.log` bằng Notepad,
    cuộn tới dòng `unhandled_exception` xem full stack trace
    (`backend/app/routers/debug.py:11`, `RuntimeError: Intentional crash for
    demo/recording: unhandled exception scenario`).
25. `~05:36–05:52` — Chạy `docker compose stop backend`.
26. `~05:52–06:06` — Chạy
    `curl.exe -k -s -o NUL -w "status: %{http_code}, time: %{time_total}s`n" https://localhost:8443/api/health`
    → chờ **~14.4 giây** → **08:58:41** → HTTP **502**. Mở
    `logs\nginx\error.log` xem dòng
    `connect() failed (113: Host is unreachable) ... upstream:
    "http://172.18.0.2:8000/api/health"`.
27. `~06:24` — Chạy `docker compose start backend`, chờ container khởi động
    lại.
28. `~06:42` — Gọi lại `/api/health` → **08:59:16.884** → HTTP **200**
    (`{"status":"ok"}`), phục hồi bình thường.
29. `~06:44–06:56` — Mở PowerShell (bản gốc, không phải Git Bash), dán đoạn
    script vòng lặp 5 lần (Windows Terminal cảnh báo "paste warning" trước
    khi cho paste đoạn multi-line).
30. `~06:57` — Chạy vòng lặp
    `1..5 | ForEach-Object { curl.exe -k -X POST https://localhost:8443/api/auth/login -H "Content-Type: application/json" -d '{"username":"carol","password":"wrong"}' }`
    → 5 request gần như liền nhau **08:59:32.406→.539** → mỗi lần **401**,
    `fail_count` 1→5, lần thứ 5 kèm `ACCOUNT_LOCKED`.
31. `~07:08–07:30` — Xem lại các cửa sổ terminal/log tổng hợp các sự kiện vừa
    demo (LOGIN_FAIL × 5, ACCOUNT_LOCKED, login_attempts trong Postgres).
32. `~07:30–07:32` — Quay lại trang Task Manager (Tasks), 3 thẻ đếm hiện
    "0 · 2 · 0" (2 task của bob = 0, đây thực chất vẫn là dữ liệu cache cũ
    hiển thị hoặc màn hình Tasks đang mở của phiên trước — không có API call
    mới nào sau 08:59:32 theo log). Video kết thúc.

---

## 7. API / BACKEND BEHAVIOR — toàn bộ `[OBSERVED]` (bắt được thật trong
`logs/nginx/access.log` + `logs/app/app.log` + `logs/app/auth.log` đúng cửa
sổ video), method/path/status **không suy đoán**.

| Method | Endpoint | Khi nào gọi trong video | Response status | UI effect |
|---|---|---|---|---|
| POST | `/api/auth/register` | Submit form Register | 201 (×2: vcstest, bob) | message xanh, ở lại trang |
| POST | `/api/auth/login` | Submit form Login | 200 (×2 UI) / 401 (×5 curl) | 200: lưu localStorage + redirect; 401: message đỏ |
| POST | `/api/auth/logout` | (không quan sát được lần gọi nào) | — | `[NOT VISIBLE]` |
| GET | `/api/tasks` | Load trang Tasks/Home, mỗi lần trước khi POST tạo task (duplicate-check), sau mỗi create/update/delete | 200 | render bảng + 3 thẻ đếm |
| POST | `/api/tasks` | Bấm "Thêm task" | 201 (×3) | thêm dòng bảng, đóng modal |
| GET | `/api/tasks/{id}` | Bấm "Xem" hoặc "Xem theo ID" | 200 (chủ sở hữu) / 403 (IDOR, ×1) | mở modal / message lỗi |
| PUT | `/api/tasks/{id}` | Đổi dropdown trạng thái | 200 (×3) | badge màu đổi ngay |
| DELETE | `/api/tasks/{id}` | Bấm "Xoá" | 204 (×1) | dòng biến mất khỏi bảng |
| GET | `/api/tasks/{id}/comments` | Mở modal chi tiết (tự động) | 200 | render list ghi chú |
| POST | `/api/tasks/{id}/comments` | Bấm "Thêm ghi chú" | 201 (×1) | thêm dòng ghi chú |
| DELETE | `/api/tasks/{id}/comments/{cid}` | Bấm "Xoá" trên ghi chú | 204 (×1) | dòng ghi chú biến mất |
| GET | `/api/debug/crash` | curl thủ công (không qua UI) | 500 | (không có UI — chỉ terminal) |
| GET | `/api/health` | curl thủ công ×2 (trước/sau khi stop backend) | 502 rồi 200 | (không có UI) |

Không quan sát được: `GET/PUT /api/users/{id}` (Profile) — route này tồn tại
trong code (`backend/app/routers/profile.py`) nhưng **không được gọi trong
video này**, đánh dấu `[FROM_SOURCE_CODE only — không phải OBSERVED]`:

| Method | Endpoint | Request | Response | UI effect |
|---|---|---|---|---|
| GET | `/api/users/{id}` | (không có body) | `UserOut` JSON | điền form Profile |
| PUT | `/api/users/{id}` | `{email?, password?}` | `UserOut` JSON hoặc lỗi | message + reload |

**Cấu trúc chung mọi response lỗi** `[FROM_SOURCE_CODE]`: FastAPI trả
`{"detail": "..."}`; riêng lỗi validate (`400`) và lỗi 500 còn kèm thêm
`"request_id"` để đối chiếu ngược lại log server — **client chỉ thấy
request_id + message chung, KHÔNG BAO GIỜ thấy stack trace**.

---

## 8. DATA MODEL — trích nguyên văn từ `backend/app/models.py` /
`backend/app/schemas.py` `[FROM_SOURCE_CODE]`

### User (`users`)
- `id`: UUID, khoá chính
- `username`: string(50), unique, bắt buộc
- `email`: string(255), unique, bắt buộc
- `password_hash`: string(255), bắt buộc — **bcrypt hash, không bao giờ lưu
  plaintext** (xem mục 9)
- `created_at`, `updated_at`: timestamp có timezone

### Session (`sessions`)
- `id`: UUID (chính là giá trị cookie `session_id`)
- `user_id`: UUID, FK → users
- `created_at`, `expires_at`, `revoked_at` (nullable): timestamp
- `ip_address`: string(64), `user_agent`: string(512)

### Task (`tasks`)
- `id`: UUID
- `user_id`: UUID, FK → users (chủ sở hữu)
- `title`: string(255), bắt buộc
- `description`: string(2000), optional
- `priority`: string(20), default `"medium"`
- `status`: string(20), default `"todo"`
- `category`: string(50), optional, có index riêng
- `due_date`: date, optional
- `created_at`, `updated_at`: timestamp

### TaskComment (`task_comments`)
- `id`: UUID
- `task_id`: UUID, FK → tasks, **`ON DELETE CASCADE` ở tầng DB** (xoá task tự
  động xoá hết comment liên quan)
- `user_id`: UUID, FK → users
- `content`: string(1000), bắt buộc
- `created_at`: timestamp

### LoginAttempt (`login_attempts`) — bảng phục vụ cơ chế khoá tài khoản
- `id`: UUID
- `username`: string(50), nullable (ghi username gõ vào, kể cả không tồn tại)
- `ip_address`: string(64), bắt buộc
- `success`: boolean
- `created_at`: timestamp, có index (dùng để đếm số lần fail trong cửa sổ 5 phút)

**Ràng buộc giá trị hợp lệ cho `priority`/`status`/`category`** `[FROM_SOURCE_CODE]`:
không có enum/CHECK constraint ở tầng DB hay Pydantic — chỉ giới hạn độ dài
string. Frontend chỉ cho chọn 3 giá trị cố định qua `<select>`
(`low/medium/high` và `todo/doing/done`), nhưng **API về lý thuyết chấp nhận
bất kỳ chuỗi nào** cho các field này nếu gọi trực tiếp (không qua UI). Category
UI gợi ý 3 giá trị (`work/study/personal`) qua placeholder nhưng là free-text
input, không phải select — API cũng chấp nhận bất kỳ chuỗi ≤50 ký tự.

---

## 9. SECURITY / LOGGING BEHAVIOR

`[FROM_SOURCE_CODE + FROM_LOGS]` — đây là phần cốt lõi của ứng dụng, quan sát
được trực tiếp qua nhiều cửa sổ terminal/Notepad trong hơn nửa thời lượng
video (~04:44 trở đi gần như toàn bộ màn hình là log).

### 9.1. Kiến trúc log — 4 nguồn, 1 mã tương quan chung

| Nguồn | File | Ghi gì |
|---|---|---|
| Nginx access | `logs/nginx/access.log` | 1 dòng JSON/request: `request_id`, method, uri, status, thời gian xử lý, session_id (đọc từ cookie), user-agent, referer |
| Nginx error | `logs/nginx/error.log` | lỗi tầng hạ tầng (vd upstream unreachable) |
| App | `logs/app/app.log` | 1 dòng `http_request` chung cho MỌI request (method/path/status/duration_ms) **+** 1 dòng nghiệp vụ cụ thể cho hầu hết action (`task_create`, `task_update`, `comment_delete`, `authorization_denied`, `unhandled_exception`...) — tức là **double-logging**: 1 request quan trọng thường có ≥2 dòng trong app.log |
| Auth | `logs/app/auth.log` | riêng các sự kiện auth: `LOGIN_SUCCESS`, `LOGIN_FAIL`, `LOGOUT`, `SESSION_EXPIRED`, `ACCOUNT_LOCKED` — **cũng bị log kép** vì app.log còn ghi thêm bản rút gọn (`login_success`, `login_fail`, `logout` chữ thường) |
| Postgres | `logs/postgres/postgresql-<ngày>.log` | với `log_statement=mod`: ghi nguyên văn câu SQL của mọi `INSERT/UPDATE/DELETE` — **KHÔNG ghi `SELECT`** |

Mã tương quan xuyên suốt 3 tầng đầu: **`request_id`** — sinh ở Nginx
(`$request_id`), forward xuống backend qua header `X-Request-ID`, backend
dùng lại đúng giá trị đó (không tự sinh mới) cho mọi dòng log của request đó
kể cả trả lại cho client qua response header `X-Request-ID` và field
`request_id` trong body lỗi. Vì vậy 1 sự cố có thể lần từ response client →
app.log → nginx access.log bằng cùng 1 chuỗi hex.

### 9.2. Các event log-được quan sát trực tiếp trong video

- `register` (app.log) — thành công cho `vcstest`, `bob`
- `LOGIN_SUCCESS` (auth.log) + `login_success` (app.log) — 2 lần qua UI
- `LOGIN_FAIL` (auth.log) + `login_fail` (app.log) — 5 lần (curl, carol)
- `ACCOUNT_LOCKED` (auth.log) — 1 lần, kèm `fail_count/window_minutes/lockout_minutes`
- `task_create`, `task_read`, `task_update`, `task_delete` (app.log) — đủ cả 4
- `comment_create`, `comment_read`, `comment_delete` (app.log)
- `authorization_denied` (app.log, level WARNING) — khi bob xem task của vcstest
- `unhandled_exception` (app.log, level ERROR) — kèm `exception_type`,
  `stack_trace` đầy đủ (chỉ trong file log, không trả về client)
- `http_request` (app.log) — 1 dòng/request, mọi request đều có

### 9.3. Điểm mù có chủ đích cần biết khi tái tạo

- Postgres không audit `SELECT` → mọi thao tác "đọc" (`task_read`,
  `comment_read`, kể cả `SELECT` bên trong request IDOR bị 403) **không để
  lại dấu vết ở tầng DB**, chỉ thấy được qua app.log. Request IDOR **vẫn thật
  sự chạm DB** (code chạy `db.get(Task, task_id)` trước khi so `owner_id`) —
  DB im lặng không có nghĩa là DB không được truy vấn.
- `ON DELETE CASCADE` xoá `task_comments` khi xoá `tasks` xảy ra hoàn toàn ở
  tầng Postgres — không sinh dòng `DELETE FROM task_comments` riêng trong
  audit log DB. Vì vậy code tầng ứng dụng chủ động đếm số comment sắp bị xoá
  **trước** khi xoá task, và ghi số đó vào field `cascaded_comments_deleted`
  của event `task_delete` — bù đắp điểm mù này ở tầng app log.
- Mật khẩu **không bao giờ ở dạng plaintext** trong bất kỳ log/bảng nào:
  hash bằng `bcrypt` (`backend/app/security.py`) ngay ở tầng ứng dụng, trước
  khi câu SQL `INSERT INTO users` được tạo ra — nên kể cả Postgres audit log
  (ghi nguyên văn giá trị literal của câu INSERT) cũng chỉ thấy chuỗi
  `$2b$12$...` (đã hash), chưa từng thấy mật khẩu gốc. Xác nhận thật trong
  log của video: `password_hash` của `vcstest` =
  `$2b$12$sAJi7bJQdv77pP5NWSPxBuOUCVR/HFjvVY1meT.OJa3ohW9/DPqZm`.
- 500 vs 502 — khác lớp trừu tượng: 500 (`/api/debug/crash`) là tầng ứng
  dụng còn sống, code tự văng exception, phản hồi nhanh (9ms); 502 là tầng hạ
  tầng chết hẳn (`docker compose stop backend`), Nginx cố kết nối rồi mới
  nhận "Host is unreachable" sau **~14.4 giây** — chậm hơn nhiều so với bị từ
  chối kết nối ngay.

---

## 10. ERROR STATES

`[FROM_SOURCE_CODE, phần nào OBSERVED ghi rõ]`

| # | Trigger | HTTP | Error message client thấy | UI | Tiếp theo |
|---|---|---|---|---|---|
| 1 | Đăng ký username/email đã tồn tại | 400 | `Error 400: {"detail":"Username or email already registered"}` | message đỏ, ở lại trang | có thể sửa lại và submit lại |
| 2 | Sai định dạng field khi đăng ký (email sai/password<8) | 400 | `Error 400: {"detail":"Validation error","request_id":"..."}` | message đỏ | `[NOT VISIBLE trong video]`, suy từ code |
| 3 | Sai username/password khi login | 401 | `Error 401: {"detail":"Invalid username or password"}` | message đỏ | `[OBSERVED qua curl, không qua UI]` |
| 4 | Tài khoản bị khoá tạm (≥5 lần sai/5 phút) | 429 | `Error 429: {"detail":"Account temporarily locked due to repeated failed logins"}` | message đỏ | `[FROM_SOURCE_CODE only]`, chờ hết 5 phút |
| 5 | Session hết hạn/không hợp lệ khi gọi API cần login | 401 | tuỳ trang — hầu hết trang không tự bắt lỗi 401 để redirect về Login (không thấy logic đó trong code) | `[FROM_SOURCE_CODE — có thể là gap]` | `[NOT VISIBLE]` |
| 6 | Xem/sửa task không phải của mình (IDOR) | 403 | `HTTP 403: {"detail":"Not allowed to access this task"}` | message đỏ trong ô lookup-msg | `[OBSERVED]` |
| 7 | Task/Comment ID không tồn tại | 404 | `{"detail":"Task not found"}` / `{"detail":"Comment not found"}` | `[NOT VISIBLE]` | |
| 8 | Lỗi server không lường trước (`/api/debug/crash`) | 500 | `{"detail":"Internal server error","request_id":"..."}` | `[OBSERVED qua curl]` | client không thấy chi tiết lỗi |
| 9 | Backend container chết hẳn | 502 (nginx) | trang lỗi nginx mặc định / timeout ~14s | `[OBSERVED qua curl]` | chờ hạ tầng phục hồi |
| 10 | Tạo task trùng tên | — (không phải lỗi HTTP) | `confirm()` dialog trình duyệt | `[FROM_SOURCE_CODE]` | Cancel = huỷ, OK = vẫn tạo |
| 11 | Bấm "Xem theo ID" mà chưa nhập gì | — (chặn phía client) | `"Nhập ID trước đã."` | `[FROM_SOURCE_CODE]` | không gọi API |
| 12 | Bấm "Thêm ghi chú" mà nội dung rỗng | — (chặn phía client) | `"Nhập nội dung ghi chú trước đã."` | `[FROM_SOURCE_CODE]` | không gọi API |

---

## 11. TIMELINE PHÂN TÍCH VIDEO (từng ~30 giây)

`[OBSERVED, đối chiếu FROM_LOGS ở mọi mốc có API call]`

**[00:00–00:30]** Desktop trống → mở `/login.html` → sang `/register.html` →
bắt đầu điền form đăng ký (`vcstest`). *Kết quả*: chuẩn bị dữ liệu demo.

**[00:30–01:00]** Submit Register (08:52:53, 201) → quay lại Login → điền +
submit → Login thành công (08:53:08, 200) → Home hiện chào mừng "vcstest",
dashboard 0 task.

**[01:00–01:30]** Ở lại Home vài giây → chuyển sang `/tasks.html` → bấm
"+ Thêm việc", modal tạo task mở ra.

**[01:30–02:00]** Điền form task 1 ("làm lab", low, study, due 2026-02-09),
đổi các dropdown ưu tiên/trạng thái, gõ danh mục.

**[02:00–02:30]** Submit task 1 (08:54:29, đếm=1) → mở lại modal, điền +
submit task 2 ("quay demo", high, work, due 2026-02-10, 08:54:55, đếm=2).

**[02:30–03:00]** Xuất hiện dialog `confirm()` cảnh báo trùng tên (hoặc thao
tác liên quan) → submit task 3 ("nấu ăn", low, personal, due 2028-02-22,
08:55:18, đếm=3) → bấm "Xem" mở chi tiết 1 task.

**[03:00–03:30]** Xem chi tiết task "quay demo" → gõ ghi chú "cần làm gấp" →
submit (08:55:56) → bấm Xoá ghi chú đó (08:56:02).

**[03:30–04:00]** Đổi trạng thái lần lượt 3 task: nấu ăn→done (08:56:09), làm
lab→doing (08:56:11), quay demo→doing (08:56:12) → xoá task "nấu ăn"
(08:56:15).

**[04:00–04:30]** Chuyển màn hình (có thể logout không ghi log được) →
`/register.html` lần 2, điền tài khoản `bob` → submit (08:56:55, 201) →
`/login.html` → submit → login thành công (08:57:03, 200) → Home "bob", 0 task.

**[04:30–05:00]** Sang `/tasks.html` (rỗng) → dán ID task của vcstest vào ô
tra cứu → bấm "Xem theo ID" → nhận lỗi 403 (08:57:11) → chuyển cửa sổ sang
PowerShell.

**[05:00–05:30]** Chạy `curl` gọi `/api/debug/crash` (08:57:45, 500) → mở
Notepad xem `app.log`, cuộn tìm dòng `unhandled_exception` + đọc `stack_trace`.

**[05:30–06:00]** Đóng Notepad (dialog "Keep unsaved changes?" xuất hiện) →
mở PowerShell mới → chạy `docker compose stop backend` → chạy curl
`/api/health`, terminal đứng chờ phản hồi.

**[06:00–06:30]** Nhận phản hồi 502 sau ~14.4s (08:58:41) → mở
`logs\nginx\error.log` bằng Notepad, chỉ dòng "Host is unreachable" → chạy
`docker compose start backend`.

**[06:30–07:00]** Chờ backend healthy → gọi lại `/api/health` → 200
(08:59:16) → mở PowerShell mới (bản gốc, không Git Bash) → dán đoạn script
vòng lặp brute-force (Windows Terminal cảnh báo paste) → chạy vòng lặp 5 lần
login sai `carol/wrong` (08:59:32, 5×401 + ACCOUNT_LOCKED).

**[07:00–07:32]** Xem lại log tổng hợp các dòng `LOGIN_FAIL`/`ACCOUNT_LOCKED`/
`login_attempts` trong nhiều cửa sổ terminal/Notepad → quay lại trình duyệt ở
trang Tasks (hiện số liệu "0 · 2 · 0" của tài khoản bob) → video kết thúc.

---

## 12. EXACT TEXT EXTRACTION

Toàn bộ text dưới đây trích **nguyên văn, giữ chính tả/viết hoa** trực tiếp
từ source code (`[FROM_SOURCE_CODE]`) — chính xác tuyệt đối, không phải đọc
qua pixel video.

### Trang Login
- Title tab: `Login - Task Manager`
- `Welcome Back`
- `Đăng nhập để tiếp tục quản lý công việc.`
- Label: `Username`, `Password`
- Button: `Sign In`
- `Sau 5 lần đăng nhập sai liên tiếp trong 5 phút, tài khoản sẽ tạm thời bị khoá.`
- `Chưa có tài khoản? Đăng ký`

### Trang Register
- Title tab: `Register - Task Manager`
- `Create Account`
- `Đăng ký để bắt đầu quản lý công việc.`
- Label: `Username`, `Email`, `Password (min 8 chars)`
- Button: `Register`
- `Đã có tài khoản? Đăng nhập`
- Message thành công (template): `Registered user '{username}'. You can now log in.`

### Trang Home
- Title tab: `Home - Task Manager`
- Nhãn: `DASHBOARD`
- Heading (guest, không có username): `Chào mừng trở lại!`
- Heading (đã login, template): `Chào mừng trở lại, {username}!`
- `Đây là tổng quan công việc của bạn.`
- `Bạn chưa đăng nhập. Đăng nhập để xem công việc của bạn.`
- Stat label: `Tổng công việc`, `Ưu tiên cao`, `Đến hạn hôm nay`
- `Bắt đầu`
- `Xem, tạo và cập nhật công việc trong trang Tasks.`
- Button: `Xem danh sách công việc`

### Trang Tasks
- Title tab: `Tasks - Task Manager`
- Nhãn: `CÔNG VIỆC CỦA TÔI`
- `Tasks`
- `Quản lý và theo dõi công việc cần làm.`
- Button: `+ Thêm việc`
- Stat label: `Chưa làm`, `Đang làm`, `Hoàn thành`
- `Danh sách`
- Filter option: `Tất cả danh mục`, `work`, `study`, `personal`
- Button: `Làm mới`
- Table header: `Tiêu đề`, `Ưu tiên`, `Trạng thái`, `Danh mục`, `Hạn chót`, `Thao tác`
- Row button: `Xem`, `Xoá`
- Priority label: `Thấp`, `Trung bình`, `Cao`
- Status label: `Chưa làm`, `Đang làm`, `Hoàn thành`
- Badge: `Quá hạn`
- `Tra cứu theo ID (test truy cập trái phép / IDOR)`
- `Dán ID của 1 task (kể cả task không phải của bạn) để thử xem — dùng để kiểm tra authorization: chỉ chủ sở hữu mới được xem, người khác sẽ nhận lỗi 403.`
- Label: `Task ID`; Placeholder: `vd: 6d137c2e-d870-430d-960c-854428acf066`
- Button: `Xem theo ID`
- `Nhập ID trước đã.`
- `Truy cập được — bạn là chủ sở hữu task này.`
- Modal tạo task heading: `Tạo công việc mới`
- Label: `Tiêu đề`, `Mô tả`, `Ưu tiên`, `Trạng thái`, `Danh mục (không bắt buộc)`,
  `Hạn chót (không bắt buộc)`
- Placeholder category: `work / study / personal`
- Button: `Thêm task` → khi đang gửi: `Đang thêm...`
- `Đã tạo công việc.`
- Duplicate confirm (template): `Đã có công việc tên "{title}". Bạn vẫn muốn tạo thêm một cái trùng tên?`
- `Đã huỷ - trùng tên với công việc đã có.`
- Modal chi tiết — detail label: `ID`, `Chủ sở hữu (user_id)`, `Mô tả`,
  `Ưu tiên`, `Trạng thái`, `Danh mục`, `Hạn chót`, `Tạo lúc`, `Cập nhật lúc`
- `Ghi chú`
- `Đang tải...`
- `Chưa có ghi chú nào.`
- Label: `Thêm ghi chú mới`; Placeholder: `VD: đã liên hệ khách hàng lúc 15h`
- Button: `Thêm ghi chú`
- `Nhập nội dung ghi chú trước đã.`
- `Đã thêm ghi chú.`
- `Đã tải {n} công việc.`

### Trang Profile
- Title tab: `Profile - Task Manager`
- Nhãn: `TÀI KHOẢN`
- `Hồ sơ cá nhân`
- `Thông tin tài khoản`
- Label: `Username`, `Email`
- `Cập nhật thông tin`
- Label: `Email mới (để trống nếu không đổi)`, `Mật khẩu mới (để trống nếu không đổi)`
- Button: `Lưu thay đổi`
- `Profile updated.`
- `Bạn chưa đăng nhập.`
- `Tham gia {ngày, vi-VN}`

### Chung mọi trang có nav
- Brand: `Task Manager`
- Nav link: `Home`, `Tasks`, `Profile`
- User area (guest): `Login`, `Register`
- User area (logged-in): `Logout`
- Footer: `Task Manager — ứng dụng quản lý công việc cá nhân`

### Text nhìn thấy trong terminal/log (video, không phải UI web)
`[OBSERVED — đã đối chiếu chính xác với file log thật]`: các dòng JSON log
`event`, `LOGIN_SUCCESS`, `LOGIN_FAIL`, `ACCOUNT_LOCKED`, `authorization_denied`,
`unhandled_exception`, thông báo lỗi nginx `connect() failed (113: Host is
unreachable)` — nguyên văn trích ở mục 6 và 9.

---

# WEB APPLICATION SPECIFICATION (tổng hợp — mục 13)

## A. Product overview

Task Manager: web app quản lý công việc cá nhân, kiến trúc 4 lớp (Frontend
tĩnh HTML/CSS/JS thuần → Nginx reverse-proxy/TLS → FastAPI backend →
PostgreSQL), có auth bằng session cookie (không phải JWT), mỗi user chỉ thấy
task của chính mình, task có ưu tiên/trạng thái/danh mục/hạn chót/ghi chú.
Kèm 2 công cụ phục vụ demo bảo mật/logging: ô tra cứu task theo ID (test
IDOR) và endpoint crash cố ý.

## B. Page map

`/login.html`, `/register.html`, `/index.html` (Home), `/tasks.html`,
`/profile.html`. Không có trang 404 tuỳ chỉnh quan sát được (nginx
`try_files` fallback về `index.html`).

## C. User flows

Xem mục 6 (đầy đủ, theo đúng thứ tự quan sát được trong video) làm chuẩn.

## D. UI specification

Xem mục 2 (từng trang) — bảng element đầy đủ, dùng làm căn cứ dựng lại UI
pixel-for-text-content chính xác. Bảng màu/spacing/font đầy đủ trong mục 2.1
(áp dụng chung mọi trang qua `style.css`).

## E. Functional requirements

CRUD Task đầy đủ (trừ Update chỉ giới hạn đổi trạng thái qua UI), CRUD Comment
đầy đủ, filter task theo category, thống kê task theo trạng thái (Tasks page)
và theo ưu tiên/hạn (Home page), tra cứu task theo ID bất kỳ (có kiểm tra
quyền sở hữu), xem/sửa hồ sơ cá nhân.

## F. Authentication requirements

Đăng ký (username 3–50, email hợp lệ, password 8–128), đăng nhập bằng
username/password → session cookie httponly 30 phút, đăng xuất revoke
session, khoá tạm 5 phút sau 5 lần sai trong 5 phút (theo username HOẶC ip).

## G. Task CRUD requirements

Xem mục 4 đầy đủ — đặc biệt lưu ý: **Delete không có confirm dialog**, **Update
qua UI chỉ đổi được status**, **Create có duplicate-title confirm dialog và
tự thực hiện 1 lượt GET toàn bộ danh sách trước khi POST**.

## H. Comment requirements

Xem mục 5 — không giới hạn quyền xoá theo tác giả (chỉ giới hạn theo quyền sở
hữu task), không có sửa comment (chỉ thêm/xoá).

## I. API specification

Xem mục 7 — 12 endpoint quan sát trực tiếp + 2 endpoint suy từ code
(`/api/users/{id}` GET/PUT).

## J. Data model

Xem mục 8 — 5 bảng, quan hệ 1-nhiều User→Task→TaskComment, User→Session,
username OR ip_address→LoginAttempt.

## K. Validation rules

Username 3–50 ký tự; Email định dạng hợp lệ; Password 8–128 ký tự; Task title
1–255; Task description ≤2000; Task priority/status/category ≤20/20/50 (không
enum-constrained ở API, chỉ constrained ở UI qua `<select>`); Comment content
1–1000. Toàn bộ validate ở server (Pydantic), lỗi → 400 message chung
"Validation error" + request_id (không trả chi tiết field-level cho client).

## L. Error handling

Xem mục 10 — bảng đầy đủ 12 tình huống lỗi với message/status/UI chính xác.

## M. Security behavior

Bcrypt hash password (không log/lưu plaintext ở bất kỳ layer nào kể cả audit
DB log), session cookie httponly + samesite=strict, IDOR check ở tầng ứng
dụng (`owner_id == current_user.id`) chứ không dựa vào DB, rate-limit đăng
nhập theo username OR ip (5 lần/5 phút → khoá 5 phút), stack trace lỗi 500
chỉ nằm trong log server, không bao giờ trả về client.

## N. Logging/audit requirements

Xem mục 9 — request_id xuyên suốt Nginx↔App↔Auth log; double-logging (1 event
nghiệp vụ + 1 `http_request` chung/mỗi request); Postgres `log_statement=mod`
chỉ audit INSERT/UPDATE/DELETE (không SELECT); cascade delete ở DB cần được
app tầng trên bù đắp bằng cách đếm rồi log tường minh (`cascaded_comments_deleted`).

## O. Navigation rules

Nav bar chỉ ở 3 trang cần auth-aware (Home/Tasks/Profile), không có ở
Login/Register. Active link có border-bottom màu accent. Click logo → Home.
Escape key đóng mọi modal đang mở trên trang Tasks.

## P. State management

Không dùng framework — vanilla JS, state của user (`{id, username}`) lưu
`localStorage` key `tm_user` (KHÔNG lưu token, chỉ lưu để hiển thị UI —
quyền thật do cookie httponly quyết định phía server). Mỗi trang tự fetch lại
dữ liệu cần thiết khi load (không có global store/cache client-side).

## Q. Acceptance criteria

Xem mục 14.

---

## 14. ACCEPTANCE CRITERIA

- [x] User có thể đăng ký tài khoản (username/email/password, validate server-side). `[OBSERVED ×2]`
- [x] Đăng ký không tự động đăng nhập/chuyển trang sau khi thành công. `[FROM_SOURCE_CODE]`
- [x] User có thể đăng nhập bằng username/password, được set session cookie httponly. `[OBSERVED ×2 + FROM_LOGS]`
- [x] Sai username/password hiển thị error message chung, không phân biệt lý do cụ thể cho client. `[FROM_SOURCE_CODE, OBSERVED qua curl]`
- [x] Sau 5 lần đăng nhập sai liên tiếp trong 5 phút (tính theo username HOẶC ip), tài khoản/IP bị khoá 5 phút, request tiếp theo trả 429. `[OBSERVED 5 lần đầu + FROM_SOURCE_CODE cho phản hồi 429]`
- [ ] Lần thử thứ 6 trở đi trong lúc bị khoá trả về 429 đúng như mô tả — **chưa được quan sát trực tiếp trong video này**, chỉ suy từ code.
- [x] User có thể xem danh sách task của chính mình, lọc theo category, xem 3 số liệu đếm theo trạng thái. `[OBSERVED]`
- [x] User có thể tạo task mới (title bắt buộc, các field khác optional có default). `[OBSERVED ×3]`
- [x] Tạo task trùng tên (case-insensitive) hiện dialog xác nhận trước khi cho tạo thêm. `[FROM_SOURCE_CODE]`
- [x] User chỉ có thể đổi trạng thái task qua UI (không có form sửa đầy đủ field khác). `[OBSERVED ×3 + FROM_SOURCE_CODE]`
- [x] User có thể xoá task ngay lập tức, không cần xác nhận; nếu task có comment, toàn bộ comment bị xoá theo (cascade) và được log rõ số lượng. `[OBSERVED ×1, 0 comment nên không kiểm chứng được số >0]`
- [x] User có thể xem chi tiết 1 task (kể cả bằng cách dán ID thủ công), gồm đầy đủ field + ghi chú. `[OBSERVED]`
- [x] User có thể thêm ghi chú (comment) vào task của mình. `[OBSERVED ×1]`
- [x] User có thể xoá ghi chú ngay lập tức, không cần xác nhận. `[OBSERVED ×1]`
- [x] User KHÔNG thể xem/sửa task của người khác — nhận lỗi 403, sự kiện `authorization_denied` được ghi log với đủ owner_id/requester_id. `[OBSERVED ×1]`
- [x] Đăng xuất xoá session phía server (revoke) và xoá cookie, redirect về Login. `[FROM_SOURCE_CODE — không quan sát trực tiếp thao tác click Logout trong video này]`
- [x] Lỗi không lường trước (unhandled exception) trả 500 kèm request_id, KHÔNG lộ stack trace cho client; stack trace đầy đủ chỉ nằm trong log server. `[OBSERVED]`
- [x] Khi backend hạ tầng chết hẳn (container dừng), Nginx trả 502 sau một khoảng chờ dài (do phải timeout kết nối tới IP container), khác biệt rõ với lỗi 500 ở tầng ứng dụng. `[OBSERVED]`
- [x] Mọi request quan trọng có `request_id` xuyên suốt Nginx/App/Auth log để đối chiếu chéo. `[OBSERVED + FROM_SOURCE_CODE]`
- [x] Mật khẩu không bao giờ xuất hiện dạng plaintext ở bất kỳ log hay bảng DB nào (chỉ bcrypt hash). `[FROM_LOGS xác nhận qua Postgres audit log]`
- [ ] Chức năng Profile (xem/sửa email, đổi mật khẩu) — tồn tại đầy đủ trong code nhưng **không được thao tác trong video này**, cần AI coding agent tự tin cậy vào mục 2.5/3 (FROM_SOURCE_CODE) khi tái tạo, không có bằng chứng hình ảnh trực tiếp.

---

## 15. GHI CHÚ PHƯƠNG PHÁP (tổng kết mức độ tin cậy)

- Mọi text UI, CSS, API contract, data model, validation rule trong tài liệu
  này lấy **trực tiếp từ mã nguồn thật** của ứng dụng đang chạy trong video —
  độ tin cậy tuyệt đối, không phải suy đoán.
- Mọi giá trị dữ liệu nhập tay trong demo (tên task, email, thứ tự thao tác,
  request/response, timestamp) lấy từ **log thật phát sinh trong đúng phiên
  quay video này** (đã xác nhận khớp cửa sổ thời gian tuyệt đối với
  `creation_time` của file video) — độ tin cậy tuyệt đối cho phần đã có log,
  không suy đoán.
- Phần bố cục/màu sắc/trình tự click quan sát qua 226 khung hình (2 giây/khung,
  480px chiều ngang) — đủ để dựng đúng trình tự và nội dung màn hình, nhưng
  **không dùng để đọc text** (vì thumbnail nhỏ) — mọi text đều đối chiếu lại
  bằng source code ở trên.
- Phần **không có bằng chứng nào** (source code, log, hay hình ảnh) được đánh
  dấu rõ `[NOT VISIBLE]` — không bịa. Chức năng Profile là ví dụ chính: tồn
  tại chắc chắn trong code nhưng chưa từng được thao tác trong video này.
- **Audio của video không được phân tích** (không có công cụ speech-to-text
  trong môi trường phân tích) — nếu video có lời thuyết minh giải thích thêm
  bối cảnh/lý do, nội dung đó không nằm trong tài liệu này.
