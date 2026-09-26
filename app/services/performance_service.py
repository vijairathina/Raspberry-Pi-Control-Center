import time
import os
import psutil
from collections import deque
from app.services.system_service import SystemService

# Circular buffers for real-time history (keeps last 60 data points, 1 per second or poll)
MAX_HISTORY = 60
_history_lock = False
_cpu_history = deque(maxlen=MAX_HISTORY)
_ram_history = deque(maxlen=MAX_HISTORY)
_net_rx_history = deque(maxlen=MAX_HISTORY)
_net_tx_history = deque(maxlen=MAX_HISTORY)
_timestamps = deque(maxlen=MAX_HISTORY)

_last_net_io = None
_last_net_time = None

class PerformanceService:
    @staticmethod
    def get_metrics() -> dict:
        global _last_net_io, _last_net_time
        now_ts = time.time()
        time_label = time.strftime("%H:%M:%S", time.localtime(now_ts))

        # CPU Metrics
        overall_cpu = psutil.cpu_percent(interval=None)
        per_core_cpu = psutil.cpu_percent(interval=None, percpu=True)
        
        freq_info = psutil.cpu_freq()
        cur_freq_mhz = round(freq_info.current, 1) if freq_info else 0.0

        # Load average (Linux/Unix has 3 values, Windows fallback)
        if hasattr(os, "getloadavg"):
            load_avg = [round(x, 2) for x in os.getloadavg()]
        else:
            load_avg = [round(overall_cpu / 100.0 * (len(per_core_cpu) or 1), 2), 0.0, 0.0]

        temp = SystemService.get_cpu_temp()

        # RAM Metrics
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        ram_info = {
            "total_bytes": vm.total,
            "used_bytes": vm.used,
            "available_bytes": vm.available,
            "cached_bytes": getattr(vm, "cached", 0),
            "free_bytes": vm.free,
            "percent": vm.percent,
            "total_mb": round(vm.total / (1024 * 1024), 1),
            "used_mb": round(vm.used / (1024 * 1024), 1),
            "available_mb": round(vm.available / (1024 * 1024), 1),
            "cached_mb": round(getattr(vm, "cached", 0) / (1024 * 1024), 1),
            "swap_total_mb": round(swap.total / (1024 * 1024), 1),
            "swap_used_mb": round(swap.used / (1024 * 1024), 1),
            "swap_percent": swap.percent
        }

        # Storage Metrics (Root partition)
        root_path = "/" if os.name != "nt" else "C:\\"
        disk = psutil.disk_usage(root_path)
        storage_info = {
            "mount": root_path,
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "percent": disk.percent,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
        }

        # Network Metrics
        net_io = psutil.net_io_counters()
        rx_speed_kbps = 0.0
        tx_speed_kbps = 0.0

        if _last_net_io is not None and _last_net_time is not None:
            time_diff = max(now_ts - _last_net_time, 0.1)
            bytes_recv_diff = max(net_io.bytes_recv - _last_net_io.bytes_recv, 0)
            bytes_sent_diff = max(net_io.bytes_sent - _last_net_io.bytes_sent, 0)
            rx_speed_kbps = round((bytes_recv_diff / 1024.0) / time_diff, 1)
            tx_speed_kbps = round((bytes_sent_diff / 1024.0) / time_diff, 1)

        _last_net_io = net_io
        _last_net_time = now_ts

        network_info = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errin": net_io.errin,
            "errout": net_io.errout,
            "dropin": net_io.dropin,
            "dropout": net_io.dropout,
            "rx_speed_kbps": rx_speed_kbps,
            "tx_speed_kbps": tx_speed_kbps,
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 * 1024), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 * 1024), 2)
        }

        # Append to historical buffer
        _timestamps.append(time_label)
        _cpu_history.append(overall_cpu)
        _ram_history.append(vm.percent)
        _net_rx_history.append(rx_speed_kbps)
        _net_tx_history.append(tx_speed_kbps)

        return {
            "timestamp": time_label,
            "cpu": {
                "overall_percent": overall_cpu,
                "per_core_percent": per_core_cpu,
                "core_count": len(per_core_cpu),
                "frequency_mhz": cur_freq_mhz,
                "load_avg": load_avg,
                "temperature_celsius": temp
            },
            "ram": ram_info,
            "storage": storage_info,
            "network": network_info,
            "history": {
                "timestamps": list(_timestamps),
                "cpu": list(_cpu_history),
                "ram": list(_ram_history),
                "net_rx": list(_net_rx_history),
                "net_tx": list(_net_tx_history)
            }
        }
