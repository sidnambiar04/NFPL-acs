# NFPL Access Control Service — 5-Minute Live / Recorded Demo Script

This script provides an exact, minute-by-minute guide for delivering the 5-minute walkthrough required for the Nagarkot assessment.

---

### Step 1: Context & Architecture (0:00 – 0:40)
- **What to say**: 
  > *"Hello! Today I'm demonstrating the Access Control Service for Nagarkot Forwarders Pvt. Ltd. (NFPL). Last month, an unauthorized alteration occurred on a filed customs shipment because the legacy system had coarse roles, no 4-eyes separation of duties, and no audit trail. To permanently solve this, we built a policy-driven, explainable authorization engine using FastAPI, React, and Scoped ABAC/RBAC. Let's see it live."*
- **What to show**:
  - Show the running dashboard at `http://localhost:5173/`. Point out the header with the active persona switcher and the policy version badge.

---

### Step 2: Maker Queue & Action Execution (0:40 – 1:30)
- **What to say**:
  > *"I am currently acting as Asha Sharma (`usr_asha`). Asha has a broad Maker role across all branches and clients, but only Checker rights for Sun Pharma and Dr. Reddy's. In her Work Queue, she sees jobs in the 'CONFIRMED' stage that need preparation. The Work Queue query directly mirrors backend authorization eligibility—there are zero ghost jobs."*
- **What to do**:
  - Click on the **Work Queue** tab.
  - Locate `JOB-BOM-2026-0102` (`CONFIRMED`).
  - Click **Execute prepare**.
  - Show the success alert: The job transitions to `PREPARED` and records Asha as `preparer_id`.

---

### Step 3: Separation of Duties / 4-Eyes Conflict (1:30 – 2:20)
- **What to say**:
  > *"Now let's examine the 4-eyes rule. Asha also has Checker rights for Sun Pharma. But on Job `JOB-BOM-2026-0101`—a Sun Pharma shipment that Asha prepared herself—what happens if she tries to approve and check it?"*
- **What to do**:
  - Open Job `job_101` (`JOB-BOM-2026-0101`).
  - In the Action Matrix, point out that `check_job` is blocked with reason code:
    `SAME_PERSON_MAKER_CHECKER`.
  - Explain: *"Even though Asha has Checker rights on this client, our backend engine strictly prohibits a user from checking their own work."*

---

### Step 4: Switch to Eligible Checker & Demonstrate Success (2:20 – 3:10)
- **What to say**:
  > *"Now let's switch personas to Ravi Kumar (`usr_ravi`). Ravi is a restricted Checker assigned specifically to Sun Pharma, Mumbai branch, and Imports only."*
- **What to do**:
  - In the persona dropdown, select **Ravi Kumar**.
  - Notice his Work Queue updates instantly: `job_101` appears because Ravi did not prepare it and the job matches his exact scope (`client_03`, `branch_bom`, `IMPORT`).
  - Click **Execute check**.
  - Show the green success toast: the job transitions to `CHECKED` and records Ravi as `checker_id`.

---

### Step 5: "Why Can She Do This and He Can't?" (Question 10) (3:10 – 3:50)
- **What to say**:
  > *"One of the key requirements of the brief is answering Question 10: 'Why can she do this and he can't?' Let's navigate to the Access Simulator."*
- **What to do**:
  - Click the **Access Simulator** tab.
  - Set User A = **Ravi Kumar**, User B = **Asha Sharma**, Job = **job_101**, Action = **check_job**.
  - Click **Compare Access Decisions**.
  - Show the side-by-side diff:
    - User A (Ravi): **ALLOWED** with matched role grant `asgn_ravi_chk`.
    - User B (Asha): **DENIED** with code `SAME_PERSON_MAKER_CHECKER` and missing requirement `DIFFERENT_ACTOR_THAN_PREPARER`.
    - Point out the automated divergence summary explaining the exact reason.

---

### Step 6: Immutable Job History & Point-in-Time Audit (3:50 – 4:30)
- **What to say**:
  > *"Now let's open the Job Timeline and Historical Investigation to answer Question 11: 'Who could have changed this job on the 3rd?'"*
- **What to do**:
  - Open `job_101` details to show the complete chronological timeline with actor IDs, from/to stages, and reasons.
  - Switch to the **Historical Investigation** tab.
  - Run the query on `job_101` for `check_job` on `2026-10-03T12:00:00Z`. Show the exact reconstructed list of eligible actors based on historical grants.

---

### Step 7: Automated Tests & 200,000 Scale Dataset (4:30 – 5:00)
- **What to say**:
  > *"Finally, let's verify reliability and scale in the terminal."*
- **What to do**:
  - In terminal, run: `pytest backend/tests -v`
  - Highlight that all 9 edge-case test suites pass in ~1.2 seconds.
  - Show the scale generator command:
    `python scripts/generate_scale_data.py --users 500 --jobs 200000`
  - Conclude: *"The service is fast, explainable, strictly enforced server-side, and ready for production deployment. Thank you!"*
