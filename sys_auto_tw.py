import requests
import time
import re
import csv
import subprocess
from datetime import datetime
import time
import json
from getpass import getpass
from wifi_manager_v11 import configure_wifi_v11
from softap_manager_v11 import softap_enable_v11
from bootdelay_manager import bootdelay_test

# =========================
# LOGGING (NON-INTRUSIVE)
# =========================
CSV_FILE = "test_results.csv"
TXT_FILE = "test_report.txt"

def init_logs():
    # CSV header
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Test", "Expected", "Observed", "Status"])

    # TXT header
    with open(TXT_FILE, "w") as f:
        f.write("===== TEST REPORT =====\n\n")

def log_csv(name, expected, observed, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, name, expected, observed, status])

def log_txt(name, expected, observed, status):
    with open(TXT_FILE, "a") as f:
        f.write(f"{name}\n")
        f.write(f"Expected: {expected}\n")
        f.write(f"Observed: {observed}\n")
        f.write(f"Result: {status}\n")
        f.write("----------------------------------------\n")

# =========================
# INPUT VALIDATION
# =========================
def is_valid_ip(ip):
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    return re.match(pattern, ip) and all(0 <= int(p) <= 255 for p in ip.split("."))

def is_valid_mac(mac):
    return bool(re.match(r"^([0-9A-Fa-f]{2}[:\-]?){5}[0-9A-Fa-f]{2}$", mac))

def normalize_mac(mac):
    return re.sub(r"[:\-]", "", mac).upper()

# =========================
# USER INPUT
# =========================

import socket

# Original WiFi (used later by WiFi & SoftAP managers)
while True:
    ORIGINAL_WIFI_SSID = input("Enter Original WiFi SSID: ").strip()

    if ORIGINAL_WIFI_SSID:
        break

    print("❌ SSID cannot be empty")

ORIGINAL_WIFI_PASSWORD = getpass("Enter Original WiFi Password: ")

# Device MAC
while True:

    raw_mac = input("Enter Device MAC: ").strip()

    if is_valid_mac(raw_mac):
        DEVICE_MAC = normalize_mac(raw_mac)
        break

    print("❌ Invalid MAC")

PASSCODE_NEW = DEVICE_MAC

# Resolve IP using mDNS
hostname = f"BTWN_{DEVICE_MAC[-4:]}.local"

print(f"\nSearching for device ({hostname})...")

while True:

    try:

        DEVICE_IP = socket.gethostbyname(hostname)

        print(f"\n✅ Device Found")
        print(f"Hostname : {hostname}")
        print(f"IP       : {DEVICE_IP}")

        confirm = input("\nContinue with this device? (Y/N): ").strip().lower()

        if confirm == "y":
            break

        print("Aborted by user.")
        exit()

    except socket.gaierror:

        retry = input(
            "❌ Device not found. Retry? (Y/N): "
        ).strip().lower()

        if retry != "y":
            exit()

        time.sleep(2)

DEVICE_URL = f"http://{DEVICE_IP}/system"

HEADERS = {"Content-Type": "application/json"}
# =========================
# REQUEST + LATENCY
# =========================
def send_request(payload, retries=5, wait=2):
    for _ in range(retries):
        try:
            start = time.time()
            r = requests.post(DEVICE_URL, json=payload, headers=HEADERS, timeout=5)
            latency = int((time.time() - start) * 1000)
            if r.status_code == 200:
                return r.json(), latency
        except Exception as e:
            print(f"⚠️ {e}")
        time.sleep(wait)
    return None, None

# =========================
# PRODUCT + VERIFY
# =========================
def get_product():
    return send_request({"passcode": PASSCODE_NEW, "command": "product"})

def verify_fields(expected):
    res, lat = get_product()
    if not res:
        return False, "No response", lat

    ok = True
    for k, v in expected.items():
        if str(res.get(k)) != str(v):
            ok = False

    return ok, str(res), lat

