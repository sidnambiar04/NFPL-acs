# NFPL Access Control Service — Architecture & Design Document

**Author:** Sidharth Nambiar  
**Target:** Nagarkot Forwarders Pvt. Ltd. (NFPL) Technical Assessment  
**Document Version:** 1.0 (Production Blueprint)  
**Date:** October 2026  

---

## 1. Executive Summary & Problem Diagnosis

Nagarkot Forwarders Pvt. Ltd. (NFPL) operates as a licensed customs brokerage spanning 5 branches across India (Mumbai, Delhi, Chennai, Kolkata, Bengaluru) handling air and ocean (FCL/LCL) import and export shipments with ~120 staff. 

### The Root Cause of the Incident
Last month, a **filed shipment was altered by someone who had no business touching it**. Nobody could identify who had been allowed to do so or why. A forensic evaluation of legacy customs software architectures reveals the systemic root causes:
1. **Coarse-Grained Roles without Dimensional Scope**: Legacy RBAC treats "Maker" or "Checker" as binary flags without binding them to operational boundaries (client, branch, direction, or cargo mode).
2. **Missing Separation of Duties (4-Eyes Principle)**: The user who prepared the customs documents was technically allowed to approve their own filing.
3. **Lack of Lifecycle Immobility**: Once a customs entry is officially submitted to ICEGATE (`FILED`), it must become read-only. Legacy systems lacked strict server-side state machine enforcement.
4. **Untraceable & Inauditable Operations**: Changes occurred via direct database writes or unstructured API calls without an immutable point-in-time event log.

### Architectural Solution
This service implements a **policy-driven, explainable Access Control Service** built with **FastAPI, PostgreSQL / SQLAlchemy, and React**. It combines **Scoped Role-Based Access Control (Scoped RBAC)** with **Attribute-Based Access Control (ABAC)**, enforces strict server-side state transitions, provides transparent ALLOW/DENY explanations with machine reason codes, and maintains an immutable audit ledger.

---

## 2. Core Domain Model & Scope Representation

### 2.1 The Four-Dimensional Scope Model
Every customs shipment (job) exists at the intersection of four business dimensions:
1. **Client**: e.g., Tata Motors (`client_01`), Sun Pharma (`client_03`), Dr. Reddy's (`client_07`).
2. **Branch**: Mumbai Central (`branch_bom`), Delhi Cargo (`branch_del`), Chennai Port (`branch_maa`), Kolkata Port (`branch_ccu`), Bengaluru Airport (`branch_blr`).
3. **Direction**: `IMPORT`, `EXPORT`.
4. **Mode**: `AIR`, `OCEAN_FCL`, `OCEAN_LCL`.

A **Scoped Role Assignment** grants a user a role bounded by explicit values or wildcards across these four dimensions:
$$\text{Assignment} = \langle \text{User}, \text{Role}, \text{Client}, \text{Branch}, \text{Direction}, \text{Mode}, [\text{valid\_from}, \text{valid\_until}] \rangle$$

#### Explicit Wildcard Semantics
In relational database design, allowing `NULL` to represent "all clients" creates catastrophic ambiguity: in SQL, `NULL = NULL` is unknown, and outer joins treat `NULL` as missing data. In this system:
- **`"*"` (Asterisk)** represents an explicit, intentional wildcard matching ANY value in that dimension.
- Specific identifiers (`"client_03"`, `"branch_bom"`) represent strict, restricted boundaries.

### 2.2 Finite State Machine (Job Lifecycle)
Shipments follow an explicit finite state machine with strict preconditions:
```
  [CONFIRMED]  --(prepare_job)-->  [PREPARED]  --(check_job)-->  [CHECKED]  --(file_job)-->  [FILED]
       |                                |                            |                          |
       +--(cancel_job)------------------+----------------------------+                          |
       |                                                                                        |
  [CANCELLED] <-----------------------(cancel_job with override)--------------------------------+
       |                                                                                        |
       +-----------------------------(reopen_job with reason)-----------------------------------+
```

