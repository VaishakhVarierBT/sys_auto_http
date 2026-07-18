import json


TEST_TOPIC = "testtopic9876"
TEST_QOS = "0"


# ==========================================================
# Helpers
# ==========================================================

def _print_json(title, data):
    print(f"\n========== {title} ==========")
    print(json.dumps(data, indent=4))


def _mqtt_connected(send_request, passcode):

    product, _ = send_request({
        "passcode": passcode,
        "command": "product"
    })

    if not product:
        return False, None

    mqtt_state = product.get("mqttState")

    print(f"\nMQTT State : {mqtt_state}")

    return mqtt_state == ["1", "1"], product


def _get_publish(send_request, passcode):

    res, _ = send_request({
        "passcode": passcode,
        "command": "getPublish"
    })

    if not res:
        return None

    _print_json("Current Publish Configuration", res)

    return res


# ==========================================================
# Main Test
# ==========================================================

def publish_test(send_request, passcode):

    print("\n========== Publish Test ==========")

    #
    # Step 1 : MQTT Connected?
    #
    ok, product = _mqtt_connected(send_request, passcode)

    if not ok:
        return False, "MQTT is not connected."

    #
    # Step 2 : Store current publish configuration
    #
    current = _get_publish(send_request, passcode)

    if not current:
        return False, "Unable to fetch current publish configuration."

    publish = current.get("publish", [])

    if not publish:
        return False, "Publish configuration missing."

    old_topic = publish[0]["topic"]
    old_qos = publish[0]["qos"]

    print(f"\nCurrent Topic : {old_topic}")
    print(f"Current QoS   : {old_qos}")

    #
    # Step 3 : Change publish topic
    #
    print(f"\nChanging publish topic to '{TEST_TOPIC}'")

    res, _ = send_request({
        "passcode": passcode,
        "command": "publish",
        "topic": TEST_TOPIC,
        "qos": TEST_QOS
    })

    if not res:
        return False, "No response to publish command."

    _print_json("Publish Response", res)

    if res.get("command") != "success":
        return False, "Publish command failed."

    #
    # Step 4 : Verify using getPublish
    #
    verify = _get_publish(send_request, passcode)

    if not verify:
        return False, "Unable to verify publish configuration."

    new_publish = verify.get("publish", [])

    if not new_publish:
        return False, "Publish configuration missing."

    if (
        new_publish[0]["topic"] != TEST_TOPIC
        or
        new_publish[0]["qos"] != TEST_QOS
    ):
        return False, "Publish configuration verification failed."

    print("\nPASS : Publish topic successfully updated.")

    #
    # Step 5 : Restore original publish topic
    #
    print("\nRestoring original publish configuration...")

    res, _ = send_request({
        "passcode": passcode,
        "command": "publish",
        "topic": old_topic,
        "qos": old_qos
    })

    if not res:
        return False, "Failed to restore publish configuration."

    if res.get("command") != "success":
        return False, "Restore publish failed."

    #
    # Step 6 : Verify restoration
    #
    restored = _get_publish(send_request, passcode)

    if not restored:
        return False, "Unable to verify restoration."

    restored_publish = restored.get("publish", [])

    if not restored_publish:
        return False, "Restored publish configuration missing."

    if (
        restored_publish[0]["topic"] != old_topic
        or
        restored_publish[0]["qos"] != old_qos
    ):
        return False, "Original publish configuration not restored."

    print("\nPASS : Original publish configuration restored.")

    return True, (
        f"Changed publish topic to '{TEST_TOPIC}' "
        f"and restored to '{old_topic}'."
    )


# ==========================================================
# Standalone getPublish
# ==========================================================

def get_publish_test(send_request, passcode):

    print("\n========== Get Publish ==========")

    ok, _ = _mqtt_connected(send_request, passcode)

    if not ok:
        return False, "MQTT is not connected."

    res = _get_publish(send_request, passcode)

    if not res:
        return False, "No response."

    return True, json.dumps(res, indent=4)