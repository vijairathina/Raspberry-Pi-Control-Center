import shutil
import subprocess
import json

# Fallback mock containers
_mock_containers = [
    {
        "id": "c7a8b9d0e1f2",
        "name": "homeassistant",
        "image": "ghcr.io/home-assistant/home-assistant:stable",
        "status": "Up 3 days",
        "state": "running",
        "cpu_percent": "1.8%",
        "memory": "142 MB / 1024 MB",
        "ports": "8123:8123/tcp"
    },
    {
        "id": "e3f4a5b6c7d8",
        "name": "pihole",
        "image": "pihole/pihole:latest",
        "status": "Up 3 days",
        "state": "running",
        "cpu_percent": "0.4%",
        "memory": "48 MB / 1024 MB",
        "ports": "53:53/udp, 8080:80/tcp"
    },
    {
        "id": "a1b2c3d4e5f6",
        "name": "node-red",
        "image": "nodered/node-red:latest",
        "status": "Exited (0) 2 hours ago",
        "state": "exited",
        "cpu_percent": "0.0%",
        "memory": "0 MB",
        "ports": "1880:1880/tcp"
    }
]

class DockerManager:
    @staticmethod
    def is_installed() -> bool:
        return shutil.which("docker") is not None

    @staticmethod
    def get_containers() -> dict:
        if DockerManager.is_installed():
            try:
                cmd = ["docker", "ps", "-a", "--format", "{{json .}}"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    containers = []
                    for line in res.stdout.splitlines():
                        if not line.strip():
                            continue
                        try:
                            item = json.loads(line)
                            containers.append({
                                "id": item.get("ID", "")[:12],
                                "name": item.get("Names", ""),
                                "image": item.get("Image", ""),
                                "status": item.get("Status", ""),
                                "state": item.get("State", "running" if "Up" in item.get("Status", "") else "exited"),
                                "cpu_percent": "N/A",
                                "memory": "N/A",
                                "ports": item.get("Ports", "")
                            })
                        except Exception:
                            pass
                    return {
                        "installed": True,
                        "containers": containers
                    }
            except Exception:
                pass

        return {
            "installed": DockerManager.is_installed(),
            "containers": _mock_containers
        }

    @staticmethod
    def control_container(container_id: str, action: str) -> tuple[bool, str]:
        if action not in ("start", "stop", "restart"):
            return False, "Invalid container action"

        if DockerManager.is_installed():
            try:
                res = subprocess.run(["docker", action, container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                if res.returncode == 0:
                    return True, f"Container {container_id} {action}ed successfully"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)

        # Mock update
        for c in _mock_containers:
            if c["id"] == container_id or c["name"] == container_id:
                if action == "start":
                    c["state"] = "running"
                    c["status"] = "Up Just now"
                elif action == "stop":
                    c["state"] = "exited"
                    c["status"] = "Exited Just now"
                elif action == "restart":
                    c["state"] = "running"
                    c["status"] = "Up Just now"
                return True, f"Container {container_id} {action}ed (Mock)"

        return True, f"Container action simulated: {action}"

    @staticmethod
    def get_container_logs(container_id: str, lines: int = 100) -> str:
        lines = max(10, min(lines, 500))
        if DockerManager.is_installed():
            try:
                res = subprocess.run(["docker", "logs", "--tail", str(lines), container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                return res.stdout or res.stderr or "No logs found"
            except Exception as e:
                return f"Error reading logs: {e}"

        return f"[MOCK LOGS] Container {container_id}\nTimestamp: 2026-09-26 12:00:00 - Service starting\nTimestamp: 2026-09-26 12:00:01 - Listening on port 80/tcp\nTimestamp: 2026-09-26 12:00:05 - Ready for incoming connections"
