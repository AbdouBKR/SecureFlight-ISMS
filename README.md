# SecureFlight-ISMS

## Overview
A high-fidelity drone simulation project developed as part of my BSc in Computer Science at the University of Essex. This project integrates real-time computer vision (using MediaPipe and OpenCV) with a robust Information Security Management System (ISMS) framework inspired by ISO 27001:2022 standards.

## Security & Compliance Implementation
This project moves beyond standard simulation by implementing security controls to protect the system's integrity and confidentiality:

* **Access Control (ISO 27001 Annex A.5.15):** Implemented a mandatory login/registration portal. The system uses Role-Based Access Control (RBAC) to restrict sensitive flight evaluation tests (e.g., Wind, Latency, Payload) to 'admin' roles.
* **Secure Authentication (ISO 27001 Annex A.8.5):** Includes a brute-force protection mechanism (lockout after 3 failed attempts) and a 30-second inactivity session timeout to prevent unauthorized use of unattended terminals.
* **Cryptography (ISO 27001 Annex A.8.24):** All user credentials are stored using SHA-256 hashing. Plaintext passwords are never saved to the `users.json` database.
* **Logging & Accountability (ISO 27001 Annex A.8.15):** The system maintains an append-only audit log (`drone_audit.log`) capturing session IDs, timestamps, and operator commands, ensuring full traceability of actions.

## Technical Stack
* **Language:** Python
* **Simulation Engine:** PyBullet
* **Computer Vision:** MediaPipe, OpenCV
* **Governance Framework:** ISO 27001:2022
