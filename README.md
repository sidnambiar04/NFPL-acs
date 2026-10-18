# Nagarkot Forwarders Pvt. Ltd. (NFPL) — Access Control Service

A policy-driven, explainable, and auditable shipment access control service designed to decide **who may do what on which job**, explain each decision, prevent unauthorized modifications, and maintain a point-in-time audit history.

Built for the **NFPL Technical Assessment** by **Sidharth Nambiar**.

---

## 🌟 Key Capabilities

- **Multi-Dimensional Scoped RBAC/ABAC**: Grants are bounded across 4 operational dimensions: `Client`, `Branch`, `Direction` (Import/Export), and `Mode` (Air/Ocean FCL/Ocean LCL). Wildcards (`"*"`) are explicit.
- **Separation of Duties (4-Eyes Principle)**: The backend strictly enforces `SAME_PERSON_MAKER_CHECKER`. A user who prepared a shipment checklist cannot verify/check their own work.
- **Explainability Engine**: Every decision returns structured ALLOW/DENY metadata, reason codes (e.g., `SAME_PERSON_MAKER_CHECKER`, `SCOPE_MISMATCH`, `JOB_LOCKED_FILED`), and matched grant evidence.
- **Zero-Drift Dynamic Work Queue**: The "jobs waiting for me" queue uses the identical SQL predicates as the authorization engine. Zero ghost jobs.
- **Time-Bounded Delegations**: Out-of-office delegations allow temporary scope coverage without password sharing.
- **Temporal Audit Engine**: Answers *"Who could have changed this job on the 3rd?"* (`/api/audit/who-could-act`) and *"Why can she do this and he can't?"* (`/api/access/compare`).
- **Zero-Dependency Reviewer Experience**: Automatically runs on embedded SQLite for instant zero-config evaluation, with full PostgreSQL and Docker Compose support.

---

## 👥 Plain Language Access Matrix (Sample Users)

The assessment requires stating each person's access in plain terms: *"Person A has role B for client C, branch D, direction E, mode F."*

| Person | Name & Type | Role | Client | Branch | Direction | Mode | Plain Language Access Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`usr_asha`** | Asha Sharma (Staff) | `MAKER`<br>`CHECKER`<br>`CHECKER` | `*`<br>`client_03`<br>`client_07` | `*`<br>`*`<br>`*` | `*`<br>`*`<br>`*` | `*`<br>`*`<br>`*` | Asha has role **Maker** for all clients, branches, directions, and modes. She has role **Checker** for Sun Pharma (`client_03`) and Dr. Reddy's (`client_07`) across all branches, directions, and modes. |
| **`usr_ravi`** | Ravi Kumar (Staff) | `CHECKER` | `client_03` | `branch_bom` | `IMPORT` | `*` | Ravi has role **Checker** for Sun Pharma (`client_03`), Mumbai branch (`branch_bom`), for **Import** only, across all modes. |
| **`usr_vikram`** | Vikram Seth (Staff, ABSENT) | `SUPERVISOR` | `*` | `branch_del` | `*` | `*` | Vikram has role **Supervisor** for all clients at Delhi branch (`branch_del`). He is currently marked **ABSENT** with an active delegation to Priya. |
| **`usr_priya`** | Priya Nair (Staff) | `MAKER`<br>*(Delegation)* | `*`<br>`*` | `branch_bom`<br>`branch_del` | `*`<br>`*` | `*`<br>`*` | Priya has role **Maker** for all clients at Mumbai branch (`branch_bom`). She also holds an active **Delegation from Vikram**, inheriting Delhi Supervisor rights. |
| **`usr_client_sun`** | Sameer Mehta (Client) | `CLIENT_VIEWER` | `client_03` | `*` | `*` | `*` | Sameer has role **Client Viewer** for Sun Pharma (`client_03`). He has strict read-only visibility into Sun Pharma shipments; all edits are denied. |
| **`usr_admin_raj`** | Rajesh Patel (Admin) | `ADMIN` | `*` | `*` | `*` | `*` | Rajesh has role **System Administrator** across all clients and branches. Governed by dual-control anti-self-escalation policy. |
| **`usr_parser_svc`** | EDI Parser (Service) | `PARSER` | `*` | `*` | `*` | `*` | Parser has role **Parser** across all branches. Authorized strictly to ingest confirmed jobs via idempotent document manifests. |
| **`usr_kavita`** | Kavita Rao (Staff) | `FILER` | `*` | `branch_maa` | `*` | `*` | Kavita has role **Filer** for all clients and modes at Chennai branch (`branch_maa`). |
| **`usr_arjun`** | Arjun Deshmukh (Staff) | `CHECKER` | `*` | `branch_bom` | `*` | `*` | Arjun has role **Checker** for all clients, directions, and modes at Mumbai branch (`branch_bom`). |
| **`usr_sneha`** | Sneha Iyer (Staff) | `FILER` | `*` | `branch_blr` | `*` | `*` | Sneha has role **Filer** for all clients, directions, and modes at Bengaluru branch (`branch_blr`). |
| **`usr_amit`** | Amit Mukherjee (Staff) | `SUPERVISOR` | `*` | `branch_ccu` | `*` | `*` | Amit has role **Supervisor** for all clients and modes at Kolkata branch (`branch_ccu`). |
| **`usr_pooja`** | Pooja Verma (Staff) | `MAKER` | `*` | `branch_del` | `*` | `*` | Pooja has role **Maker** for all clients and modes at Delhi branch (`branch_del`). |
| **`usr_divya`** | Divya Menon (Staff) | `FILER` | `*` | `branch_bom` | `*` | `*` | Divya has role **Filer** for all clients, directions, and modes at Mumbai branch (`branch_bom`). |
| **`usr_client_tata`**| Nikhil Rane (Client) | `CLIENT_VIEWER` | `client_01` | `*` | `*` | `*` | Nikhil has role **Client Viewer** strictly isolated to Tata Motors (`client_01`). |
| **`usr_suresh`** | Suresh Raina (Staff) | `SUPERVISOR` | `*` | `branch_del` | `*` | `*` | Account is **INACTIVE** (blocked from all operations). |
| **`usr_manish`** | Manish Pandey (Staff) | `CHECKER` | `*` | `branch_del` | `*` | `*` | Manish has role **Checker** for all clients at Delhi branch (`branch_del`). |
| **`usr_rohit`** | Rohit Sen (Staff) | `MAKER` | `*` | `branch_ccu` | `*` | `*` | Rohit has role **Maker** for all clients at Kolkata branch (`branch_ccu`). |
| **`usr_meera`** | Meera Nambiar (Staff) | `CHECKER` | `*` | `branch_maa` | `*` | `*` | Meera has role **Checker** for all clients at Chennai branch (`branch_maa`). |
| **`usr_karan`** | Karan Johar (Staff) | `MAKER` | `*` | `branch_blr` | `*` | `*` | Karan has role **Maker** for all clients at Bengaluru branch (`branch_blr`). |
| **`usr_anita`** | Anita Bose (Staff) | `FILER` | `*` | `branch_ccu` | `*` | `*` | Anita has role **Filer** for all clients at Kolkata branch (`branch_ccu`). |

