# Crab Farm Backend

MVP backend cho hệ thống nuôi cua lột thông minh. Stack: FastAPI, PostgreSQL, SQLAlchemy 2 async, Alembic, Pydantic v2, paho-mqtt và Docker Compose.

## Chạy project

```bash
cd crab-farm-backend
docker compose up --build
```

Tạo migration ban đầu và apply database schema:

```bash
docker compose exec backend alembic revision --autogenerate -m "init"
docker compose exec backend alembic upgrade head
```

Sau khi pull code có migration sẵn, thường chỉ cần:

```bash
docker compose exec backend alembic upgrade head
```

Trong môi trường Docker dev, `./alembic/versions` được mount vào container để migration tạo bằng `alembic revision` không bị mất sau khi rebuild image.

Tạo admin ban đầu:

```bash
docker compose exec backend python -m app.scripts.create_admin
```

Mặc định đọc từ env:

- `ADMIN_USERNAME=admin`
- `ADMIN_PASSWORD=admin123`
- `ADMIN_EMAIL=admin@example.com`

Login lấy JWT:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Gọi API có Bearer token:

```bash
curl http://localhost:8000/api/v1/tanks \
  -H "Authorization: Bearer <access_token>"
```

Chạy frontend riêng:

```bash
cd ../crab-farm-frontend
npm install
npm run serve
```

Frontend dev server mặc định: http://localhost:8080

Hoặc chạy kèm bằng Docker Compose service `frontend`:

```bash
docker compose up --build frontend
```

API docs:

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API chính

- Tanks: `GET/POST /api/v1/tanks`, `GET/PATCH/DELETE /api/v1/tanks/{tank_id}`
- Devices: `GET/POST /api/v1/devices`, `PATCH /api/v1/devices/{device_id}/status`
- Motion: `POST /api/v1/motion/home`, `POST /api/v1/motion/move-to-tank/{tank_id}`, `POST /api/v1/motion/gcode`, `POST /api/v1/motion/emergency-stop`
- Camera: `POST /api/v1/camera/capture/{tank_id}`, `POST /api/v1/camera/upload`, `GET /api/v1/camera/images`
- Detections: `POST /api/v1/detections/mock`, `GET /api/v1/detections`, `GET /api/v1/detections/by-tank/{tank_id}`
- Harvest: `POST /api/v1/harvest/queue/{tank_id}`, `POST /api/v1/harvest/start/{harvest_id}`, `GET /api/v1/harvest`
- Scan schedules: `GET/POST /api/v1/scan-schedules`, `GET/PATCH/DELETE /api/v1/scan-schedules/{schedule_id}`, `POST /api/v1/scan-schedules/{schedule_id}/enable`, `POST /api/v1/scan-schedules/{schedule_id}/disable`
- Scans: `POST /api/v1/scans/run-all`, `POST /api/v1/scans/run-tank/{tank_id}`, `GET /api/v1/scans/jobs`, `GET /api/v1/scans/jobs/{job_id}`

Ví dụ tạo tank:

```bash
curl -X POST http://localhost:8000/api/v1/tanks \
  -H "Content-Type: application/json" \
  -d '{"code":"T001","name":"Tank 001","row_index":1,"col_index":1,"level_index":1,"x_position":120,"y_position":0,"z_position":300,"status":"normal"}'
```

Ví dụ gửi G-code:

```bash
curl -X POST http://localhost:8000/api/v1/motion/gcode \
  -H "Content-Type: application/json" \
  -d '{"lines":["G90","G1 X120 Z300 F3000","M400"]}'
```

Ví dụ upload ảnh:

```bash
curl -X POST http://localhost:8000/api/v1/camera/upload \
  -F "tank_id=<tank_uuid>" \
  -F "file=@sample.jpg"
```

Ví dụ tạo lịch scan tất cả bể mỗi 15 phút:

```bash
curl -X POST http://localhost:8000/api/v1/scan-schedules \
  -H "Content-Type: application/json" \
  -d '{"name":"Scan every 15 minutes","interval_minutes":15,"scan_mode":"all_tanks","is_active":true}'
```

Ví dụ chạy scan thủ công một bể:

```bash
curl -X POST http://localhost:8000/api/v1/scans/run-tank/<tank_uuid>
```

Scan scheduler chạy cùng FastAPI và kiểm tra lịch đến hạn mỗi 60 giây. MVP hiện tạo `scan_job`, tạo `scan_job_items`, chạy tuần tự qua các trạng thái `moving -> capturing -> detecting -> success`, publish motion/camera MQTT command và để sẵn placeholder cho bước chờ ACK, nhận ảnh, chạy detection thật.

## Test MQTT

Theo dõi command server publish:

```bash
docker compose exec mosquitto mosquitto_sub -h localhost -t 'farm/motion/cmd' -v
```

Giả lập ESP32 gửi ACK về server:

```bash
docker compose exec mosquitto mosquitto_pub -h localhost -t farm/motion/ack \
  -m '{"cmd_id":"CMD_20260512_000001","status":"done","message":"completed"}'
```

Theo dõi tất cả topic farm:

```bash
docker compose exec mosquitto mosquitto_sub -h localhost -t 'farm/#' -v
```

## MQTT topics

Server publish:

- `farm/motion/cmd`
- `farm/camera/cmd`

Server subscribe:

- `farm/motion/ack`
- `farm/motion/status`
- `farm/motion/error`
- `farm/camera/status`
- `farm/camera/result`

## Việc cần làm tiếp theo

- Thêm auth cho dashboard và phân quyền operator/admin.
- Chuẩn hóa protocol ACK/status từ ESP32 và Pi Camera.
- Thêm background job timeout cho motion command.
- Thêm detection service thật, lưu ảnh detected/verify và pipeline review.
- Thêm test suite, seed data và dashboard Vue.
