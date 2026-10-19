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
    # Mock GitHub releases/latest returning same version v2.0.0
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"tag_name": "v2.0.0", "body": "Current stable"}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    svc = UpdateService()
    svc.current_version = "v2.0.0"
    with patch.object(svc, "get_local_git_info", return_value={"is_git": False, "commit_sha": "", "short_sha": "unknown", "branch": "main", "tag": "v2.0.0"}):
        result = svc.check_for_updates()

    assert result["latest_version"] == "v2.0.0"
    assert result["status"] == "UP_TO_DATE"


def test_safe_fetch_json_ssl_verification_fallback():
    """Verify that SSL certificate verification failures automatically fallback to unverified context."""
    from app.services.update_service import _safe_fetch_json
    import urllib.error

    calls = []
    def mock_urlopen_fn(req, timeout=6, context=None):
        calls.append(context)
        if len(calls) == 1:
            raise urllib.error.URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)")
        mock_r = MagicMock()
        mock_r.__enter__.return_value = mock_r
        mock_r.status = 200
        mock_r.read.return_value = b'{"tag_name": "v1.0.8"}'
        return mock_r

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_fn):
        data, status, err = _safe_fetch_json("https://api.github.com/repos/chavxxx/HuaweiBMS/releases/latest", {})
        assert status == 200
        assert data == {"tag_name": "v1.0.8"}
        assert len(calls) == 2
        assert err is None


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
