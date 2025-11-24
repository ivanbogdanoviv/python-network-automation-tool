"""
Python Network Automation Tool
Author: Ivan Bogdanov Ivanov
Purpose: Connect to Cisco devices via SSH and run show/config commands.
"""

import json
from netmiko import ConnectHandler
from datetime import datetime


def load_devices(path="devices.json"):
    """Load device list from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def connect_and_run(device, commands):
    """
    Connect to a device and run a list of commands.
    Returns output as a string.
    """
    print(f"\n🔌 Connecting to {device['name']} ({device['host']}) ...")

    conn = ConnectHandler(
        device_type=device["device_type"],
        host=device["host"],
        username=device["username"],
        password=device["password"],
        secret=device.get("secret", "")
    )

    if device.get("secret"):
        conn.enable()

    output = []
    for cmd in commands:
        print(f"➡ Running: {cmd}")
        result = conn.send_command(cmd)
        output.append(f"\n===== {cmd} =====\n{result}")

    conn.disconnect()
    print(f"✅ Done with {device['name']}")
    return "\n".join(output)


def save_output(device_name, text):
    """Save command output to a timestamped file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"output_{device_name}_{timestamp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"📄 Output saved to {filename}")


def main():
    print("=== Python Network Automation Tool ===")

    devices = load_devices()

    commands = [
        "show ip interface brief",
        "show version",
        "show running-config"
    ]

    for device in devices:
        try:
            output = connect_and_run(device, commands)
            save_output(device["name"], output)
        except Exception as e:
            print(f"❌ Error on {device['name']}: {e}")


if __name__ == "__main__":
    main()
