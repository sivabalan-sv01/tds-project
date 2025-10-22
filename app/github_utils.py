# app/github_utils.py
import os
import httpx
import base64
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")
BASE_URL = "https://api.github.com"

def create_repo(repo_name: str, description: str = ""):
    """
    Create a public repository with the given name.
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Sanitize description for GitHub API
    if description:
        # Remove control characters and limit length
        import re
        description = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', description)  # Remove control chars
        description = description.strip()
        if len(description) > 350:
            description = description[:347] + "..."
    
    # Check if repo exists
    url = f"{BASE_URL}/repos/{USERNAME}/{repo_name}"
    try:
        r = httpx.get(url, headers=headers, timeout=30.0)
        if r.status_code == 200:
            print("Repo already exists:", f"{USERNAME}/{repo_name}")
            return {"full_name": f"{USERNAME}/{repo_name}", "name": repo_name}
    except Exception:
        pass

    # Create new repo
    url = f"{BASE_URL}/user/repos"
    data = {
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": True,
        "license_template": "mit"
    }
    try:
        r = httpx.post(url, headers=headers, json=data, timeout=30.0)
        if r.status_code == 201:
            repo_data = r.json()
            print("Created repo:", repo_data["full_name"])
            return repo_data
        else:
            raise Exception(f"Failed to create repo: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Error creating repo: {e}")
        raise

def create_or_update_file(repo, path: str, content: str, message: str):
    """
    Create a file or update if it already exists.
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get repo name from repo object (could be dict or object)
    if isinstance(repo, dict):
        repo_name = repo["name"]
        full_name = repo["full_name"]
    else:
        repo_name = repo.name
        full_name = repo.full_name
    
    # Encode content to base64
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    url = f"{BASE_URL}/repos/{full_name}/contents/{path}"
    
    try:
        # Try to get file to see if exists
        r = httpx.get(url, headers=headers, timeout=30.0)
        if r.status_code == 200:
            # File exists, update it
            file_data = r.json()
            data = {
                "message": message,
                "content": content_b64,
                "sha": file_data["sha"]
            }
            r = httpx.put(url, headers=headers, json=data, timeout=30.0)
            if r.status_code == 200:
                print(f"Updated {path} in {full_name}")
            else:
                raise Exception(f"Failed to update file: {r.status_code} {r.text}")
        elif r.status_code == 404:
            # File doesn't exist, create it
            data = {
                "message": message,
                "content": content_b64
            }
            r = httpx.put(url, headers=headers, json=data, timeout=30.0)
            if r.status_code == 201:
                print(f"Created {path} in {full_name}")
            else:
                raise Exception(f"Failed to create file: {r.status_code} {r.text}")
        else:
            raise Exception(f"Failed to check file: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Error creating/updating file {path}: {e}")
        raise


def create_or_update_binary_file(repo, path: str, binary_content, commit_message: str):
    """
    Create or update a binary file in the repository.
    This function handles binary data like images directly without encoding/decoding.
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get repo name from repo object (could be dict or object)
    if isinstance(repo, dict):
        repo_name = repo["name"]
        full_name = repo["full_name"]
    else:
        repo_name = repo.name
        full_name = repo.full_name
    
    # Encode binary content to base64
    content_b64 = base64.b64encode(binary_content).decode('utf-8')
    
    url = f"{BASE_URL}/repos/{full_name}/contents/{path}"
    
    try:
        # Try to get file to see if exists
        r = httpx.get(url, headers=headers, timeout=30.0)
        if r.status_code == 200:
            # File exists, update it
            file_data = r.json()
            data = {
                "message": commit_message,
                "content": content_b64,
                "sha": file_data["sha"]
            }
            r = httpx.put(url, headers=headers, json=data, timeout=30.0)
            if r.status_code == 200:
                print(f"Updated binary file {path} in {full_name}")
                return True
            else:
                print(f"Failed to update binary file: {r.status_code} {r.text}")
                return False
        elif r.status_code == 404:
            # File doesn't exist, create it
            data = {
                "message": commit_message,
                "content": content_b64
            }
            r = httpx.put(url, headers=headers, json=data, timeout=30.0)
            if r.status_code == 201:
                print(f"Created binary file {path} in {full_name}")
                return True
            else:
                print(f"Failed to create binary file: {r.status_code} {r.text}")
                return False
        else:
            print(f"Failed to check binary file: {r.status_code} {r.text}")
            return False
    except Exception as e:
        print(f"Error creating/updating binary file {path}: {e}")
        return False

def enable_pages(repo_name: str, branch: str = "main"):
    """
    Enable GitHub Pages via REST API; expects GITHUB_USERNAME in env.
    """
    url = f"{BASE_URL}/repos/{USERNAME}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"source": {"branch": branch, "path": "/"}}
    try:
        r = httpx.post(url, headers=headers, json=data, timeout=30.0)
        if r.status_code in (201, 202, 204):
            # 202 indicates Pages is being provisioned/building
            print("Pages enable request accepted for", repo_name, "status:", r.status_code)
            return True
        else:
            print("Pages API returned:", r.status_code, r.text)
            return False
    except Exception as e:
        print("Failed to call Pages API:", e)
        return False

def wait_for_pages(repo_name: str, timeout_seconds: int = 120) -> str | None:
    """Backward compatible poll using env USERNAME. Prefer wait_for_pages_for_repo."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    import time
    start = time.time()
    owner = USERNAME
    pages_url = f"{BASE_URL}/repos/{owner}/{repo_name}/pages"
    while time.time() - start < timeout_seconds:
        try:
            r = httpx.get(pages_url, headers=headers, timeout=15.0)
            if r.status_code == 200:
                info = r.json()
                html_url = info.get("html_url")
                status = info.get("status")  # e.g., 'built', 'building'
                if html_url and (status in (None, "built")):
                    return html_url
                # fallthrough to wait if building
            elif r.status_code == 404:
                # Not ready yet
                pass
        except Exception:
            pass
        time.sleep(3)
    return None

