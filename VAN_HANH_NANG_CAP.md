# Vận hành ứng dụng — Nâng cấp mã nguồn

Tài liệu này mô tả các đợt **nâng cấp mã nguồn** thực hiện trên ứng dụng
Task Manager đang chạy (đã có dữ liệu thật của user), cùng các vấn đề
cần quan tâm khi đưa thay đổi vào một hệ thống đang vận hành — không chỉ
đơn thuần là sửa code. Có 2 đợt nâng cấp: **Đợt 1** (mục 1-2, bên dưới)
thêm nhãn/category; **Đợt 2** (mục 3) thêm ghi chú/comment cho task —
đọc mục 3 nếu bạn cần ví dụ về migration **tạo bảng mới** (khác với đợt
1 chỉ `ADD COLUMN`).

---

# Đợt nâng cấp 1 — Category

## 1. Tính năng thêm mới

| Trước nâng cấp | Sau nâng cấp |
|---|---|
| Task chỉ có title/description/priority/status/due_date | Task có thêm `category` (nhãn tự do, VD `work`/`study`/`personal`) |
| `GET /api/tasks` luôn trả toàn bộ task của user | `GET /api/tasks?category=work` lọc được theo nhãn |

Thay đổi cụ thể trong code:
- `backend/app/models.py` — thêm cột `category` vào `Task`
- `backend/app/schemas.py` — thêm field `category` (optional) vào `TaskCreate`, `TaskUpdate`, `TaskOut`
- `backend/app/routers/tasks.py` — `list_tasks` nhận query param `category` optional, filter theo cột đó; `task_read`/`task_create` log thêm field liên quan
- `frontend/tasks.html` — thêm ô nhập category khi tạo task, thêm dropdown lọc theo nhãn, thêm cột Category trong bảng
- `db/migrations/0001_add_task_category.sql` — migration script (chi tiết ở mục 2)

## 2. Vấn đề cần quan tâm khi nâng cấp

### 2.1. Migration database — vấn đề quan trọng nhất

App dùng `Base.metadata.create_all(bind=engine)` lúc startup
(`backend/app/main.py`) để tạo bảng. Hàm này **chỉ tạo bảng chưa tồn
tại**, **không** tự động `ALTER TABLE` một bảng đã có sẵn để thêm cột
mới. Vì bảng `tasks` đã tồn tại từ bản cũ (đã có dữ liệu), nếu chỉ deploy
code mới mà không migrate DB trước:

- SQLAlchemy model có cột `category`, nhưng bảng thật trong Postgres thì
  không → mọi câu query/insert đụng tới `tasks` sẽ lỗi
  `column "category" does not exist`, toàn bộ tính năng task (không chỉ
  tính năng mới) sập theo — đây là lỗi nghiêm trọng, không phải lỗi nhỏ.

**Cách xử lý**: chạy migration SQL thủ công (`db/migrations/0001_add_task_category.sql`)
**trước khi** deploy code backend mới:

```powershell
docker compose exec -T db psql -U soclab -d soclab < db/migrations/0001_add_task_category.sql
```

Migration chỉ có 1 câu `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` +
1 `CREATE INDEX IF NOT EXISTS` — idempotent (chạy lại nhiều lần không
lỗi), an toàn để chạy nhầm 2 lần.

*Ghi chú: dự án này không dùng công cụ migration chuyên dụng (Alembic) vì
quy mô nhỏ — với dự án lớn hơn/nhiều môi trường (dev/staging/prod), nên
dùng Alembic hoặc tương đương để version hoá schema thay vì chạy SQL tay,
tránh quên chạy migration ở 1 trong các môi trường.*

### 2.2. Tính tương thích ngược (backward compatibility)

- Cột `category` được thêm **nullable, không có `DEFAULT` bắt buộc** →
  toàn bộ task cũ tự động có `category = NULL`, không cần backfill dữ
  liệu, không có bản ghi nào bị phá.
- Field `category` trong API (`TaskCreate`/`TaskUpdate`) là **optional**
  → client cũ (chưa cập nhật UI) vẫn gọi `POST /api/tasks` mà không gửi
  `category` được bình thường, không bị lỗi validation.
