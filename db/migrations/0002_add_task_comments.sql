-- Nâng cấp: thêm tính năng ghi chú (comment) cho từng task.
--
-- Khác với migration 0001 (ADD COLUMN vào bảng có sẵn), đây là migration
-- TẠO BẢNG MỚI có khoá ngoại tới bảng đã tồn tại (tasks, users) - loại
-- migration này không cần backfill (bảng mới luôn rỗng lúc tạo), nhưng
-- có một quyết định thiết kế bắt buộc phải chọn: xử lý comment con thế
-- nào khi task cha bị xoá.
--
-- QUYẾT ĐỊNH: ON DELETE CASCADE (xoá task thì xoá luôn toàn bộ comment
-- của task đó). Lý do - xem giải thích đầy đủ ở VAN_HANH_NANG_CAP.md,
-- mục "Task Comments — quyết định cascade delete". Tóm tắt: comment ở
-- đây là ghi chú cá nhân gắn với 1 task cụ thể, không có giá trị độc
-- lập/giá trị audit nào một khi task đã không còn tồn tại (khác với vd
-- 1 bản ghi thanh toán vẫn cần giữ lại dù đơn hàng gốc bị huỷ) - nên
-- xoá cùng task cha là hành vi đúng với kỳ vọng người dùng, tránh để
-- lại dữ liệu mồ côi vô nghĩa trong DB.
--
-- Cách chạy (chạy TRƯỚC khi deploy code backend mới, giống 0001):
--   docker compose exec -T db psql -U soclab -d soclab < db/migrations/0002_add_task_comments.sql

CREATE TABLE IF NOT EXISTS task_comments (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    content VARCHAR(1000) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_task_comments_task_id ON task_comments (task_id);
