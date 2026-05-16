# DF_PROJECT_V3 — Digital Forensics Acquisition System (Controller + Agent)

## Overview
DF_PROJECT_V3 is a **Controller + Agent** based digital forensic acquisition system.

- **Controller (Flask server)**  
  Provides a web UI + REST APIs to:
  - register agents
  - create tasks (e.g., disk acquisition)
  - receive evidence archives
  - store evidence metadata in SQLite
  - maintain chain-of-custody logging

- **Agent (Linux VM)**  
  Polls controller for tasks, performs acquisition (e.g., disk imaging), packages the result as forensic evidence, and uploads it to the controller.

> Disk imaging requires **root privileges** on Linux.

---

## Project Structure
```
DF_PROJECT_V3/
├─ controller/
├─ agent/
├─ config.py
├─ run_controller.py
├─ run_agent.py
├─ forensic.db
└─ evidence/
```

---

## Requirements
- OS: Linux (Agent), Any OS (Controller)
- Python: 3.10+
- Tools: dd
- Python packages:
  - flask
  - requests

---

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests
```

---

## Run Controller
```bash
python3 run_controller.py
```
Access:
```
http://<controller-ip>:5000
```

---

## Run Agent
```bash
sudo python3 run_agent.py --controller http://<controller-ip>:5000 --debug
```

---

## Disk Acquisition
- Uses RAW disk imaging with `dd`
- Evidence written directly to mounted evidence disk
- Hashes calculated post-acquisition

Example task payload:
```json
{
  "action": "disk",
  "case_id": "CASE_001",
  "src_disk": "/dev/sda",
  "evidence_mount": "/mnt/evidence"
}
```

---

## Evidence Handling
- Evidence staged and archived on evidence disk
- Metadata + hashes included
- Uploaded securely to controller

---

## Troubleshooting
- Permission denied: run agent with sudo
- No space left: ensure `/mnt/evidence` is mounted to secondary disk
- Controller unreachable: verify IP/port

---

## Ethical Notice
Use only in authorized forensic/lab environments.

---

## Author
Muhammad Fahad-231307
Ayesha Wajid-231331
DF-LAB / ABDULLAH FAROQ
