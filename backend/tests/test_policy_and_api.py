from datetime import datetime, timezone, timedelta
import pytest
from app.models.job import Job
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.services.policy_engine import evaluate_access

def test_maker_checker_conflict(client, db_session):
    """
    Test Case 1: Maker cannot check their own job (Separation of Duties / 4-Eyes Principle).
    Asha prepared job_101. Even though Asha is also a Checker for client_03,
    she must be blocked with SAME_PERSON_MAKER_CHECKER.
    """
    # 1. Direct Policy Engine Evaluation
    asha = db_session.query(User).filter(User.id == "usr_asha").first()
    job_101 = db_session.query(Job).filter(Job.id == "job_101").first()
    
    assert job_101.preparer_id == asha.id
    decision = evaluate_access(db_session, asha, "check_job", job_101)
    assert decision.allowed is False
    assert decision.reason_code == "SAME_PERSON_MAKER_CHECKER"
    assert "Separation of Duties violation" in decision.reason

    # 2. HTTP Endpoint Check
    resp = client.post("/api/jobs/job_101/check", json={"reason": "Self check attempt"}, headers={"X-User-Id": "usr_asha"})
    assert resp.status_code == 403
    data = resp.json()["detail"]
    assert data["reason_code"] == "SAME_PERSON_MAKER_CHECKER"

    # 3. An independent eligible checker (Ravi) CAN check it
    ravi_resp = client.post("/api/jobs/job_101/check", json={"reason": "Approved documentation"}, headers={"X-User-Id": "usr_ravi"})
    assert ravi_resp.status_code == 200
    assert ravi_resp.json()["stage"] == "CHECKED"
    assert ravi_resp.json()["checker_id"] == "usr_ravi"