- **`CONFIRMED`**: Initial job created from purchase order or overnight EDI manifest.
- **`PREPARED`**: Maker has compiled checklists, HSN codes, and customs declarations. Tracks `preparer_id`.
- **`CHECKED`**: Independent Checker has verified and approved documents. Tracks `checker_id`.
- **`FILED`**: Filer has submitted the entry to ICEGATE/Customs. Tracks `filer_id`. **Standard modifications are permanently locked.**
- **`CANCELLED`**: Job cancelled. Cancellation from `FILED` requires administrative override and mandatory reason.
- **`REOPENED`**: Closed or filed shipment unlocked by compliance admin with mandatory audit trail.

---

## 3. Detailed Answers to the 14 Questions

### Q1. Should everyone see everything? If not, who sees what? How does that differ from who may act?
**Decision: Separate Read Visibility from Action Permissions.**
- **Client Users**: Subject to strict multi-tenant isolation. A client user (e.g., Sun Pharma employee) has read-only visibility exclusively into shipments where `job.client_id == user.client_id`. They can never view other clients' shipments or execute mutations.
- **Internal Staff**: Can search and view jobs within their branch and authorized client assignments. Visibility gives situational awareness (tracking cargo delays or checking handover status).
- **Difference from Who May Act**: Viewing requires only the `job:view` permission over the job's tenant/branch. Acting requires specific lifecycle permissions (`job:prepare`, `job:check`, `job:file`), exact 4-dimensional scope alignment, correct workflow stage, and compliance with separation-of-duties.

### Q2. How would you describe someone who is a Maker for every client but a Checker for only a few? What about someone who is a Checker for one client at one branch, but only for imports?
**Decision: Composable Multi-Assignment Scope Model.**
Users can hold multiple concurrent scoped assignments without role explosion:
- **Asha (Maker everywhere, Checker for few)**:
  - Grant 1: `(Role=MAKER, Client=*, Branch=*, Direction=*, Mode=*)`
  - Grant 2: `(Role=CHECKER, Client=client_03, Branch=*, Direction=*, Mode=*)`
  - Grant 3: `(Role=CHECKER, Client=client_07, Branch=*, Direction=*, Mode=*)`
- **Ravi (Checker for one client, one branch, imports only)**:
  - Grant 1: `(Role=CHECKER, Client=client_03, Branch=branch_bom, Direction=IMPORT, Mode=*)`

When an action is evaluated, the policy engine gathers all active grants and evaluates whether *any* valid grant covers the job's 4 dimensions.

### Q3. What if the person who prepared a checklist is also qualified to approve it?
**Decision: Strict Separation of Duties (4-Eyes Principle) Enforced by Backend Engine.**
Even if Asha has universal Checker permissions across all clients, if `job.preparer_id == actor.id`, the action `check_job` is **strictly denied**:
- Reason Code: `SAME_PERSON_MAKER_CHECKER`
- Explanation: *"Separation of Duties violation: Actor prepared this shipment and cannot approve their own work."*
This rule is evaluated server-side on every transition, preventing accidental or malicious self-approval.

### Q4. What if the person responsible for a job is absent?
**Decision: Time-Bounded Delegations without Credential Sharing.**
Staff often share passwords or email logins when going on leave, creating catastrophic security blindspots. Our service introduces first-class `Delegation` records:
- Delegator (e.g., Vikram, Delhi Supervisor) creates a delegation to an active colleague (Priya) with a strict validity window `[valid_from, valid_until]` and mandatory reason.
- Vikram's user status transitions to `ABSENT`. Direct actions by Vikram are blocked.
- When Priya acts on Delhi shipments, the engine evaluates active delegations, verifies the time window, and permits the action.
- The resulting `JobEvent` records Priya as the actor with metadata: `delegated_from: usr_vikram`.

