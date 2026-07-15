"""
softap_manager_v11.py

Standalone SoftAP validation helper.

Usage:

from softap_manager_v11 import softap_enable_v11

success, obs, DEVICE_IP = softap_enable_v11(
    device_ip=DEVICE_IP,
    device_mac=DEVICE_MAC,
    passcode=PASSCODE_NEW,
    original_ssid="Office",
    original_password="office123",
    softap_ssid=f"BTWN_{DEVICE_MAC[-4:]}",
    softap_password="123456789"
)

DEVICE_URL = f"http://{DEVICE_IP}/system"
"""

import subprocess
import socket
import time
import requests


SOFTAP_IP = "192.168.4.1"


def _post(ip, payload):
    try:
        r = requests.post(
            f"http://{ip}/system",
            json=payload,
            timeout=5
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _connect_wifi(ssid, password):
    r = subprocess.run(
        [
            "nmcli",
            "device",
            "wifi",
            "connect",
            ssid,
            "password",
            password,
        ],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0, r.stdout + r.stderr


def _scan_for_ssid(ssid, timeout=30):
    end = time.time() + timeout

    while time.time() < end:

        try:
            out = subprocess.check_output(
                [
                    "nmcli",
                    "-t",
                    "-f",
                    "SSID",
                    "device",
                    "wifi",
                    "list",
                ],
                text=True,
            )

            for line in out.splitlines():
                if line.strip() == ssid:
                    return True

        except Exception:
            pass

        time.sleep(2)

    return False


def _resolve_mdns(host, timeout=40):

    end = time.time() + timeout

    while time.time() < end:
        try:
            return socket.gethostbyname(host)
        except Exception:
            time.sleep(2)

    return None


def softap_enable_v11(
    device_ip,
    device_mac,
    passcode,
    original_ssid,
    original_password,
    softap_ssid,
    softap_password,
):

    print("\n========== SoftAP Validation ==========")

    print("Enabling SoftAP...")

    res = _post(
        device_ip,
        {
            "passcode": passcode,
            "command": "softap",
            "value": "1",
        },
    )

    if not res:
        return False, "Unable to enable SoftAP.", device_ip

    print("Waiting for SoftAP...")
    time.sleep(5)

    print("Scanning for SoftAP...")

    if not _scan_for_ssid(softap_ssid):
        return False, "SoftAP SSID not found.", device_ip

    print("Connecting laptop to SoftAP...")

    ok, msg = _connect_wifi(
        softap_ssid,
        softap_password,
    )

    if not ok:
        return False, msg, device_ip

    print("Verifying device over SoftAP...")

    prod = _post(
        SOFTAP_IP,
        {
            "passcode": passcode,
            "command": "product",
        },
    )

    if not prod:
        return False, "Product command failed over SoftAP.", device_ip

    print("PASS - Device reachable on SoftAP.")

    print("Restoring device WiFi...")

    res = _post(
        SOFTAP_IP,
        {
            "passcode": passcode,
            "command": "config",
            "primarySsid": original_ssid,
            "primaryPassword": original_password,
        },
    )

    if not res:
        return False, "Failed restoring device WiFi.", SOFTAP_IP

    print("Waiting for reboot...")
    time.sleep(6)

    print("Restoring laptop WiFi...")

    ok, msg = _connect_wifi(
        original_ssid,
        original_password,
    )

    if not ok:
        return False, msg, SOFTAP_IP

    print("Rediscovering device...")

    host = f"BTWN_{device_mac[-4:]}.local"

    restored_ip = _resolve_mdns(host)

    if not restored_ip:
        return False, "Unable to rediscover device.", SOFTAP_IP

    prod = _post(
        restored_ip,
        {
            "passcode": passcode,
            "command": "product",
        },
    )

    if not prod:
        return False, "Final product verification failed.", restored_ip

    return (
        True,
        "SoftAP validation completed successfully.",
        restored_ip,
    )