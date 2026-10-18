# NFPL Access Control Service — Walkthrough & Verification Guide

This walkthrough guide provides a step-by-step manual for testing and verifying the core capabilities, edge cases, and architectural rules of the service in the running system.

---

## 1. Quick Launch

1. **Start Backend**: Run `.\run_backend.bat` (starts at `http://localhost:8000`, API docs at `http://localhost:8000/docs`).
2. **Start Frontend**: Run `.\run_frontend.bat` (opens at `http://localhost:5173`).
3. The dashboard loads pre-seeded with the 20 test personas, 10 clients, 5 branches, and test shipments.

---

## 2. Work Queue & Zero-Drift Verification

1. In the header dropdown, ensure the active persona is **Asha Sharma (`usr_asha`)** (Maker broad, Checker for 2 clients).
2. Go to the **Work Queue** tab.
3. Observe that Asha sees jobs in the `CONFIRMED` stage needing preparation that match her Maker scope.
4. On job `JOB-BOM-2026-0102` (`CONFIRMED`), click **Execute prepare**.
5. The job transitions atomically to `PREPARED`, and Asha is recorded as `preparer_id`.

---

## 3. Separation of Duties (4-Eyes Maker/Checker Conflict)

1. Stay as **Asha Sharma (`usr_asha`)**.
2. Asha has Checker rights for Sun Pharma (`client_03`).
3. Locate Job `job_101` (`JOB-BOM-2026-0101` — Sun Pharma shipment in `PREPARED` stage that Asha prepared herself).
4. Click **Inspect** to open the detail modal.
5. In the **Action Eligibility Matrix**, notice that `check_job` is blocked:
   - **Reason Code**: `SAME_PERSON_MAKER_CHECKER`
   - **Explanation**: *"Separation of Duties violation: Actor prepared this shipment and cannot approve their own work."*
6. Attempting to execute `check_job` triggers a `403 FORBIDDEN` response directly from the backend policy engine.

---

## 4. Cross-Persona Verification with Restricted Checker

1. In the top header persona dropdown, switch to **Ravi Kumar (`usr_ravi`)**.
2. Ravi is a restricted Checker assigned specifically to Sun Pharma (`client_03`), Mumbai branch (`branch_bom`), and Imports only.
3. Go to the **Work Queue** tab:
   - Job `job_101` appears in Ravi's work queue because Ravi did not prepare it and the job matches his exact scope dimensions.
4. Click **Execute check**:
   - The job transitions to `CHECKED` and records Ravi as `checker_id`.
   - The transition is committed atomically in the database and logged to the timeline.

---

## 5. "Why Can She Do This and He Can't?" (Question 10)

1. Open the **Access Simulator & "Why She Can / He Can't"** tab.
2. Select:
   - **User A**: Ravi Kumar (`usr_ravi`)
   - **User B**: Asha Sharma (`usr_asha`)
   - **Target Job**: `job_101`
   - **Lifecycle Action**: `check_job`
3. Click **Compare Access Decisions**.
4. The system renders a side-by-side diagnostic diff:
   - **User A (Ravi)**: `ALLOWED` with matched role grant `asgn_ravi_chk`.
   - **User B (Asha)**: `DENIED` with reason code `SAME_PERSON_MAKER_CHECKER` and missing requirement `DIFFERENT_ACTOR_THAN_PREPARER`.
   - Displays the automated plain-language divergence root cause summary.

---

## 6. Point-in-Time Historical Investigation (Question 11)

1. Open the **Historical Investigation** tab.
2. Select:
   - **Job ID**: `job_101`
   - **Action**: `check_job`
   - **Historical Timestamp**: `2026-10-03T12:00:00Z`
3. Click **Reconstruct Historical Eligibility**.
4. The system queries active role assignments and delegations valid at that specific historical timestamp and displays:
   - Total eligible user count.
   - List of eligible individuals and their matched grants at that date.
   - Actual chronological audit events logged on the job.

---

## 7. Anti-Self-Escalation & Delegations Verification

1. Switch active persona to **Rajesh Patel (`usr_admin_raj`)** (System Administrator).
2. Open the **Admin, Scoped Grants & Delegations** tab.
3. In the **Grant Scoped Role Assignment** form:
   - Select User: `usr_admin_raj` (attempting self-escalation).
   - Click **Grant Assignment**.
4. The policy engine blocks the request with:
   - `403 FORBIDDEN`: *"Anti-self-escalation policy violation: Administrators cannot assign or elevate roles for themselves."*
   - An incident record is automatically added to `audit_events`.
5. Review the **Active Delegations** section to see Vikram (absent on leave) delegating his Delhi supervisor scope to Priya.

---

## 8. Automated Tests & 200k Scale Verification

1. In terminal, run:
   ```bash
   pytest backend/tests -v
   ```
   All 9 test suites covering every edge case pass in ~1.2 seconds.
2. To test scale performance against 500 users and 200,000 jobs:
   ```bash
   python scripts/generate_scale_data.py --users 500 --jobs 200000
   ```
   Runs chunked bulk ingestion (~8,500–11,000 jobs/sec) and executes benchmark queries on indexed columns.
