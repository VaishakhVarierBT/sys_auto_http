import json


# ==========================================================
# Internal Helpers
# ==========================================================

def _print_json(title, data):
    print(f"\n========== {title} ==========")
    print(json.dumps(data, indent=4))


def _reboot_and_wait(
    send_request,
    get_reboot_log,
    wait_for_reboot,
    wait_product,
    passcode
):
    """
    Reboot the device and verify reboot completed successfully.
    """

    before_count, _ = get_reboot_log()

    _, _ = send_request({
        "passcode": passcode,
        "command": "reboot"
    })

    rebooted, reboot_time = wait_for_reboot()

    up, _ = wait_product()

    after_count, _ = get_reboot_log()

    reboot_ok = (
        rebooted and
        up and
        before_count is not None and
        after_count is not None and
        after_count > before_count
    )

    if reboot_ok:
        print(f"\nDevice rebooted successfully ({reboot_time}s)")
    else:
        print("\nDevice reboot verification failed.")

    return reboot_ok


# ==========================================================
# Get Subscription List
# ==========================================================

def get_subs_list(send_request, passcode):

    res, _ = send_request({
        "passcode": passcode,
        "command": "getSubsList"
    })

    if not res:
        return False, None

    _print_json("Current Subscription List", res)

    return True, res


# ==========================================================
# Subscribe
# ==========================================================

def subscribe_topic(
    send_request,
    get_reboot_log,
    wait_for_reboot,
    wait_product,
    passcode
):

    topic = input("\nEnter topic to subscribe: ").strip()

    if not topic:
        return False, "Topic cannot be empty."

    qos = input("Enter QoS (0/1) [Default=0]: ").strip()

    if qos not in ("0", "1"):
        qos = "0"

    print(f"\nSubscribing to '{topic}' (QoS={qos})...")

    res, _ = send_request({
        "passcode": passcode,
        "command": "subscribe",
        "topic": topic,
        "qos": qos
    })

    if not res:
        return False, "No response from device."

    _print_json("Subscribe Response", res)

    if res.get("status") != "success":
        return False, f"Subscribe failed ({res.get('status')})"

    print("\nRebooting device...")

    if not _reboot_and_wait(
        send_request,
        get_reboot_log,
        wait_for_reboot,
        wait_product,
        passcode
    ):
        return False, "Device failed to reboot."

    ok, subs = get_subs_list(send_request, passcode)

    if not ok:
        return False, "Failed to fetch subscription list."

    if topic in json.dumps(subs):

        print(f"\nPASS : Topic '{topic}' found.")

        return True, f"Topic '{topic}' successfully subscribed."

    return False, f"Topic '{topic}' not present after reboot."


# ==========================================================
# Unsubscribe
# ==========================================================

def unsubscribe_topic(
    send_request,
    get_reboot_log,
    wait_for_reboot,
    wait_product,
    passcode
):

    topic = input("\nEnter topic to unsubscribe: ").strip()

    if not topic:
        return False, "Topic cannot be empty."

    print(f"\nUnsubscribing '{topic}'...")

    res, _ = send_request({
        "passcode": passcode,
        "command": "unsubscribe",
        "topic": topic
    })

    if not res:
        return False, "No response from device."

    _print_json("Unsubscribe Response", res)

    # badCommand = not subscribed OR default topic
    if res.get("command") == "badCommand":
        return False, "Device returned badCommand."

    print("\nRebooting device...")

    if not _reboot_and_wait(
        send_request,
        get_reboot_log,
        wait_for_reboot,
        wait_product,
        passcode
    ):
        return False, "Device failed to reboot."

    ok, subs = get_subs_list(send_request, passcode)

    if not ok:
        return False, "Failed to fetch subscription list."

    if topic in json.dumps(subs):

        return False, f"Topic '{topic}' is still present."

    print(f"\nPASS : Topic '{topic}' removed.")

    return True, f"Topic '{topic}' successfully unsubscribed."