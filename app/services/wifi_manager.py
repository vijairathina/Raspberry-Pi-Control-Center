import shutil
import subprocess
import re
import socket

# Mock saved connections and scanned networks for non-Linux / test dev
_mock_wifi_state = {
    "current": {
        "ssid": "Home-Network-5G",
        "signal": 88,
        "channel": 36,
        "frequency": "5180 MHz",
        "security": "WPA2-PSK",
        "ip_address": "192.168.1.145",
        "gateway": "192.168.1.1",
        "dns": "192.168.1.1, 8.8.8.8",
        "interface": "wlan0",
        "speed": "433.3 Mbit/s"
    },
    "saved": [
        {"name": "Home-Network-5G", "uuid": "3a7b1c4d-98e2-4521-a3f2-1a2b3c4d5e6f", "type": "802-11-wireless", "device": "wlan0", "priority": 100, "autoconnect": True},
        {"name": "Office-Guest-WiFi", "uuid": "8f9e0a1b-2c3d-4e5f-6a7b-8c9d0e1f2a3b", "type": "802-11-wireless", "device": "--", "priority": 50, "autoconnect": True},
        {"name": "Mobile-Hotspot", "uuid": "11223344-5566-7788-99aa-bbccddeeff00", "type": "802-11-wireless", "device": "--", "priority": 20, "autoconnect": False}
    ],
    "scanned": [
        {"ssid": "Home-Network-5G", "signal": 88, "channel": 36, "security": "WPA2-PSK", "frequency": "5.180 GHz", "in_use": True},
        {"ssid": "Home-Network-2.4G", "signal": 95, "channel": 6, "security": "WPA2-PSK", "frequency": "2.437 GHz", "in_use": False},
        {"ssid": "Neighbor_WiFi", "signal": 42, "channel": 1, "security": "WPA2-PSK", "frequency": "2.412 GHz", "in_use": False},
        {"ssid": "IoT_Lab_Secure", "signal": 65, "channel": 11, "security": "WPA2/WPA3", "frequency": "2.462 GHz", "in_use": False}
    ]
}

