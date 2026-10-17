# Windows Installation and Setup Guide

## 1. Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Python:** Python 3.10+ (ensure "Add Python to PATH" is checked during installation)
- **Node.js:** Node.js v18+ and npm

## 2. USB-to-RS485 Adapter Driver Setup
When you plug in your USB-to-RS485 serial dongle, Windows should assign it a **COM Port** (e.g. `COM3`, `COM4`):
1. Open **Device Manager** (`Win + X` -> Device Manager).
2. Expand the **Ports (COM & LPT)** category.
3. Look for your adapter:
   - FTDI chipsets: `USB Serial Port (COMx)`
   - CH340 / CH341 chipsets: `USB-SERIAL CH340 (COMx)`
   - Silicon Labs: `Silicon Labs CP210x USB to UART Bridge (COMx)`
4. If a yellow exclamation mark appears under "Other devices", install the manufacturer VCP (Virtual COM Port) driver:
   - FTDI VCP Drivers: https://ftdichip.com/drivers/vcp-drivers/
   - CH340/CH341 Drivers: http://www.wch-ic.com/downloads/CH341SER_EXE.html
   - Silicon Labs CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

## 3. Application Installation
Open PowerShell or Command Prompt in the project folder:

```powershell
# 1. Setup Python Virtual Environment
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup React Desktop Frontend
cd ..\frontend
npm install
npm run build
```

## 4. Running the Application
To run both backend and frontend concurrently:

```powershell
# Run backend service
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000

# In a second terminal window, run the UI:
cd frontend
npm run dev
```

Open your browser to: `http://localhost:5173`.
Navigate to **Connect Device**, choose your `COMx` port, set `9600 baud`, and click **Connect**.
