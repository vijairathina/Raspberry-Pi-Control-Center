import os
import sys
import platform
import subprocess
import shutil
import time
import socket
from datetime import datetime
import psutil

class SystemService:
    @staticmethod
    def get_hostname() -> str:
        return socket.gethostname()

    @staticmethod
    def get_model() -> str:
        # Check standard Raspberry Pi device tree files
        for path in ["/proc/device-tree/model", "/sys/firmware/devicetree/base/model"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        model = f.read().strip().replace("\x00", "")
                        if model:
                            return model
                except Exception:
                    pass

        # Check /proc/cpuinfo for Hardware or Model
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("Model"):
                            return line.split(":", 1)[1].strip()
                        elif line.startswith("Hardware"):
                            return f"Raspberry Pi ({line.split(':', 1)[1].strip()})"
            except Exception:
                pass

        # Fallback for dev / host OS
        if platform.system() == "Windows":
            return f"Development Workstation ({platform.node()})"
        return f"{platform.system()} ({platform.machine()})"

    @staticmethod
    def get_os_info() -> dict:
        info = {
            "os": platform.system(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version()
        }

        # Check /etc/os-release on Linux
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["os"] = line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass
        elif platform.system() == "Windows":
            info["os"] = f"Windows {platform.version()}"

        return info

    @staticmethod
    def get_uptime() -> dict:
        boot_time = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_time)
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)

        formatted = ""
        if days > 0:
            formatted += f"{days}d "
        if hours > 0 or days > 0:
            formatted += f"{hours}h "
        formatted += f"{minutes}m {seconds}s"

        return {
            "seconds": uptime_seconds,
            "formatted": formatted,
            "boot_time": datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def get_primary_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def get_current_user() -> str:
        try:
            return os.getlogin()
        except Exception:
            return os.environ.get("USER", os.environ.get("USERNAME", "pi"))

    @staticmethod
    def get_cpu_temp() -> float:
        # 1. Try vcgencmd measure_temp
        if shutil.which("vcgencmd"):
            try:
                out = subprocess.check_output(["vcgencmd", "measure_temp"], timeout=2).decode("utf-8")
                # output format: temp=48.2'C
                if "temp=" in out:
                    temp_str = out.split("temp=")[1].split("'")[0]
                    return float(temp_str)
            except Exception:
                pass

        # 2. Try thermal_zone
        for tz_path in ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone1/temp"]:
            if os.path.exists(tz_path):
                try:
                    with open(tz_path, "r") as f:
                        val = float(f.read().strip())
                        return round(val / 1000.0, 1)
                except Exception:
                    pass

        # 3. Try psutil sensors_temperatures
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            return round(entries[0].current, 1)
        except Exception:
            pass

        # Fallback simulation for non-pi dev environment
        # Generate stable realistic value based on current CPU usage
        cpu_usage = psutil.cpu_percent(interval=None)
        return round(42.0 + (cpu_usage * 0.25), 1)

    @staticmethod
    def get_throttling_status() -> dict:
        """
        Parses vcgencmd get_throttled.
        Bitmask:
          0: under-voltage detected
          1: arm frequency capped
          2: currently throttled
          3: soft temperature limit active
          16: under-voltage has occurred
          17: arm frequency capping has occurred
          18: throttling has occurred
          19: soft temperature limit has occurred
        """
        status = {
            "available": False,
            "raw_hex": "0x0",
            "undervoltage_now": False,
            "freq_capped_now": False,
            "throttled_now": False,
            "soft_temp_limit_now": False,
            "undervoltage_past": False,
            "freq_capped_past": False,
            "throttled_past": False,
            "soft_temp_limit_past": False,
            "healthy": True,
            "messages": []
        }

        if shutil.which("vcgencmd"):
            try:
                out = subprocess.check_output(["vcgencmd", "get_throttled"], timeout=2).decode("utf-8").strip()
                # format: throttled=0x0
                if "throttled=" in out:
                    val_str = out.split("throttled=")[1].strip()
                    val = int(val_str, 16)
                    status["available"] = True
                    status["raw_hex"] = val_str
                    status["undervoltage_now"] = bool(val & 0x1)
                    status["freq_capped_now"] = bool(val & 0x2)
                    status["throttled_now"] = bool(val & 0x4)
                    status["soft_temp_limit_now"] = bool(val & 0x8)
                    status["undervoltage_past"] = bool(val & 0x10000)
                    status["freq_capped_past"] = bool(val & 0x20000)
                    status["throttled_past"] = bool(val & 0x40000)
                    status["soft_temp_limit_past"] = bool(val & 0x80000)

                    if status["undervoltage_now"]:
                        status["messages"].append("Active under-voltage detected! Check power supply.")
                        status["healthy"] = False
                    elif status["undervoltage_past"]:
                        status["messages"].append("Under-voltage occurred previously.")

                    if status["throttled_now"]:
                        status["messages"].append("CPU is currently thermal throttling.")
                        status["healthy"] = False
                    elif status["throttled_past"]:
                        status["messages"].append("CPU thermal throttling occurred previously.")

                    if status["freq_capped_now"]:
                        status["messages"].append("ARM frequency is currently capped.")
                    return status
            except Exception:
                pass

        # If vcgencmd is not available, we report healthy fallback
        status["messages"].append("vcgencmd not present; hardware throttling telemetry unavailable")
        return status

    @staticmethod
    def get_overall_health() -> dict:
        temp = SystemService.get_cpu_temp()
        throttling = SystemService.get_throttling_status()
        
        # Disk usage check
        root_usage = psutil.disk_usage("/" if os.name != "nt" else "C:\\")
        disk_healthy = root_usage.percent < 90.0

        items = []
        # Temperature
        if temp < 70.0:
            items.append({"title": "CPU Temperature", "status": "normal", "text": f"{temp}°C (Normal)"})
        elif temp < 80.0:
            items.append({"title": "CPU Temperature", "status": "warning", "text": f"{temp}°C (Elevated)"})
        else:
            items.append({"title": "CPU Temperature", "status": "critical", "text": f"{temp}°C (Critical Throttling Risk)"})

        # Voltage
        if throttling["undervoltage_now"]:
            items.append({"title": "Power / Voltage", "status": "critical", "text": "Under-voltage detected!"})
        elif throttling["undervoltage_past"]:
            items.append({"title": "Power / Voltage", "status": "warning", "text": "Past under-voltage recorded"})
        else:
            items.append({"title": "Power / Voltage", "status": "normal", "text": "Stable (No under-voltage)"})

        # Throttling
        if throttling["throttled_now"]:
            items.append({"title": "CPU Throttling", "status": "critical", "text": "Active thermal throttling"})
        elif throttling["throttled_past"]:
            items.append({"title": "CPU Throttling", "status": "warning", "text": "Past throttling recorded"})
        else:
            items.append({"title": "CPU Throttling", "status": "normal", "text": "No throttling"})

        # Storage
        if root_usage.percent < 75.0:
            items.append({"title": "Storage Health", "status": "normal", "text": f"{root_usage.percent}% used (Healthy)"})
        elif root_usage.percent < 90.0:
            items.append({"title": "Storage Health", "status": "warning", "text": f"{root_usage.percent}% used (High)"})
        else:
            items.append({"title": "Storage Health", "status": "critical", "text": f"{root_usage.percent}% used (Nearly Full)"})

        is_critical = any(x["status"] == "critical" for x in items)
        is_warning = any(x["status"] == "warning" for x in items)

        overall_state = "critical" if is_critical else ("warning" if is_warning else "normal")

        return {
            "overall_state": overall_state,
            "temp_celsius": temp,
            "throttling": throttling,
            "indicators": items,
            "items": items
        }

    @staticmethod
    def get_system_summary() -> dict:
        os_info = SystemService.get_os_info()
        uptime = SystemService.get_uptime()
        health = SystemService.get_overall_health()

        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)
        root_usage = psutil.disk_usage("/" if os.name != "nt" else "C:\\")

        return {
            "hostname": SystemService.get_hostname(),
            "model": SystemService.get_model(),
            "os": os_info["os"],
            "kernel": os_info["kernel"],
            "architecture": os_info["architecture"],
            "uptime": uptime["formatted"],
            "uptime_seconds": uptime["seconds"],
            "ip_address": SystemService.get_primary_ip(),
            "current_user": SystemService.get_current_user(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "health": health,
            "quick_metrics": {
                "cpu_percent": cpu_pct,
                "ram_percent": vm.percent,
                "ram_used_mb": round(vm.used / (1024 * 1024), 1),
                "ram_total_mb": round(vm.total / (1024 * 1024), 1),
                "disk_percent": root_usage.percent,
                "temp_celsius": health["temp_celsius"]
            }
        }

    @staticmethod
    def reboot() -> tuple[bool, str]:
        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "reboot"], check=True, timeout=5)
                return True, "Reboot initiated via systemctl"
            except Exception as e:
                return False, f"Failed to reboot: {e}"
        return True, "Reboot simulation (development mode)"

    @staticmethod
    def shutdown() -> tuple[bool, str]:
        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "poweroff"], check=True, timeout=5)
                return True, "Poweroff initiated via systemctl"
            except Exception as e:
                return False, f"Failed to shutdown: {e}"
        return True, "Shutdown simulation (development mode)"

    @staticmethod
    def check_updates() -> dict:
        result = {
            "available": False,
            "updates_count": 0,
            "packages": [],
            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if shutil.which("apt-get"):
            try:
                cmd = ["apt-get", "-s", "upgrade"]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                lines = proc.stdout.splitlines()
                pkgs = []
                for line in lines:
                    if line.startswith("Inst "):
                        pkgs.append(line.split()[1])
                result["available"] = len(pkgs) > 0
                result["updates_count"] = len(pkgs)
                result["packages"] = pkgs[:50]
                return result
            except Exception:
                pass

        return result