# --- Owner-aware Pages helpers ---
def _owner_repo_from_repo(repo) -> tuple[str, str | None]:
    """Extract (owner, name) from a repo dict/object, with env fallback for owner."""
    if isinstance(repo, dict):
        full_name = repo.get("full_name")
        name = repo.get("name")
    else:
        full_name = getattr(repo, "full_name", None)
        name = getattr(repo, "name", None)
    if full_name and "/" in full_name:
        owner, nm = full_name.split("/", 1)
        return owner, nm
    return USERNAME, name

def enable_pages_for_repo(repo, branch: str = "main") -> bool:
    """Enable GitHub Pages using the repo's actual owner/name."""
    owner, name = _owner_repo_from_repo(repo)
    url = f"{BASE_URL}/repos/{owner}/{name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"source": {"branch": branch, "path": "/"}}
    try:
        r = httpx.post(url, headers=headers, json=data, timeout=30.0)
        if r.status_code in (201, 202, 204):
            print("Pages enable request accepted for", f"{owner}/{name}", "status:", r.status_code)
            return True
        else:
            print("Pages API returned:", r.status_code, r.text)
            return False
    except Exception as e:
        print("Failed to call Pages API:", e)
        return False

def wait_for_pages_for_repo(repo, timeout_seconds: int = 120) -> str | None:
    """Poll Pages status using owner/name from repo; return html_url when built or None on timeout."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    import time
    start = time.time()
    owner, name = _owner_repo_from_repo(repo)
    pages_url = f"{BASE_URL}/repos/{owner}/{name}/pages"
    while time.time() - start < timeout_seconds:
        try:
            r = httpx.get(pages_url, headers=headers, timeout=15.0)
            if r.status_code == 200:
                info = r.json()
                html_url = info.get("html_url")
                status = info.get("status")
                if html_url and (status in (None, "built")):
                    return html_url
            elif r.status_code == 404:
                pass
        except Exception:
            pass
        time.sleep(3)
    return None

"""
The repository is now created with an MIT license by default using
GitHub's license_template parameter at creation time.
"""

# -------------------------
# Read helpers (REST-based)
# -------------------------

def _repo_full_name(repo) -> str:
    """Accepts a dict (from create_repo) or an object with full_name attr."""
    if isinstance(repo, dict):
        return repo.get("full_name") or f"{USERNAME}/{repo.get('name')}"
    return getattr(repo, "full_name")


def get_file_text(repo, path: str) -> str | None:
    """
    Fetch a text file's content via GitHub Contents API and decode base64.
    Returns None if not found or on error.
    """
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    full_name = _repo_full_name(repo)
    url = f"{BASE_URL}/repos/{full_name}/contents/{path}"
    try:
        r = httpx.get(url, headers=headers, timeout=30.0)
        if r.status_code == 200:
            data = r.json()
            content_b64 = data.get("content", "")
            try:
                # GitHub may include newlines; strip before decode
                decoded = base64.b64decode(content_b64.encode("utf-8")).decode(
                    "utf-8", errors="ignore"
                )
                return decoded
            except Exception:
                return None
        return None
    except Exception:
        return None


def get_latest_commit_sha(repo) -> str | None:
    """Return the latest commit SHA on the default branch via REST API."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    full_name = _repo_full_name(repo)
    url = f"{BASE_URL}/repos/{full_name}/commits?per_page=1"
    try:
        r = httpx.get(url, headers=headers, timeout=30.0)
        if r.status_code == 200:
            items = r.json()
            if isinstance(items, list) and items:
                return items[0].get("sha")
        return None
    except Exception:
        return None
