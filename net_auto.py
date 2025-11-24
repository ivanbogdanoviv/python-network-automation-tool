"""
Python Network Automation Tool (PRO v2)
Author: Ivan Bogdanov Ivanov

PRO v2 Features:
- Menu-driven (SHOW vs CONFIG)
- Custom commands or load from file
- Dry-run safety mode for config pushes
- Multi-device execution from devices.json
- Timestamped outputs to /outputs
- Logs to /logs/automation.log
- Session summary CSV to /reports
- Colorized terminal output
"""

import json
import os
import csv
import logging
from datetime import datetime
from netmiko import ConnectHandler
from colorama import Fore, Style, init

# enable color output on Windows too
init(autoreset=True)

# ---------------------------
# Folders + Logging
# ---------------------------
OUTPUT_DIR = "outputs"
LOG_DIR = "logs"
REPORT_DIR = "reports"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "automation.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------
# Load devices
# ---------------------------
def load_devices(path="devices.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------
# Connect to device
# ---------------------------
def connect_device(device):
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
# Command helpers
# ---------------------------
def load_commands_from_file(filename):
    """One command per line. Ignoring empty lines."""
    commands = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            cmd = line.strip()
            if cmd:
                commands.append(cmd)
    return commands

def get_commands_interactively(mode_name):
    print(Fore.CYAN + f"\nEnter {mode_name} commands one by one.")
    print(Fore.CYAN + "Type 'done' when finished.\n")

    commands = []
    while True:
        cmd = input("> ").strip()
        if cmd.lower() == "done":
            break
        if cmd:
            commands.append(cmd)
    return commands

# ---------------------------
# SHOW mode
# ---------------------------
def run_show_commands(conn, show_commands):
    output = []
    for cmd in show_commands:
        logging.info(f"Running SHOW: {cmd}")
        result = conn.send_command(cmd)
        output.append(f"\n===== {cmd} =====\n{result}")
    return "\n".join(output)

# ---------------------------
# CONFIG mode
# ---------------------------
def run_config_commands(conn, config_commands):
    logging.info("Entering CONFIG mode")
    return conn.send_config_set(config_commands)

# ---------------------------
# Save output
# ---------------------------
def save_output(device_name, text, mode):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{mode}_{device_name}_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    logging.info(f"Output saved to {filepath}")
    return filepath

# ---------------------------
# CSV session report
# ---------------------------
def save_session_report(rows):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(REPORT_DIR, f"session_summary_{timestamp}.csv")

    headers = ["device_name", "host", "mode", "status", "commands_count", "output_file"]
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(Fore.GREEN + f"\n📊 Session report saved → {report_path}")
    logging.info(f"Session report saved to {report_path}")

# ---------------------------
# Menus
# ---------------------------
def main_menu():
    print(Style.BRIGHT + "\n=== Python Network Automation Tool (PRO v2) ===")
    print("1) Run SHOW commands (safe / read-only)")
    print("2) Push CONFIG commands (makes changes)")
    return input("Choose option (1 or 2): ").strip()

def command_source_menu():
    print("\nChoose command source:")
    print("1) Load from file")
    print("2) Type commands manually")
    return input("Choose option (1 or 2): ").strip()

def ask_dry_run():
    ans = input(Fore.YELLOW + "\nDry-run? (y/n): ").strip().lower()
    return ans == "y"

# ---------------------------
# Main
# ---------------------------
def main():
    devices = load_devices()
    choice = main_menu()

    session_rows = []

    if choice == "1":
        # SHOW MODE
        src = command_source_menu()
        if src == "1":
            show_commands = load_commands_from_file("commands_show.txt")
        else:
            show_commands = get_commands_interactively("SHOW")

        mode = "show"

    elif choice == "2":
        # CONFIG MODE
        src = command_source_menu()
        if src == "1":
            config_commands = load_commands_from_file("commands_config.txt")
        else:
            config_commands = get_commands_interactively("CONFIG")

        dry_run = ask_dry_run()
        mode = "config"

    else:
        print(Fore.RED + "❌ Invalid choice. Run again.")
        return

    for device in devices:
        row = {
            "device_name": device["name"],
            "host": device["host"],
            "mode": mode,
            "status": "fail",
            "commands_count": 0,
            "output_file": ""
        }

        try:
            print(Fore.MAGENTA + f"\n🔌 Connecting to {device['name']} ({device['host']})...")
            conn = connect_device(device)

            if mode == "show":
                print(Fore.CYAN + "📡 Running SHOW commands...")
                output = run_show_commands(conn, show_commands)
                out_file = save_output(device["name"], output, mode="show")

                row["status"] = "success"
                row["commands_count"] = len(show_commands)
                row["output_file"] = out_file

            else:
                # config mode
                row["commands_count"] = len(config_commands)

                if dry_run:
                    print(Fore.YELLOW + "\n🧪 DRY RUN ENABLED — No changes will be pushed.")
                    preview = "\n".join(config_commands)
                    out_file = save_output(device["name"], preview, mode="dryrun")

                    row["status"] = "dryrun"
                    row["output_file"] = out_file
                else:
                    print(Fore.RED + "⚙️ Pushing CONFIG commands...")
                    output = run_config_commands(conn, config_commands)
                    out_file = save_output(device["name"], output, mode="config")

                    row["status"] = "success"
                    row["output_file"] = out_file

            conn.disconnect()
            print(Fore.GREEN + f"✅ Done with {device['name']}")
            logging.info(f"Finished {device['name']} successfully")

        except Exception as e:
            print(Fore.RED + f"❌ Error on {device['name']}: {e}")
            logging.error(f"Error on {device['name']}: {e}")

        session_rows.append(row)

    save_session_report(session_rows)

if __name__ == "__main__":
    main()