---

## 🚀 Quickstart: Running Locally (Zero Friction)

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend dashboard)

### 2. Backend Setup
```bash
# Clone repository
git clone https://github.com/sidnambiar04/NFPL-acs.git
cd NFPL-acs

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run deterministic demo seed (Creates 5 branches, 10 clients, 20 users, and awkward cases)
python -m app.seed --scenario demo

# Start backend API (runs on http://localhost:8000)
uvicorn app.main:app --app-dir backend --reload --port 8000
```
- Interactive Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser to interact with the dashboard, switch personas, execute actions, and run the access simulator.

---

## 🧪 Automated Edge-Case Test Suite

Run the full pytest suite:
```bash
pytest backend/tests -v
```

### Verified Test Cases:
1. `test_maker_checker_conflict`: Maker cannot check their own job (`SAME_PERSON_MAKER_CHECKER`), while independent eligible checker succeeds.
2. `test_scope_mismatch`: Restricted checker is denied when client, branch, direction, or mode diverges (`SCOPE_MISMATCH`).
3. `test_absent_employee_and_delegation`: Direct actions by absent staff are blocked (`ACCOUNT_ABSENT`); delegate acts within validity window.
4. `test_filed_job_immutability_and_admin_reopen`: Filed shipments locked against edits (`JOB_LOCKED_FILED`); admin reopen requires mandatory reason.
5. `test_admin_anti_self_escalation`: Admin self-assignment blocked and audited (`SELF_ESCALATION_FORBIDDEN`).
6. `test_client_tenant_isolation`: Cross-client queries return 403 (`CLIENT_ISOLATION_VIOLATION`); client edits blocked.
7. `test_parser_service_account_restrictions`: Ingestion succeeds; duplicate retries are idempotent; approval actions rejected.
8. `test_work_queue_accuracy`: Work queue queries match exact action eligibility with zero drift.
9. `test_access_comparison_and_history`: Side-by-side comparison engine and chronological audit logs.

---

## 📈 Scale Benchmark (500 Users, 200,000 Jobs)

To generate the full scale case and benchmark indexing performance:
```bash
python scripts/generate_scale_data.py --users 500 --jobs 200000
```
or via the seed module:
```bash
python -m app.seed --scenario scale --users 500 --jobs 200000
```

### Performance Results:
- **Bulk Insert Throughput**: ~8,500 – 11,000 jobs/sec using chunked bulk mappings.
- **Index Latency**: Sub-10ms queries across 200,000 records leveraging composite B-tree indexes:
  - `jobs(client_id, branch_id, stage)`
  - `jobs(direction, mode, stage)`
  - `role_assignments(user_id, status, valid_from, valid_until)`

---

## 🐳 Optional Docker Run

If you prefer running via Docker and PostgreSQL:
```bash
docker compose up --build
```
This launches a PostgreSQL container on port 5432 and the FastAPI service on port 8000.

---

## 📚 Deliverables & Documentation Index

- **Design Document (2–4 Pages)**: [docs/design.md](docs/design.md) — Comprehensive model design, trade-offs, and in-depth answers to all 14 questions.
- **5-Minute Demo Walkthrough Script**: [docs/demo_walkthrough.md](docs/demo_walkthrough.md) — Exact step-by-step presentation script for the live/recorded evaluation.
- **Implementation Blueprint**: [implementation_plan.md](docs/implementation_plan.md) — Initial engineering blueprint.

---

## 📜 License
Developed for the Nagarkot Forwarders Pvt. Ltd. Technical Assessment. Confidential.