- Đây là **additive change** (chỉ thêm, không đổi/xoá field hay đổi kiểu
  dữ liệu cột nào đang có) — loại thay đổi an toàn nhất khi nâng cấp một
  hệ thống đang chạy, vì code cũ và code mới có thể cùng đọc/ghi được
  bảng `tasks` sau migration mà không xung đột.

### 2.3. Thứ tự triển khai (deployment order)

Đúng thứ tự: **migrate DB trước → deploy code mới sau**.

Lý do: nếu làm ngược lại (deploy code mới trước), có một khoảng thời
gian code mới chạy trên schema cũ → lỗi `column does not exist` như mục
2.1. Nếu migrate DB trước rồi mới deploy code, trong lúc chờ deploy thì
code cũ vẫn chạy bình thường (nó chỉ đơn giản không biết tới cột
`category` mới, không đọc/ghi cột đó, Postgres không ép buộc gì thêm vì
cột nullable) — không có khoảng thời gian nào bị lỗi.

### 2.4. Zero-downtime / rolling deploy

Vì đây là additive change, không cần dừng ứng dụng để nâng cấp:
1. Chạy migration (vài mili-giây, `ADD COLUMN` không kèm `DEFAULT` trên
   Postgres 11+ không rewrite toàn bảng, không khoá bảng lâu).
2. `docker compose up -d --build` để rebuild + restart container
   `backend` với code mới — Nginx và DB không cần restart, request đang
   xử lý dở không bị mất vì Docker restart container tuần tự.

### 2.5. Kiểm thử trước khi triển khai thật

- Chạy migration + code mới trên bản sao dữ liệu (hoặc môi trường
  dev/staging riêng) trước, không migrate thẳng vào dữ liệu thật.
- Sau khi migrate, xác nhận các task **cũ** (tạo từ trước khi nâng cấp)
  vẫn đọc/sửa/xoá được bình thường và trả `category: null` — không bị
  lỗi vì "thiếu" field mới.
- Lặp lại các kịch bản trong `LOGGING_MAP.md` (đặc biệt bước 6-9, thao
  tác CRUD task) để xác nhận log vẫn sinh ra đúng, không bị vỡ vì field
  mới trong `log_event(...)`.

### 2.6. Cập nhật tài liệu logging song song với code

Khi thêm field/tham số mới cho một action đã có log
(`task_create`, `task_read`), rất dễ quên cập nhật
[`LOGGING_MAP.md`](LOGGING_MAP.md) theo — dẫn tới tài liệu bị lệch so
với log thật ("log drift"), gây khó khăn khi có người khác (hoặc chính
mình sau này) dựa vào tài liệu đó để điều tra sự cố mà không biết field
`category`/`category_filter` đã tồn tại trong log. Đã cập nhật
`LOGGING_MAP.md` cùng đợt nâng cấp này — nguyên tắc rút ra: **coi tài
liệu log là một phần của thay đổi code, không phải việc làm sau**.

### 2.7. Rollback plan

- **Rollback code**: an toàn — quay lại code cũ vẫn chạy được trên
  schema đã migrate, vì code cũ chỉ đơn giản bỏ qua cột `category` (cột
  nullable, không có ràng buộc NOT NULL bắt code cũ phải biết tới nó).
- **Rollback migration (`DROP COLUMN category`)**: **không nên làm** nếu
  đã có dữ liệu category được người dùng nhập vào sau khi nâng cấp — xoá
  cột sẽ mất vĩnh viễn dữ liệu đó. Chỉ rollback migration khi chắc chắn
  chưa có dữ liệu thật nào ghi vào cột mới (VD: rollback ngay trong lúc
  test ở staging).
- Nguyên tắc chung: **rollback code dễ và nên làm khi có bug**; **rollback
  schema (đặc biệt DROP COLUMN/DROP TABLE) là thao tác phá huỷ, chỉ làm
  khi thật sự cần và đã xác nhận không mất dữ liệu**.

### 2.8. Versioning

Gắn tag git riêng cho lần nâng cấp (VD `v1.1-task-category`) để biết
chính xác điểm code nào tương ứng với migration `0001_add_task_category.sql`
— cần thiết nếu sau này phải rollback đúng cả code lẫn xác định được
migration nào đã/chưa chạy trên từng môi trường.

---

# Đợt nâng cấp 2 — Task Comments

