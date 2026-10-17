# macOS Installation and Setup Guide

## 1. Prerequisites
Ensure you have Homebrew, Python, and Node installed:

```bash
brew install python node
```

## 2. Serial Port Identification on macOS
When a USB-to-RS485 adapter is inserted into your Mac:
1. macOS creates character device nodes under `/dev/cu.*` and `/dev/tty.*`.
2. Always select the **`/dev/cu.*`** port for outgoing serial client connections (e.g. `/dev/cu.usbserial-1410` or `/dev/cu.wchusbserial1420`).
   - Note: `/dev/tty.*` is meant for incoming connections and may block until DCD signal changes.

List connected serial devices:
```bash
ls -la /dev/cu.usbserial* /dev/cu.wch* /dev/cu.SLAB*
```

### Driver Notes for Apple Silicon (M1/M2/M3/M4)
- **FTDI devices:** Native macOS driver support is built into macOS Monterey, Ventura, Sonoma, and Sequoia without needing extra kernel extensions.
- **CH340/CH341 devices:** macOS 12+ includes native AppleUSBCHCOM driver. If an older clone chip is used, install the WCH signed driver from wch-ic.com.
- **CP2102/CP2104 devices:** Native VCP driver provided by Silicon Labs.

## 3. Launching the Application
Run the root launch script:

```bash
./scripts/start.sh
```
Or start manually:
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```
Open `http://localhost:5173`.
