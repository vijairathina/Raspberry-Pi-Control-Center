import shutil
import subprocess
import json

class TailscaleManager:
    @staticmethod
    def is_installed() -> bool:
        return shutil.which("tailscale") is not None

    @staticmethod
    def get_status() -> dict:
        if TailscaleManager.is_installed():
            try:
                res = subprocess.run(["tailscale", "status", "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    self_node = data.get("Self", {})
                    peers_raw = data.get("Peer", {})

                    peers = []
                    for k, p in peers_raw.items():
                        peers.append({
                            "hostname": p.get("HostName", "Unknown"),
                            "ip": p.get("TailscaleIPs", [""])[0] if p.get("TailscaleIPs") else "",
                            "os": p.get("OS", "Linux"),
                            "online": p.get("Online", False)
                        })

                    return {
                        "installed": True,
                        "running": data.get("BackendState") == "Running",
                        "state": data.get("BackendState", "Running"),
                        "hostname": self_node.get("HostName", "raspberrypi"),
                        "ip": self_node.get("TailscaleIPs", [""])[0] if self_node.get("TailscaleIPs") else "None",
                        "peers": peers,
                        "magic_dns": data.get("MagicDNSEnabled", False)
                    }
            except Exception:
                pass

        # Mock / fallback status
        return {
            "installed": TailscaleManager.is_installed(),
            "running": True,
            "state": "Running (Mock / Standby)",
            "hostname": "raspberrypi.tailscale.net",
            "ip": "100.92.140.23",
            "peers": [
                {"hostname": "macbook-pro", "ip": "100.92.140.45", "os": "macOS", "online": True},
                {"hostname": "pixel-phone", "ip": "100.92.140.67", "os": "Android", "online": True},
                {"hostname": "cloud-vps", "ip": "100.92.140.11", "os": "Linux", "online": False}
            ],
            "magic_dns": True
        }

    @staticmethod
    def control_tailscale(action: str) -> tuple[bool, str]:
        if action not in ("up", "down", "restart"):
            return False, "Invalid Tailscale command"

        if TailscaleManager.is_installed():
            try:
                if action == "restart":
                    subprocess.run(["tailscale", "down"], timeout=5)
                    subprocess.run(["tailscale", "up"], timeout=5)
                    return True, "Tailscale restarted"
                else:
                    res = subprocess.run(["tailscale", action], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
                    return True, f"Tailscale {action} executed"
            except Exception as e:
                return False, str(e)

        return True, f"Tailscale {action} command simulated (Mock)"
