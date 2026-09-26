import os
import secrets
import yaml

CONFIG_PATH = os.environ.get("RPI_CONFIG_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"))

def load_config():
    default_config = {
        "server": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False,
            "secret_key": secrets.token_hex(32),
            "session_lifetime_minutes": 1440,
        },
        "database": {
            "path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rpi_control.db"),
        },
        "defaults": {
            "admin_username": "admin",
            "admin_default_password": "admin",
            "theme": "dark",
            "polling_interval_seconds": 3,
            "temperature_warning_celsius": 70,
            "temperature_critical_celsius": 80,
            "cpu_warning_percent": 85,
            "cpu_critical_percent": 95,
            "ram_warning_percent": 85,
            "ram_critical_percent": 95,
            "disk_warning_percent": 75,
            "disk_critical_percent": 90,
        },
        "home_assistant": {
            "enabled": False,
            "base_url": "http://homeassistant.local:8123",
            "access_token": "",
            "notify_service": "notify",
            "send_alerts": True,
            "sensor_entity_id": "sensor.rpi_internet_status",
        },
        "internet_monitor": {
            "enabled": True,
            "interval_seconds": 60,
            "ping_hosts": ["8.8.8.8", "1.1.1.1"],
            "timeout_seconds": 2,
            "retry_on_timeout": 3,
            "send_to_ha": True,
        }
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    for section, values in loaded.items():
                        if section in default_config and isinstance(values, dict):
                            default_config[section].update(values)
                        else:
                            default_config[section] = values
        except Exception as e:
            print(f"Warning: Failed to load config from {CONFIG_PATH}: {e}")

    # Ensure DB directory exists
    db_path = default_config["database"]["path"]
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return default_config

config = load_config()
