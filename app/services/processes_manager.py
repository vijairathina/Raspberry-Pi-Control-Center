import os
import psutil

CRITICAL_PIDS = {1}
CRITICAL_NAMES = {"systemd", "init", "sshd", "ssh", "svchost.exe", "csrss.exe", "services.exe", "wininit.exe"}

class ProcessManager:
    @staticmethod
    def get_current_pid() -> int:
        return os.getpid()

    @staticmethod
    def is_protected(proc_info: dict) -> bool:
        pid = proc_info.get("pid")
        name = (proc_info.get("name") or "").lower()
        if pid in CRITICAL_PIDS or pid == ProcessManager.get_current_pid():
            return True
        if name in CRITICAL_NAMES:
            return True
        return False

    @staticmethod
    def list_processes(sort_by: str = "cpu", reverse: bool = True, search: str = "") -> list[dict]:
        processes = []
        current_pid = ProcessManager.get_current_pid()

        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = p.info
                name = info.get("name") or "Unknown"
                if search:
                    q = search.lower()
                    if q not in name.lower() and q not in str(info.get("pid")):
                        continue

                is_critical = (info.get("pid") in CRITICAL_PIDS or 
                               info.get("pid") == current_pid or 
                               name.lower() in CRITICAL_NAMES)

                processes.append({
                    "pid": info.get("pid"),
                    "name": name,
                    "user": info.get("username") or "system",
                    "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                    "memory_percent": round(info.get("memory_percent") or 0.0, 1),
                    "status": info.get("status") or "running",
                    "is_protected": is_critical
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort
        sort_key_map = {
            "cpu": lambda x: x["cpu_percent"],
            "ram": lambda x: x["memory_percent"],
            "pid": lambda x: x["pid"],
            "name": lambda x: x["name"].lower()
        }
        key_func = sort_key_map.get(sort_by, sort_key_map["cpu"])
        processes.sort(key=key_func, reverse=reverse)

        return processes[:150] # Top 150 processes for lightweight performance

    @staticmethod
    def kill_process(pid: int, force: bool = False) -> tuple[bool, str]:
        if pid in CRITICAL_PIDS or pid == ProcessManager.get_current_pid():
            return False, f"Process {pid} is system-critical and cannot be terminated"

        try:
            p = psutil.Process(pid)
            name = p.name()
            if name.lower() in CRITICAL_NAMES:
                return False, f"Process {name} (PID {pid}) is protected"

            if force:
                p.kill()
                return True, f"Sent SIGKILL to process {name} (PID {pid})"
            else:
                p.terminate()
                return True, f"Sent SIGTERM to process {name} (PID {pid})"
        except psutil.NoSuchProcess:
            return False, f"Process PID {pid} does not exist"
        except psutil.AccessDenied:
            return False, f"Access denied when trying to terminate PID {pid}"
        except Exception as e:
            return False, f"Failed to terminate PID {pid}: {e}"