def test_scope_mismatch(client, db_session):
    """
    Test Case 2: Scope Mismatch.
    Ravi is Checker ONLY for client_03 (Sun Pharma), branch_bom (Mumbai), IMPORT.
    If Ravi attempts to check a Delhi export job, it must be denied with SCOPE_MISMATCH.
    """
    delhi_job = db_session.query(Job).filter(Job.id == "job_105").first() # client_02, Delhi
    resp = client.post(f"/api/jobs/{delhi_job.id}/check", json={}, headers={"X-User-Id": "usr_ravi"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason_code"] == "SCOPE_MISMATCH"

def test_absent_employee_and_delegation(client, db_session):
    """
    Test Case 3: Absent Employee and Delegation.
    Vikram is marked ABSENT. Direct actions by Vikram are blocked.
    His delegate (Priya) CAN act on Delhi jobs within the delegation validity window.
    """
    delhi_job = db_session.query(Job).filter(Job.id == "job_105").first()
    
    # Vikram is absent -> denied
    vikram_resp = client.post(f"/api/jobs/{delhi_job.id}/check", json={}, headers={"X-User-Id": "usr_vikram"})
    assert vikram_resp.status_code == 403
    assert vikram_resp.json()["detail"]["reason_code"] == "ACCOUNT_ABSENT"

    # Delegate Priya has Mumbai Maker directly, but covers Delhi Supervisor via delegation
    priya_decision = evaluate_access(db_session, db_session.query(User).filter(User.id == "usr_priya").first(), "check_job", delhi_job)
    assert priya_decision.allowed is True
    assert priya_decision.matched_grants[0]["delegated_from"] == "usr_vikram"

    # Priya checks it via API
    priya_resp = client.post(f"/api/jobs/{delhi_job.id}/check", json={"reason": "Delegate approval for Vikram"}, headers={"X-User-Id": "usr_priya"})
    assert priya_resp.status_code == 200
    assert priya_resp.json()["stage"] == "CHECKED"

def test_filed_job_immutability_and_admin_reopen(client, db_session):
    """
    Test Case 4: Filed Job Protection and Reopen.
    job_104 is FILED. Normal users cannot modify it.
    Only an Admin with a mandatory reason can cancel or reopen it.
    """
    # Ordinary user tries to check or prepare a filed job
    resp = client.post("/api/jobs/job_104/check", json={}, headers={"X-User-Id": "usr_asha"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason_code"] == "JOB_LOCKED_FILED"

    # Admin reopens with reason
    reopen_resp = client.post(
        "/api/jobs/job_104/reopen",
        json={"reason": "Customs query amendment requested by customs officer"},
        headers={"X-User-Id": "usr_admin_raj"}
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["stage"] == "REOPENED"

def test_admin_anti_self_escalation(client, db_session):
    """
    Test Case 5: Anti-Self-Escalation.
    An Admin cannot assign roles to themselves to bypass separation of duties or elevate power.
    """
    resp = client.post(
        "/api/admin/assignments",
        json={
            "user_id": "usr_admin_raj",
            "role_id": "SUPERVISOR",
            "client_id": "*",
            "branch_id": "*",
            "direction": "*",
            "mode": "*"
        },
        headers={"X-User-Id": "usr_admin_raj"}
    )
    assert resp.status_code == 403
    assert "Anti-self-escalation policy violation" in resp.json()["detail"]

def test_client_tenant_isolation(client, db_session):
    """
    Test Case 6: Client User Isolation.
    User Sameer (client_03) can view Sun Pharma jobs, but cannot view Tata Motors (client_01) jobs,
    and cannot perform mutation actions.
    """
    # 1. Attempt to view other client's job -> 403 Forbidden
    other_job = db_session.query(Job).filter(Job.client_id == "client_01").first()
    resp = client.get(f"/api/jobs/{other_job.id}", headers={"X-User-Id": "usr_client_sun"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason_code"] == "CLIENT_ISOLATION_VIOLATION"

    # 2. Attempt to prepare own job -> 403 (Client has read-only visibility)
    own_job = db_session.query(Job).filter(Job.client_id == "client_03", Job.stage == "CONFIRMED").first()
    if own_job:
        mut_resp = client.post(f"/api/jobs/{own_job.id}/prepare", json={}, headers={"X-User-Id": "usr_client_sun"})
        assert mut_resp.status_code == 403
        assert mut_resp.json()["detail"]["reason_code"] == "CLIENT_ACTION_RESTRICTED"

def test_parser_service_account_restrictions(client, db_session):
    """
    Test Case 7: Automated Parser Restrictions & Idempotency.
    Parser can ingest jobs, cannot approve or check jobs, and retrying duplicate manifest hash is idempotent.
    """
    # 1. Parser tries to check a job -> 403
    job = db_session.query(Job).filter(Job.stage == "PREPARED").first()
    resp = client.post(f"/api/jobs/{job.id}/check", json={}, headers={"X-User-Id": "usr_parser_svc"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["reason_code"] == "SERVICE_ACCOUNT_RESTRICTED"

    # 2. Ingest batch of jobs
    batch_payload = [
        {
            "job_number": "JOB-PARSER-AUTO-01",
            "client_id": "client_01",
            "branch_id": "branch_bom",
            "direction": "IMPORT",
            "mode": "AIR",
            "description": "Auto parsed air manifest",
            "external_manifest_hash": "hash_xyz_9981"
        }
    ]
    ingest_resp = client.post("/api/parser/jobs", json=batch_payload, headers={"X-User-Id": "usr_parser_svc"})
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["created"] == 1

    # 3. Retry identical batch -> skipped duplicates (idempotent)
    retry_resp = client.post("/api/parser/jobs", json=batch_payload, headers={"X-User-Id": "usr_parser_svc"})
    assert retry_resp.status_code == 200
    assert retry_resp.json()["created"] == 0
    assert retry_resp.json()["skipped_duplicates"] == 1

def test_work_queue_accuracy(client, db_session):
    """
    Test Case 8: Work Queue Accuracy.
    Every job in a user's work queue has can_act == True and matches their active scope.
    """
    resp = client.get("/api/me/work-queue", headers={"X-User-Id": "usr_asha"})
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    for item in data["jobs"]:
        assert item["can_act"] is True
        assert item["required_action"] is not None

def test_access_comparison_and_history(client, db_session):
    """
    Test Case 9: 'Why can she do this and he can't?' (Question 10) & Job History.
    """
    compare_resp = client.post(
        "/api/access/compare",
        json={
            "user_a_id": "usr_ravi",
            "user_b_id": "usr_asha",
            "job_id": "job_101",
            "action": "check_job"
        }
    )
    assert compare_resp.status_code == 200
    data = compare_resp.json()
    assert data["user_a"]["decision"]["allowed"] is True
    assert data["user_b"]["decision"]["allowed"] is False
    assert "comparison_summary" in data

    # Job history
    hist_resp = client.get("/api/jobs/job_101/history", headers={"X-User-Id": "usr_asha"})
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["timeline"]) >= 2
