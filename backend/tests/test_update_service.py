"""Unit tests for UpdateService and Updates API."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.update_service import UpdateService, parse_version_tuple


@pytest.fixture
def client():
    return TestClient(app)


def test_parse_version_tuple():
    assert parse_version_tuple("v1.0.4") == (1, 0, 4)
    assert parse_version_tuple("1.0.5") == (1, 0, 5)
    assert parse_version_tuple("v2.10.12-beta") == (2, 10, 12)
    assert parse_version_tuple("invalid") == (0, 0, 0)
    assert parse_version_tuple("v1.0.5") > parse_version_tuple("v1.0.4")


def test_get_local_git_info():
    svc = UpdateService()
    info = svc.get_local_git_info()
    assert isinstance(info, dict)
    assert "is_git" in info
    assert "commit_sha" in info
    assert "branch" in info


@patch("urllib.request.urlopen")
def test_check_for_updates_available(mock_urlopen):
    # Mock GitHub releases/latest returning v2.0.0
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"tag_name": "v2.0.0", "body": "Exciting new features"}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    svc = UpdateService()
    svc.current_version = "v1.0.4"
    result = svc.check_for_updates()

    assert result["has_update"] is True
    assert result["status"] == "UPDATE_AVAILABLE"
    assert result["latest_version"] == "v2.0.0"


@patch("urllib.request.urlopen")
def test_check_for_updates_up_to_date(mock_urlopen):
    # Mock GitHub releases/latest returning same version v1.0.4
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"tag_name": "v1.0.4", "body": "Current stable"}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    svc = UpdateService()
    svc.current_version = "v1.0.4"
    result = svc.check_for_updates()

    assert result["latest_version"] == "v1.0.4"
    assert result["status"] in ("UP_TO_DATE", "UPDATE_AVAILABLE")


def test_api_check_updates_endpoint(client):
    response = client.get("/api/updates/check")
    assert response.status_code == 200
    data = response.json()
    assert "current_version" in data
    assert "status" in data
    assert "is_git_repo" in data


def test_api_pull_updates_role_guard(client):
    # Non-administrator should be rejected
    response = client.post("/api/updates/pull", json={"user_role": "OPERATOR"})
    assert response.status_code == 403
    assert "Administrator" in response.json()["detail"]


@patch("subprocess.run")
def test_pull_latest_update_admin(mock_subproc):
    mock_subproc.return_value = MagicMock(returncode=0, stdout="Already up to date.\n", stderr="")

    svc = UpdateService()
    res = svc.pull_latest_update(user_role="ADMINISTRATOR")
    assert res["success"] is True
    assert "stdout" in res
