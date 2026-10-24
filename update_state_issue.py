#!/usr/bin/env python3
"""Download, validate, and safely apply the published State Issue update."""
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

REPOSITORY_ZIP = (
    "https://github.com/XLFatFluffy/State-Issue-App/archive/refs/heads/main.zip"
)
SERVICE_NAME = "StateIssueServer"
UPDATE_FILES = (
    "ADMIN_GUIDE.txt",
    "CONNECT_AND_TROUBLESHOOT.txt",
    "INSTALL_STATE_ISSUE_SERVICE.bat",
    "OPEN_STATE_ISSUE.bat",
    "README.txt",
    "SETUP_NEW_COMPUTER.bat",
    "START_STATE_ISSUE.bat",
    "Stateissue.html",
    "UNINSTALL_STATE_ISSUE_SERVICE.bat",
    "UPDATE_STATE_ISSUE.bat",
    "VERIFY_BACKUP.bat",
    "seed.json",
    "server.py",
    "sw.js",
    "test_server.py",
    "update_state_issue.py",
    "windows_service.py",
)


def run_sc(action):
    result = subprocess.run(
        ["sc.exe", action, SERVICE_NAME],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    return result.returncode, result.stdout


def service_state():
    code, output = run_sc("query")
    if code:
        raise RuntimeError(
            "Could not query the State Issue service. Run this updater as "
            "administrator.\n" + output.strip()
        )
    match = re.search(r"STATE\s*:\s*\d+\s+(\w+)", output)
    if not match:
        raise RuntimeError("Could not determine the State Issue service status.")
    return match.group(1).upper()


def wait_for_service(expected, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if service_state() == expected:
            return
        time.sleep(1)
    raise RuntimeError(
        "Timed out waiting for the State Issue service to become " + expected + "."
    )


def download_archive(destination):
    request = urllib.request.Request(
        REPOSITORY_ZIP,
        headers={"User-Agent": "State-Issue-Updater"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with open(destination, "wb") as archive:
                shutil.copyfileobj(response, archive)
    except (OSError, urllib.error.URLError) as error:
        raise RuntimeError(
            "Could not download the published update. Check the host's internet "
            "connection and try again.\n" + str(error)
        )
    if not zipfile.is_zipfile(destination):
        raise RuntimeError("GitHub did not return a valid update archive.")


def stage_archive(archive_path, stage_dir):
    with zipfile.ZipFile(archive_path) as archive:
        source_root = None
        staged = set()
        for entry in archive.infolist():
            parts = entry.filename.split("/")
            if len(parts) != 2 or parts[1] not in UPDATE_FILES:
                continue
            if source_root is None:
                source_root = parts[0]
            if parts[0] != source_root or entry.is_dir():
                continue
            target = os.path.join(stage_dir, parts[1])
            with archive.open(entry) as source, open(target, "wb") as output:
                contents = source.read()
                if parts[1].lower().endswith(".bat"):
                    contents = contents.replace(b"\r\n", b"\n").replace(
                        b"\n", b"\r\n"
                    )
                output.write(contents)
            staged.add(parts[1])
        missing = sorted(set(UPDATE_FILES) - staged)
        if missing:
            raise RuntimeError(
                "The downloaded update is incomplete. Missing: "
                + ", ".join(missing)
            )


def run_update_tests(stage_dir):
    result = subprocess.run(
        [sys.executable, "test_server.py"],
        cwd=stage_dir,
    )
    if result.returncode:
        raise RuntimeError("The downloaded update did not pass its server tests.")


def check_server_version(stage_dir):
    with open(os.path.join(stage_dir, "server.py"), "r", encoding="utf-8") as file:
        source = file.read()
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', source, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not read the downloaded application version.")
    return match.group(1)


def replace_files(stage_dir, install_dir, changed_files):
    for name in changed_files:
        source = os.path.join(stage_dir, name)
        target = os.path.join(install_dir, name)
        temporary = target + ".update-tmp"
        try:
            shutil.copy2(source, temporary)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)


def restore_files(backup_dir, install_dir, replaced):
    for name in reversed(replaced):
        backup = os.path.join(backup_dir, name)
        target = os.path.join(install_dir, name)
        if os.path.isfile(backup):
            shutil.copy2(backup, target)
        elif os.path.isfile(target):
            os.remove(target)


def verify_running_version(expected_version):
    url = "http://127.0.0.1:8787/api/ping"
    deadline = time.time() + 30
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                result = json.loads(response.read().decode("utf-8"))
            if result.get("version") == expected_version:
                return
            last_error = "The server responded with version " + str(
                result.get("version")
            )
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = str(error)
        time.sleep(1)
    raise RuntimeError(
        "The service did not report the updated version "
        + expected_version
        + ". "
        + (last_error or "")
    )


def main():
    install_dir = os.path.dirname(os.path.abspath(__file__))
    stage_dir = tempfile.mkdtemp(prefix=".state-issue-stage-", dir=install_dir)
    backup_dir = tempfile.mkdtemp(prefix=".state-issue-rollback-", dir=install_dir)
    service_was_running = False
    try:
        archive_path = os.path.join(stage_dir, "update.zip")
        extracted_dir = os.path.join(stage_dir, "files")
        os.makedirs(extracted_dir)
        print("Downloading the published update from GitHub...")
        download_archive(archive_path)
        print("Checking the downloaded application...")
        stage_archive(archive_path, extracted_dir)
        run_update_tests(extracted_dir)
        version = check_server_version(extracted_dir)
        changed_files = [
            name
            for name in UPDATE_FILES
            if not filecmp.cmp(
                os.path.join(extracted_dir, name),
                os.path.join(install_dir, name),
                shallow=False,
            )
        ]
        if not changed_files:
            print("Update checks passed. This host already has the published files.")
            return 0
        print(
            "Update checks passed. Version "
            + version
            + "; "
            + str(len(changed_files))
            + " application file(s) will change."
        )

        service_was_running = service_state() == "RUNNING"
        if service_was_running:
            print("Stopping the State Issue service...")
            code, output = run_sc("stop")
            if code and service_state() != "STOPPED":
                raise RuntimeError("Could not stop the State Issue service.\n" + output)
            wait_for_service("STOPPED")

        print("Updating application files (database and backups are not changed)...")
        replacement_started = False
        try:
            for name in changed_files:
                current = os.path.join(install_dir, name)
                if os.path.isfile(current):
                    shutil.copy2(current, os.path.join(backup_dir, name))
            replacement_started = True
            replace_files(extracted_dir, install_dir, changed_files)
            if service_was_running:
                print("Starting the updated State Issue service...")
                code, output = run_sc("start")
                if code and service_state() != "RUNNING":
                    raise RuntimeError(
                        "Could not start the updated State Issue service.\n" + output
                    )
                wait_for_service("RUNNING")
                verify_running_version(version)
        except Exception:
            if service_was_running and service_state() != "STOPPED":
                run_sc("stop")
                wait_for_service("STOPPED")
            if replacement_started:
                print("Update failed. Restoring the previous application files...")
                restore_files(backup_dir, install_dir, changed_files)
            if service_was_running:
                run_sc("start")
                wait_for_service("RUNNING")
            raise

        print("State Issue is updated to version " + version + ".")
        if service_was_running:
            print("The server is running. Workstations can reload the page.")
        else:
            print("The service was stopped before the update and remains stopped.")
        return 0
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)
        shutil.rmtree(backup_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Update failed: " + str(error), file=sys.stderr)
        sys.exit(1)
