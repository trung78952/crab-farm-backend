# Crab Farm Backend

FastAPI backend cho hệ thống farm nuôi cua lột: PostgreSQL async SQLAlchemy, Alembic, JWT auth, MQTT, WebSocket realtime, scan queue theo shelf, AI decision engine và sensor module.

## Chạy Backend

```bash
cd crab-farm-backend
docker compose up --build
```

Apply migration:

```bash
docker compose exec backend alembic upgrade head
```

Tạo admin ban đầu:

```bash
docker compose exec backend python -m app.scripts.create_admin
```

Mặc định đọc từ env:

- `ADMIN_USERNAME=admin`
- `ADMIN_PASSWORD=admin123`
- `ADMIN_EMAIL=admin@example.com`

Frontend:

```bash
cd ../crab-farm-frontend
npm install
npm run serve
```

URL chính:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Frontend: `http://localhost:8080`
- WebSocket: `ws://localhost:8000/ws?token=<JWT>`

## Auth Và Role

JWT Bearer token được giữ nguyên. Viewer chỉ đọc dữ liệu. Các action/write yêu cầu `admin` hoặc `operator`: scan, motion, MQTT publish, emergency stop, edit shelves/tanks, schedules và sensor config.

## Simulation Mode

Env:

```env
SIMULATION_MODE=true
MQTT_SIMULATE_PUBLISH=false
AI_MOCK_MODE=false
```

Khi `SIMULATION_MODE=true`, motion/camera không được coi là thành công phần cứng thật. `scan_job` và `scan_job_item` kết thúc là `simulated`, không phải `success`. Frontend hiển thị banner Simulation Mode.

## Scan Queue

Tất cả scan tạo `scan_job.status=queued` rồi đi qua `scan_runner`:

- Manual run all: `POST /api/v1/scans/run-all?shelf_id=<optional>`
- Manual scan tank: `POST /api/v1/scans/run-tank/{tank_id}`
- Scheduled scan: sinh job từ `scan_schedules`
- AUTO recheck/verify: dùng `scan_schedules.tag=AUTO`

Priority mặc định:

- harvest: `1`
- auto_verify: `5`
- auto_recheck: `10`
- manual_scan: `20`
- scheduled_scan: `100`

Cùng một `shelf_id` chỉ dispatch một scan job đang chạy tại một thời điểm. Khác shelf có thể chạy song song. `SCAN_DEDUPE_SECONDS=60` áp dụng cho user periodic schedules để bỏ qua tank vừa scan gần đây.

Scan item flow:

1. `moving`
2. tạo `motion_command` `move_to_tank`
3. publish MQTT motion command
4. chờ motion `DONE`
5. đợi `MOTION_SETTLE_MS`
6. publish camera capture
7. chờ camera result/upload
8. chạy AI detect
9. lưu detection và chạy decision engine

Không publish camera capture trước motion `DONE`.

Scan job status:

- `success`: tất cả item cần scan success
- `partial_success`: có item success và có item failed/timeout
- `failed`: tất cả item failed/timeout
- `simulated`: simulation mode hoặc tất cả item simulated
- `queued`, `running`, `cancelled`

Scan item status:

`queued`, `waiting_for_motion`, `moving`, `motion_done`, `waiting_for_camera`, `capturing`, `image_received`, `detecting`, `success`, `failed`, `timeout`, `simulated`, `skipped`.

## Scan Schedules

API:

- `GET /api/v1/scan-schedules?shelf_id=&tag=&schedule_type=&is_active=`
- `POST /api/v1/scan-schedules`
- `GET/PATCH /api/v1/scan-schedules/{id}`
- `POST /api/v1/scan-schedules/{id}/enable`
- `POST /api/v1/scan-schedules/{id}/disable`
- `POST /api/v1/scan-schedules/{id}/cancel`

User schedule:

```json
{
  "schedule_type": "user_periodic",
  "tag": "USER",
  "scan_mode": "all_tanks",
  "interval_minutes": 120,
  "priority": 100,
  "run_immediately": false
}
```

Mặc định tạo schedule không scan ngay. Nếu `run_immediately=false`, `next_run_at = now + interval_minutes`. Chỉ khi `run_immediately=true` backend mới tạo thêm queued scan job ngay, còn `next_run_at` vẫn là lần chạy chu kỳ tiếp theo.

AUTO schedules do decision engine tạo:

- `auto_recheck`: cua đang lột, ảnh xấu, uncertain
- `auto_verify`: nghi cua đã lột, verify một lần trước khi queue harvest

`recheck_tasks` vẫn còn API/table để backward compatible, nhưng flow mới không dùng nữa.

## AI Decision Engine

Sau detection:

