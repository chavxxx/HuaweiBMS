import json
import logging
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from ..database.crud import AuditCRUD

logger = logging.getLogger("huawei_bms.update_service")

CURRENT_VERSION = "v1.1.2"
DEFAULT_REPO_OWNER = "chavxxx"
DEFAULT_REPO_NAME = "HuaweiBMS"
DEFAULT_REPO_URL = f"https://github.com/{DEFAULT_REPO_OWNER}/{DEFAULT_REPO_NAME}"


def _build_ssl_context() -> ssl.SSLContext:
    """Create SSL context with certifi CA bundle if available, else default."""
    try:
        import certifi
        ca_file = certifi.where()
        if os.path.exists(ca_file):
            return ssl.create_default_context(cafile=ca_file)
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()


def _safe_fetch_json(url: str, headers: dict[str, str], timeout: int = 6) -> tuple[Optional[Any], Optional[int], Optional[str]]:
    """Fetch JSON from URL with SSL verification fallback for frozen bundles and environments without local certificates.
    
    Returns (data, http_status_code, error_message).
    """
    req = urllib.request.Request(url, headers=headers)
    ctx = _build_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8")), resp.status, None
            return None, resp.status, None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, 404, "Not Found (404)"
        logger.warning("HTTP %d error requesting %s: %s", e.code, url, e)
        return None, e.code, str(e)
    except urllib.error.URLError as e:
        err_msg = str(e)
        if (
            "CERTIFICATE_VERIFY_FAILED" in err_msg
            or "certificate verify failed" in err_msg
            or "local issuer certificate" in err_msg
            or "self signed certificate" in err_msg
        ):
            logger.warning("SSL verification failed for %s (%s); retrying with unverified SSL context", url, err_msg)
            try:
                unverified_ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=timeout, context=unverified_ctx) as resp:
                    if resp.status == 200:
                        return json.loads(resp.read().decode("utf-8")), resp.status, None
                    return None, resp.status, None
            except urllib.error.HTTPError as retry_http_err:
                if retry_http_err.code == 404:
                    return None, 404, "Not Found (404)"
                return None, retry_http_err.code, str(retry_http_err)
            except Exception as retry_err:
                logger.error("Retry with unverified context failed for %s: %s", url, retry_err)
                return None, None, str(retry_err)
        return None, None, str(e)
    except Exception as e:
        logger.warning("Unexpected error fetching %s: %s", url, e)
        return None, None, str(e)


def find_project_root() -> Path:
    """Locate the git project root directory."""
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        if (curr / ".git").exists() or (curr / "package.json").exists():
            return curr
        curr = curr.parent
    return Path.cwd()


def parse_version_tuple(v: str) -> tuple[int, ...]:
    """Parse semver string like 'v1.0.4' into comparable integer tuple (1, 0, 4)."""
    clean = v.strip().lstrip("vV").split("-")[0]
    try:
        parts = [int(p) for p in clean.split(".") if p.isdigit()]
        return tuple(parts) if parts else (0, 0, 0)
    except Exception:
        return (0, 0, 0)


