import json
import pytest

def test_login_flow(client):
    # GET login page
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Raspberry Pi Control" in res.data

    # POST login failure
    res_fail = client.post("/login", data={
        "username": "admin",
        "password": "wrongpassword",
        "csrf_token": "invalid"
    })
    # CSRF or invalid credentials check
    assert res_fail.status_code in (400, 200)

def test_authenticated_dashboard(auth_client):
    res = auth_client.get("/dashboard")
    assert res.status_code == 200
    assert b"System Dashboard" in res.data

    api_res = auth_client.get("/api/dashboard/summary")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert data["success"] is True
    assert "summary" in data["data"]
    assert "quick_metrics" in data["data"]["summary"]

def test_performance_metrics(auth_client):
    res = auth_client.get("/api/performance/metrics")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "cpu" in data["data"]
    assert "ram" in data["data"]
    assert "storage" in data["data"]
    assert "network" in data["data"]

def test_services_and_critical_protection(auth_client):
    res = auth_client.get("/api/services/list")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]) > 0

    # Test trying to stop a critical service (e.g. ssh)
    res_stop = auth_client.post("/api/services/control", 
        json={"name": "ssh.service", "action": "stop"},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_stop.status_code == 400
    stop_data = res_stop.get_json()
    assert "protected" in stop_data["message"].lower()

def test_process_manager_safeguards(auth_client):
    res = auth_client.get("/api/processes/list")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]) > 0

    # Test trying to kill PID 1
    res_kill = auth_client.post("/api/processes/kill",
        json={"pid": 1, "force": True},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_kill.status_code == 400
    kill_data = res_kill.get_json()
    assert "critical" in kill_data["message"].lower()

def test_bluetooth_manager(auth_client):
    res = auth_client.get("/api/bluetooth/status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "powered" in data["data"]

    # Toggle power
    res_toggle = auth_client.post("/api/bluetooth/power",
        json={"enable": True},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_toggle.status_code == 200

def test_wifi_and_priority(auth_client):
    res = auth_client.get("/api/wifi/current")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    # Saved networks
    res_saved = auth_client.get("/api/wifi/saved")
    assert res_saved.status_code == 200
    saved_data = res_saved.get_json()
    assert len(saved_data["data"]) > 0

    # Update Priority
    first_uuid = saved_data["data"][0]["uuid"]
    res_prio = auth_client.post("/api/wifi/priority",
        json={"identifier": first_uuid, "priority": 110},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_prio.status_code == 200

def test_network_interfaces_and_temporary_block(auth_client):
    res = auth_client.get("/api/network/interfaces")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["data"]) > 0

    first_iface = data["data"][0]["name"]
    # Schedule temporary disable (fail-safe test with 1 minute)
    res_block = auth_client.post("/api/network/temporary-block",
        json={"interface": first_iface, "duration_minutes": 1},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_block.status_code == 200
    block_data = res_block.get_json()
    assert block_data["success"] is True
    assert "auto-restore scheduled" in block_data["message"].lower()

    # Restore immediately
    res_restore = auth_client.post("/api/network/temporary-restore",
        json={"interface": first_iface},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_restore.status_code == 200

def test_diagnostics(auth_client):
    # Safe Ping
    res_ping = auth_client.post("/api/diagnostics/ping",
        json={"host": "127.0.0.1", "count": 1},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_ping.status_code == 200
    assert res_ping.get_json()["success"] is True

    # Connectivity probe
    res_conn = auth_client.get("/api/diagnostics/connectivity")
    assert res_conn.status_code == 200

def test_tasks_and_automation(auth_client):
    # Add Task
    res_task = auth_client.post("/api/tasks/add",
        json={"name": "Nightly Reboot", "task_type": "reboot", "target": "", "schedule_type": "daily", "schedule_value": "04:00"},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_task.status_code == 200

    # Add Automation Rule
    res_rule = auth_client.post("/api/automation/add",
        json={"name": "High Temp Cool", "metric": "cpu_temp", "operator": ">", "value": 75.0, "action_type": "create_alert", "action_target": ""},
        headers={"X-CSRFToken": "test-csrf-token"}
    )
    assert res_rule.status_code == 200

    # Export backup
    res_exp = auth_client.get("/api/settings/export")
    assert res_exp.status_code == 200
    backup_data = json.loads(res_exp.data.decode("utf-8"))
    assert "settings" in backup_data
    assert "scheduled_tasks" in backup_data
    assert "automation_rules" in backup_data
