"""
wifi_manager_v11.py

Integrated WiFi handoff helper for the BuildTrack firmware tester.

Call:

from wifi_manager_v11 import configure_wifi_v11

success, obs, DEVICE_IP = configure_wifi_v11(
    DEVICE_IP,
    DEVICE_MAC,
    PASSCODE_NEW
)
DEVICE_URL = f"http://{DEVICE_IP}/system"

"""

import socket
import subprocess
import time
from getpass import getpass

import requests


def _nmcli_current():
    out = subprocess.check_output(
        ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
        text=True,
    )
    for line in out.splitlines():
        if line.startswith("yes:"):
            return line.split(":", 1)[1]
    return ""


def _connect_wifi(ssid, password):
    r = subprocess.run(
        ["nmcli", "device", "wifi", "connect", ssid, "password", password],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0, r.stdout + r.stderr


def _scan():
    out = subprocess.check_output(
        ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list"],
        text=True,
    )
    d = {}
    for line in out.splitlines():
        try:
            ssid, sig = line.rsplit(":", 1)
            if ssid:
                sig = int(sig)
                if ssid not in d or sig > d[ssid]:
                    d[ssid] = sig
        except Exception:
            pass
    return sorted(d.items(), key=lambda x: x[1], reverse=True)


def _resolve(host, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        try:
            return socket.gethostbyname(host)
        except Exception:
            time.sleep(2)
    return None


def _post(ip, payload):
    try:
        r = requests.post(f"http://{ip}/system", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def configure_wifi_v11(
    device_ip,
    device_mac,
    passcode,
    original_ssid,
    original_pwd
):
    print("\n========== WiFi Test ==========")

    print("\n1. Scan WiFi")
    print("2. Manual SSID")

    while True:
        c = input("Choice: ").strip()
        if c in ("1", "2"):
            break

    if c == "1":

        while True:

            nets = _scan()

            if not nets:
                print("\n❌ No WiFi networks found.")
            else:
                print("\nAvailable WiFi Networks:")
                for i, (s, sig) in enumerate(nets, 1):
                    print(f"{i}. {s:30} {sig}%")

            print("\nOptions:")
            print("  [number] Select a network")
            print("  R        Rescan")
            print("  M        Enter SSID manually")
            print("  Q        Cancel")

            choice = input("Choice: ").strip().lower()

            if choice == "r":
                print("\nRescanning...\n")
                time.sleep(2)
                continue

            elif choice == "m":
                test_ssid = input("Test SSID: ").strip()
                break

            elif choice == "q":
                return False, "WiFi selection cancelled.", device_ip

            else:
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(nets):
                        test_ssid = nets[idx - 1][0]
                        break
                except ValueError:
                    pass

                print("❌ Invalid selection.")

    else:
        test_ssid = input("Test SSID: ").strip()

    test_pwd = getpass(f"Password for '{test_ssid}': ")

    print("\nConfiguring device...")
    ok = _post(device_ip, {
        "passcode": passcode,
        "command": "config",
        "primarySsid": test_ssid,
        "primaryPassword": test_pwd
    })

    if not ok:
        return False, "Failed sending config.", device_ip

    print("Waiting for reboot...")
    time.sleep(6)

    print("Connecting laptop...")
    ok, msg = _connect_wifi(test_ssid, test_pwd)
    if not ok:
        return False, msg, device_ip

    host = f"BTWN_{device_mac[-4:]}.local"

    print("Resolving", host)
    new_ip = _resolve(host)

    if not new_ip:
        return False, "Unable to resolve device.", device_ip

    print("Device IP:", new_ip)

    prod = _post(new_ip, {
        "passcode": passcode,
        "command": "product"
    })

    if not prod:
        return False, "Product verification failed.", new_ip

    print("PASS - Device reachable.")

    if input("\nRestore original WiFi? (Y/N): ").lower() != "y":
        return True, "WiFi verified.", new_ip

    print("\nRestoring device WiFi...")

    ok = _post(new_ip, {
        "passcode": passcode,
        "command": "config",
        "primarySsid": original_ssid,
        "primaryPassword": original_pwd
    })

    if not ok:
        return False, "Failed restoring device.", new_ip

    print("Waiting for reboot...")
    time.sleep(6)

    print("Restoring laptop...")
    ok, msg = _connect_wifi(original_ssid, original_pwd)
    if not ok:
        return False, msg, new_ip

    restored_ip = _resolve(host)

    if not restored_ip:
        return False, "Could not rediscover restored device.", new_ip

    prod = _post(restored_ip, {
        "passcode": passcode,
        "command": "product"
    })

    if not prod:
        return False, "Final product verification failed.", restored_ip

    return True, "Device and laptop restored successfully.", restored_ip