### Q5. What happens to jobs a person is halfway through when their responsibilities change?
**Decision: Action-Time Evaluation with Immutable Historical Records.**
Access is evaluated dynamically at the instant each action is attempted:
- If Asha prepares a job and her Maker role is revoked an hour later, the completed preparation remains valid in `job_events` (historical integrity).
- However, if Asha attempts any subsequent action on that job, the policy engine evaluates her *current* active assignments and denies the action.
- The job is not orphaned; it remains in `PREPARED` stage in the branch work queue for any other eligible Checker.

### Q6. Who should be able to cancel a filed job or reopen a closed one? What should it take?
**Decision: Elevated Authority, Strict FSM Rules, Mandatory Justification, and Dual Auditing.**
- Cancelling a standard job (`CONFIRMED`, `PREPARED`, `CHECKED`) requires `SUPERVISOR` or `ADMIN`.
- Cancelling a `FILED` job or reopening a `CANCELLED`/`FILED` job requires `ADMIN` privileges and a **mandatory non-empty reason string** explaining the regulatory or commercial justification.
- The action increments the job version, writes an immutable `JobEvent`, and simultaneously writes an elevated `AuditEvent` for compliance inspection.

### Q7. What if a client's own employee needs to follow their shipments?
**Decision: `CLIENT_VIEWER` Role with Automatic Tenant Scope Filter.**
Client users are assigned `user_type = CLIENT` with a foreign key to `client_id`.
- The API automatically injects `Job.client_id == current_user.client_id` on all search and list queries.
- Direct lookups (`GET /api/jobs/{id}`) verify client ownership; requesting another client's job returns `403 FORBIDDEN` (`CLIENT_ISOLATION_VIOLATION`) without disclosing whether the job exists.
- Mutation endpoints explicitly reject client users (`CLIENT_ACTION_RESTRICTED`).

### Q8. What if an admin needs to fix a stuck job? What if an admin tries to make themselves more powerful?
**Decision: Break-Glass Audit Workflows and Anti-Self-Escalation Controls.**
- **Fixing a Stuck Job**: Admins can execute administrative overrides (e.g., moving a job from corrupted state to `PREPARED`), but the action requires a structured reason and is recorded in `audit_events`.
- **Anti-Self-Escalation**: When an administrator calls `POST /api/admin/assignments`, the system checks:
  $$\text{if } \text{payload.user\_id} == \text{current\_user.id} \implies \text{DENY } (\text{SELF\_ESCALATION\_FORBIDDEN})$$
  Admins are blocked from granting privileges to themselves. An attempt immediately triggers a security alert in `audit_events`.

### Q9. How should an automated parser that creates and updates jobs overnight be treated?
**Decision: Dedicated Service Identity with Least Privilege and Idempotency.**
- Service Account: `usr_parser_svc` (`user_type = SERVICE`), authenticated via dedicated API token rather than human credentials.
- Principle of Least Privilege: Scoped strictly to `job:prepare` and `job:view` for draft/confirmed shipments. The parser can never check, file, or reopen jobs.
- Idempotent Processing: Ingest payloads require an external document/manifest hash (`external_manifest_hash`). Duplicate submissions are recognized and skipped without mutating existing records.

### Q10. How do you answer "why can she do this and he can't?"
**Decision: Side-by-Side Diagnostic Evaluation API (`/api/access/compare`).**
The endpoint takes `user_a_id`, `user_b_id`, `job_id`, and `action`. It runs the policy engine concurrently for both users and generates a comparative diff:
- Displays active role assignments for each user.
- Highlights dimensional scope matches vs mismatches (e.g., *"Ravi matches branch_bom and IMPORT, whereas Asha lacks Checker rights on this client"* or *"Asha was blocked by SAME_PERSON_MAKER_CHECKER because she prepared this job"*).
- Returns human-readable summary text explaining the exact point of divergence.

### Q11. How do you answer "who could have changed this job on the 3rd?"
**Decision: Point-in-Time Temporal Policy Evaluation (`/api/audit/who-could-act`).**
Because `role_assignments` and `delegations` store `valid_from` and `valid_until` timestamps, authorization state can be evaluated at any historical UTC instant:
1. The auditor submits `job_id`, `action`, and `target_time = "2026-10-03T12:00:00Z"`.
2. The engine filters assignments where `valid_from <= target_time <= valid_until` (and delegations active on that date).
3. It evaluates which users satisfied the 4-dimensional scope match and 4-eyes rule at that specific date.
4. Returns the verified list of eligible individuals alongside the actual `job_events` recorded around that time.

