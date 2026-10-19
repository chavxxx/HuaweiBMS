"""Unit tests for MultiBatteryService and Multi-Battery Fleet API."""

import pytest
from fastapi.testclient import TestClient

from app.database.crud import MultiBatteryAuditCRUD
from app.main import app
from app.state import app_context


@pytest.fixture
def client():
    return TestClient(app)


def test_list_batteries(client):
    res = client.get("/api/batteries")
    assert res.status_code == 200
    data = res.json()
    assert "batteries" in data
    assert "active_slave_id" in data
    assert data["total_count"] >= 4
    # Verify battery structure
    b1 = data["batteries"][0]
    assert "slave_id" in b1
    assert "name" in b1
    assert "soc" in b1
    assert "total_voltage" in b1


def test_select_active_battery(client):
    # Switch to Battery 2
    res = client.post("/api/batteries/select", json={"slave_id": 2})
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert res.json()["active_slave_id"] == 2

    # Verify state reflects switch
    status = client.get("/api/batteries").json()
    assert status["active_slave_id"] == 2

    # Switch back to Battery 1
    res = client.post("/api/batteries/select", json={"slave_id": 1})
    assert res.status_code == 200
    assert res.json()["active_slave_id"] == 1


def test_add_and_remove_battery(client):
    # Add Battery 5
    res = client.post("/api/batteries/add", json={"slave_id": 5, "name": "Battery #5 (Reserve)"})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Verify it is listed
    status = client.get("/api/batteries").json()
    ids = [b["slave_id"] for b in status["batteries"]]
    assert 5 in ids

    # Remove Battery 5
    del_res = client.delete("/api/batteries/5")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify it is removed
    status2 = client.get("/api/batteries").json()
    ids2 = [b["slave_id"] for b in status2["batteries"]]
    assert 5 not in ids2


def test_scan_bus_simulation(client):
    res = client.post("/api/batteries/scan", json={"candidate_ids": [1, 2, 3, 4, 99]})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["discovered_count"] >= 4


def test_read_all_batteries(client):
    res = client.post("/api/batteries/read-all")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "batteries" in data
    summary = data["summary"]
    assert summary["battery_count"] >= 4
    assert summary["total_capacity_ah"] >= 400
    assert summary["avg_soc"] > 0
    assert summary["avg_soh"] > 0
    assert "max_cell_delta_mv" in summary

    # Check that individual battery has cells, temps, and parameters
    first_b = data["batteries"][0]
    assert len(first_b["cell_voltages"]) == 16
    assert len(first_b["cell_temps"]) == 16
    assert "parameters" in first_b
    assert "gyroscope_anti_theft_locked" in first_b["parameters"]


def test_save_audit_and_retrieve(client):
    res = client.post("/api/batteries/save-audit", json={
        "operator": "ADMINISTRATOR",
        "notes": "Automated test fleet comparison snapshot"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    audit_id = data["audit_id"]
    assert audit_id > 0

    # Retrieve audit from list
    audits_res = client.get("/api/batteries/audits")
    assert audits_res.status_code == 200
    audits = audits_res.json()["audits"]
    assert any(a["id"] == audit_id for a in audits)

    # Retrieve specific audit
    detail_res = client.get(f"/api/batteries/audits/{audit_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == audit_id
    assert "summary" in detail
    assert "audit_data" in detail
    assert len(detail["audit_data"]) >= 4


def test_export_csv_and_json(client):
    # CSV export
    csv_res = client.get("/api/batteries/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    content = csv_res.text
    assert "Huawei BMS Fleet Comparison" in content
    assert "Slave ID" in content
    assert "Pack Voltage" in content

    # JSON export
    json_res = client.get("/api/batteries/export/json")
    assert json_res.status_code == 200
    data = json_res.json()
    assert "summary" in data
    assert "batteries" in data