class UpdateService:
    """Checks the remote GitHub repository for new releases or commits, and applies updates."""

    def __init__(self, repo_owner: str = DEFAULT_REPO_OWNER, repo_name: str = DEFAULT_REPO_NAME):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = CURRENT_VERSION
        self.project_root = find_project_root()
        self.last_check_result: Optional[dict[str, Any]] = None

    def get_local_git_info(self) -> dict[str, Any]:
        """Inspect local git repository if available."""
        is_git = (self.project_root / ".git").exists()
        commit_sha = ""
        branch = "main"
        tag = self.current_version

        if is_git:
            try:
                commit_sha = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.project_root),
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass

            try:
                branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(self.project_root),
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass

            try:
                tag = subprocess.check_output(
                    ["git", "describe", "--tags", "--abbrev=0"],
                    cwd=str(self.project_root),
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
            except Exception:
                pass

        return {
            "is_git": is_git,
            "commit_sha": commit_sha,
            "short_sha": commit_sha[:7] if commit_sha else "unknown",
            "branch": branch,
            "tag": tag or self.current_version
        }

    def check_for_updates(self) -> dict[str, Any]:
        """Query GitHub API and remote git for the latest release/commit."""
        now = time.time()
        local_info = self.get_local_git_info()
        repo_url = f"https://github.com/{self.repo_owner}/{self.repo_name}"
        api_base = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"

        remote_version = self.current_version
        remote_sha = local_info["commit_sha"]
        latest_commit_msg = ""
        latest_commit_date = ""
        release_notes = ""
        error_msg = None

        # 1. Fetch latest release and tags from GitHub API
        headers = {
            "User-Agent": "HuaweiBMS-UpdateChecker/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        api_success = False
        api_404_count = 0

        # Try releases/latest
        rel_data, rel_status, rel_err = _safe_fetch_json(f"{api_base}/releases/latest", headers=headers)
        if rel_status == 200 and isinstance(rel_data, dict):
            remote_version = rel_data.get("tag_name", remote_version)
            release_notes = rel_data.get("body", "")
            api_success = True
        elif rel_status == 404:
            api_404_count += 1
        elif rel_err:
            error_msg = rel_err

        # Try tags
        tags_data, tags_status, tags_err = _safe_fetch_json(f"{api_base}/tags", headers=headers)
        if tags_status == 200 and isinstance(tags_data, list) and len(tags_data) > 0:
            latest_tag = tags_data[0].get("name", "")
            if parse_version_tuple(latest_tag) > parse_version_tuple(remote_version):
                remote_version = latest_tag
            if not remote_sha:
                remote_sha = tags_data[0].get("commit", {}).get("sha", "")
            api_success = True
            error_msg = None
        elif tags_status == 404:
            api_404_count += 1
        elif tags_err and not error_msg:
            error_msg = tags_err

        # Try commits/main
        c_data, c_status, c_err = _safe_fetch_json(f"{api_base}/commits/main", headers=headers)
        if c_status == 200 and isinstance(c_data, dict):
            remote_sha = c_data.get("sha", remote_sha)
            commit_obj = c_data.get("commit") or {}
            raw_msg = commit_obj.get("message") or ""
            msg_lines = raw_msg.splitlines()
            latest_commit_msg = msg_lines[0] if msg_lines else ""
            author_obj = commit_obj.get("author") or {}
            latest_commit_date = author_obj.get("date", "")
            api_success = True
            error_msg = None
        elif c_status == 404:
            api_404_count += 1
        elif c_err and not error_msg:
            error_msg = c_err

        # If all API endpoints return 404, the repo may be private
        if api_404_count >= 2 and not api_success:
            if not token:
                error_msg = (
                    f"Repository '{self.repo_owner}/{self.repo_name}' is private or inaccessible anonymously (HTTP 404). "
                    "Make the repository public or set GITHUB_TOKEN environment variable."
                )

        # 2. Offline / Git CLI fallback if available in git environment
        if local_info["is_git"]:
            # Query git remote tags
            try:
                tags_out = subprocess.check_output(
                    ["git", "ls-remote", "--tags", "origin"],
                    cwd=str(self.project_root),
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL
                ).strip()
                if tags_out:
                    found_tags = []
                    for line in tags_out.splitlines():
                        parts = line.split()
                        if len(parts) == 2 and parts[1].startswith("refs/tags/"):
                            t_clean = parts[1].replace("refs/tags/", "").replace("^{}", "")
                            found_tags.append(t_clean)
                    if found_tags:
                        found_tags.sort(key=parse_version_tuple)
                        newest_git_tag = found_tags[-1]
                        if parse_version_tuple(newest_git_tag) > parse_version_tuple(remote_version):
                            remote_version = newest_git_tag
                        error_msg = None
            except Exception as e:
                logger.debug("git ls-remote --tags failed: %s", e)

            # Query git remote main branch commit
            if not remote_sha or error_msg:
                try:
                    ls_out = subprocess.check_output(
                        ["git", "ls-remote", "origin", "refs/heads/main"],
                        cwd=str(self.project_root),
                        text=True,
                        timeout=5,
                        stderr=subprocess.DEVNULL
                    ).strip()
                    if ls_out:
                        remote_sha = ls_out.split()[0]
                        error_msg = None
                except Exception as e:
                    logger.warning("git ls-remote failed: %s", e)

        # 3. Determine if update is available
        has_update = False
        curr_tuple = parse_version_tuple(self.current_version)
        remote_tuple = parse_version_tuple(remote_version)

        if remote_tuple > curr_tuple:
            has_update = True
        elif local_info["commit_sha"] and remote_sha and len(local_info["commit_sha"]) >= 7 and len(remote_sha) >= 7:
            if local_info["commit_sha"][:7] != remote_sha[:7]:
                if local_info["is_git"]:
                    try:
                        # Count how many commits remote is ahead of local
                        ahead = subprocess.check_output(
                            ["git", "rev-list", "--count", f"HEAD..{remote_sha}"],
                            cwd=str(self.project_root),
                            text=True,
                            stderr=subprocess.DEVNULL
                        ).strip()
                        has_update = int(ahead) > 0
                    except Exception:
                        has_update = True
                else:
                    has_update = True


        result = {
            "current_version": self.current_version,
            "latest_version": remote_version or self.current_version,
            "current_commit": local_info["short_sha"],
            "latest_commit": remote_sha[:7] if remote_sha else local_info["short_sha"],
            "latest_commit_message": latest_commit_msg,
            "latest_commit_date": latest_commit_date,
            "release_notes": release_notes,
            "has_update": has_update,
            "repo_url": repo_url,
            "releases_url": f"{repo_url}/releases",
            "last_checked": now,
            "is_git_repo": local_info["is_git"],
            "branch": local_info["branch"],
            "error": error_msg,
            "status": "UPDATE_AVAILABLE" if has_update else ("ERROR" if error_msg else "UP_TO_DATE"),
        }

        self.last_check_result = result
        return result

    def pull_latest_update(self, user_role: str = "ADMINISTRATOR") -> dict[str, Any]:
        """Pull the latest git commits from origin main."""
        local_info = self.get_local_git_info()
        if not local_info["is_git"]:
            raise RuntimeError("Application is running from standalone binaries. Please download the latest release installer from GitHub.")

        try:
            # 1. Fetch
            fetch_res = subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            if fetch_res.returncode != 0:
                raise RuntimeError(f"Git fetch failed: {fetch_res.stderr.strip()}")

            # 2. Pull
            pull_res = subprocess.run(
                ["git", "pull", "--ff-only", "origin", "main"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            if pull_res.returncode != 0:
                raise RuntimeError(f"Git pull failed: {pull_res.stderr.strip() or pull_res.stdout.strip()}")

            new_info = self.get_local_git_info()
            audit_id = AuditCRUD.record_entry({
                "user_role": user_role,
                "action": "SYSTEM_UPDATE_PULLED",
                "parameter_name": "Application Version",
                "previous_value": local_info["short_sha"],
                "requested_value": new_info["short_sha"],
                "status": "SUCCESS",
                "details": f"Successfully pulled update from origin/main. New HEAD: {new_info['short_sha']}."
            })

            return {
                "success": True,
                "previous_commit": local_info["short_sha"],
                "updated_commit": new_info["short_sha"],
                "stdout": pull_res.stdout.strip(),
                "message": f"Successfully updated repository to commit {new_info['short_sha']}.",
                "audit_id": audit_id
            }
        except Exception as e:
            logger.error("Error executing git pull: %s", e)
            raise RuntimeError(f"Failed to apply update: {str(e)}")
