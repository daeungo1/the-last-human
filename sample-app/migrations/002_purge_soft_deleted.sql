-- 90일 넘게 소프트 삭제 상태인 주문을 물리 삭제한다.
DELETE FROM orders
WHERE deleted_at IS NOT NULL
  AND deleted_at < NOW() - INTERVAL 90 DAY;

-- 삭제 후 인덱스 재구성
DROP INDEX idx_orders_customer_status ON orders;
CREATE INDEX idx_orders_customer_status ON orders (customer_id, status, deleted_at);
