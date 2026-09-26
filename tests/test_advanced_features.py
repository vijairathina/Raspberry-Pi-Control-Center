import json
import io
import pytest

def test_hardware_gpio_and_camera(auth_client):
    # Hardware overview
    res_hw = auth_client.get("/api/hardware/overview")
    assert res_hw.status_code == 200
    hw_data = res_hw.get_json()["data"]
    assert "cpu" in hw_data
    assert "usb_devices" in hw_data

    # GPIO pins list
    res_gpio = auth_client.get("/api/hardware/gpio")
    assert res_gpio.status_code == 200
    pins = res_gpio.get_json()["data"]
    assert len(pins) == 40

    # Toggle GPIO 17 (safe pin) mode and state
    res_mode = auth_client.post("/api/hardware/gpio/mode",
        json={"gpio": 17, "mode": "OUT"},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_mode.status_code == 200

    res_state = auth_client.post("/api/hardware/gpio/state",
        json={"gpio": 17, "state": 1},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_state.status_code == 200

    # Try setting power pin (Pin 1) - should be rejected
    res_bad_gpio = auth_client.post("/api/hardware/gpio/state",
        json={"gpio": 0, "state": 0},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_bad_gpio.status_code == 400

    # Camera preview frame
    res_cam = auth_client.get("/api/hardware/camera/preview")
    assert res_cam.status_code == 200
    assert "data_url" in res_cam.get_json()

def test_docker_and_tailscale(auth_client):
    # Docker containers
    res_doc = auth_client.get("/api/docker/status")
    assert res_doc.status_code == 200
    assert "containers" in res_doc.get_json()["data"]

    # Docker logs
    res_dlogs = auth_client.get("/api/docker/logs?id=c7a8b9d0e1f2&lines=10")
    assert res_dlogs.status_code == 200
    assert "logs" in res_dlogs.get_json()["data"].lower() or len(res_dlogs.get_json()["data"]) > 0

    # Tailscale status
    res_ts = auth_client.get("/api/tailscale/status")
    assert res_ts.status_code == 200
    assert "peers" in res_ts.get_json()["data"]

def test_settings_import_export(auth_client):
    # Update setting
    res_up = auth_client.post("/api/settings/update",
        json={"temperature_warning_celsius": "72", "polling_interval_seconds": "4"},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_up.status_code == 200

    # Export configuration JSON
    res_exp = auth_client.get("/api/settings/export")
    assert res_exp.status_code == 200
    content = json.loads(res_exp.data.decode("utf-8"))
    assert content["settings"]["temperature_warning_celsius"] == "72"

    # Import configuration back
    import_payload = {
        "version": "1.0",
        "settings": {"temperature_warning_celsius": "68", "polling_interval_seconds": "2"}
    }
    data = {
        "backup_file": (io.BytesIO(json.dumps(import_payload).encode("utf-8")), "backup.json")
    }
    res_imp = auth_client.post("/api/settings/import",
        data=data,
        content_type="multipart/form-data",
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_imp.status_code == 200

def test_app_logs_and_audit(auth_client):
    # Read app logs
    res_logs = auth_client.get("/api/logs/app?lines=50")
    assert res_logs.status_code == 200
    assert "data" in res_logs.get_json()

    # Query audit logs
    res_audit = auth_client.get("/api/security/audit-logs?limit=10")
    assert res_audit.status_code == 200
    assert len(res_audit.get_json()["data"]) > 0

def test_system_reboot_and_shutdown_simulation(auth_client):
    res_reboot = auth_client.post("/api/system/reboot", headers={"X-CSRFToken": "test-csrf-token"})
    assert res_reboot.status_code == 200

    res_shutdown = auth_client.post("/api/system/shutdown", headers={"X-CSRFToken": "test-csrf-token"})
    assert res_shutdown.status_code == 200

def test_home_assistant_and_internet_monitor(auth_client):
    # Test HA test endpoints (returns 400 when disabled, gracefully handled)
    res_ha = auth_client.post("/api/ha/test", headers={"X-CSRFToken": "test-csrf-token"})
    assert res_ha.status_code in (200, 400)

    # Test resilient internet check (should succeed in 1 attempt when online)
    res_net = auth_client.post("/api/internet/check-now", headers={"X-CSRFToken": "test-csrf-token"})
    assert res_net.status_code == 200
    net_data = res_net.get_json()["data"]
    assert "status" in net_data
    assert "attempts" in net_data
    assert net_data["attempts"] >= 1

