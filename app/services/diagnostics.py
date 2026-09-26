import re
import socket
import subprocess
import shutil
import time
import threading
from datetime import datetime, timedelta
from app.database import get_db

HOST_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

class DiagnosticsService:
    @staticmethod
    def is_safe_host(host: str) -> bool:
        if not host or len(host) > 255:
            return False
        return bool(HOST_REGEX.match(host))

    @staticmethod
    def get_default_gateway() -> str:
        # Determine default gateway
        try:
            # Connect socket to external to find outgoing route
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            # Often gateway is .1
            parts = local_ip.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.1"
        except Exception:
            pass
        return "192.168.1.1"

    @staticmethod
    def ping_host(host: str, count: int = 2, timeout_sec: int = 2) -> dict:
        if not DiagnosticsService.is_safe_host(host):
            return {"success": False, "host": host, "error": "Invalid host syntax"}

        count = max(1, min(count, 4))
        # Use platform ping
        param_count = "-n" if shutil.which("ping") and subprocess.os.name == "nt" else "-c"
        param_timeout = "-w" if subprocess.os.name == "nt" else "-W"

        cmd = ["ping", param_count, str(count), param_timeout, str(timeout_sec * 1000 if subprocess.os.name == "nt" else timeout_sec), host]
        
        start_t = time.time()
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec * count + 2)
            elapsed_ms = round((time.time() - start_t) * 1000, 1)

            if res.returncode == 0:
                # Parse average latency if possible
                latency_ms = DiagnosticsService._parse_latency(res.stdout) or round(elapsed_ms / count, 1)
                return {
                    "success": True,
                    "host": host,
                    "latency_ms": latency_ms,
                    "packet_loss_percent": 0.0,
                    "raw_output": res.stdout
                }
            else:
                return {
                    "success": False,
                    "host": host,
                    "latency_ms": None,
                    "packet_loss_percent": 100.0,
                    "error": "Destination unreachable or timed out"
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "host": host, "latency_ms": None, "packet_loss_percent": 100.0, "error": "Ping timed out"}
        except Exception as e:
            return {"success": False, "host": host, "latency_ms": None, "packet_loss_percent": 100.0, "error": str(e)}

    @staticmethod
    def _parse_latency(output: str) -> float | None:
        # Linux: rtt min/avg/max/mdev = 12.345/14.567/16.789/1.234 ms
        # Windows: Average = 14ms or Minimum = 12ms, Maximum = 16ms, Average = 14ms
        for line in output.splitlines():
            if "Average =" in line:
                try:
                    return float(line.split("Average =")[1].replace("ms", "").strip())
                except Exception:
                    pass
            elif "min/avg/max" in line:
                try:
                    avg_part = line.split("=")[1].split("/")[1]
                    return float(avg_part)
                except Exception:
                    pass
        return None

    @staticmethod
    def dns_lookup(domain: str) -> dict:
        if not DiagnosticsService.is_safe_host(domain):
            return {"success": False, "domain": domain, "error": "Invalid domain name"}

        start_t = time.time()
        try:
            name, aliases, ip_list = socket.gethostbyname_ex(domain)
            elapsed_ms = round((time.time() - start_t) * 1000, 1)
            return {
                "success": True,
                "domain": domain,
                "resolved_name": name,
                "ips": ip_list,
                "response_time_ms": elapsed_ms
            }
        except Exception as e:
            return {"success": False, "domain": domain, "error": str(e)}

    @staticmethod
    def traceroute(host: str, max_hops: int = 15) -> dict:
        if not DiagnosticsService.is_safe_host(host):
            return {"success": False, "host": host, "error": "Invalid host syntax"}

        max_hops = max(5, min(max_hops, 20))
        cmd = None

        if shutil.which("traceroute"):
            cmd = ["traceroute", "-m", str(max_hops), "-w", "2", host]
        elif shutil.which("tracert"):
            cmd = ["tracert", "-h", str(max_hops), "-w", "2000", host]

        if not cmd:
            return {"success": False, "host": host, "error": "Neither traceroute nor tracert utility is available on system"}

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            return {
                "success": res.returncode == 0,
                "host": host,
                "output": res.stdout or res.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "host": host, "error": "Traceroute exceeded 30s timeout"}
        except Exception as e:
            return {"success": False, "host": host, "error": str(e)}

    @staticmethod
    def run_connectivity_test() -> dict:
        gw = DiagnosticsService.get_default_gateway()
        gw_res = DiagnosticsService.ping_host(gw, count=1, timeout_sec=2)
        dns_res = DiagnosticsService.ping_host("1.1.1.1", count=1, timeout_sec=2)
        inet_res = DiagnosticsService.ping_host("8.8.8.8", count=1, timeout_sec=2)

        gw_lat = gw_res.get("latency_ms")
        dns_lat = dns_res.get("latency_ms")
        inet_lat = inet_res.get("latency_ms")

        is_connected = inet_res.get("success", False) or dns_res.get("success", False)
        status_text = "online" if is_connected else "offline"

        # Record to SQLite
        try:
            conn = get_db()
            with conn:
                conn.execute("""
                    INSERT INTO connectivity_history 
                    (gateway_latency, dns_latency, internet_latency, packet_loss, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (gw_lat, dns_lat, inet_lat, 0.0 if is_connected else 100.0, status_text))
        except Exception:
            pass

        return {
            "gateway": {"host": gw, "success": gw_res.get("success", False), "latency_ms": gw_lat},
            "dns": {"host": "1.1.1.1", "success": dns_res.get("success", False), "latency_ms": dns_lat},
            "internet": {"host": "8.8.8.8", "success": inet_res.get("success", False), "latency_ms": inet_lat},
            "status": status_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def check_internet_resilient() -> dict:
        """
        Resilient Internet Check:
        1. If first ping succeeds, 1 time is enough.
        2. If timeout/fail, retry up to 3 times before declaring offline.
        3. Push status to Home Assistant if configured.
        """
        from app.config import config
        from app.services.ha_service import HomeAssistantService

        mon_conf = config.get("internet_monitor", {})
        hosts = mon_conf.get("ping_hosts", ["8.8.8.8", "1.1.1.1"])
        timeout_sec = mon_conf.get("timeout_seconds", 2)
        max_retries = mon_conf.get("retry_on_timeout", 3)

        success = False
        latency = None
        successful_host = None
        attempts_used = 0

        for host in hosts:
            for attempt in range(1, max_retries + 1):
                attempts_used += 1
                res = DiagnosticsService.ping_host(host, count=1, timeout_sec=timeout_sec)
                if res.get("success"):
                    success = True
                    latency = res.get("latency_ms")
                    successful_host = host
                    break  # 1 time enough if successful!
            if success:
                break

        status_text = "online" if success else "offline"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Record to SQLite history
        try:
            conn = get_db()
            with conn:
                conn.execute("""
                    INSERT INTO connectivity_history 
                    (gateway_latency, dns_latency, internet_latency, packet_loss, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (None, None, latency, 0.0 if success else 100.0, status_text))
        except Exception:
            pass

        # Send to Home Assistant
        if mon_conf.get("send_to_ha", True) and HomeAssistantService.is_enabled():
            sensor_id = config.get("home_assistant", {}).get("sensor_entity_id", "sensor.rpi_internet_status")
            HomeAssistantService.update_sensor(sensor_id, status_text, {
                "latency_ms": latency or 0.0,
                "ping_host": successful_host or hosts[0],
                "attempts_used": attempts_used,
                "last_checked": timestamp,
                "friendly_name": "Raspberry Pi Internet Connectivity"
            })

            # Check if state changed to trigger an HA notification
            global _last_known_status
            if '_last_known_status' in globals() and _last_known_status != status_text:
                if status_text == "offline":
                    HomeAssistantService.send_notification(
                        "🚨 Raspberry Pi Internet Disconnected",
                        f"Internet check timed out after {attempts_used} ping attempts on {hosts}. The Pi may be offline."
                    )
                elif status_text == "online" and _last_known_status == "offline":
                    HomeAssistantService.send_notification(
                        "✅ Raspberry Pi Internet Restored",
                        f"Internet connectivity is back online ({latency} ms latency to {successful_host})."
                    )

        globals()['_last_known_status'] = status_text

        return {
            "status": status_text,
            "latency_ms": latency,
            "host": successful_host or hosts[0],
            "attempts": attempts_used,
            "timestamp": timestamp
        }

    @staticmethod
    def start_internet_monitor_loop():
        global _internet_monitor_started
        if globals().get('_internet_monitor_started'):
            return
        globals()['_internet_monitor_started'] = True

        def monitor_worker():
            from app.config import config
            while True:
                try:
                    mon_conf = config.get("internet_monitor", {})
                    if mon_conf.get("enabled", True):
                        DiagnosticsService.check_internet_resilient()
                    interval = mon_conf.get("interval_seconds", 60)
                except Exception as e:
                    print(f"Internet monitor error: {e}")
                    interval = 60
                time.sleep(max(10, interval))

        t = threading.Thread(target=monitor_worker, daemon=True)
        t.start()

    @staticmethod
    def get_connectivity_stats(hours: int = 1) -> dict:
        hours = max(1, min(hours, 48))
        since_time = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        cursor = conn.execute("""
            SELECT timestamp, gateway_latency, dns_latency, internet_latency, packet_loss, status
            FROM connectivity_history
            WHERE timestamp >= ?
            ORDER BY id ASC
        """, (since_time,))
        rows = cursor.fetchall()

        if not rows:
            # Return current baseline
            now_res = DiagnosticsService.run_connectivity_test()
            return {
                "uptime_percent": 100.0,
                "packet_loss_avg": 0.0,
                "avg_latency_ms": now_res["internet"]["latency_ms"] or 20.0,
                "last_failure": "None recorded",
                "last_recovery": "Active",
                "history": [{
                    "time": now_res["timestamp"].split()[1],
                    "latency": now_res["internet"]["latency_ms"] or 20.0,
                    "status": "online"
                }]
            }

        total_tests = len(rows)
        online_count = sum(1 for r in rows if r["status"] == "online")
        uptime_pct = round((online_count / total_tests) * 100.0, 1)

        latencies = [r["internet_latency"] for r in rows if r["internet_latency"] is not None]
        avg_lat = round(sum(latencies) / len(latencies), 1) if latencies else 0.0

        last_failure = "None"
        last_recovery = "None"
        for r in rows:
            if r["status"] == "offline":
                last_failure = r["timestamp"]
            elif r["status"] == "online" and last_failure != "None":
                last_recovery = r["timestamp"]

        history_pts = []
        for r in rows[-30:]:
            history_pts.append({
                "time": r["timestamp"].split()[1] if " " in r["timestamp"] else r["timestamp"],
                "latency": r["internet_latency"] or 0.0,
                "status": r["status"]
            })

        return {
            "uptime_percent": uptime_pct,
            "packet_loss_avg": round(100.0 - uptime_pct, 1),
            "avg_latency_ms": avg_lat,
            "last_failure": last_failure,
            "last_recovery": last_recovery,
            "history": history_pts
        }
