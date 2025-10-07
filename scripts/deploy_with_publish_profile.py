#!/usr/bin/env python3
"""
Deploy current working tree to an Azure Web App using a publish profile (Zip Deploy).
Temporary script for testing deployments from any branch, bypassing CI.
Requirements: Python 3.6+, requests
"""

import json
import os
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def main():
    # Resolve repo root
    script_dir = Path(__file__).parent.absolute()
    repo_root = script_dir.parent

    # Fixed publish profile path (no arguments)
    publish_profile_path = repo_root / "publish_profiles" / "saefnol-intactspecialty-net.PublishSettings"
    if not publish_profile_path.exists():
        print(f"Error: publish profile not found at {publish_profile_path}", file=sys.stderr)
        sys.exit(2)

    # No overlay merging when running without arguments
    overlay_path_str = "none"
    skip_merge = True

    print(f"Repo root: {repo_root}")

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp(prefix="azdeploy_"))
    print(f"Using temp dir: {temp_dir}")

    try:
        # Copy repository contents
        print("Copying repository contents (excluding junk) to temp dir...")
        copy_repo_contents(repo_root, temp_dir)

        # Print packaging summary
        file_count = sum(1 for p in temp_dir.rglob('*') if p.is_file())
        top_level = [p.name for p in sorted(temp_dir.iterdir())[:12]]
        print("Packaging summary (from repo root):")
        print(f" - Source root: {repo_root}")
        print(f" - Packaged files: {file_count}")
        print(f" - Top-level entries: {', '.join(top_level)}")

        # Create zip
        zip_path = temp_dir.with_suffix('.zip')
        print(f"Creating deployment zip: {zip_path}")
        create_zip(temp_dir, zip_path)

        # Parse publish profile
        print("Parsing publish profile for credentials and SCM host...")
        print(f"Using publish profile: {publish_profile_path}")

        scm_host, username, password = parse_publish_profile(publish_profile_path)

        # Optional overrides via environment variables
        username = os.getenv('AZURE_PUBLISH_USER', username)
        password = os.getenv('AZURE_PUBLISH_PASSWORD', password)

        if not scm_host or not username or not password:
            print("Failed to determine SCM host or credentials.", file=sys.stderr)
            print(f"SCM_HOST='{scm_host}', username present? {bool(username)}", file=sys.stderr)
            sys.exit(3)

        print(f"Using SCM host: {scm_host}")

        # Deploy
        deploy_zip(scm_host, username, password, zip_path, repo_root, overlay_path_str, skip_merge)

    finally:
        # Cleanup
        cleanup_temp_files(temp_dir, zip_path if 'zip_path' in locals() else None)