- `crab_normal`: tank `normal`, complete AUTO schedules liên quan nếu confidence đủ cao.
- `crab_molting`: tank `molting`, tạo/cập nhật AUTO `auto_recheck`.
- `crab_soft_shell` confidence cao: tank `soft_shell`, tạo AUTO `auto_verify` sau `SOFT_SHELL_VERIFY_SECONDS`, chưa harvest ngay.
- `auto_verify` vẫn `crab_soft_shell`: tạo harvest queued, complete AUTO verify/recheck.
- `uncertain_or_bad_image`: tạo/cập nhật AUTO `auto_recheck`.
- `empty_tank`: tank `empty`, complete AUTO schedules nếu confidence đủ cao.

Env liên quan:

```env
MOLTING_RECHECK_MINUTES=10
UNCERTAIN_RECHECK_MINUTES=3
SOFT_SHELL_VERIFY_SECONDS=60
SOFT_SHELL_CONFIDENCE_THRESHOLD=0.85
AUTO_RECHECK_MAX_RUNS=12
AUTO_RECHECK_EXPIRE_HOURS=3
SCAN_DEDUPE_SECONDS=60
MOTION_TIMEOUT_SECONDS=60
CAMERA_TIMEOUT_SECONDS=30
AI_TIMEOUT_SECONDS=30
MOTION_SETTLE_MS=800
```

## Shelves Và Tanks

API chính:

- `GET/POST /api/v1/shelves`
- `GET/PATCH /api/v1/shelves/{id}`
- `POST /api/v1/shelves/{id}/maintenance`
- `POST /api/v1/shelves/{id}/activate`
- `GET /api/v1/tanks?shelf_id=...`
- `POST /api/v1/tanks`
- `GET/PATCH/DELETE /api/v1/tanks/{id}`

Frontend gộp Shelves/Tanks thành Farm Layout: chọn shelf bên trái, xem/edit shelf và tanks bên phải, có table/grid layout, scan tank, move to tank và filter theo status/level/row/column.

## Sensor Module

Tables:

- `sensor_types`
- `sensors`
- `sensor_readings`
- `sensor_alert_rules`
- `sensor_alerts`

API:

- `GET/POST/PATCH /api/v1/sensor-types`
- `GET/POST/PATCH/DELETE /api/v1/sensors`
- `GET/POST /api/v1/sensor-readings`
- `GET /api/v1/sensor-readings/latest?tank_id=...|shelf_id=...`
- `GET/POST/PATCH /api/v1/sensor-alert-rules`
- `GET /api/v1/sensor-alerts`
- `POST /api/v1/sensor-alerts/{id}/ack`
- `POST /api/v1/sensor-alerts/{id}/resolve`

Sensor có thể thuộc tank hoặc shelf. Backend validate sensor phải có ít nhất một trong `tank_id` hoặc `shelf_id`.

MQTT sensor topics:

- `farm/shelf/{shelf_code}/tank/{tank_code}/sensor/{sensor_type}`
- `farm/shelf/{shelf_code}/sensor/{sensor_type}`

Payload:

```json
{
  "sensor_code": "TEMP_T001",
  "shelf_code": "SHELF_01",
  "tank_code": "T001",
  "type": "temperature",
  "value": 27.4,
  "unit": "C",
  "measured_at": "2026-05-15T10:00:00Z"
}
```

Test MQTT sensor:

```bash
docker compose exec mosquitto mosquitto_pub -h localhost \
  -t "farm/shelf/SHELF_01/tank/T001/sensor/temperature" \
  -m '{"sensor_code":"TEMP_T001","shelf_code":"SHELF_01","tank_code":"T001","type":"temperature","value":27.4,"unit":"C"}'
```

Backend sẽ lưu `sensor_reading`, check alert rules, broadcast `sensor_reading_created` và nếu vượt ngưỡng thì tạo/broadcast `sensor_alert_created`.

## MQTT Console

API:

- `GET /api/v1/mqtt/logs`
- `GET /api/v1/mqtt/topics`
- `POST /api/v1/mqtt/publish`

Console frontend hỗ trợ All topics, filter contains, publish realtime, pretty JSON payload. Clear console chỉ clear local UI, không xóa DB.

## WebSocket Realtime

Endpoint:

```text
GET /ws?token=JWT_TOKEN
```

Event format:

```json
{
  "event": "scan_job_updated",
  "data": {
    "id": "...",
    "status": "running"
  },
  "created_at": "2026-05-15T10:00:00Z"
}
```

Events chính:

- `shelf_created`, `shelf_updated`
- `tank_created`, `tank_updated`
- `sensor_reading_created`, `sensor_alert_created`
- `mqtt_log_created`
- `motion_command_created`, `motion_command_updated`
- `scan_schedule_created`, `scan_schedule_updated`
- `scan_job_created`, `scan_job_updated`, `scan_job_item_updated`
- `detection_created`
- `harvest_updated`
- `emergency_stop_triggered`

Frontend tự connect sau login, auto reconnect khi mất kết nối và disconnect khi logout.
