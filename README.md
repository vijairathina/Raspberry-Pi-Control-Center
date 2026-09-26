# 🍓 Raspberry Pi Control Center

A production-quality, lightweight, and modern Web Management Console built for Raspberry Pi (optimized for Raspberry Pi 3, 4, 5, and Zero 2W).

Provides a secure browser-based interface for monitoring telemetry, configuring Wi-Fi and Bluetooth, managing systemd services and processes, inspecting hardware and 40-pin GPIOs, running network diagnostics, executing automated IF/THEN rules, and controlling peripherals.

---

## 🚀 Key Features

1. **Dashboard & Hardware Telemetry:**
   - Real-time CPU, RAM, temperature, and disk gauges with 3-second live polling.
   - Decodes Raspberry Pi hardware throttling telemetry via `vcgencmd get_throttled` (detects active & historical under-voltage, ARM frequency capping, and thermal limits).
   - Board model identification (`/proc/device-tree/model` or `/proc/cpuinfo`), OS kernel, architecture, and uptime.

2. **Real-time Performance Graphs:**
   - Real-time Chart.js telemetry: overall CPU %, per-core breakdown, load average, clock frequency.
   - Memory analysis: RAM used/free/buffers and swap utilization.
   - Dual-channel network bandwidth monitor (RX & TX speed in KB/s).

3. **Linux Services & Logs:**
   - Comprehensive `systemctl` unit manager (Start, Stop, Restart, Enable, Disable, Status).
   - Critical system services (`ssh`, `systemd`, `dbus`, `NetworkManager`) are protected against accidental termination.
   - Terminal-style journal log viewer with `journalctl` (Last 50, 100, 500 lines, search filter, error-only filter, and raw log download).

4. **Process Manager:**
   - Inspect processes by PID, Name, CPU %, RAM %, User, and Status.
   - Interactive sorting and instant filtering.
   - Protected PID 1 (init) and control server process; graceful `SIGTERM` or force `SIGKILL`.

5. **Bluetooth Management:**
   - Adapter state controls (Power ON/OFF, Restart HCI service, Pairable & Discoverable modes).
   - Scan for nearby Bluetooth / BLE peripherals using `bluetoothctl`.
   - Pair, trust, connect, disconnect, and remove paired devices with strict MAC address validation.

6. **Wi-Fi & Network Priority:**
   - Active Wi-Fi telemetry: SSID, signal strength, channel, frequency, encryption, IP, gateway.
   - Spectrum scan for local access points.
   - Saved Wi-Fi profiles with NetworkManager connection priority order adjustment (`↑` / `↓`).
   - Wi-Fi pre-shared keys are never exposed in API responses or UI.

7. **Network Interfaces & Safe Temporary Block:**
   - Interface controls: `eth0`, `wlan0`, `tailscale0`, `docker0` link up/down and DHCP lease renewal.
   - **Fail-safe Temporary Network Block:**
     - Checks if current browser connection is routed through target interface and issues lockout warning.
     - Automatically schedules an independent restoration task **BEFORE** disabling the interface (survives Flask restart).
     - Live countdown with immediate `[Restore Now]` button.
   - Local listening ports viewer and firewall status (`ufw` / `iptables`).

8. **Network Diagnostics:**
   - Safe ICMP ping (Gateway, 1.1.1.1, 8.8.8.8, custom host).
   - DNS query resolution benchmark and multi-hop traceroute.
   - 24-hour Internet connectivity reliability and latency tracking.

9. **Hardware, 40-Pin GPIO & Camera:**
   - Peripheral inventory: USB devices (`lsusb`), PCI devices, serial ports (`/dev/ttyAMA0`), and I2C/SPI buses.
   - 40-pin GPIO interactive table: configure safe pins as Input/Output and toggle logic states (HIGH/LOW). Power and ground pins are locked.
   - Camera module auto-detection (`vcgencmd get_camera`, `libcamera`, or V4L2) with live test pattern / frame capture.

