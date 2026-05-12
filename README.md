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
