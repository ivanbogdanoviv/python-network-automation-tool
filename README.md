# 🔌 Python Network Automation Tool

Automate Cisco device tasks via SSH using **Python + Netmiko**.  
This repo demonstrates real-world networking automation: multi-device execution, show-mode auditing, config pushing, and professional logging.

---

## ✅ Features
- Connects to one or many Cisco IOS devices via SSH  
- **Menu-driven** workflow (Show vs Config Push)  
- Runs multiple commands automatically  
- Saves device outputs into `/outputs`  
- Logs every action into `/logs/automation.log`  
- Uses `devices.json` inventory (scales easily)
- SSH reachability check before connecting (fast fail)
- Automatic running-config backup before config push
- Per-command timeout protection  

---

## 📂 Project Structure
- backups/            # Auto-created running-config backups



