# Linux Installation and Permissions Guide (Ubuntu, Debian, RHEL)

## 1. Prerequisites
Install system build tools and python3:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm git
```

## 2. Serial Port Identification and Permissions
When plugging in your USB-to-RS485 adapter, check `dmesg`:

```bash
dmesg | grep -E "ttyUSB|ttyACM"
```
Typical output:
```
[ 1420.12] usb 1-1.2: FTDI USB Serial Device converter now attached to ttyUSB0
```

### Granting Dialout Group Permissions (Crucial!)
By default, non-root users cannot read or write `/dev/ttyUSB0` or `/dev/ttyACM0`. Add your current user to the `dialout` (or `uucp` on Arch) group:

```bash
sudo usermod -aG dialout $USER
# On Arch/Manjaro:
sudo usermod -aG uucp $USER
```
> [!IMPORTANT]
> Log out and log back in, or run `newgrp dialout` for group permission changes to take effect.

Verify access permissions:
```bash
ls -l /dev/ttyUSB0
# Should output: crw-rw---- 1 root dialout ... /dev/ttyUSB0
```

### Avoiding ModemManager Port Contention
On Ubuntu, the `ModemManager` service frequently opens serial ports to probe for 3G/LTE modems, which disrupts Modbus communication:

```bash
sudo systemctl stop ModemManager
sudo systemctl disable ModemManager
```

## 3. Application Setup & Running

```bash
# 1. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Frontend setup
cd ../frontend
npm install
npm run build

# 3. Launch via provided script
cd ..
./scripts/start.sh
```
Open your browser at `http://localhost:5173`.
