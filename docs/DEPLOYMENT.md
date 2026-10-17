# Production Deployment Guide: Huawei EMS B1 Battery Manager

This document covers deploying the **Huawei EMS B1 Battery Manager** in industrial environments across three supported deployment models:

1. **Native Local Production Service** (Single process serving both React SPA and FastAPI on port 8000).
2. **Docker & Docker Compose** (Containerized with USB-to-RS485 device pass-through).
3. **Linux Systemd Service** (24/7 background service for edge gateways, IPCs, and Raspberry Pi).

---

## Deployment Option 1: Native Local Production Service

This is the recommended deployment for local workstations and edge gateways. A single Python process serves the optimized React 19 UI bundle, WebSockets, REST endpoints, and serial communication on port `8000`.

### Deploy & Start:
```bash
cd /Users/chavxxx/Documents/Projects/huawei-ems-b1-manager
./scripts/deploy_production.sh
```

- **Application Web UI:** `http://localhost:8000`
- **Swagger API Documentation:** `http://localhost:8000/docs`
- **WebSocket Telemetry Stream:** `ws://localhost:8000/ws/telemetry`

---

## Deployment Option 2: Docker Container with RS485 Pass-Through

A multi-stage `Dockerfile` is provided that compiles the frontend and packages the Python backend into a slim container image.

### 1. Build and Run Container
```bash
docker compose up -d --build
```

### 2. Physical USB-to-RS485 Device Pass-Through
When connecting real battery hardware, grant the container access to your serial dongle. Edit `docker-compose.yml`:

```yaml
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    privileged: true
```
Then restart:
```bash
docker compose up -d
```

### 3. Check Container Health
```bash
docker compose ps
docker compose logs -f
```

---

## Deployment Option 3: Linux Systemd 24/7 Background Service

For unattended operation on an Industrial PC or Raspberry Pi running Ubuntu/Debian:

### 1. Copy Application Directory
```bash
sudo cp -r /Users/chavxxx/Documents/Projects/huawei-ems-b1-manager /opt/huawei-ems-b1-manager
cd /opt/huawei-ems-b1-manager
```

### 2. Install and Start Service
```bash
sudo cp systemd/huawei-bms.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable huawei-bms
sudo systemctl start huawei-bms
```

### 3. Check Service Status and Logs
```bash
sudo systemctl status huawei-bms
sudo journalctl -u huawei-bms -f
```

---

## Production Security Check-List

- [x] Application initializes strictly in **Read-Only Mode**.
- [x] Writes to undocumented or non-allowlisted register addresses are rejected.
- [x] All parameter changes require Administrator confirmation and enforce read-back verification.
- [x] The SQLite database uses Write-Ahead Logging (`WAL`) to prevent database corruption during sudden power losses.
- [x] Telemetry freshness monitors actively indicate frozen or stale communications.
