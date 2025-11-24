"""
Python Network Automation Tool (PRO v3)
Author: Ivan Bogdanov Ivanov

PRO v3 adds:
- Reachability check (TCP/22) before SSH
- Automatic running-config backup before CONFIG push
- Per-command timeout safety
- Smarter errors + improved session CSV

Still supports PRO v2:
- SHOW vs CONFIG menu
- Commands from file or manual
- Dry-run mode
- outputs/, logs/, reports/
"""

import json
import os
import csv
import socket
import logging
from datetime import datetime
from netmiko import ConnectHandler
from colorama import Fore, Style, init

init(autoreset=True)

# ---------------------------
# Folders + Logging
# ---------------------------
OUTPUT_DIR = "outputs"
LOG_DIR = "logs"
REPORT_DIR = "reports"
BACKUP_DIR = "backups"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

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
# Reachability check (TCP 22)
# ---------------------------
def is_reachable(host, port=22, timeout=3):
    """Returns True if TCP port is open, else False."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

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
        secret=device.get("secret", ""),
        conn_timeout=8,        # connection timeout
        banner_timeout=8,
        auth_timeout=8
    )

    if device.get("secret"):
        conn.enable()

    return conn

# ---------------------------
# Command helpers
# ---------------------------
def load_commands_from_file(filename):
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
# SHOW mode (with per-command timeout)
# ---------------------------
def run_show_commands(conn, show_commands, cmd_timeout=10):
    output = []
    for cmd in show_commands:
        try:
            logging.info(f"Running SHOW: {cmd}")
            result = conn.send_command(cmd, read_timeout=cmd_timeout)
            output.append(f"\n===== {cmd} =====\n{result}")
        except Exception as e:
            msg = f"[SHOW TIMEOUT/ERROR] {cmd} -> {e}"
            logging.warning(msg)
            output.append(f"\n===== {cmd} =====\n{msg}")
    return "\n".join(output)

# ---------------------------
# Backup running-config
# ---------------------------
def backup_running_config(conn, device_name):
    """Save running-config to backups/ before pushing changes."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{device_name}_running-config_{timestamp}.cfg"
    filepath = os.path.join(BACKUP_DIR, filename)

    logging.info("Backing up running-config")
    run_cfg = conn.send_command("show running-config", read_timeout=15)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(run_cfg)

    logging.info(f"Backup saved to {filepath}")
    return filepath

# ---------------------------
# CONFIG mode (with per-command timeout)
# ---------------------------
def run_config_commands(conn, config_commands, cmd_timeout=10):
    logging.info("Entering CONFIG mode")
    return conn.send_config_set(config_commands, read_timeout=cmd_timeout)

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

    headers = [
        "device_name", "host", "reachable", "mode",
        "status", "commands_count", "backup_file", "output_file"
    ]
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
    print(Style.BRIGHT + "\n=== Python Network Automation Tool (PRO v3) ===")
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
        show_commands = load_commands_from_file("commands_show.txt") if src == "1" else get_commands_interactively("SHOW")
        mode = "show"
        dry_run = False
        config_commands = []

    elif choice == "2":
        # CONFIG MODE
        src = command_source_menu()
        config_commands = load_commands_from_file("commands_config.txt") if src == "1" else get_commands_interactively("CONFIG")
        dry_run = ask_dry_run()
        mode = "config"
        show_commands = []

    else:
        print(Fore.RED + "❌ Invalid choice. Run again.")
        return

    for device in devices:
        reachable = is_reachable(device["host"], 22, timeout=3)

        row = {
            "device_name": device["name"],
            "host": device["host"],
            "reachable": reachable,
            "mode": mode,
            "status": "fail",
            "commands_count": len(show_commands) if mode == "show" else len(config_commands),
            "backup_file": "",
            "output_file": ""
        }

        if not reachable:
            print(Fore.RED + f"\n🚫 {device['name']} ({device['host']}) unreachable on SSH/22. Skipping.")
            logging.error(f"{device['name']} unreachable on port 22")
            row["status"] = "unreachable"
            session_rows.append(row)
            continue

        try:
            print(Fore.MAGENTA + f"\n🔌 Connecting to {device['name']} ({device['host']})...")
            conn = connect_device(device)

            if mode == "show":
                print(Fore.CYAN + "📡 Running SHOW commands...")
                output = run_show_commands(conn, show_commands)
                out_file = save_output(device["name"], output, mode="show")

                row["status"] = "success"
                row["output_file"] = out_file

            else:
                # CONFIG MODE
                if dry_run:
                    print(Fore.YELLOW + "\n🧪 DRY RUN ENABLED — No changes will be pushed.")
                    preview = "\n".join(config_commands)
                    out_file = save_output(device["name"], preview, mode="dryrun")

                    row["status"] = "dryrun"
                    row["output_file"] = out_file

                else:
                    # Backup before changes
                    backup_file = backup_running_config(conn, device["name"])
                    row["backup_file"] = backup_file

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
            row["status"] = "error"

        session_rows.append(row)

    save_session_report(session_rows)

if __name__ == "__main__":
    main()