# =========================
# REBOOT LOG (NEW)
# =========================
def get_reboot_log():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "rebootLog"})
    if not res:
        return None, lat
    try:
        return int(res.get("rebootCount", -1)), lat
    except:
        return -1, lat

# =========================
# REBOOT DETECTION
# =========================
def wait_for_reboot(timeout=40):
    start = time.time()
    down = False
    down_time = None

    while time.time() - start < timeout:
        try:
            requests.post(DEVICE_URL, json={"command": "product"}, timeout=2)
            if down:
                return True, round(time.time() - down_time, 2)
        except:
            if not down:
                down = True
                down_time = time.time()
        time.sleep(1)

    return False, 0

def wait_product():
    for _ in range(15):
        res, _ = get_product()
        if res:
            return True, str(res)
        time.sleep(2)
    return False, "No response"

# =========================
# CORE FLOW (UPDATED)
# =========================
def config_flow(payload, expected=None):
    before_count, _ = get_reboot_log()

    _, config_lat = send_request(payload)

    rebooted, dt = wait_for_reboot()
    up, prod = wait_product()

    after_count, _ = get_reboot_log()

    reboot_ok = (
        before_count is not None and
        after_count is not None and
        after_count > before_count
    )

    if expected:
        ok, obs, verify_lat = verify_fields(expected)
    else:
        ok, obs, verify_lat = True, prod, 0

    final = (
        f"{obs} | reboot_dt={dt}s | "
        f"rebootCount:{before_count}->{after_count} | "
        f"config_lat={config_lat}ms | verify_lat={verify_lat}ms"
    )

    return rebooted and up and ok and reboot_ok, final

# =========================
# TEST FUNCTIONS
# =========================
def set_passcode():
    return config_flow({"passcode": PASSCODE_NEW, "command": "config", "setPasscode": PASSCODE_NEW})

def set_srid():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "systemSrid": "123456789ABC"},
        {"srID": "123456789ABC"}
    )


def configure_wifi():
    global DEVICE_IP, DEVICE_URL

    success, observation, DEVICE_IP = configure_wifi_v11(
        DEVICE_IP,
        DEVICE_MAC,
        PASSCODE_NEW,
        ORIGINAL_WIFI_SSID,
        ORIGINAL_WIFI_PASSWORD
    )

    DEVICE_URL = f"http://{DEVICE_IP}/system"

    return success, observation

def configure_softap():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config",
         "softapSsid": f"BTWN_{DEVICE_MAC[-4:]}",
         "softapPassword": "123456789"}
    )

def set_server():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "serverType": "5"},
        {"serverType": "5"}
    )

def set_mqtt():

    print("\nConfiguring MQTT...")

    success, obs = config_flow(
        {
            "passcode": PASSCODE_NEW,
            "command": "config",
            "serverType": "2",
            "mqttServerName": "rnd-ms.buildtrack.in",
            "mqttServerPort": "1899",
            "mqttUsername": "btmqtt",
            "mqttPassword": "btmqtt123",
            "mqttSsl": "1",
            "setAuthPath":"https://rnd-ms.buildtrack.in/service/ota/v1/getFP/1/"
        }
    )

    if not success:
        return False, obs

    print("Waiting 25 seconds for MQTT connection...")

    time.sleep(25)

    product, _ = get_product()

    if not product:
        return False, "Unable to fetch Product after MQTT configuration."

    mqtt_state = product.get("mqttState")

    print(f"MQTT State : {mqtt_state}")

    if mqtt_state == ["1", "1"]:
        return True, "MQTT Connected Successfully."

    return False, f"MQTT Connection Failed. mqttState={mqtt_state}"

def configure_udp():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config",
         "udpIp": "239.0.1.5",
         "udpPort": "49152",
         "udpStatus": "1"}
    )

