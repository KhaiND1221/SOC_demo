# Vận hành ứng dụng — Nâng cấp mã nguồn

Tài liệu này mô tả một đợt **nâng cấp mã nguồn** thực hiện trên ứng dụng
Task Manager đang chạy (đã có dữ liệu thật của user): thêm tính năng
**gắn nhãn (category) cho task và lọc task theo nhãn**, cùng các vấn đề
cần quan tâm khi đưa thay đổi này vào một hệ thống đang vận hành —
không chỉ đơn thuần là sửa code.

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