10. **Automation & Task Scheduler:**
    - Background task scheduler for recurring daily or weekly reboots, service restarts, and maintenance passes.
    - Reactive IF/THEN automation engine: triggers actions (e.g. alert, service restart) based on temperature, CPU, RAM, or Wi-Fi state.
    - Historical alert log with severity tags (`Normal`, `Warning`, `Critical`).

11. **Security & Audit Logs:**
    - Werkzeug PBKDF2:SHA256 password hashing.
    - Sliding window rate limiting on login (5 attempts per minute per IP).
    - Strict CSRF token validation on all state-modifying requests.
    - Tamper-evident administrative audit log with timestamps, actions, IP addresses, and outcomes.
    - JSON configuration backup export and validated restore.

---

## 📦 Project Structure

```
Raspberry Pi Control Center/
│
├── run.py                          # Application entry point
├── requirements.txt                # Lightweight Python dependencies
├── config.yaml                     # Application settings & thresholds
├── README.md                       # Documentation & deployment guide
│
├── app/
│   ├── __init__.py                 # Flask app factory & blueprint registration
│   ├── config.py                   # Configuration parser
│   ├── database.py                 # SQLite schema, WAL mode, default seeding
│   ├── auth.py                     # Session auth, CSRF, rate limiter, audit helper
│   │
│   ├── routes/
│   │   ├── auth_routes.py          # Login, logout, change password
│   │   ├── dashboard.py            # Overview & telemetry polling
│   │   ├── performance.py          # Real-time metrics API & graphs
│   │   ├── services.py             # Systemd service manager & journal logs
│   │   ├── processes.py            # Task inspection & termination
│   │   ├── bluetooth.py            # Bluetoothctl manager & scans
│   │   ├── wifi.py                 # Wi-Fi scanner, profiles, priorities
│   │   ├── network.py              # Interface manager & temporary blocks
│   │   ├── storage.py              # Filesystems & disk hardware
│   │   ├── hardware.py             # Hardware overview, 40-pin GPIO, camera
│   │   ├── diagnostics.py          # Ping, DNS, traceroute, uptime stats
│   │   ├── tasks.py                # Scheduled background tasks
│   │   ├── automation.py           # IF/THEN rules & alerts
│   │   ├── docker_routes.py        # Container manager & logs
│   │   ├── tailscale_routes.py     # Tailscale mesh VPN overview
│   │   └── security_routes.py      # Audit logs, app logs, settings backup
│   │
│   ├── services/                   # Modular service classes (command allowlists)
│   │   ├── system_service.py       # Hostname, vcgencmd throttling, reboot
│   │   ├── performance_service.py  # psutil circular metrics buffer
│   │   ├── service_manager.py      # systemctl & journalctl wrapper
│   │   ├── processes_manager.py    # psutil process manager & safeguards
│   │   ├── bluetooth_manager.py    # bluetoothctl & rfkill operations
│   │   ├── wifi_manager.py         # nmcli & iw wireless operations
│   │   ├── network_manager.py      # Interfaces & fail-safe rollback timers
│   │   ├── storage_manager.py      # Mounted filesystems & lsblk parser
│   │   ├── hardware_manager.py     # USB, PCI, serial, and bus inspection
│   │   ├── gpio_manager.py         # 40-pin header map & safe logic toggles
│   │   ├── camera_manager.py       # Camera sensor detection & frame capture
│   │   ├── docker_manager.py       # Docker CLI inspection & log reader
│   │   ├── tailscale_manager.py    # Tailscale status & daemon controls
│   │   ├── diagnostics.py          # Safe ICMP, DNS, traceroute subprocesses
│   │   ├── scheduler.py            # SQLite-backed background scheduler
│   │   ├── automation_engine.py    # Reactive telemetry rule evaluator
│   │   └── audit_logger.py         # Audit trail & app log buffer
│   │
│   ├── templates/                  # Modern responsive Jinja2 templates
│   │   ├── base.html               # Responsive sidebar, theme toggle, modals
│   │   ├── login.html              # Modern dark authentication portal
│   │   ├── dashboard.html          # Device telemetry & alerts
│   │   ├── performance.html        # Real-time Chart.js streams
│   │   ├── services.html           # Systemd unit manager
│   │   ├── service_logs.html       # Terminal-style journalctl viewer
│   │   ├── processes.html          # Process list & termination
│   │   ├── bluetooth.html          # Bluetooth controller & pairing
│   │   ├── wifi.html               # Wi-Fi scanner & priority list
│   │   ├── network.html            # Interfaces & safe temporary disable
│   │   ├── storage.html            # Filesystems & disk drives
│   │   ├── hardware.html           # 40-pin GPIO & camera stream
│   │   ├── diagnostics.html        # Ping, DNS, traceroute tools
│   │   ├── tasks.html              # Scheduled maintenance jobs
│   │   ├── automation.html         # IF/THEN rules & alert history
│   │   ├── docker.html             # Container management
│   │   ├── tailscale.html          # Mesh VPN peers
│   │   ├── logs.html               # Application logs
│   │   ├── security.html           # Audit trail & credentials
│   │   └── settings.html           # Alert thresholds & backup/restore
│   │
│   └── static/
│       ├── css/style.css           # Glassmorphism, Dark/Light modes, layout
│       └── js/
│           ├── app.js              # CSRF handling, toasts, confirm modals
│           └── charts.js           # Chart.js live rendering engine
│
├── tests/                          # Automated Pytest test suite (15 tests)
│   ├── conftest.py                 # Test fixtures & test DB setup
│   ├── test_all_features.py        # Core feature & security tests
│   └── test_advanced_features.py   # GPIO, Docker, Tailscale, Backup tests
│
└── systemd/
    └── raspberry-controller.service # Systemd unit file for autostart
```

