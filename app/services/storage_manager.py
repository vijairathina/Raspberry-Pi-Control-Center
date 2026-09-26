import os
import shutil
import subprocess
import json
import psutil

class StorageManager:
    @staticmethod
    def get_mounted_filesystems(warning_threshold: float = 75.0, critical_threshold: float = 90.0) -> list[dict]:
        results = []
        partitions = psutil.disk_partitions(all=False)
        seen_mounts = set()

        for p in partitions:
            # Skip duplicate or pseudo mounts
            if p.mountpoint in seen_mounts:
                continue
            seen_mounts.add(p.mountpoint)

            try:
                usage = psutil.disk_usage(p.mountpoint)
                pct = usage.percent

                status = "normal"
                if pct >= critical_threshold:
                    status = "critical"
                elif pct >= warning_threshold:
                    status = "warning"

                results.append({
                    "device": p.device,
                    "mount": p.mountpoint,
                    "fstype": p.fstype,
                    "opts": p.opts,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "percent": pct,
                    "status": status
                })
            except (PermissionError, OSError):
                continue

        return results

    @staticmethod
    def get_disk_hardware_info() -> list[dict]:
        """
        Gathers hardware disk info (SD card, USB, SSD, NVMe) using lsblk where available.
        """
        disks = []
        if shutil.which("lsblk"):
            try:
                # lsblk in JSON format
                cmd = ["lsblk", "-J", "-b", "-o", "NAME,MODEL,SIZE,FSTYPE,MOUNTPOINT,ROTA,TYPE,TRAN"]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    for block in data.get("blockdevices", []):
                        size_bytes = int(block.get("size") or 0)
                        size_gb = round(size_bytes / (1024 ** 3), 2)
                        name = block.get("name", "")
                        dtype = block.get("type", "disk")

                        # Determine media type (SD Card is typically mmcblk0)
                        media_type = "Generic Disk"
                        if "mmcblk" in name:
                            media_type = "SD Card (eMMC/MicroSD)"
                        elif block.get("tran") == "usb":
                            media_type = "USB Storage"
                        elif "nvme" in name:
                            media_type = "NVMe SSD"
                        elif block.get("rota") == "0":
                            media_type = "SSD"
                        elif block.get("rota") == "1":
                            media_type = "HDD"

                        disks.append({
                            "device": f"/dev/{name}",
                            "model": block.get("model") or media_type,
                            "type": media_type,
                            "size_gb": size_gb,
                            "fstype": block.get("fstype") or "partitioned",
                            "mountpoint": block.get("mountpoint") or "Multiple / Not mounted",
                            "smart_supported": False,
                            "health": "Healthy"
                        })
                    return disks
            except Exception:
                pass

        # Fallback for Windows / dev
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "device": p.device,
                    "model": f"Storage Drive ({p.fstype.upper()})",
                    "type": "System / External Disk",
                    "size_gb": round(usage.total / (1024 ** 3), 2),
                    "fstype": p.fstype,
                    "mountpoint": p.mountpoint,
                    "smart_supported": False,
                    "health": "Healthy"
                })
            except Exception:
                pass

        return disks
