"""
Python Network Automation Tool (PRO v1)
Author: Ivan Bogdanov Ivanov

What this tool does:
1) Loads devices from devices.json
2) Lets you choose:
   - Show Commands (read-only)
   - Config Push (changes config)
3) Connects to every device via SSH (Netmiko)
4) Runs commands
5) Saves outputs to outputs/ and logs to logs/
"""

import json
import os
import logging
from datetime import datetime
from netmiko import ConnectHandler


# ---------------------------
# Folders + Logging (Pro setup)
# ---------------------------
OUTPUT_DIR = "outputs"
LOG_DIR = "logs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "automation.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ---------------------------
# Load devices
# ---------------------------
def load_devices(path="devices.json"):
    """Load a list of devices from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        devices = json.load(f)
    return devices


# ---------------------------
# Connect to device
# ---------------------------
def connect_device(device):
    """Create SSH connection to one device."""
    logging.info(f"Connecting to {device['name']} ({device['host']})")

    conn = ConnectHandler(
        device_type=device["device_type"],
        host=device["host"],
        username=device["username"],
        password=device["password"],
        secret=device.get("secret", "")
    )

    if device.get("secret"):
        conn.enable()

    return conn


# ---------------------------
# SHOW commands mode
# ---------------------------
def run_show_commands(conn, show_commands):
    """Run read-only show commands and return combined output."""
    output = []
    for cmd in show_commands:
        logging.info(f"Running SHOW: {cmd}")
        result = conn.send_command(cmd)
        output.append(f"\n===== {cmd} =====\n{result}")
    return "\n".join(output)


# ---------------------------
# CONFIG push mode
# ---------------------------
def run_config_commands(conn, config_commands):
    """
    Push configuration commands.
    Netmiko uses send_config_set for config mode.
    """
    logging.info("Entering CONFIG mode")
    result = conn.send_config_set(config_commands)
    logging.info("Config pushed successfully")
    return result


# ---------------------------
# Save output to file
# ---------------------------
def save_output(device_name, text, mode):
    """Save output into outputs/ folder with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{mode}_{device_name}_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"📄 Saved → {filepath}")
    logging.info(f"Output saved to {filepath}")


# ---------------------------
# Simple menu for user
# ---------------------------
def menu():
    print("\n=== Python Network Automation Tool ===")
    print("1) Run SHOW commands (safe / read-only)")
    print("2) Push CONFIG commands (makes changes)")
    choice = input("Choose option (1 or 2): ").strip()
    return choice


def main():
    devices = load_devices()
    choice = menu()

    # Safe default commands
    show_commands = [
        "show ip interface brief",
        "show version",
        "show running-config"
    ]

    # Example config commands (you can change later)
    config_commands = [
        "interface loopback 99",
        "description Configured by Ivan's Automation Tool",
        "ip address 99.99.99.99 255.255.255.255",
        "no shutdown"
    ]

    for device in devices:
        try:
            print(f"\n🔌 Connecting to {device['name']} ({device['host']})...")
            conn = connect_device(device)

            if choice == "1":
                print("📡 Running SHOW commands...")
                output = run_show_commands(conn, show_commands)
                save_output(device["name"], output, mode="show")

            elif choice == "2":
                print("⚙️ Pushing CONFIG commands...")
                output = run_config_commands(conn, config_commands)
                save_output(device["name"], output, mode="config")

            else:
                print("❌ Invalid choice. Please run again.")
                conn.disconnect()
                return

            conn.disconnect()
            print(f"✅ Done with {device['name']}")

        except Exception as e:
            print(f"❌ Error on {device['name']}: {e}")
            logging.error(f"Error on {device['name']}: {e}")


if __name__ == "__main__":
    main()
