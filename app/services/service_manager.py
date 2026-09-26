import re
import shutil
import subprocess

SERVICE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.@]+$")
CRITICAL_SERVICES = {"ssh", "sshd", "systemd", "dbus", "systemd-logind", "network", "networking", "NetworkManager"}

# Fallback mock service registry for testing / non-Linux environments
_MOCK_SERVICES = {
    "ssh.service": {"description": "OpenBSD Secure Shell server", "running": True, "enabled": True, "pid": 582},
    "NetworkManager.service": {"description": "Network Manager", "running": True, "enabled": True, "pid": 412},
    "bluetooth.service": {"description": "Bluetooth service", "running": True, "enabled": True, "pid": 605},
    "cron.service": {"description": "Regular background program processing daemon", "running": True, "enabled": True, "pid": 320},
    "avahi-daemon.service": {"description": "Avahi mDNS/DNS-SD Stack", "running": True, "enabled": True, "pid": 331},
    "rsyslog.service": {"description": "System Logging Service", "running": True, "enabled": True, "pid": 345},
    "wpa_supplicant.service": {"description": "WPA supplicant", "running": True, "enabled": True, "pid": 450},
    "raspberry-controller.service": {"description": "Raspberry Pi Control Center", "running": True, "enabled": True, "pid": 1120},
    "nginx.service": {"description": "A high performance web server", "running": False, "enabled": False, "pid": 0},
    "mosquitto.service": {"description": "Mosquitto MQTT Broker", "running": False, "enabled": True, "pid": 0},
}

class ServiceManager:
    @staticmethod
    def is_valid_name(name: str) -> bool:
        if not name or len(name) > 128:
            return False
        return bool(SERVICE_NAME_REGEX.match(name))

    @staticmethod
    def is_critical(name: str) -> bool:
        clean = name.replace(".service", "").lower()
        return clean in CRITICAL_SERVICES

    @staticmethod
    def list_services(search_query: str = "") -> list[dict]:
        services = []
        if shutil.which("systemctl"):
            try:
                cmd = ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        parts = line.strip().split(None, 4)
                        if len(parts) >= 4:
                            unit = parts[0]
                            load = parts[1]
                            active = parts[2]
                            sub = parts[3]
                            desc = parts[4] if len(parts) > 4 else ""
                            
                            is_running = (active == "active" and sub == "running")
                            
                            # Filter search
                            if search_query:
                                q = search_query.lower()
                                if q not in unit.lower() and q not in desc.lower():
                                    continue

                            services.append({
                                "name": unit,
                                "description": desc,
                                "running": is_running,
                                "enabled": (load == "loaded"),
                                "active_state": active,
                                "sub_state": sub,
                                "pid": None,
                                "is_critical": ServiceManager.is_critical(unit)
                            })
                    return services
            except Exception:
                pass

        # Emulated / Mock services
        for name, data in _MOCK_SERVICES.items():
            if search_query:
                q = search_query.lower()
                if q not in name.lower() and q not in data["description"].lower():
                    continue
            services.append({
                "name": name,
                "description": data["description"],
                "running": data["running"],
                "enabled": data["enabled"],
                "active_state": "active" if data["running"] else "inactive",
                "sub_state": "running" if data["running"] else "dead",
                "pid": data["pid"],
                "is_critical": ServiceManager.is_critical(name)
            })

        return sorted(services, key=lambda s: s["name"])

    @staticmethod
    def control_service(name: str, action: str) -> tuple[bool, str]:
        if not ServiceManager.is_valid_name(name):
            return False, "Invalid service name"

        allowed_actions = {"start", "stop", "restart", "enable", "disable", "reload"}
        if action not in allowed_actions:
            return False, f"Action {action} is not allowed"

        if action in {"stop", "disable"} and ServiceManager.is_critical(name):
            return False, f"Action '{action}' is protected for critical system service: {name}"

        if shutil.which("systemctl"):
            try:
                cmd = ["systemctl", action, name]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                if res.returncode == 0:
                    return True, f"Service '{name}' {action}ed successfully"
                else:
                    return False, f"systemctl {action} error: {res.stderr.strip()}"
            except Exception as e:
                return False, f"Execution failed: {e}"

        # Mock action update
        if name in _MOCK_SERVICES:
            if action == "start":
                _MOCK_SERVICES[name]["running"] = True
                _MOCK_SERVICES[name]["pid"] = 1420
            elif action == "stop":
                _MOCK_SERVICES[name]["running"] = False
                _MOCK_SERVICES[name]["pid"] = 0
            elif action == "restart":
                _MOCK_SERVICES[name]["running"] = True
            elif action == "enable":
                _MOCK_SERVICES[name]["enabled"] = True
            elif action == "disable":
                _MOCK_SERVICES[name]["enabled"] = False
            return True, f"Service '{name}' {action}ed successfully (Mock)"

        return True, f"Service '{name}' {action} command simulated"

    @staticmethod
    def get_service_logs(name: str, lines: int = 50, error_only: bool = False, search: str = "") -> dict:
        if not ServiceManager.is_valid_name(name):
            return {"success": False, "logs": "Invalid service name"}

        lines = max(10, min(lines, 1000))

        if shutil.which("journalctl"):
            try:
                cmd = ["journalctl", "-u", name, "-n", str(lines), "--no-pager"]
                if error_only:
                    cmd.extend(["-p", "3"]) # err or higher
                if search:
                    cmd.extend(["-g", search])

                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
                log_text = res.stdout if res.stdout else "No log records found for unit."
                return {"success": True, "logs": log_text, "unit": name, "lines": lines}
            except Exception as e:
                return {"success": False, "logs": f"journalctl error: {e}"}

        # Mock logs for development
        sample_logs = [
            f"Mar 26 12:00:01 rpi systemd[1]: Started {name}.",
            f"Mar 26 12:00:02 rpi {name}[1234]: Service initialized in worker pool.",
            f"Mar 26 12:01:15 rpi {name}[1234]: Telemetry heartbeat OK.",
            f"Mar 26 12:05:00 rpi {name}[1234]: Scheduled maintenance pass complete.",
        ]
        if error_only:
            sample_logs = [f"Mar 26 12:02:10 rpi {name}[1234]: (Error filter active) No critical alerts recorded."]

        return {
            "success": True,
            "logs": "\n".join(sample_logs),
            "unit": name,
            "lines": lines
        }