def set_boot_delay():
    """
    Delegates entirely to bootdelay_manager.bootdelay_test(), which now
    handles the full lifecycle: set bootDelay -> measure reboot ->
    verify -> restore bootDelay to 1 -> verify second reboot.
    Only DEVICE_IP/DEVICE_URL bookkeeping happens here; the rest of the
    test framework (config_flow, logging, runner) is untouched.
    """
    global DEVICE_IP, DEVICE_URL

    success, observation, DEVICE_IP = bootdelay_test(
        device_ip=DEVICE_IP,
        device_mac=DEVICE_MAC,
        passcode=PASSCODE_NEW,
        boot_delay=60
    )

    DEVICE_URL = f"http://{DEVICE_IP}/system"

    return success, observation

def set_product_name():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "productName": "Test_Device"},
        {"productName": "Test_Device"}
    )

# MQTT ops
def subscribe_topic():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "subscribe",
                             "topic": f"{DEVICE_MAC}/status", "qos": "1"})
    return res is not None, f"lat={lat}ms"

def unsubscribe_topic():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "unsubscribe",
                             "topic": f"{DEVICE_MAC}/status"})
    return res is not None, f"lat={lat}ms"

def get_subs():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "getSubsList"})
    return res is not None, f"lat={lat}ms"

def set_will():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "setWill"})
    return res is not None, f"lat={lat}ms"

def get_will():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "getWill"})
    return res is not None, f"lat={lat}ms"

def configure_ping():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config",
         "pingIPAddr1": DEVICE_IP,
         "pingIPAddr2": "8.8.8.8"}
    )

def reboot():
    before_count, _ = get_reboot_log()

    _, lat = send_request({"passcode": PASSCODE_NEW, "command": "reboot"})

    rebooted, dt = wait_for_reboot()
    up, obs = wait_product()

    after_count, _ = get_reboot_log()

    reboot_ok = (
        before_count is not None and
        after_count is not None and
        after_count > before_count
    )

    return rebooted and up and reboot_ok, (
        f"{obs} | reboot_dt={dt}s | "
        f"rebootCount:{before_count}->{after_count} | cmd_lat={lat}ms"
    )

def ntp_settings():
    res, _ = send_request({"passcode": PASSCODE_NEW, "command": "ntpSettings"})
    return res is not None, str(res)

def set_network_type():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "networkType": "1"},
        {"networkType": "1"}
    )

def set_ota_secure():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "otaSecure": "1"},
        {"otaSecure": "1"}
    )

def configure_network_settings():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "ipType": "0"},
        {"ipType": "0"}
    )
def set_mqtt_alive():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "config", "mqttSetAlive": "60"},
        {"mqttSetAlive": "60"}
    )

def publish_topic():
    res, lat = send_request({
        "passcode": PASSCODE_NEW,
        "command": "publish",
        "topic": "test/topic",
        "qos": "0"
    })
    return res is not None, f"lat={lat}ms"

def get_publish():
    res, lat = send_request({
        "passcode": PASSCODE_NEW,
        "command": "getPublish"
    })
    return res is not None, f"lat={lat}ms"

def sensorscantime():
    res, lat = send_request({
        "passcode": PASSCODE_NEW,
        "command": "sensorcscantime",
        "value": "120"
    })

    if not res:
        return False, "No response"

    ok = res.get("command") == "badCommand"
    return ok, str(res)
def get_auth():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "getAuthPath"})
    return res is not None, str(res)

def set_auth():
    return config_flow(
        {
            "passcode": PASSCODE_NEW,
            "command": "setAuthPath",
            "authPath": "https://ms.buildtrack.in/service/ota/v1/getFP/0/"
        }
    )

def perform_auth():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "performAuth"})
    return res is not None, f"lat={lat}ms"
def get_board_detail():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "getBoardDetail"})
    return res is not None, str(res)

def get_maintenance():
    res, lat = send_request({"passcode": PASSCODE_NEW, "command": "getMaintenanceMode"})
    return res is not None, str(res)