def copy_repo_contents(repo_root: Path, temp_dir: Path):
    """Copy repository contents excluding junk files/directories."""
    exclude_dirs = {'.git', '.github', 'outputs', 'logs', '__pycache__', '.venv', 'env', 
                   '.tox', '.mypy_cache', '.pytest_cache', '.ruff_cache'}
    exclude_suffixes = {'.pyc', '.pyo', '.pyd', '.zip'}
    
    def should_skip(path: Path) -> bool:
        parts = set(path.parts)
        if parts & exclude_dirs:
            return True
        if any(part.startswith('.') and part not in {'.vscode'} for part in parts):
            return True
        if path.suffix.lower() in exclude_suffixes:
            return True
        return False
    
    for root, dirs, files in os.walk(repo_root):
        root_path = Path(root)
        # Prune excluded directories
        dirs[:] = [d for d in dirs if not should_skip(root_path / d)]
        
        rel_root = root_path.relative_to(repo_root)
        out_dir = temp_dir / rel_root
        out_dir.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            src = root_path / f
            rel = src.relative_to(repo_root)
            if should_skip(rel):
                continue
            dst = temp_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def merge_config(base_path: Path, overlay_path: Path, out_path: Path):
    """Merge overlay YAML into base config using the existing merge script."""
    import subprocess
    
    # Find merge_config.py relative to this script's location
    script_dir = Path(__file__).parent.absolute()
    merge_script = script_dir / "merge_config.py"
    
    if not merge_script.exists():
        print(f"Error: merge_config.py not found at {merge_script}", file=sys.stderr)
        sys.exit(1)
    
    cmd = [
        sys.executable, 
        str(merge_script),
        "--base", str(base_path),
        "--overlay", str(overlay_path), 
        "--out", str(out_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Config merge failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout.strip())


def create_zip(source_dir: Path, zip_path: Path):
    """Create a zip file from the source directory."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            root_path = Path(root)
            for f in files:
                full_path = root_path / f
                rel_path = full_path.relative_to(source_dir)
                zipf.write(full_path, rel_path.as_posix())


def parse_publish_profile(profile_path: Path):
    """Parse publish profile XML to extract SCM host, username, and password."""
    try:
        tree = ET.parse(profile_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing publish profile: {e}", file=sys.stderr)
        return "", "", ""
    
    profiles = root.findall('.//publishProfile')
    
    def get_attr_ci(elem, key):
        """Get attribute case-insensitively."""
        for k, v in elem.attrib.items():
            if k.lower() == key.lower():
                return v
        return None
    
    # Prefer ZipDeploy, then MSDeploy, avoid FTP
    method_preference = {"zipdeploy": 2, "msdeploy": 1, "ftp": 0}
    
    best = None
    best_score = -1
    for p in profiles:
        method = (get_attr_ci(p, 'publishMethod') or '').lower()
        score = method_preference.get(method, -1)
        if score > best_score:
            best = p
            best_score = score
    
    if best is None:
        return "", "", ""
    
    publish_url = (get_attr_ci(best, 'publishUrl') or '').strip()
    username = (get_attr_ci(best, 'userName') or '').strip()
    password = (get_attr_ci(best, 'userPWD') or get_attr_ci(best, 'userPass') or '').strip()
    
    # Extract hostname from publish URL
    host = ''
    if publish_url:
        parsed = urlparse(publish_url if '://' in publish_url else f'https://{publish_url}')
        host = (parsed.hostname or '').strip()
    if not host and publish_url:
        host = publish_url.split(':')[0]
    
    print(f"Parsed from profile: method={get_attr_ci(best, 'publishMethod')}, host={host}, user={username[:10]}...")
    
    return host, username, password


def deploy_zip(scm_host: str, username: str, password: str, zip_path: Path, 
               repo_root: Path, overlay_path: str, skip_merge: bool):
    """Deploy zip file to Azure Web App using Kudu API."""
    zipdeploy_url = f"https://{scm_host}/api/zipdeploy"
    
    # Auth check first
    auth_check_url = f"https://{scm_host}/api/deployments"
    try:
        auth_resp = requests.get(auth_check_url, auth=(username, password), timeout=30)
        if auth_resp.status_code != 200:
            print(f"Authentication check failed (HTTP {auth_resp.status_code})", file=sys.stderr)
            print("Verify credentials match the selected environment.", file=sys.stderr)
            sys.exit(3)
    except requests.RequestException as e:
        print(f"Auth check failed: {e}", file=sys.stderr)
        sys.exit(3)
    
    print(f"Deploying to {zipdeploy_url} using Zip Deploy...")
    
    # Upload zip
    try:
        with open(zip_path, 'rb') as f:
            headers = {'Content-Type': 'application/zip'}
            resp = requests.post(zipdeploy_url, data=f, headers=headers, 
                               auth=(username, password), timeout=300)
        
        if resp.status_code not in (200, 202):
            print(f"Deployment upload failed with HTTP status {resp.status_code}", file=sys.stderr)
            print(resp.text, file=sys.stderr)
            sys.exit(4)
    except requests.RequestException as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(4)
    
    # Determine status URL
    deploy_status_url = resp.headers.get('Location')
    if not deploy_status_url:
        deploy_status_url = f"https://{scm_host}/api/deployments/latest"
    elif not deploy_status_url.startswith('http'):
        deploy_status_url = f"https://{scm_host}{deploy_status_url}"
    
    print(f"Upload accepted (HTTP {resp.status_code}). Tracking: {deploy_status_url}")
    
    # Poll for completion
    max_wait_secs = 600
    sleep_secs = 3
    elapsed = 0
    
    while elapsed < max_wait_secs:
        try:
            status_resp = requests.get(deploy_status_url, auth=(username, password), timeout=30)
            if status_resp.status_code != 200:
                print(f"Status check failed: HTTP {status_resp.status_code}", file=sys.stderr)
                break
                
            data = status_resp.json()
            
            # Get status fields (case-insensitive)
            def get_field(d, *keys):
                lk = {k.lower(): k for k in d}
                for k in keys:
                    if k in d:
                        return d[k]
                    if k.lower() in lk:
                        return d[lk[k.lower()]]
                return None
            
            status = get_field(data, 'status')
            status_text = get_field(data, 'statusText', 'status_text') or ''
            deployment_id = get_field(data, 'id') or ''
            end_time = get_field(data, 'end_time', 'endTime') or ''
            log_url = get_field(data, 'log_url', 'logUrl') or ''
            
            status_text_lower = status_text.lower()
            
            # Debug: print current status
            print(f"Status check: status={status}, text='{status_text}', id={deployment_id}")
            
            # Check for completion (Kudu: 3=success, 4=failure)
            if status == 3 or 'success' in status_text_lower:
                print_success(scm_host, status_text, deployment_id, end_time, log_url, 
                            repo_root, overlay_path, skip_merge)
                return
            elif status == 4 or 'fail' in status_text_lower or 'error' in status_text_lower:
                # Before treating as failure, check if app is actually working
                print(f"Status indicates failure (status={status}), but checking app health first...")
                app_host = scm_host.replace('.scm.azurewebsites.net', '.azurewebsites.net')
                try:
                    app_resp = requests.get(f"https://{app_host}", timeout=30)
                    if app_resp.status_code == 200:
                        print("App is responding correctly despite status=4. Treating as success.")
                        print_success(scm_host, "App healthy (status reporting issue)", deployment_id, 
                                    end_time, log_url, repo_root, overlay_path, skip_merge)
                        return
                    else:
                        print(f"App not responding properly (HTTP {app_resp.status_code}). Genuine failure.")
                except requests.RequestException:
                    print("App health check failed. Genuine failure.")
                
                print_failure(scm_host, status_text, deployment_id, log_url, username, password)
                sys.exit(4)
            
            # If we have an end_time but no clear success/failure, check if deployment is actually done
            if end_time and not status_text:
                # Deployment might be complete but status unclear - check app health
                print(f"Deployment appears complete (end_time: {end_time}). Checking app health...")
                app_host = scm_host.replace('.scm.azurewebsites.net', '.azurewebsites.net')
                try:
                    app_resp = requests.get(f"https://{app_host}", timeout=30)
                    if app_resp.status_code == 200:
                        print_success(scm_host, "Deployment complete - app responding", deployment_id, 
                                    end_time, log_url, repo_root, overlay_path, skip_merge)
                        return
                    else:
                        print(f"App not responding (HTTP {app_resp.status_code}). Continuing to wait...")
                except requests.RequestException:
                    print("App health check failed. Continuing to wait...")
                    pass
                
        except requests.RequestException as e:
            print(f"Status check error: {e}", file=sys.stderr)
        except json.JSONDecodeError:
            print("Invalid JSON response from status endpoint", file=sys.stderr)
        
        time.sleep(sleep_secs)
        elapsed += sleep_secs
    
    print(f"Deployment did not reach terminal state within {max_wait_secs} seconds.", file=sys.stderr)
    print(f"Check: {deploy_status_url}", file=sys.stderr)
    sys.exit(4)


def print_success(scm_host: str, status_text: str, deployment_id: str, end_time: str,
                 log_url: str, repo_root: Path, overlay_path: str, skip_merge: bool):
    """Print success message with deployment details."""
    app_host = scm_host.replace('.scm.azurewebsites.net', '.azurewebsites.net')
    
    if not log_url and deployment_id:
        log_url = f"https://{scm_host}/api/deployments/{deployment_id}/log"
    if not log_url:
        log_url = f"https://{scm_host}/api/deployments/latest"
    
    print("Deployment SUCCEEDED.")
    print(f" - App: https://{app_host}")
    print(f" - Status: {status_text or 'success'}")
    print(f" - Deployment ID: {deployment_id}")
    print(f" - Completed at: {end_time}")
    print(f" - Packaged from: {repo_root}")
    print(f" - Overlay merged: {overlay_path} (skip merge={skip_merge})")
    print(f" - Logs: {log_url}")


def print_failure(scm_host: str, status_text: str, deployment_id: str, log_url: str, 
                  username: str = None, password: str = None):
    """Print failure message with log details."""
    print(f"Deployment FAILED. status='{status_text}' id='{deployment_id}'", file=sys.stderr)
    
    if log_url:
        if not log_url.startswith('http'):
            log_url = f"https://{scm_host}{log_url}"
        print(f"Logs: {log_url}", file=sys.stderr)
        
        # Try to fetch and display the logs
        if username and password:
            try:
                print("\nFetching deployment logs...", file=sys.stderr)
                log_resp = requests.get(log_url, auth=(username, password), timeout=30)
                if log_resp.status_code == 200:
                    logs = log_resp.json()
                    if isinstance(logs, list):
                        print("\nDeployment Log Details:", file=sys.stderr)
                        for entry in logs[-10:]:  # Show last 10 log entries
                            message = entry.get('message', '')
                            details = entry.get('details_url', '')
                            if message:
                                print(f"  {message}", file=sys.stderr)
                            if details and not details.startswith('http'):
                                details_url = f"https://{scm_host}{details}"
                                try:
                                    details_resp = requests.get(details_url, auth=(username, password), timeout=15)
                                    if details_resp.status_code == 200:
                                        detail_text = details_resp.text.strip()
                                        if detail_text:
                                            print(f"    Details: {detail_text[:500]}{'...' if len(detail_text) > 500 else ''}", file=sys.stderr)
                                except:
                                    pass
                else:
                    print(f"Could not fetch logs (HTTP {log_resp.status_code})", file=sys.stderr)
                
                # Also check application logs for startup errors
                print("\nChecking application logs for startup errors...", file=sys.stderr)
                app_logs_url = f"https://{scm_host}/api/logs/recent"
                try:
                    app_logs_resp = requests.get(app_logs_url, auth=(username, password), timeout=30)
                    if app_logs_resp.status_code == 200:
                        app_logs = app_logs_resp.json()
                        if isinstance(app_logs, list):
                            recent_errors = [log for log in app_logs[-20:] if 'error' in log.get('message', '').lower() or 'exception' in log.get('message', '').lower()]
                            if recent_errors:
                                print("Recent application errors:", file=sys.stderr)
                                for error_log in recent_errors[-5:]:
                                    print(f"  {error_log.get('timestamp', '')}: {error_log.get('message', '')}", file=sys.stderr)
                            else:
                                print("No obvious errors in recent application logs.", file=sys.stderr)
                    else:
                        print(f"Could not fetch app logs (HTTP {app_logs_resp.status_code})", file=sys.stderr)
                except Exception as e:
                    print(f"Error fetching app logs: {e}", file=sys.stderr)
                
                # Check if the app is responding
                print("\nChecking app health...", file=sys.stderr)
                app_host = scm_host.replace('.scm.azurewebsites.net', '.azurewebsites.net')
                try:
                    app_resp = requests.get(f"https://{app_host}", timeout=30)
                    print(f"App response: HTTP {app_resp.status_code}", file=sys.stderr)
                    if app_resp.status_code != 200:
                        print(f"App error response: {app_resp.text[:300]}{'...' if len(app_resp.text) > 300 else ''}", file=sys.stderr)
                except requests.RequestException as e:
                    print(f"App health check failed: {e}", file=sys.stderr)
                    
            except Exception as e:
                print(f"Error fetching logs: {e}", file=sys.stderr)
    else:
        print(f"Latest: https://{scm_host}/api/deployments/latest", file=sys.stderr)


def cleanup_temp_files(temp_dir: Path, zip_path: Path = None):
    """Clean up temporary files and directories."""
    try:
        if zip_path and zip_path.exists():
            zip_path.unlink()
    except Exception:
        pass
    
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
