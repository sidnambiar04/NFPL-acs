# NFPL Access Control Service — Architecture & Implementation Plan

## 1. Executive Summary & Problem Understanding

Nagarkot Forwarders Pvt. Ltd. (NFPL) operates as a customs brokerage across 5 branches handling air and ocean (FCL/LCL) import/export shipments with ~120 staff. The recent incident—an unauthorized, untraceable alteration of a filed shipment—highlights a dual failure:
1. **Coarse or absent authorization boundaries**: Lack of fine-grained, contextual controls across branches, clients, trade directions, and workflow stages.
2. **Missing explainability and point-in-time auditability**: The inability to reconstruct *who had what access when*, *why an action was permitted*, or *who made which modification*.

This service delivers an enterprise-grade, **explainable, policy-driven Access Control Service** built with **FastAPI, SQLAlchemy, and React**, featuring:
- **Multi-dimensional Scoped RBAC/ABAC** (`client_id`, `branch_id`, `direction`, `mode`).
- **Strict Separation of Duties (4-Eyes Principle)** preventing makers from checking their own work.
- **Explainability Engine** providing machine- and human-readable ALLOW/DENY explanations with exact reason codes and matched grant evidence.
- **Dynamic Work Queue Engine** guaranteeing that "jobs waiting for me" directly mirrors backend action eligibility (zero drift/ghost jobs).
- **Time-bounded Delegations** for seamless absence coverage without credential sharing.
- **Point-in-time Audit Trails** answering "who could have changed this on the 3rd?" and "why can Asha do this but Ravi cannot?".
- **Zero-Dependency Reviewer Experience**: Dual-dialect support (SQLite for instant zero-setup local evaluation, PostgreSQL + Docker Compose for production scale testing).

---

## 2. Core Domain & Authorization Architecture

### 2.1 Multi-Dimensional Scope Model
Each job is uniquely categorized across four operational dimensions:
- **Client**: `client_01` to `client_10`
- **Branch**: `branch_bom` (Mumbai), `branch_del` (Delhi), `branch_maa` (Chennai), `branch_ccu` (Kolkata), `branch_blr` (Bengaluru)
- **Direction**: `IMPORT`, `EXPORT`
- **Mode**: `AIR`, `OCEAN_FCL`, `OCEAN_LCL`

A **Scoped Role Assignment** grants a user a role over a scope. Wildcard semantics are made explicit with `"*"` (ALL), eliminating `NULL` ambiguity:
```json
{
  "user_id": "usr_ravi",
  "role": "CHECKER",
  "client_id": "client_03",
  "branch_id": "branch_bom",
  "direction": "IMPORT",
  "mode": "*"
}
```

### 2.2 Lifecycle & Stage Transition Rules
Shipment jobs follow a finite state machine:
```
  [CONFIRMED]  --(prepare_job)-->  [PREPARED]  --(check_job)-->  [CHECKED]  --(file_job)-->  [FILED]
       |                                |                            |                          |
       +--(cancel_job)------------------+----------------------------+                          |
       |                                                                                        |
  [CANCELLED] <-----------------------(cancel_job with override)--------------------------------+
       |                                                                                        |
       +-----------------------------(reopen_job with reason)-----------------------------------+
```

1. **Maker Action (`prepare_job`)**: Job must be in `CONFIRMED`. User must possess `MAKER` role on matching scope. Records user as `preparer_id`.
2. **Checker Action (`check_job`)**: Job must be in `PREPARED`. User must possess `CHECKER` role on matching scope. **Separation of duties**: User must NOT be the `preparer_id` (4-eyes enforcement). Records user as `checker_id`.
3. **Filer Action (`file_job`)**: Job must be in `CHECKED`. User must possess `FILER` role on matching scope. Transitions job to `FILED`. Once filed, standard edits are strictly locked.
4. **Cancel Action (`cancel_job`)**:
   - For `CONFIRMED` / `PREPARED` / `CHECKED`: Requires `SUPERVISOR` or `ADMIN` role.
   - For `FILED`: Requires elevated `ADMIN` or `BRANCH_MANAGER` role, plus mandatory structured reason.
5. **Reopen Action (`reopen_job`)**: Allowed from `FILED` or `CANCELLED`. Requires elevated `ADMIN` role, mandatory justification reason, and emits critical audit events.

---

## 3. Technology Stack & Repository Structure

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (Dual-dialect: SQLite / PostgreSQL), Pydantic v2, pytest.
- **Frontend**: React (Vite), Modern Custom CSS with rich dark-mode aesthetics, Lucide React icons.
- **DevOps & Verification**: Docker Compose, deterministic seed scripts, 200k scale generator.

---

## 4. Deliverables Index

- **Design Document (2–4 Pages)**: [docs/design.md](design.md) — Model, decisions, trade-offs, and in-depth answers to all 14 questions.
- **5-Minute Walkthrough Demo Script**: [docs/demo_walkthrough.md](demo_walkthrough.md) — Presentation script.
- **Automated Tests**: [backend/tests/test_policy_and_api.py](../backend/tests/test_policy_and_api.py) — 9 comprehensive edge-case test suites.
