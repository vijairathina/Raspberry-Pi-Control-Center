import re
import shutil
import subprocess
import threading
import time

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

# Mock storage for testing / non-Linux dev
_mock_bt_state = {
    "powered": True,
    "discoverable": False,
    "pairable": True,
    "adapter": "hci0",
    "mac": "B8:27:EB:12:34:56",
    "paired_devices": [
        {
            "name": "BLE Temp & Humidity Sensor",
            "mac": "A4:C1:38:99:12:34",
            "device_type": "BLE",
            "connected": True,
            "trusted": True,
            "rssi": -62,
            "battery": 88
        },
        {
            "name": "Wireless Mechanical Keyboard",
            "mac": "E4:58:B8:A1:02:11",
            "device_type": "Classic BT",
            "connected": True,
            "trusted": True,
            "rssi": -48,
            "battery": 75
        },
        {
            "name": "Pixel 8 Pro",
            "mac": "9C:28:B3:77:43:89",
            "device_type": "Classic BT",
            "connected": False,
            "trusted": True,
            "rssi": None,
            "battery": None
        }
    ],
    "discovered_devices": [
        {"name": "BLE Smart Fitness Band", "mac": "D8:52:19:44:88:AA", "device_type": "BLE", "connected": False, "trusted": False, "rssi": -71},
        {"name": "Sony WH-1000XM4 Audio", "mac": "FC:58:FA:44:21:00", "device_type": "Classic BT", "connected": False, "trusted": False, "rssi": -55},
        {"name": "BLE Beacon Node 04", "mac": "E0:4F:43:11:22:33", "device_type": "BLE", "connected": False, "trusted": False, "rssi": -80}
    ]
}