---

## 🛠️ Installation & Setup on Raspberry Pi

### 1. Prerequisites
On Raspberry Pi OS (Debian Bookworm or Bullseye):
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### 2. Clone or Copy the Repository
```bash
cd /opt
sudo git clone https://github.com/your-username/raspberry-controller.git
cd /opt/raspberry-controller
```

### 3. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### 4. Run the Test Suite
```bash
./venv/bin/python -m pytest -v
```

### 5. Launch Manually (Development Mode)
```bash
./venv/bin/python run.py
```
Open your browser at:
`http://<raspberrypi-ip>:5000` or `http://raspberrypi.local:5000`

Default credentials:
- **Username:** `admin`
- **Password:** `admin` *(Change immediately in Settings)*

---

## ⚙️ Production Deployment via Systemd

To automatically launch the Control Center on boot and restart on failures:

1. Copy the systemd service file:
```bash
sudo cp systemd/raspberry-controller.service /etc/systemd/system/
```

2. Reload systemd daemon and enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable raspberry-controller.service
sudo systemctl start raspberry-controller.service
```

3. Check service status:
```bash
sudo systemctl status raspberry-controller.service
```

4. View service logs:
```bash
sudo journalctl -u raspberry-controller -f
```

---

## 🔒 Security Model & Architectural Rules

- **Strict Predefined Allowlist:** The application **never** exposes an `/api/execute-command` endpoint or accepts arbitrary shell commands from the browser.
- **Layered Architecture:** Routes invoke backend service managers which perform parameterized, validated system calls.
- **Fail-safe Network Operations:** When an interface is temporarily blocked, the rollback timer is scheduled **BEFORE** the interface state is changed.
- **Brute Force Protection:** Rate limiting locks IP addresses after 5 unsuccessful login attempts per minute.
- **Session Hardening:** All session cookies use `HttpOnly` and `SameSite=Lax` with persistent CSRF token checks.
