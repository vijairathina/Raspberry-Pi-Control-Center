import os
import shutil
import subprocess
import socket
from app.database import get_db

class ProxyManager:
    """
    Manages Reverse Proxy & Custom URLs for Raspberry Pi services.
    Enables accessing services via custom paths (e.g. http://raspberrypi.local/control)
    or custom domains (e.g. http://control.local) on standard port 80/443 without :port.
    """

    @staticmethod
    def get_hostname() -> str:
        try:
            return socket.gethostname()
        except Exception:
            return "raspberrypi"

    @staticmethod
    def get_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def check_nginx_status() -> dict:
        installed = bool(shutil.which("nginx"))
        running = False
        version = ""

        if installed:
            try:
                ver_res = subprocess.run(["nginx", "-v"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                version = (ver_res.stderr or ver_res.stdout).strip().replace("nginx version: ", "")
            except Exception:
                version = "nginx/installed"

            if shutil.which("systemctl"):
                try:
                    res = subprocess.run(["systemctl", "is-active", "nginx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
                    running = res.stdout.strip() == "active"
                except Exception:
                    pass
            else:
                running = True

        return {
            "installed": installed,
            "running": running,
            "version": version
        }

    @staticmethod
    def get_routes() -> list[dict]:
        routes = []
        hostname = ProxyManager.get_hostname()
        local_ip = ProxyManager.get_local_ip()

        try:
            conn = get_db()
            cur = conn.execute("SELECT * FROM reverse_proxy_routes ORDER BY port ASC")
            for r in cur.fetchall():
                path = r["custom_path"] or ""
                domain = r["custom_domain"] or ""
                port = r["port"]

                path_url = f"http://{hostname}.local{path}" if path else ""
                ip_path_url = f"http://{local_ip}{path}" if path else ""
                domain_url = f"http://{domain}" if domain else ""

                routes.append({
                    "id": r["id"],
                    "port": port,
                    "name": r["name"],
                    "custom_path": path,
                    "custom_domain": domain,
                    "websocket_support": bool(r["websocket_support"]),
                    "enabled": bool(r["enabled"]),
                    "target_url": f"http://127.0.0.1:{port}",
                    "path_url": path_url,
                    "ip_path_url": ip_path_url,
                    "domain_url": domain_url,
                    "primary_url": path_url or domain_url or f"http://{hostname}.local:{port}"
                })
        except Exception:
            pass

        return routes

    @staticmethod
    def save_route(port: int, name: str, custom_path: str = "", custom_domain: str = "", websocket_support: bool = True) -> tuple[bool, str]:
        if port <= 0 or port > 65535:
            return False, "Port number must be between 1 and 65535"

        name = (name or f"Service on {port}").strip()
        custom_path = (custom_path or "").strip()
        custom_domain = (custom_domain or "").strip().lower()

        # Normalize path: ensure leading slash if path is given
        if custom_path:
            if not custom_path.startswith("/"):
                custom_path = "/" + custom_path
            custom_path = custom_path.rstrip("/")
            if not custom_path:
                custom_path = f"/port{port}"

        try:
            conn = get_db()
            with conn:
                conn.execute("""
                    INSERT INTO reverse_proxy_routes (port, name, custom_path, custom_domain, websocket_support, enabled)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(port) DO UPDATE SET
                        name = excluded.name,
                        custom_path = excluded.custom_path,
                        custom_domain = excluded.custom_domain,
                        websocket_support = excluded.websocket_support,
                        enabled = 1
                """, (port, name, custom_path, custom_domain, 1 if websocket_support else 0))

                # Also update friendly port alias in settings
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"port_alias_{port}", name))

            return True, f"Custom URL route for port {port} saved successfully"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def delete_route(port: int) -> tuple[bool, str]:
        try:
            conn = get_db()
            with conn:
                conn.execute("DELETE FROM reverse_proxy_routes WHERE port = ?", (port,))
            return True, f"Custom URL route for port {port} removed"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def generate_nginx_config() -> str:
        """
        Generates production-grade Nginx reverse proxy configuration.
        Maps all configured paths and domains on standard port 80 to 127.0.0.1:<port>.
        """
        routes = ProxyManager.get_routes()
        lines = [
            "# ===========================================================================",
            "# Raspberry Pi Control Center - Automated Reverse Proxy Configuration",
            "# Generated automatically - Do not edit manually",
            "# ===========================================================================",
            "",
            "# Main HTTP Server - Path-based Routing (Accessible via IP or hostname.local)",
            "server {",
            "    listen 80 default_server;",
            "    listen [::]:80 default_server;",
            "    server_name _;",
            "    client_max_body_size 100M;",
            ""
        ]

        for r in routes:
            if not r["enabled"] or not r["custom_path"]:
                continue
            path = r["custom_path"]
            port = r["port"]
            ws = r["websocket_support"]

            lines.append(f"    # {r['name']} (Port {port})")
            lines.append(f"    location {path}/ {{")
            lines.append(f"        proxy_pass http://127.0.0.1:{port}/;")
            lines.append("        proxy_http_version 1.1;")
            if ws:
                lines.append("        proxy_set_header Upgrade $http_upgrade;")
                lines.append("        proxy_set_header Connection \"upgrade\";")
            lines.append("        proxy_set_header Host $host;")
            lines.append("        proxy_set_header X-Real-IP $remote_addr;")
            lines.append("        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;")
            lines.append("        proxy_set_header X-Forwarded-Proto $scheme;")
            lines.append("        proxy_read_timeout 86400s;")
            lines.append("        proxy_send_timeout 86400s;")
            lines.append("    }")
            lines.append("")

        lines.append("}")
        lines.append("")

        # Domain-based Virtual Hosts (e.g. control.local, myapi.local)
        for r in routes:
            if not r["enabled"] or not r["custom_domain"]:
                continue
            domain = r["custom_domain"]
            port = r["port"]
            ws = r["websocket_support"]

            lines.append(f"# Virtual Host: http://{domain} -> Port {port} ({r['name']})")
            lines.append("server {")
            lines.append("    listen 80;")
            lines.append(f"    server_name {domain};")
            lines.append("    client_max_body_size 100M;")
            lines.append("")
            lines.append("    location / {")
            lines.append(f"        proxy_pass http://127.0.0.1:{port};")
            lines.append("        proxy_http_version 1.1;")
            if ws:
                lines.append("        proxy_set_header Upgrade $http_upgrade;")
                lines.append("        proxy_set_header Connection \"upgrade\";")
            lines.append("        proxy_set_header Host $host;")
            lines.append("        proxy_set_header X-Real-IP $remote_addr;")
            lines.append("        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;")
            lines.append("        proxy_set_header X-Forwarded-Proto $scheme;")
            lines.append("        proxy_read_timeout 86400s;")
            lines.append("        proxy_send_timeout 86400s;")
            lines.append("    }")
            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def apply_nginx_config() -> tuple[bool, str]:
        """
        Writes and activates Nginx configuration on Raspberry Pi.
        Tests with `nginx -t` and reloads via `systemctl reload nginx`.
        """
        config_text = ProxyManager.generate_nginx_config()

        # If on Linux and Nginx is installed
        target_dir = "/etc/nginx/conf.d"
        target_file = os.path.join(target_dir, "rpi_control_center_proxy.conf")

        if os.path.exists(target_dir) and shutil.which("nginx"):
            try:
                # Write config
                with open(target_file, "w") as f:
                    f.write(config_text)

                # Test config syntax
                t_res = subprocess.run(["nginx", "-t"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if t_res.returncode != 0:
                    err_msg = t_res.stderr or t_res.stdout
                    return False, f"Nginx configuration test failed: {err_msg}"

                # Reload Nginx service
                subprocess.run(["systemctl", "reload", "nginx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                return True, "Nginx reverse proxy configuration deployed and reloaded successfully!"
            except Exception as e:
                return False, f"Failed to apply Nginx configuration: {e}"

        # Dev / Simulation mode
        return True, "Nginx reverse proxy configuration generated successfully (Simulation mode - Nginx config ready)."

    @staticmethod
    def install_nginx() -> tuple[bool, str]:
        if shutil.which("nginx"):
            return True, "Nginx is already installed"

        if shutil.which("apt-get"):
            try:
                subprocess.run(["apt-get", "update"], timeout=30)
                res = subprocess.run(["apt-get", "install", "-y", "nginx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
                if res.returncode == 0:
                    if shutil.which("systemctl"):
                        subprocess.run(["systemctl", "enable", "--now", "nginx"], timeout=10)
                    return True, "Nginx installed and started successfully!"
                return False, f"Apt install failed: {res.stderr}"
            except Exception as e:
                return False, f"Installation error: {e}"

        return True, "Simulated Nginx installation complete"
