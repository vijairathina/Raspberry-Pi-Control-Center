import os
import sys
import shutil
import subprocess
import time
import socket
import ipaddress
import threading
import psutil

# Active temporary block status
_temp_blocks = {}
_temp_blocks_lock = threading.Lock()

class NetworkManager:
    @staticmethod
    def get_interfaces() -> list[dict]:
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)

        for iface, addr_list in addrs.items():
            ipv4 = ""
            netmask = ""
            mac = ""
            for a in addr_list:
                if a.family == socket.AF_INET:
                    ipv4 = a.address
                    netmask = a.netmask
                elif hasattr(socket, "AF_PACKET") and a.family == socket.AF_PACKET:
                    mac = a.address
                elif hasattr(psutil, "AF_LINK") and a.family == psutil.AF_LINK:
                    mac = a.address

            st = stats.get(iface)
            is_up = st.isup if st else False
            speed = st.speed if st else 0
            mtu = st.mtu if st else 1500

            io = io_counters.get(iface)
            rx_bytes = io.bytes_recv if io else 0
            tx_bytes = io.bytes_sent if io else 0

            # Check if temporary block is active
            block_info = _temp_blocks.get(iface)
            block_active = False
            remaining_seconds = 0
            if block_info:
                rem = int(block_info["expires_at"] - time.time())
                if rem > 0:
                    block_active = True
                    remaining_seconds = rem
                else:
                    with _temp_blocks_lock:
                        _temp_blocks.pop(iface, None)

            interfaces.append({
                "name": iface,
                "is_up": is_up,
                "ip": ipv4 or "None",
                "netmask": netmask or "None",
                "mac": mac or "Unknown",
                "speed_mbps": speed,
                "mtu": mtu,
                "rx_mb": round(rx_bytes / (1024 * 1024), 2),
                "tx_mb": round(tx_bytes / (1024 * 1024), 2),
                "is_temp_blocked": block_active,
                "remaining_block_seconds": remaining_seconds
            })

        return interfaces

    @staticmethod
    def is_client_on_interface(iface: str, client_ip: str) -> bool:
        """
        Safety check: Checks if client_ip belongs to this interface's network,
        warning against accidental browser lockout.
        """
        if not client_ip or client_ip in ("127.0.0.1", "localhost", "::1"):
            # Localhost connection
            return iface in ("lo", "Loopback Pseudo-Interface 1")

        try:
            client_addr = ipaddress.ip_address(client_ip)
            addrs = psutil.net_if_addrs().get(iface, [])
            for a in addrs:
                if a.family == socket.AF_INET and a.address and a.netmask:
                    net = ipaddress.ip_network(f"{a.address}/{a.netmask}", strict=False)
                    if client_addr in net:
                        return True
        except Exception:
            pass
        return False

    @staticmethod
    def set_interface_state(iface: str, state: str) -> tuple[bool, str]:
        # state: 'up' or 'down'
        if state not in ("up", "down"):
            return False, "Invalid state"

        if shutil.which("ip"):
            try:
                res = subprocess.run(["ip", "link", "set", iface, state], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if res.returncode == 0:
                    return True, f"Interface {iface} turned {state}"
                return False, res.stderr.strip()
            except Exception as e:
                return False, str(e)
        elif shutil.which("nmcli"):
            try:
                action = "connect" if state == "up" else "disconnect"
                res = subprocess.run(["nmcli", "dev", action, iface], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                return True, f"Interface {iface} set to {state}"
            except Exception as e:
                return False, str(e)

        return True, f"Interface {iface} set to {state} (Mock)"

    @staticmethod
    def renew_dhcp(iface: str) -> tuple[bool, str]:
        if shutil.which("dhclient"):
            try:
                subprocess.run(["dhclient", "-r", iface], timeout=5)
                subprocess.run(["dhclient", iface], timeout=10)
                return True, f"DHCP lease renewed on {iface}"
            except Exception as e:
                return False, str(e)
        elif shutil.which("nmcli"):
            try:
                subprocess.run(["nmcli", "dev", "reapply", iface], timeout=5)
                return True, f"DHCP re-applied on {iface}"
            except Exception as e:
                return False, str(e)

        return True, f"DHCP lease renewed on {iface} (Mock)"

    @staticmethod
    def schedule_temporary_disable(iface: str, duration_seconds: int, client_ip: str = "") -> dict:
        """
        Temporary Network Disable:
        CRITICAL SAFETY RULE:
        1. Schedule rollback task BEFORE disabling.
        2. Use systemd-run or independent background daemon thread.
        3. Record state and countdown.
        4. User can restore immediately at any time.
        """
        if duration_seconds < 10 or duration_seconds > 86400:
            return {"success": False, "message": "Duration must be between 10 seconds and 24 hours"}

        # Safety lockout warning check
        is_current_connection = NetworkManager.is_client_on_interface(iface, client_ip)

        # 1. Schedule restoration first!
        # If systemd-run is available, use it so it survives Flask restart
        if shutil.which("systemd-run") and shutil.which("ip"):
            try:
                timer_str = f"{duration_seconds}s"
                subprocess.run([
                    "systemd-run",
                    f"--on-active={timer_str}",
                    "--unit=rpi-net-restore",
                    "ip", "link", "set", iface, "up"
                ], timeout=5)
            except Exception:
                pass

        # Also run python background timer as internal tracker
        def restore_worker():
            time.sleep(duration_seconds)
            with _temp_blocks_lock:
                _temp_blocks.pop(iface, None)
            NetworkManager.set_interface_state(iface, "up")

        t = threading.Thread(target=restore_worker, daemon=True)
        t.start()

        expires_at = time.time() + duration_seconds
        with _temp_blocks_lock:
            _temp_blocks[iface] = {
                "expires_at": expires_at,
                "duration": duration_seconds,
                "timer_thread": t
            }

        # 2. Now disable the interface
        success, msg = NetworkManager.set_interface_state(iface, "down")

        return {
            "success": success,
            "message": f"Interface {iface} temporarily disabled for {duration_seconds}s. Auto-restore scheduled.",
            "is_current_connection": is_current_connection,
            "expires_at": expires_at,
            "remaining_seconds": duration_seconds
        }

    @staticmethod
    def restore_temporary_disable(iface: str) -> tuple[bool, str]:
        with _temp_blocks_lock:
            _temp_blocks.pop(iface, None)

        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "stop", "rpi-net-restore.timer"], timeout=2)
            except Exception:
                pass

        return NetworkManager.set_interface_state(iface, "up")

    @staticmethod
    def get_listening_ports() -> list[dict]:
        """
        Lists local listening TCP/UDP ports using psutil.net_connections.
        Monitoring only, safe and non-intrusive.
        """
        ports = []
        try:
            conns = psutil.net_connections(kind='inet')
            for c in conns:
                if c.status == psutil.CONN_LISTEN or c.type == socket.SOCK_DGRAM:
                    laddr = f"{c.laddr.ip}:{c.laddr.port}"
                    proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                    proc_name = "Unknown"
                    if c.pid:
                        try:
                            proc_name = psutil.Process(c.pid).name()
                        except Exception:
                            pass

                    # Common friendly service naming
                    port = c.laddr.port
                    label = ""
                    if port == 22:
                        label = "SSH"
                    elif port == 5000:
                        label = "Raspberry Pi Control Center (Flask)"
                    elif port == 80:
                        label = "HTTP (Web)"
                    elif port == 443:
                        label = "HTTPS (SSL)"
                    elif port == 1883:
                        label = "MQTT Broker"
                    elif port == 3000:
                        label = "Grafana"
                    elif port == 53:
                        label = "DNS / Pi-hole"

                    ports.append({
                        "port": port,
                        "protocol": proto,
                        "process": proc_name,
                        "pid": c.pid or 0,
                        "address": laddr,
                        "service_label": label
                    })
        except Exception:
            pass

        return sorted(ports, key=lambda x: x["port"])

    @staticmethod
    def get_firewall_status() -> dict:
        """
        Detects ufw, iptables, or nftables. Read-only informational overview.
        """
        status = {
            "type": "None detected",
            "enabled": False,
            "default_policy": "Allow / Unrestricted",
            "rules": []
        }

        # Check ufw
        if shutil.which("ufw"):
            try:
                res = subprocess.run(["ufw", "status", "numbered"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                if "Status: active" in res.stdout:
                    status["type"] = "UFW (Uncomplicated Firewall)"
                    status["enabled"] = True
                    status["default_policy"] = "Deny (incoming), Allow (outgoing)"
                    rules = []
                    for line in res.stdout.splitlines():
                        if "[" in line and "]" in line:
                            rules.append(line.strip())
                    status["rules"] = rules
                    return status
                elif "Status: inactive" in res.stdout:
                    status["type"] = "UFW (Uncomplicated Firewall)"
                    status["enabled"] = False
                    status["default_policy"] = "Inactive"
                    return status
            except Exception:
                pass

        # Check iptables
        if shutil.which("iptables"):
            try:
                res = subprocess.run(["iptables", "-L", "-n", "--line-numbers"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                if res.returncode == 0:
                    status["type"] = "iptables / Netfilter"
                    status["enabled"] = True
                    status["default_policy"] = "ACCEPT (Default)"
                    status["rules"] = [l.strip() for l in res.stdout.splitlines()[:20] if l.strip()]
                    return status
            except Exception:
                pass

        # Emulated / Mock firewall status
        status["type"] = "Standard Linux IP Stack"
        status["enabled"] = True
        status["default_policy"] = "Accept All Incoming (No firewall active)"
        status["rules"] = ["Port 22 (SSH) open", "Port 5000 (Control Center) open"]
        return status
