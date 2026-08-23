-- Nâng cấp: thêm tính năng gắn nhãn (category) cho task.
--
-- QUAN TRỌNG: app dùng SQLAlchemy `Base.metadata.create_all()` khi start
-- (app/main.py::on_startup), hàm này CHỈ tạo bảng chưa tồn tại, KHÔNG tự
-- ALTER bảng đã có sẵn để thêm cột mới. Nếu chỉ deploy code mới mà không
-- chạy migration này trước, mọi request tới /api/tasks sẽ lỗi 500 vì
-- Postgres báo "column tasks.category does not exist".
--
-- Cách chạy (chạy TRƯỚC khi deploy code backend mới):
--   docker compose exec -T db psql -U soclab -d soclab < db/migrations/0001_add_task_category.sql
--
-- An toàn cho dữ liệu cũ: cột mới nullable, không có giá trị mặc định bắt
-- buộc -> các task đã tồn tại tự động có category = NULL, không cần
-- backfill, không có downtime, không khoá bảng lâu (ADD COLUMN không kèm
-- DEFAULT trên Postgres 11+ là thao tác nhanh, không rewrite toàn bảng).

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS category VARCHAR(50);
CREATE INDEX IF NOT EXISTS ix_tasks_category ON tasks (category);
