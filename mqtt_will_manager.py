import json

TEST_WILL = {
    "status": "1",
    "topic": "testtopic9876",
    "payload": "testpayload9876",
    "qos": "1",
    "retain": "1"
}


def print_json(title, data):
    print(f"\n========== {title} ==========")
    print(json.dumps(data, indent=4))


def mqtt_connected(send_request, passcode):

    product, _ = send_request({
        "passcode": passcode,
        "command": "product"
    })

    if not product:
        return False

    mqtt_state = product.get("mqttState")

    print(f"\nMQTT State : {mqtt_state}")

    return mqtt_state == ["1", "1"]


def get_will(send_request, passcode):

    res, _ = send_request({
        "passcode": passcode,
        "command": "getWill"
    })

    if res:
        print_json("getWill", res)

    return res


def set_will_test(send_request, passcode):

    print("\n========== SetWill Test ==========")

    if not mqtt_connected(send_request, passcode):
        return False, "MQTT is not connected."

    #
    # Store current configuration
    #
    current = get_will(send_request, passcode)

    if not current:
        return False, "Unable to fetch current Will configuration."

    will = current.get("will", [])

    if will:
        old = will[0]
    else:
        old = {
            "status": "0",
            "topic": "",
            "payload": "",
            "qos": "0",
            "retain": "0"
        }

    #
    # Configure test Will
    #
    print("\nSetting test Will...")

    res, _ = send_request({
        "passcode": passcode,
        "command": "setWill",
        **TEST_WILL
    })

    if not res:
        return False, "No response from setWill."

    print_json("setWill Response", res)

    returned = res.get("will", [])

    if not returned:
        return False, "No Will returned."

    returned = returned[0]

    for key, value in TEST_WILL.items():
        if returned.get(key) != value:
            return False, f"{key} mismatch after setWill."

    #
    # Verify using getWill
    #
    verify = get_will(send_request, passcode)

    if not verify:
        return False, "Unable to verify using getWill."

    verify = verify.get("will", [])

    if not verify:
        return False, "getWill returned empty."

    verify = verify[0]

    for key, value in TEST_WILL.items():
        if verify.get(key) != value:
            return False, f"{key} mismatch after getWill."

    #
    # Restore original configuration
    #
    print("\nRestoring original Will configuration...")

    res, _ = send_request({
        "passcode": passcode,
        "command": "setWill",
        "status": old.get("status", "0"),
        "topic": old.get("topic", ""),
        "payload": old.get("payload", ""),
        "qos": old.get("qos", "0"),
        "retain": old.get("retain", "0")
    })

    if not res:
        return False, "Unable to restore original Will."

    restored = get_will(send_request, passcode)

    if not restored:
        return False, "Unable to verify restored Will."

    restored = restored.get("will", [])

    if restored:
        restored = restored[0]

        for key in ["status", "topic", "payload", "qos", "retain"]:
            if restored.get(key) != old.get(key):
                return False, f"Restore failed ({key})."

    print("\nOriginal Will restored successfully.")

    return True, "Will configured, verified and restored successfully."


def get_will_test(send_request, passcode):

    print("\n========== GetWill Test ==========")

    if not mqtt_connected(send_request, passcode):
        return False, "MQTT is not connected."

    res = get_will(send_request, passcode)

    if not res:
        return False, "No response."

    will = res.get("will", [])

    if not will:
        return False, "Will configuration missing."

    return True, json.dumps(res, indent=4)