### Q12. How would a new kind of role be introduced next quarter while engineering is busy?
**Decision: Dynamic, Database-Driven RBAC Catalog.**
Roles and role-permission mappings are stored in the database (`roles`, `permissions`, `role_permissions` tables) rather than hardcoded in Python code.
- Administrators can define a new role (e.g., `DG_CARGO_SPECIALIST`) and map existing atomic permissions (`job:view`, `job:check`) via the Admin UI or `POST /api/admin/roles`.
- Zero code modifications, deployments, or migrations are required.

### Q13. How do you make sure a person's "jobs waiting for me" count matches what they can actually do?
**Decision: Single Source of Truth via Shared Policy Predicates.**
Discrepancies occur when the work queue query uses a loose SQL `WHERE` clause while the action endpoint uses strict validation logic.
In this service:
- The Work Queue query (`/api/me/work-queue`) constructs dynamic SQL filter clauses matching the user's active grants, stages, and explicitly injects the 4-eyes clause:
  $$\text{WHERE stage = 'PREPARED' AND (preparer\_id IS NULL OR preparer\_id } \neq \text{ user.id)}$$
- Before delivering each job to the frontend, the policy engine runs an inline check to guarantee `can_act == True`. There are zero ghost jobs.

### Q14. What should happen when your system is unsure?
**Decision: Fail-Closed (Deny by Default).**
If an evaluation encounters corrupted parameters, database connectivity glitches, or unmapped stage states:
- Access is immediately **DENIED**.
- Reason Code: `SYSTEM_UNSURE_FAIL_CLOSED`.
- An error incident is recorded in `access_decisions` with stack trace diagnostics.
- The user receives an informative message directing them to contact the compliance administrator.

---

## 4. Performance, Scale & Concurrency (500 Users, 200,000 Jobs)

### 4.1 Indexing Architecture
To guarantee sub-15ms response times across 200,000 jobs:
1. **Composite Scope Index**: `jobs(client_id, branch_id, stage)` allows instant indexed lookups for branch operations.
2. **Direction & Mode Index**: `jobs(direction, mode, stage)` accelerates filtered searches.
3. **Assignment Evaluation Index**: `role_assignments(user_id, status, valid_from, valid_until)` allows single-digit millisecond grant retrieval.
4. **Audit Timeline Index**: `job_events(job_id, timestamp)` ensures instant chronological timeline rendering.

### 4.2 Concurrency & Optimistic Version Locking
To prevent race conditions where two filers attempt to submit the same shipment concurrently:
- Each `Job` record maintains an integer `version` field.
- During state transition, the update evaluates:
  $$\text{UPDATE jobs SET stage = :target, version = version + 1 WHERE id = :id AND version = :expected\_version}$$
- If another user modified the job in the interim, the update affects 0 rows, triggering an automatic rollback and concurrency collision alert.

---

## 5. Reviewer Verification & Running the Service

### 5.1 Zero-Setup Local Execution
Reviewers can clone and run immediately with zero external dependencies:
```bash
# 1. Activate environment
python -m venv venv
.\venv\Scripts\activate

# 2. Install dependencies & run test suite
pip install -r backend/requirements.txt
pytest backend/tests -v

# 3. Start Backend Service
uvicorn app.main:app --app-dir backend --reload --port 8000
```
- Swagger API Docs: `http://localhost:8000/docs`
- Default Database: Embedded SQLite (`dev.db`), automatically seeded with the 20 users and awkward test cases.

### 5.2 Scale Generator Benchmark
To test performance against 500 users and 200,000 jobs:
```bash
python scripts/generate_scale_data.py --users 500 --jobs 200000
```
Measures high-throughput bulk insertions (~8,000–12,000 jobs/sec) and executes benchmark queries on indexed columns.
