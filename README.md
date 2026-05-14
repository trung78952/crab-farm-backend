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
- WebSocket realtime: `ws://localhost:8000/ws?token=<JWT>`

## API chính

- Tanks: `GET/POST /api/v1/tanks`, `GET/PATCH/DELETE /api/v1/tanks/{tank_id}`
- Devices: `GET/POST /api/v1/devices`, `PATCH /api/v1/devices/{device_id}/status`
- Motion: `POST /api/v1/motion/home`, `POST /api/v1/motion/move-to-tank/{tank_id}`, `POST /api/v1/motion/gcode`, `POST /api/v1/motion/emergency-stop`
- Camera: `POST /api/v1/camera/capture/{tank_id}`, `POST /api/v1/camera/upload`, `GET /api/v1/camera/images`
- Detections: `POST /api/v1/detections/mock`, `GET /api/v1/detections`, `GET /api/v1/detections/by-tank/{tank_id}`
- Harvest: `POST /api/v1/harvest/queue/{tank_id}`, `POST /api/v1/harvest/start/{harvest_id}`, `GET /api/v1/harvest`
- Scan schedules: `GET/POST /api/v1/scan-schedules`, `GET/PATCH/DELETE /api/v1/scan-schedules/{schedule_id}`, `POST /api/v1/scan-schedules/{schedule_id}/enable`, `POST /api/v1/scan-schedules/{schedule_id}/disable`
- Scans: `POST /api/v1/scans/run-all`, `POST /api/v1/scans/run-tank/{tank_id}`, `GET /api/v1/scans/jobs`, `GET /api/v1/scans/jobs/{job_id}`
- Shelves: `GET/POST /api/v1/shelves`, `GET/PATCH /api/v1/shelves/{shelf_id}`, `POST /api/v1/shelves/{shelf_id}/maintenance`, `POST /api/v1/shelves/{shelf_id}/activate`
- Scan jobs v2: `GET /api/v1/scan-jobs`, `GET /api/v1/scan-jobs/{job_id}`
- Recheck tasks: `GET /api/v1/recheck-tasks`, `POST /api/v1/recheck-tasks/{id}/cancel`, `POST /api/v1/recheck-tasks/run-due-now`
- MQTT console: `GET /api/v1/mqtt/logs`, `GET /api/v1/mqtt/topics`, `POST /api/v1/mqtt/publish`
- AI: `GET /api/v1/ai/status`, `GET /api/v1/ai/models`, `POST /api/v1/ai/models/activate`, `POST /api/v1/ai/detect/{image_id}`
- Training samples: `GET /api/v1/training-samples`, `POST /api/v1/training-samples/from-detection/{detection_id}`, `PATCH /api/v1/training-samples/{id}/label`, `POST /api/v1/datasets/export-yolo`
- Auth settings: `POST /api/v1/auth/change-password`

## Realtime events

FastAPI cung cấp WebSocket `/ws?token=<JWT>`. Event format:

```json
{
  "event": "mqtt_log_created",
  "data": {},
  "created_at": "2026-05-14T10:00:00Z"
}
```

Các event chính:

- `device_status_updated`
- `mqtt_log_created`
- `motion_command_updated`
- `scan_job_created`
- `scan_job_updated`
- `scan_job_item_updated`
- `detection_created`
- `harvest_updated`
- `emergency_stop_triggered`
- `ai_model_changed`

## Env quan trọng

```env
APP_TIMEZONE=Asia/Ho_Chi_Minh
SIMULATION_MODE=true
MQTT_SIMULATE_PUBLISH=false
MOLTING_RECHECK_MINUTES=10
UNCERTAIN_RECHECK_MINUTES=3
SOFT_SHELL_VERIFY_SECONDS=60
SOFT_SHELL_CONFIDENCE_THRESHOLD=0.85
MOTION_TIMEOUT_SECONDS=60
CAMERA_TIMEOUT_SECONDS=30
AI_TIMEOUT_SECONDS=30
MOTION_SETTLE_MS=800
AI_ENABLED=true
AI_MOCK_MODE=false
AI_MODEL_PATH=storage/models/crab_yolov8_v1.pt
AI_MODEL_VERSION=crab_yolov8_v1
AI_CONFIDENCE_THRESHOLD=0.5
AI_IMAGE_SIZE=640
```

`SIMULATION_MODE=true` không publish motion/camera thật nếu `MQTT_SIMULATE_PUBLISH=false`; scan job/item kết thúc ở `simulated`, không giả lập `success`.

## Scan queue thực tế

- Schedule chỉ tạo `scan_job` status `queued`, không chạy trực tiếp.
- `scan_runner` lấy job theo `priority`, `created_at`.
- Cùng một `shelf_id` chỉ chạy một scan/harvest/motion job tại một thời điểm.
- Flow scan item: move command -> chờ motion done -> settle -> camera capture -> chờ image -> AI detect -> decision engine.
- Không publish camera capture trước bước motion done. Trong MVP hiện phần chờ ACK/DONE thật là điểm tích hợp tiếp theo; nếu không simulation và chưa có camera result, item sẽ timeout/failed thay vì success.

## Multi-shelf MQTT topics

Topic phân tầng mới:

- `farm/shelf/{shelf_code}/motion/cmd`
- `farm/shelf/{shelf_code}/motion/ack`
- `farm/shelf/{shelf_code}/motion/status`
- `farm/shelf/{shelf_code}/motion/error`
- `farm/shelf/{shelf_code}/camera/cmd`
- `farm/shelf/{shelf_code}/camera/status`
- `farm/shelf/{shelf_code}/camera/result`
- `farm/shelf/{shelf_code}/device/status`

Server subscribe `farm/#` và lưu toàn bộ MQTT logs.

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

Publish test ACK:

```bash
docker compose exec mosquitto mosquitto_pub -h localhost -t "farm/shelf/SHELF_01/motion/ack" \
  -m '{"cmd_id":"CMD_001","status":"done"}'
```

Publish từ dashboard dùng `POST /api/v1/mqtt/publish` hoặc trang MQTT Console.

## AI YOLOv8 pipeline

Thư mục storage:

```text
storage/
  raw/
  detected/
  datasets/
  models/
    crab_yolov8_v1.pt
    active_model.txt
```

Luồng triển khai model:

1. Thu ảnh bằng camera/upload vào `storage/raw`.
2. Chạy detect: `POST /api/v1/ai/detect/{image_id}`.
3. Verify hoặc sửa label trên dashboard Detections/Training Samples.
4. Export dataset YOLO: `POST /api/v1/datasets/export-yolo`.
5. Train trên máy mạnh/cloud GPU.
6. Copy `best.pt` vào `storage/models`.
7. Activate model:

```bash
curl -X POST http://localhost:8000/api/v1/ai/models/activate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"model_path":"storage/models/crab_yolov8_v2.pt","model_version":"crab_yolov8_v2"}'
```

Ghi chú MVP: exporter ghi YOLO label từ bbox đã normalized nếu có `x_center/y_center/width/height`; nếu bbox thiếu hoặc format khác thì tạm xuất full-image bbox và ghi chú trong `data.yaml`. Server farm nên chạy inference; training nên chạy trên GPU/cloud.

## Frontend

```bash
cd ../crab-farm-frontend
npm install
npm run serve
```

Login admin mặc định: `admin / admin123`.

Các trang mới/chính:

- Dashboard realtime + banner simulation mode
- Shelves
- Tanks filter theo shelf
- Scan Schedules
- Scan Jobs
- Recheck Tasks
- MQTT Console realtime
- Detections verify
- Training Samples export YOLO
- Settings đổi mật khẩu + AI model status/activate

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
