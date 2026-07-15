# BuildTrack Firmware Testing Automation Framework

## Objective

Develop a Python-based automated firmware validation framework for BuildTrack IoT devices that executes system test cases, validates device behavior after configuration changes and reboot cycles, and generates structured test reports (.csv and terminal output) with minimal manual intervention.

The framework is designed to improve testing efficiency, ensure firmware stability across firmware releases, and provide repeatable and consistent validation of firmware features.

---

## Working

1. Enter the following details:
   - Device MAC Address
   - Current Wi-Fi SSID
   - Current Wi-Fi Password

   **Prerequisite:** The device must be configured using SmartConfig and connected to the network.

2. The framework automatically discovers the device using mDNS, executes the configured system test cases, and displays the status of each test in real time.

3. During the Wi-Fi configuration test, the user can choose either of the following:
   - Scan for available Wi-Fi networks and select one from the list (ordered by signal strength).
   - Manually enter the target Wi-Fi SSID and password.

4. After all test cases are completed, a CSV report is generated with the following columns:

   | Timestamp | Test | Expected | Observed | Status |
   |-----------|------|----------|----------|--------|

---

## Test Cases Covered (Current Version)

The current version of the framework validates the following firmware features:

| Test | Description |
|------|-------------|
| Passcode | Configures and verifies the device passcode. |
| SRID | Sets and validates the System Reference ID (SRID). |
| Wi-Fi Configuration | Configures the device Wi-Fi, validates connectivity, and restores the original Wi-Fi configuration. |
| SoftAP Configuration | Configures SoftAP SSID and password. |
| Server Configuration | Verifies Server Type configuration. |
| MQTT Configuration | Configures MQTT server parameters and validates MQTT connection status. |
| MQTT Keep Alive | Configures and verifies the MQTT Keep Alive interval. |
| MQTT Subscribe | Subscribes the device to an MQTT topic. |
| MQTT Subscription List | Retrieves and validates the subscribed topic list. |
| MQTT Unsubscribe | Removes an existing MQTT subscription. |
| MQTT Will Message | Configures the MQTT Last Will message. |
| MQTT Will Retrieval | Retrieves the configured MQTT Will message. |
| MQTT Publish | Publishes data to an MQTT topic. |
| MQTT Publish Retrieval | Retrieves the configured publish information. |
| UDP Configuration | Configures UDP multicast IP, port, and status. |
| Boot Delay | Configures Boot Delay, measures actual reboot delay, validates timing, and restores the default Boot Delay. |
| Product Name | Configures and verifies the Product Name. |
| Device Reboot | Initiates a reboot and validates successful recovery using reboot count and product response. |
| NTP Settings | Retrieves the current NTP configuration. |
| Network Type | Configures and validates the network type. |
| OTA Secure | Enables and verifies OTA Secure mode. |
| IP Type | Configures and validates DHCP/Static IP settings. |
| UZID | Sets a temporary UZID, verifies authentication using the new UZID, restores the original UZID, and validates restoration. |
| Reboot Log | Retrieves and validates the reboot counter. |
| Authentication Path | Retrieves the configured authentication server path. |
| Perform Authentication | Executes device authentication with the configured server. |
| SoftAP Validation | Enables SoftAP, validates connectivity over SoftAP, restores original Wi-Fi, and verifies device accessibility. |
| Board Details | Retrieves board information from the firmware. |
| Maintenance Mode | Retrieves the current maintenance mode status. |
| Touch Flow | Executes touch-specific commands when the device supports touch functionality. |
| Network Reset | Performs a network configuration reset. |
| Hard Reset | Performs a factory reset and validates device reset behavior. |

---

## Technologies Used

- Python 3.x
- Requests
- Subprocess
- CSV
- NetworkManager (`nmcli`)
- Git

---

## Features

- Automated firmware validation
- Automatic device discovery using mDNS
- Wi-Fi configuration validation
- SoftAP validation
- Boot Delay validation
- MQTT configuration and verification
- Reboot validation
- Device parameter verification
- CSV and text-based test report generation
- Modular architecture for easy feature addition

---

## Current Limitations
### Linux : 
Several configuration parameters are currently hardcoded, limiting flexibility.
Limited support for large-scale regression testing.
Automatic IP assignment for the device within a specified network is not yet implemented.

### Windows :

Windows is currently not supported.
Windows support can be added in future releases by replacing Linux-specific networking utilities with platform-independent implementations.
Wi-Fi Configuration, SoftAP Validation, and Boot Delay Validation rely on Linux networking utilities and therefore will not function correctly on Windows in the current implementation.

---

## Future Improvements

- Cross-platform support (Linux & Windows)
- Automatic device IP assignment
- Enhanced regression test execution
- HTML/PDF reporting
- Improved logging and failure diagnostics

---

## Requirements

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Run the framework:

```bash
python3 sys_auto_tw.py
```