class WifiManager:
    @staticmethod
    def get_current_connection() -> dict:
        if shutil.which("nmcli"):
            try:
                # Active wifi connection
                cmd = ["nmcli", "-t", "-f", "active,ssid,bssid,signal,chan,freq,security,device", "dev", "wifi"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    if line.startswith("yes:"):
                        parts = line.split(":")
                        if len(parts) >= 8:
                            ssid = parts[1]
                            signal = int(parts[3]) if parts[3].isdigit() else 0
                            chan = parts[4]
                            freq = parts[5]
                            security = parts[6]
                            iface = parts[7]
                            
                            # Get IP info for interface
                            ip_info = WifiManager.get_interface_ip(iface)
                            return {
                                "connected": True,
                                "ssid": ssid,
                                "signal": signal,
                                "channel": chan,
                                "frequency": freq,
                                "security": security or "Open",
                                "ip_address": ip_info.get("ip", "Unknown"),
                                "gateway": ip_info.get("gateway", "Unknown"),
                                "dns": ip_info.get("dns", "Unknown"),
                                "interface": iface,
                                "speed": ip_info.get("speed", "Unknown")
                            }
            except Exception:
                pass

        # Return mock / fallback
        return {
            "connected": True,
            **_mock_wifi_state["current"]
        }

    @staticmethod
    def get_interface_ip(iface: str) -> dict:
        result = {"ip": "Unknown", "gateway": "Unknown", "dns": "Unknown", "speed": "Auto"}
        if shutil.which("nmcli"):
            try:
                cmd = ["nmcli", "-t", "-f", "IP4.ADDRESS,IP4.GATEWAY,IP4.DNS", "dev", "show", iface]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                for line in res.stdout.splitlines():
                    if line.startswith("IP4.ADDRESS"):
                        result["ip"] = line.split(":", 1)[1].split("/")[0]
                    elif line.startswith("IP4.GATEWAY"):
                        result["gateway"] = line.split(":", 1)[1]
                    elif line.startswith("IP4.DNS"):
                        result["dns"] = line.split(":", 1)[1]
            except Exception:
                pass
        return result

    @staticmethod
    def scan_networks() -> list[dict]:
        networks = []
        if shutil.which("nmcli"):
            try:
                # Trigger rescan
                cmd = ["nmcli", "-t", "-f", "in-use,ssid,signal,chan,freq,security", "dev", "wifi", "list", "--rescan", "yes"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
                seen_ssids = set()
                for line in res.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 6:
                        in_use = (parts[0] == "*")
                        ssid = parts[1].strip()
                        if not ssid or ssid in seen_ssids:
                            continue
                        seen_ssids.add(ssid)
                        signal = int(parts[2]) if parts[2].isdigit() else 0
                        chan = parts[3]
                        freq = parts[4]
                        sec = parts[5] or "Open"
                        networks.append({
                            "ssid": ssid,
                            "signal": signal,
                            "channel": chan,
                            "frequency": freq,
                            "security": sec,
                            "in_use": in_use
                        })
                if networks:
                    return sorted(networks, key=lambda n: n["signal"], reverse=True)
            except Exception:
                pass

        return _mock_wifi_state["scanned"]

    @staticmethod
    def get_saved_networks() -> list[dict]:
        saved = []
        if shutil.which("nmcli"):
            try:
                cmd = ["nmcli", "-t", "-f", "NAME,UUID,TYPE,DEVICE", "connection", "show"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                for line in res.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 4 and ("wireless" in parts[2] or "wifi" in parts[2]):
                        name = parts[0]
                        uuid = parts[1]
                        dev = parts[3] or "--"
                        # Check autoconnect priority
                        pri_res = subprocess.run(["nmcli", "-t", "-f", "connection.autoconnect-priority,connection.autoconnect", "connection", "show", uuid], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
                        prio = 0
                        autoconnect = True
                        for pline in pri_res.stdout.splitlines():
                            if "autoconnect-priority" in pline:
                                val = pline.split(":", 1)[1]
                                prio = int(val) if val.isdigit() or (val.startswith("-") and val[1:].isdigit()) else 0
                            elif "autoconnect:" in pline:
                                autoconnect = "yes" in pline
                        saved.append({
                            "name": name,
                            "uuid": uuid,
                            "type": parts[2],
                            "device": dev,
                            "priority": prio,
                            "autoconnect": autoconnect
                        })
                if saved:
                    return sorted(saved, key=lambda x: x["priority"], reverse=True)
            except Exception:
                pass

        return sorted(_mock_wifi_state["saved"], key=lambda x: x["priority"], reverse=True)

    @staticmethod
    def connect_network(ssid: str, password: str = "") -> tuple[bool, str]:
        if not ssid or len(ssid) > 64:
            return False, "Invalid SSID"

        if shutil.which("nmcli"):
            try:
                cmd = ["nmcli", "dev", "wifi", "connect", ssid]
                if password:
                    cmd.extend(["password", password])
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
                if res.returncode == 0:
                    return True, f"Successfully connected to Wi-Fi network '{ssid}'"
                return False, res.stderr.strip() or f"Failed to connect to '{ssid}'"
            except Exception as e:
                return False, str(e)

        # Mock connection update
        _mock_wifi_state["current"]["ssid"] = ssid
        return True, f"Connected to '{ssid}' (Mock)"

    @staticmethod
    def disconnect_network(iface: str = "wlan0") -> tuple[bool, str]:
        if shutil.which("nmcli"):
            try:
                res = subprocess.run(["nmcli", "dev", "disconnect", iface], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if res.returncode == 0:
                    return True, f"Disconnected Wi-Fi on {iface}"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        _mock_wifi_state["current"]["ssid"] = "Disconnected"
        return True, f"Disconnected Wi-Fi on {iface} (Mock)"

    @staticmethod
    def forget_network(identifier: str) -> tuple[bool, str]:
        # identifier can be SSID name or UUID
        if shutil.which("nmcli"):
            try:
                res = subprocess.run(["nmcli", "connection", "delete", identifier], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if res.returncode == 0:
                    return True, f"Forgot network '{identifier}'"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        _mock_wifi_state["saved"] = [n for n in _mock_wifi_state["saved"] if n["name"] != identifier and n["uuid"] != identifier]
        return True, f"Forgot network '{identifier}' (Mock)"

    @staticmethod
    def set_priority(name_or_uuid: str, new_priority: int) -> tuple[bool, str]:
        if shutil.which("nmcli"):
            try:
                cmd = ["nmcli", "connection", "modify", name_or_uuid, "connection.autoconnect-priority", str(new_priority)]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    return True, f"Priority for '{name_or_uuid}' set to {new_priority}"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        for n in _mock_wifi_state["saved"]:
            if n["name"] == name_or_uuid or n["uuid"] == name_or_uuid:
                n["priority"] = new_priority
        return True, f"Priority set to {new_priority} (Mock)"
