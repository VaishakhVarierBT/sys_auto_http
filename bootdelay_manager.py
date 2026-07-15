"""
bootdelay_manager.py

Standalone Boot Delay validation module.

Algorithm:
    1. Send {"command": "config", "bootDelay": "<value>"}.
    2. Wait until the device stops responding to ping (BTWN_<last4>.local).
    3. Start timing only after the device is offline.
    4. Ping once every second.
    5. On the first successful ping, stop the timer.
    6. Resolve the device IP via mDNS.
    7. Send the `product` command to verify HTTP is available.
    8. Compare the measured delay against the configured boot delay (+/- tolerance).
    9. Restore bootDelay to 1.
    10. Wait for the second reboot.
    11. Verify the device again with the `product` command.
    12. Return (success, observation, updated_device_ip).

Usage:

    from bootdelay_manager import bootdelay_test

    success, obs, DEVICE_IP = bootdelay_test(
        device_ip=DEVICE_IP,
        device_mac=DEVICE_MAC,
        passcode=PASSCODE_NEW,
        boot_delay=60
    )

    DEVICE_URL = f"http://{DEVICE_IP}/system"
"""

import socket
import subprocess
import time
import requests


# ==============================
# LOW-LEVEL HELPERS
# ==============================
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


def _resolve(host):
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def _ping_ok(hostname):
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "1", hostname],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0


def _wait_offline(hostname):
    """Block until the device stops responding to ping."""
    print("\nWaiting for device to go offline...")
    while _ping_ok(hostname):
        time.sleep(0.5)
    print("Device is offline.")


def _wait_online_timed(hostname, hard_timeout):
    """
    Ping once per second starting now. Returns elapsed seconds on the
    first successful ping, or None if hard_timeout is exceeded.
    """
    start = time.time()
    while True:
        if _ping_ok(hostname):
            return round(time.time() - start, 1)

        if time.time() - start > hard_timeout:
            return None

        time.sleep(1)


def _verify_product(hostname, passcode):
    """
    Resolve current IP via mDNS and confirm HTTP/product command works.
    Returns (ok, resolved_ip, product_response_or_None).
    """
    observed_ip = _resolve(hostname)
    if not observed_ip:
        return False, None, None

    prod = _post(observed_ip, {"passcode": passcode, "command": "product"})
    if not prod:
        return False, observed_ip, None

    return True, observed_ip, prod


# ==============================
# MAIN TEST
# ==============================
def bootdelay_test(
    device_ip,
    device_mac,
    passcode,
    boot_delay=60,
    tolerance=3,
    restore_delay=1,
    restore_timeout_margin=60,
):
    """
    Validates a configured boot delay, then restores bootDelay to 1 and
    confirms the device recovers cleanly on the follow-up reboot.

    Returns:
        success (bool), observation (str), updated_device_ip (str)
    """
    hostname = f"BTWN_{device_mac[-4:]}.local"
    current_ip = device_ip

    # ----------------------------------------
    # PHASE 1: Configure & measure boot delay
    # ----------------------------------------
    print(f"\nSetting Boot Delay = {boot_delay}s")

    res = _post(
        current_ip,
        {
            "passcode": passcode,
            "command": "config",
            "bootDelay": str(boot_delay),
        },
    )

    if not res:
        return False, "Failed to configure Boot Delay.", current_ip

    _wait_offline(hostname)

    print(f"Measuring Boot Delay ({boot_delay}s)...")
    elapsed = _wait_online_timed(hostname, hard_timeout=boot_delay + 60)

    if elapsed is None:
        return False, "Device never came online after Boot Delay config.", current_ip

    print(f"Ping response after {elapsed}s")

    ok, observed_ip, prod = _verify_product(hostname, passcode)
    if not ok:
        if observed_ip is None:
            return False, "Ping received but mDNS resolution failed.", current_ip
        return (
            False,
            "Ping successful but Product command failed.",
            observed_ip,
        )

    current_ip = observed_ip
    print("\nProduct command successful.")

    print(f"\nExpected Boot Delay : {boot_delay}s")
    print(f"Observed Boot Delay : {elapsed}s")

    within_tolerance = abs(elapsed - boot_delay) <= tolerance

    phase1_obs = (
        f"{'PASS' if within_tolerance else 'FAIL'} | "
        f"Expected={boot_delay}s Observed={elapsed}s"
    )

    if not within_tolerance:
        return False, phase1_obs, current_ip

    # ----------------------------------------
    # PHASE 2: Restore bootDelay to 1 and verify recovery
    # ----------------------------------------
    print(f"\nRestoring Boot Delay = {restore_delay}s")

    restore_res = _post(
        current_ip,
        {
            "passcode": passcode,
            "command": "config",
            "bootDelay": str(restore_delay),
        },
    )

    if not restore_res:
        return (
            False,
            f"{phase1_obs} | Failed to restore Boot Delay to {restore_delay}s.",
            current_ip,
        )

    _wait_offline(hostname)

    print(f"Waiting for second reboot (bootDelay={restore_delay}s)...")
    restore_elapsed = _wait_online_timed(
        hostname, hard_timeout=restore_delay + restore_timeout_margin
    )

    if restore_elapsed is None:
        return (
            False,
            f"{phase1_obs} | Device never came online after Boot Delay restore.",
            current_ip,
        )

    ok, observed_ip, prod = _verify_product(hostname, passcode)
    if not ok:
        if observed_ip is None:
            return (
                False,
                f"{phase1_obs} | Restore ping received but mDNS resolution failed.",
                current_ip,
            )
        return (
            False,
            f"{phase1_obs} | Restore ping successful but Product command failed.",
            observed_ip,
        )

    current_ip = observed_ip

    final_obs = (
        f"{phase1_obs} | Restore=PASS bootDelay reset to {restore_delay}s, "
        f"reboot_dt={restore_elapsed}s, product verified"
    )

    return True, final_obs, current_ip