class BluetoothManager:
    @staticmethod
    def is_valid_mac(mac: str) -> bool:
        return bool(MAC_REGEX.match(mac))

    @staticmethod
    def get_status() -> dict:
        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(["bluetoothctl", "show"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                powered = "Powered: yes" in res.stdout
                discoverable = "Discoverable: yes" in res.stdout
                pairable = "Pairable: yes" in res.stdout
                
                adapter_name = "hci0"
                mac_addr = "Unknown"
                for line in res.stdout.splitlines():
                    if "Controller" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            mac_addr = parts[1]
                    elif "Name:" in line:
                        adapter_name = line.split("Name:", 1)[1].strip()

                devices = BluetoothManager.get_paired_devices_real()
                connected_devices = [d for d in devices if d.get("connected")]

                return {
                    "available": True,
                    "powered": powered,
                    "discoverable": discoverable,
                    "pairable": pairable,
                    "adapter": adapter_name,
                    "mac": mac_addr,
                    "connected_devices": connected_devices,
                    "paired_devices": devices
                }
            except Exception:
                pass

        # Fallback Mock status
        all_paired = _mock_bt_state["paired_devices"]
        connected = [d for d in all_paired if d.get("connected")]
        return {
            "available": True,
            "powered": _mock_bt_state["powered"],
            "discoverable": _mock_bt_state["discoverable"],
            "pairable": _mock_bt_state["pairable"],
            "adapter": _mock_bt_state["adapter"],
            "mac": _mock_bt_state["mac"],
            "connected_devices": connected,
            "paired_devices": all_paired
        }

    @staticmethod
    def get_paired_devices_real() -> list[dict]:
        devices = []
        if not shutil.which("bluetoothctl"):
            return devices
        try:
            res = subprocess.run(["bluetoothctl", "paired-devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            for line in res.stdout.splitlines():
                parts = line.split(None, 2)
                if len(parts) >= 3 and parts[0] == "Device":
                    mac = parts[1]
                    name = parts[2]
                    
                    info_res = subprocess.run(["bluetoothctl", "info", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                    stdout = info_res.stdout
                    connected = "Connected: yes" in stdout
                    trusted = "Trusted: yes" in stdout
                    
                    # Detect BLE vs Classic BT
                    # Bluez flags LE devices with AddressType: random, or Service UUIDs, or Class not present
                    is_le = ("Type: LE" in stdout or "AddressType: random" in stdout or "GATT" in stdout or "0000180f" in stdout.lower())
                    device_type = "BLE" if is_le else "Classic BT"

                    # Parse RSSI if connected
                    rssi = None
                    battery = None
                    for iline in stdout.splitlines():
                        if "RSSI:" in iline:
                            try:
                                rssi = int(iline.split("RSSI:")[1].strip())
                            except Exception:
                                pass
                        elif "Battery Percentage:" in iline:
                            try:
                                battery = int(iline.split("Battery Percentage:")[1].replace("%", "").strip())
                            except Exception:
                                pass

                    devices.append({
                        "name": name,
                        "mac": mac,
                        "device_type": device_type,
                        "connected": connected,
                        "trusted": trusted,
                        "rssi": rssi,
                        "battery": battery
                    })
        except Exception:
            pass
        return devices

    @staticmethod
    def set_power(enable: bool) -> tuple[bool, str]:
        cmd_arg = "on" if enable else "off"
        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(["bluetoothctl", "power", cmd_arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    return True, f"Bluetooth turned {cmd_arg}"
                return False, res.stderr.strip() or f"Failed to turn bluetooth {cmd_arg}"
            except Exception as e:
                return False, str(e)

        _mock_bt_state["powered"] = enable
        return True, f"Bluetooth turned {cmd_arg} (Mock)"

    @staticmethod
    def restart_bluetooth() -> tuple[bool, str]:
        if shutil.which("systemctl"):
            try:
                res = subprocess.run(["systemctl", "restart", "bluetooth"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
                if res.returncode == 0:
                    return True, "Bluetooth service restarted"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        return True, "Bluetooth service restarted (Mock)"

    @staticmethod
    def scan_devices(duration_seconds: int = 5) -> list[dict]:
        duration_seconds = max(3, min(duration_seconds, 15))
        if shutil.which("bluetoothctl"):
            try:
                subprocess.run(["bluetoothctl", "--timeout", str(duration_seconds), "scan", "on"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=duration_seconds + 3)
                res = subprocess.run(["bluetoothctl", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                found = []
                for line in res.stdout.splitlines():
                    parts = line.split(None, 2)
                    if len(parts) >= 3 and parts[0] == "Device":
                        mac = parts[1]
                        name = parts[2]
                        # Quick check if LE
                        is_le = "LE" in name.upper() or "BEACON" in name.upper()
                        found.append({
                            "name": name,
                            "mac": mac,
                            "device_type": "BLE" if is_le else "Classic BT",
                            "connected": False,
                            "trusted": False,
                            "rssi": -65
                        })
                return found
            except Exception:
                pass

        return _mock_bt_state["discovered_devices"]

    @staticmethod
    def pair_device(mac: str) -> tuple[bool, str]:
        if not BluetoothManager.is_valid_mac(mac):
            return False, "Invalid MAC address format"

        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(["bluetoothctl", "pair", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                if res.returncode == 0:
                    subprocess.run(["bluetoothctl", "trust", mac], timeout=5)
                    return True, f"Paired with device {mac}"
                return False, res.stderr.strip() or f"Failed to pair with {mac}"
            except Exception as e:
                return False, str(e)

        dev = next((d for d in _mock_bt_state["discovered_devices"] if d["mac"] == mac), None)
        name = dev["name"] if dev else "Unknown Device"
        dtype = dev.get("device_type", "BLE" if "BLE" in name else "Classic BT")
        if not any(d["mac"] == mac for d in _mock_bt_state["paired_devices"]):
            _mock_bt_state["paired_devices"].append({
                "name": name,
                "mac": mac,
                "device_type": dtype,
                "connected": False,
                "trusted": True,
                "rssi": -60,
                "battery": None
            })
        return True, f"Device {mac} paired successfully (Mock)"

    @staticmethod
    def remove_device(mac: str) -> tuple[bool, str]:
        if not BluetoothManager.is_valid_mac(mac):
            return False, "Invalid MAC address format"

        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(["bluetoothctl", "remove", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
                if res.returncode == 0:
                    return True, f"Removed pairing for {mac}"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        _mock_bt_state["paired_devices"] = [d for d in _mock_bt_state["paired_devices"] if d["mac"] != mac]
        return True, f"Device {mac} removed (Mock)"

    @staticmethod
    def connect_device(mac: str, connect: bool = True) -> tuple[bool, str]:
        if not BluetoothManager.is_valid_mac(mac):
            return False, "Invalid MAC address format"

        action = "connect" if connect else "disconnect"
        if shutil.which("bluetoothctl"):
            try:
                res = subprocess.run(["bluetoothctl", action, mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if res.returncode == 0:
                    return True, f"Device {mac} {action}ed"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        for d in _mock_bt_state["paired_devices"]:
            if d["mac"] == mac:
                d["connected"] = connect
                if connect and not d.get("battery"):
                    d["battery"] = 90
        return True, f"Device {mac} {action}ed (Mock)"
