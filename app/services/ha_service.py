import json
import urllib.request
import urllib.error
from app.config import config
from app.services.audit_logger import AuditLogger

class HomeAssistantService:
    @staticmethod
    def is_enabled() -> bool:
        ha_conf = config.get("home_assistant", {})
        return bool(ha_conf.get("enabled") and ha_conf.get("base_url") and ha_conf.get("access_token"))

    @staticmethod
    def get_headers() -> dict:
        token = config.get("home_assistant", {}).get("access_token", "").strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "RaspberryPi-ControlCenter/1.0"
        }

    @staticmethod
    def get_base_url() -> str:
        url = config.get("home_assistant", {}).get("base_url", "http://homeassistant.local:8123").strip()
        return url.rstrip("/")

    @staticmethod
    def test_connection() -> tuple[bool, str]:
        if not HomeAssistantService.is_enabled():
            return False, "Home Assistant integration is not enabled or credentials are missing"

        url = f"{HomeAssistantService.get_base_url()}/api/"
        try:
            req = urllib.request.Request(url, headers=HomeAssistantService.get_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return True, data.get("message", "API running.")
                return False, f"Unexpected response status {response.status}"
        except urllib.error.HTTPError as e:
            return False, f"HTTP Error {e.code}: {e.reason}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    @staticmethod
    def send_notification(title: str, message: str, service: str = "") -> tuple[bool, str]:
        if not HomeAssistantService.is_enabled():
            return False, "Home Assistant is disabled in config"

        notify_svc = service or config.get("home_assistant", {}).get("notify_service", "notify")
        url = f"{HomeAssistantService.get_base_url()}/api/services/notify/{notify_svc}"
        payload = json.dumps({"title": title, "message": message}).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers=HomeAssistantService.get_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in (200, 201):
                    AuditLogger.log_app_event("INFO", f"HA Notification sent: {title}")
                    return True, "Notification sent to Home Assistant"
                return False, f"HA responded with code {response.status}"
        except Exception as e:
            AuditLogger.log_app_event("WARNING", f"Failed sending HA notification: {e}")
            return False, str(e)

    @staticmethod
    def update_sensor(entity_id: str, state: str, attributes: dict = None) -> tuple[bool, str]:
        if not HomeAssistantService.is_enabled():
            return False, "Home Assistant is disabled in config"

        if not entity_id:
            entity_id = config.get("home_assistant", {}).get("sensor_entity_id", "sensor.rpi_internet_status")

        url = f"{HomeAssistantService.get_base_url()}/api/states/{entity_id}"
        payload = json.dumps({
            "state": state,
            "attributes": attributes or {}
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers=HomeAssistantService.get_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in (200, 201):
                    return True, f"State updated for {entity_id}"
                return False, f"HA responded with code {response.status}"
        except Exception as e:
            return False, str(e)