def set_maintenance():
    return config_flow(
        {"passcode": PASSCODE_NEW, "command": "setMaintenanceMode", "value": "1"}
    )
def set_uzid():

    TEST_UZID = "112233445566"

    print("\nSetting UZID...")

    # --------------------------
    # Set Test UZID
    # --------------------------
    res, _ = send_request(
        {
            "passcode": PASSCODE_NEW,
            "command": "systemUzid",
            "value": TEST_UZID
        }
    )

    if not res:
        return False, "Failed to set UZID."

    # --------------------------
    # Verify using new UZID
    # --------------------------
    print("Verifying new UZID...")

    res, _ = send_request(
        {
            "passcode": TEST_UZID,
            "command": "product"
        }
    )

    if not res:
        return False, "Product failed with new UZID."

    print("New UZID verified.")

    # --------------------------
    # Restore original UZID
    # --------------------------
    print("Restoring original UZID...")

    res, _ = send_request(
        {
            "passcode": TEST_UZID,
            "command": "systemUzid",
            "value": DEVICE_MAC
        }
    )

    if not res:
        return False, "Failed to restore original UZID."

    # --------------------------
    # Verify original UZID
    # --------------------------
    print("Verifying restored UZID...")

    res, _ = send_request(
        {
            "passcode": DEVICE_MAC,
            "command": "product"
        }
    )

    if not res:
        return False, "Original UZID verification failed."

    return True, "UZID changed, verified and restored successfully."
def softap_enable():

    global DEVICE_IP, DEVICE_URL

    success, observation, DEVICE_IP = softap_enable_v11(

        device_ip=DEVICE_IP,

        device_mac=DEVICE_MAC,

        passcode=PASSCODE_NEW,

        original_ssid=ORIGINAL_WIFI_SSID,

        original_password=ORIGINAL_WIFI_PASSWORD,

        softap_ssid=f"BTWN_{DEVICE_MAC[-4:]}",

        softap_password="123456789"
    )

    DEVICE_URL = f"http://{DEVICE_IP}/system"

    return success, observation

def touch_flow():
    res, _ = send_request({"passcode": PASSCODE_NEW, "command": "product"})
    if not res:
        return False, "No product response"

    if "Touch" not in res.get("type", ""):
        return True, "Skipped (not touch device)"

    ok1, _ = send_request({"passcode": PASSCODE_NEW, "command": "touchDelay", "delayTime": "50"})
    ok2, _ = send_request({"passcode": PASSCODE_NEW, "command": "getEnableTouchPin"})
    ok3, _ = send_request({
        "passcode": PASSCODE_NEW,
        "command": "enableTouchPin",
        "params": ["1","1","1","1","1","1"]
    })

    return (ok1 and ok2 and ok3), "Touch flow executed"
def network_reset():
    res, lat = send_request({
        "passcode": PASSCODE_NEW,
        "command": "reset",
        "value": "networkReset"
    })
    return res is not None, f"lat={lat}ms"

def final_reset():
    res, lat = send_request({
        "passcode": PASSCODE_NEW,
        "command": "reset",
        "value": "hardReset"
    })

    if not res:
        return False, "Reset command failed"

    print("Waiting for device to reset...")
    time.sleep(8)

    # Check if device is still reachable
    reachable = True
    try:
        requests.post(DEVICE_URL, timeout=3)
    except:
        reachable = False

    if not reachable:
        return True, "Device unreachable after hard reset (expected)"

    return False, "Device still reachable → reset failed"

def write_device_info():
    product, _ = get_product()
    board, _ = get_board_detail()

    with open(TXT_FILE, "a") as f:
        f.write("===== DEVICE INFORMATION =====\n\n")

        f.write(f"Original WiFi SSID : {ORIGINAL_WIFI_SSID}\n")
        f.write(f"Device MAC         : {DEVICE_MAC}\n")

        if product:
            f.write(f"Product Type       : {product.get('type', 'N/A')}\n")

        f.write("\nProduct Response:\n")
        f.write(json.dumps(product, indent=4))

        f.write("\n\nBoard Detail Response:\n")
        f.write(json.dumps(board, indent=4))

        f.write("\n\n========================================\n\n")