Thêm tính năng **ghi chú (comment) cho từng task**: user tự do thêm
nhiều ghi chú theo thời gian cho 1 task (VD "đã liên hệ khách hàng lúc
15h", "đang chờ duyệt"), xem danh sách ghi chú, xoá 1 ghi chú.

Khác với Đợt 1 (chỉ `ADD COLUMN` vào bảng có sẵn), đợt này minh hoạ 1
loại migration khác: **tạo bảng mới có khoá ngoại**, kèm theo 1 quyết
định thiết kế bắt buộc phải chọn tường minh (không có "mặc định đúng
cho mọi trường hợp").

## 3.1. Tính năng thêm mới

| Trước nâng cấp | Sau nâng cấp |
|---|---|
| Task chỉ có 1 khối `description` tĩnh | Có thêm bảng `task_comments` — nhiều ghi chú theo thời gian cho 1 task |
| Không có endpoint nào cho ghi chú | `POST/GET /api/tasks/{id}/comments`, `DELETE /api/tasks/{id}/comments/{comment_id}` |

Thay đổi cụ thể trong code:
- `backend/app/models.py` — model `TaskComment` mới, quan hệ `Task.comments`
- `backend/app/schemas.py` — `CommentCreate`, `CommentOut`
- `backend/app/routers/comments.py` — router mới, 3 endpoint (tạo/xem/xoá)
- `backend/app/routers/tasks.py` — đổi `_get_owned_task` (private) thành
  `get_owned_task` (dùng chung), và **sửa `delete_task` để log thêm số
  comment bị xoá kèm theo** (xem mục 3.3)
- `db/migrations/0002_add_task_comments.sql` — migration tạo bảng mới

## 3.2. Quyết định thiết kế: Cascade Delete

**Câu hỏi**: xoá 1 task thì các comment của nó đi đâu?

Có 2 lựa chọn, không có lựa chọn nào "mặc định đúng" — phải tự chọn và
giải thích được lý do:

| Lựa chọn | Ưu điểm | Nhược điểm |
|---|---|---|
| `ON DELETE CASCADE` — xoá comment con theo task cha | Đơn giản, không để lại dữ liệu mồ côi vô nghĩa trong DB | Mất dữ liệu vĩnh viễn, không thể "xem lại lịch sử" sau khi task bị xoá |
| `ON DELETE RESTRICT` hoặc giữ orphan (`task_id = NULL`) | An toàn hơn nếu comment có giá trị audit độc lập | Phức tạp hơn (RESTRICT chặn luôn việc xoá task nếu còn comment; giữ orphan thì cần thêm UI riêng để xem comment "mồ côi", và cột `task_id` phải nullable) |

**Đã chọn: `ON DELETE CASCADE`** (xem `db/migrations/0002_add_task_comments.sql`
và `backend/app/models.py::TaskComment.task_id`). Lý do:

- Comment trong tính năng này là **ghi chú cá nhân gắn chặt với 1 task
  cụ thể** — không có ý nghĩa gì nếu đứng riêng lẻ khi task đã không còn
  tồn tại (khác hẳn với ví dụ 1 bản ghi thanh toán, cần giữ lại dù đơn
  hàng gốc bị huỷ, vì bản thân bản ghi thanh toán có giá trị pháp lý/kế
  toán độc lập).
- Nhất quán với cách 2 quan hệ khác trong hệ thống đã xử lý (`User.tasks`,
  `User.sessions` đều `cascade="all, delete-orphan"`) — không tạo ra 1
  ngoại lệ khó nhớ.
- User xoá task với kỳ vọng hợp lý là "dọn sạch mọi thứ liên quan", để
  lại comment mồ côi sẽ gây khó hiểu hơn là hữu ích trong phạm vi 1 app
  quản lý công việc cá nhân đơn giản.

*Nếu đây là hệ thống có giá trị audit/pháp lý cao hơn (VD comment ghi
nhận quyết định phê duyệt), lựa chọn đúng sẽ ngược lại — giữ orphan
hoặc RESTRICT để không mất bằng chứng.*

## 3.3. "Log on Commit", không phải "Log on Request"

Nguyên tắc: **chỉ ghi log `result=success` SAU KHI thao tác ghi DB đã
`commit()` thành công**, không log ngay khi vừa nhận request. Nếu log
trước khi commit, có nguy cơ log nói "đã tạo thành công" trong khi thực
ra `commit()` phía sau bị lỗi/rollback — log và dữ liệu thật lệch nhau,
phá vỡ toàn bộ giá trị của log để điều tra sự cố.

Toàn bộ codebase (kể cả trước đợt nâng cấp này) đã tuân theo đúng thứ tự
này — xem `backend/app/routers/comments.py::create_comment`:

```python
db.add(comment)
db.commit()       # <- persist thật sự xảy ra ở đây
db.refresh(comment)

log_event(..., event="comment_create", ...)   # <- chỉ chạy tới đây nếu commit() ở trên không raise exception
```

Nếu `db.commit()` raise lỗi (vi phạm constraint, mất kết nối DB...),
luồng thực thi dừng lại ngay tại đó — dòng `log_event(...)` phía dưới
**không bao giờ được gọi tới**. Không cần try/except gì thêm để đảm bảo
điều này; đơn giản là đặt đúng thứ tự lệnh.

## 3.4. Điểm mù (blind spot): CASCADE DELETE không tự sinh log ở DB layer

Phát hiện được khi tự kiểm chứng bằng tay: sau khi xoá 1 task có sẵn 3
comment, log Postgres (`log_statement=mod`) **chỉ có đúng 1 dòng**
`DELETE FROM tasks ...` — **không có** dòng `DELETE FROM task_comments`
nào, dù 3 comment đó thực sự đã biến mất khỏi DB (kiểm chứng lại bằng
`SELECT count(*) FROM task_comments WHERE task_id = ...` → 0).

**Lý do**: `ON DELETE CASCADE` là hành động **nội bộ của Postgres**,
được kích hoạt bởi ràng buộc khoá ngoại khi thực thi câu lệnh
`DELETE FROM tasks`, chứ không phải một câu lệnh SQL riêng do
client/ứng dụng gửi lên. `log_statement` chỉ ghi lại **câu lệnh mà
client gửi**, không ghi lại hệ quả nội bộ mà Postgres tự thực hiện để
đảm bảo ràng buộc toàn vẹn dữ liệu.

**Vì sao đây là vấn đề thật**: nếu chỉ dựa vào log Postgres để điều tra
"dữ liệu nào đã bị xoá", sẽ **bỏ sót hoàn toàn** các comment bị xoá theo
— một khoảng trống trong khả năng truy vết (traceability gap), có thể
bị hiểu nhầm là "3 comment đó biến mất không rõ lý do" nếu chỉ nhìn vào
DB log.

**Cách khắc phục — bù ở tầng Application, vì tầng DB không sửa được**:
`delete_task` (`backend/app/routers/tasks.py`) được sửa để **đếm số
comment sẽ bị xoá theo TRƯỚC KHI xoá task** (không thể đếm sau, vì lúc
đó cascade đã xảy ra rồi), rồi đưa số đó vào chính dòng log
`task_delete`:

```python
deleted_comments_count = db.query(TaskComment).filter(TaskComment.task_id == task.id).count()
db.delete(task)
db.commit()
log_event(..., event="task_delete", ..., cascaded_comments_deleted=deleted_comments_count)
```

Kết quả: dòng `app.log` cho `task_delete` giờ luôn có field
`cascaded_comments_deleted` (vd `3`), khôi phục lại đầy đủ khả năng
truy vết mà log Postgres không cung cấp được. Đây chính là ví dụ thực
tế cho nguyên tắc phân tích log: **không bao giờ chỉ tin vào 1 layer**
— khi phát hiện 1 layer có điểm mù, phải chủ động bù bằng layer khác
mà mình kiểm soát được, không được để trống.

## 3.5. Kiểm thử

- Tạo task, thêm 2-3 comment, xoá task → xác nhận `SELECT count(*) FROM
  task_comments WHERE task_id = '<id>'` trả về 0 (cascade hoạt động
  đúng ở DB), và dòng log `task_delete` có
  `cascaded_comments_deleted` khớp đúng số lượng đã thêm.
- Test authorization: đăng nhập tài khoản khác, gọi `POST
  /api/tasks/{id_task_không_phải_của_mình}/comments` → phải nhận 403
  (dùng chung `get_owned_task`, cùng cơ chế chống IDOR như task).
