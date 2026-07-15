# BuildTrack Firmware Testing Automation Framework

## Objective

Develop a Python-based automated firmware validation framework for BuildTrack IoT devices that executes system test cases, validates device behavior after configuration changes and reboot cycles, and generates structured test reports with minimal manual intervention.

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

## Technologies Used

- Python 3.x
- Requests
- Socket Programming
- Subprocess
- JSON
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

- Several configuration parameters are currently hardcoded, limiting flexibility.
- Limited support for large-scale regression testing.
- Device network configuration is partially manual.
- Automatic IP assignment for the device within a specified network is not yet implemented.
- Currently supports **Linux only**.
- Windows support can be added in future releases by replacing Linux-specific networking utilities with platform-independent implementations.
- Wi-Fi Configuration, SoftAP Validation, and Boot Delay Validation may not function correctly on Windows.

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