# =========================
# RUNNER
# =========================
def run_test(name, func):
    print(f"\n▶ {name}")
    start = time.time()

    try:
        success, obs = func()
    except Exception as e:
        success, obs = False, str(e)

    total = round(time.time() - start, 2)
    status = "PASS" if success else "FAIL"

    print(f"{status} ({total}s)")
    print(obs)

    return {
        "test_name": name,
        "observed": obs,
        "status": status,
        "time": total
    }

# =========================
# MAIN
# =========================
def run_all():
    init_logs()
    write_device_info()
    tests = [
        ("Passcode", set_passcode, "Passcode should be set"),
        ("SRID", set_srid, "srID = 123456789ABC"),
        ("WiFi", configure_wifi, "SSID=Wifi and IP"),
        ("SoftAP Config", configure_softap, "SoftAP configured"),
        ("Server", set_server, "serverType=5"),
        ("MQTT & SetAuthPath", set_mqtt, "serverType=2"),
        ("MQTT Alive", set_mqtt_alive, "mqttSetAlive=60"),
        ("Subscribe", subscribe_topic, "MQTT subscribe"),
        ("GetSubs", get_subs, "Subs list"),
        ("Unsubscribe", unsubscribe_topic, "MQTT unsubscribe"),
        ("SetWill", set_will, "Will set"),
        ("GetWill", get_will, "Will get"),
        ("Publish", publish_topic, "Publish ok"),
        ("GetPublish", get_publish, "Publish fetch"),
        ("UDP", configure_udp, "UDP config"),
        ("BootDelay", set_boot_delay, "bootDelay=5"),
        ("ProductName", set_product_name, "productName"),
        #("Ping", configure_ping, "Ping config"),
        ("Reboot", reboot, "Device reboot"),
        ("NTP", ntp_settings, "NTP response"),
        ("NetworkType", set_network_type, "networkType=1"),
        ("OTASecure", set_ota_secure, "otaSecure=1"),
        ("IPType", configure_network_settings, "ipType=0"),
        #("Sensor Scan Time", sensorscantime, "badCommand expected"),
        ("UZID", set_uzid, "UZID set"),
        ("RebootLog", get_reboot_log, "rebootLog fetch"),
        ("GetAuth", get_auth, "Auth path"),
        #("SetAuth", set_auth, "Auth set"),
        ("PerformAuth", perform_auth, "Auth success"),
        ("SoftAP Enable", softap_enable, "SoftAP Pass"),
        ("BoardDetail", get_board_detail, "Board info"),
        ("GetMaintenance", get_maintenance, "Maintenance get"),
        #("SetMaintenance", set_maintenance, "Maintenance set"),
        ("TouchFlow", touch_flow, "Touch test"),
        ("NetworkReset", network_reset, "Network reset"),
        ("FinalReset", final_reset, "Hard reset"),
    ]

    results = []

    for name, func, expected in tests:
        print(f"\n▶ {name}")
        start = time.time()

        try:
            success, obs = func()
        except Exception as e:
            success, obs = False, str(e)

        total = round(time.time() - start, 2)
        status = "PASS" if success else "FAIL"

        print(f"{status} ({total}s)")
        print(obs)

        observed_full = f"{obs} | total_time={total}s"

        # 🔹 LOGGING (ADDED, DOES NOT TOUCH CORE FLOW)
        log_csv(name, expected, observed_full, status)
        log_txt(name, expected, observed_full, status)

        results.append({
            "test_name": name,
            "observed": observed_full,
            "status": status,
            "time": total
        })

    print("\n==== SUMMARY ====")
    for r in results:
        print(f"{r['test_name']}: {r['status']}")

if __name__ == "__main__":
    run_all()