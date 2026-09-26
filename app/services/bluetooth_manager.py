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
        {"name": "Wireless Keyboard", "mac": "E4:58:B8:A1:02:11", "connected": True, "trusted": True},
        {"name": "Pixel 8 Pro", "mac": "9C:28:B3:77:43:89", "connected": False, "trusted": True}
    ],
    "discovered_devices": [
        {"name": "BLE Temp Sensor", "mac": "A4:C1:38:99:12:34", "connected": False, "trusted": False},
        {"name": "Smart Speaker", "mac": "FC:58:FA:44:21:00", "connected": False, "trusted": False}
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
                return {
                    "available": True,
                    "powered": powered,
                    "discoverable": discoverable,
                    "pairable": pairable,
                    "adapter": adapter_name,
                    "mac": mac_addr,
                    "paired_devices": devices
                }
            except Exception:
                pass

        # Fallback Mock status
        return {
            "available": True,
            "powered": _mock_bt_state["powered"],
            "discoverable": _mock_bt_state["discoverable"],
            "pairable": _mock_bt_state["pairable"],
            "adapter": _mock_bt_state["adapter"],
            "mac": _mock_bt_state["mac"],
            "paired_devices": _mock_bt_state["paired_devices"]
        }

    @staticmethod
    def get_paired_devices_real() -> list[dict]:
        devices = []
        if not shutil.which("bluetoothctl"):
            return devices
        try:
            res = subprocess.run(["bluetoothctl", "paired-devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            for line in res.stdout.splitlines():
                # Device AA:BB:CC:DD:EE:FF Name
                parts = line.split(None, 2)
                if len(parts) >= 3 and parts[0] == "Device":
                    mac = parts[1]
                    name = parts[2]
                    # Check info for connection status
                    info_res = subprocess.run(["bluetoothctl", "info", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                    connected = "Connected: yes" in info_res.stdout
                    trusted = "Trusted: yes" in info_res.stdout
                    devices.append({
                        "name": name,
                        "mac": mac,
                        "connected": connected,
                        "trusted": trusted
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
                # Trigger scan on
                subprocess.run(["bluetoothctl", "--timeout", str(duration_seconds), "scan", "on"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=duration_seconds + 3)
                # List discovered
                res = subprocess.run(["bluetoothctl", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                found = []
                for line in res.stdout.splitlines():
                    parts = line.split(None, 2)
                    if len(parts) >= 3 and parts[0] == "Device":
                        mac = parts[1]
                        name = parts[2]
                        found.append({"name": name, "mac": mac, "connected": False, "trusted": False})
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

        # Mock pair
        dev = next((d for d in _mock_bt_state["discovered_devices"] if d["mac"] == mac), None)
        name = dev["name"] if dev else "Unknown Device"
        if not any(d["mac"] == mac for d in _mock_bt_state["paired_devices"]):
            _mock_bt_state["paired_devices"].append({"name": name, "mac": mac, "connected": False, "trusted": True})
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
        return True, f"Device {mac} {action}ed (Mock)"
