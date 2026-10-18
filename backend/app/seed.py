import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.organization import Branch, Client
from app.models.role import Role, Permission
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.models.delegation import Delegation
from app.models.job import Job
from app.models.job_event import JobEvent

def seed_initial_demo_data(force: bool = False):
    """
    Populates deterministic demo data conforming to the assessment specifications:
    - 5 Branches
    - 10 Clients
    - Standard Roles & Granular Permissions
    - 20 Users including all required awkward cases
    - ~150 Jobs across stages, directions, modes
    """
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_users = db.query(User).count()
        if existing_users > 0 and not force:
            return

        # 1. Seed Branches (5 branches)
        branches = [
            Branch(id="branch_mum", code="MUM", name="Mumbai Central Branch", city="Mumbai"),
            Branch(id="branch_del", code="DEL", name="Delhi IGI Cargo Branch", city="Delhi"),
            Branch(id="branch_cen", code="CEN", name="Chennai Harbor Branch", city="Chennai"),
            Branch(id="branch_kol", code="KOL", name="Kolkata Port Branch", city="Kolkata"),
            Branch(id="branch_blr", code="BLR", name="Bengaluru Airport Branch", city="Bengaluru"),
        ]
        db.add_all(branches)

        # 2. Seed Clients (10 clients)
        clients = [
            Client(id="client_01", code="TATA_MOTORS", name="Tata Motors Commercial Logistics"),
            Client(id="client_02", code="RELIANCE_RET", name="Reliance Retail Supply Chain"),
            Client(id="client_03", code="SUN_PHARMA", name="Sun Pharma Global Active Ingredients"),
            Client(id="client_04", code="INFOSYS_IMP", name="Infosys Tech & Hardware Imports"),
            Client(id="client_05", code="MAHINDRA_AUTO", name="Mahindra Automotive Components"),
            Client(id="client_06", code="LT_HEAVY_ENG", name="Larsen & Toubro Heavy Engineering"),
            Client(id="client_07", code="DR_REDDYS", name="Dr. Reddy's Generics & Formulations"),
            Client(id="client_08", code="BHEL_ENERGY", name="Bharat Heavy Electricals Power Gear"),
            Client(id="client_09", code="HUL_CONSUMER", name="Hindustan Unilever Consumer Goods"),
            Client(id="client_10", code="WIPRO_ELEC", name="Wipro Electronics International"),
        ]
        db.add_all(clients)

        # 3. Seed Permissions
        permissions_data = [
            ("job:view", "View Shipment Jobs", "Read-only access to job records"),
            ("job:prepare", "Prepare Job Checklists", "Maker action to draft and prepare shipment filing"),
            ("job:check", "Check and Verify Job", "Checker action to verify documentation"),
            ("job:file", "File Job to Customs", "Filer action submitting to customs portal"),
            ("job:cancel", "Cancel Shipment Job", "Permission to mark job cancelled"),
            ("job:reopen", "Reopen Closed Job", "Elevated authority to reopen cancelled/filed job"),
            ("job:edit_filed", "Edit Filed Job", "Special amendment permission for filed jobs"),
            ("admin:manage_roles", "Manage Role Assignments", "Assign and revoke user roles"),
            ("admin:create_delegation", "Create Delegation", "Authorize out-of-office coverage"),
            ("admin:break_glass_repair", "Break Glass Repair", "Repair corrupted job states with audit"),
        ]
        perms_dict = {}
        for p_id, p_name, p_desc in permissions_data:
            perm = Permission(id=p_id, name=p_name, description=p_desc)
            db.add(perm)
            perms_dict[p_id] = perm

        # 4. Seed Roles and map permissions
        roles_data = [
            ("MAKER", "Shipment Maker", "Can view and prepare shipment documentation", ["job:view", "job:prepare"]),
            ("CHECKER", "Shipment Checker", "Can view and verify prepared documentation", ["job:view", "job:check"]),
            ("FILER", "Customs Filer", "Can view and submit verified jobs to customs", ["job:view", "job:file"]),
            ("SUPERVISOR", "Branch Supervisor", "Can view, prepare, check, file, and cancel jobs", ["job:view", "job:prepare", "job:check", "job:file", "job:cancel"]),
            ("ADMIN", "System Administrator", "Full access to policy administration, audit, and overrides", list(perms_dict.keys())),
            ("CLIENT_VIEWER", "Client Portal Viewer", "Strict read-only visibility for client users", ["job:view"]),
            ("PARSER", "Overnight EDI Parser", "Automated ingestion identity for shipments", ["job:view", "job:prepare"]),
        ]
        for r_id, r_name, r_desc, p_ids in roles_data:
            role = Role(id=r_id, name=r_name, description=r_desc, is_system=True)
            for pid in p_ids:
                role.permissions.append(perms_dict[pid])
            db.add(role)

        db.flush()

        # 5. Seed 20 Users with explicit roles and awkward cases
        default_pw = get_password_hash("password123")
        now = datetime.now(timezone.utc)

        users_specs = [
            # ID, Name, Email, Type, Client_ID, Branch_ID, Status
            ("usr_asha", "Asha Sharma", "asha@nagarkot.in", "STAFF", None, "branch_mum", "ACTIVE"),
            ("usr_ravi", "Ravi Kumar", "ravi@nagarkot.in", "STAFF", None, "branch_mum", "ACTIVE"),
            ("usr_vikram", "Vikram Seth", "vikram@nagarkot.in", "STAFF", None, "branch_del", "ABSENT"),
            ("usr_priya", "Priya Nair", "priya@nagarkot.in", "STAFF", None, "branch_mum", "ACTIVE"),
            ("usr_client_sun", "Sameer Mehta", "sameer@sunpharma.com", "CLIENT", "client_03", None, "ACTIVE"),
            ("usr_admin_raj", "Rajesh Patel", "rajesh.admin@nagarkot.in", "ADMIN", None, "branch_mum", "ACTIVE"),
            ("usr_parser_svc", "Overnight EDI Parser", "parser@system.internal", "SERVICE", None, None, "ACTIVE"),
            ("usr_kavita", "Kavita Rao", "kavita@nagarkot.in", "STAFF", None, "branch_cen", "ACTIVE"),
            ("usr_arjun", "Arjun Deshmukh", "arjun@nagarkot.in", "STAFF", None, "branch_mum", "ACTIVE"),
            ("usr_sneha", "Sneha Iyer", "sneha@nagarkot.in", "STAFF", None, "branch_blr", "ACTIVE"),
            ("usr_amit", "Amit Mukherjee", "amit@nagarkot.in", "STAFF", None, "branch_kol", "ACTIVE"),
            ("usr_pooja", "Pooja Verma", "pooja@nagarkot.in", "STAFF", None, "branch_del", "ACTIVE"),
            ("usr_rohit", "Rohit Sen", "rohit@nagarkot.in", "STAFF", None, "branch_kol", "ACTIVE"),
            ("usr_meera", "Meera Nambiar", "meera@nagarkot.in", "STAFF", None, "branch_cen", "ACTIVE"),
            ("usr_karan", "Karan Johar", "karan@nagarkot.in", "STAFF", None, "branch_blr", "ACTIVE"),
            ("usr_divya", "Divya Menon", "divya@nagarkot.in", "STAFF", None, "branch_mum", "ACTIVE"),
            ("usr_client_tata", "Nikhil Rane", "nikhil@tatamotors.com", "CLIENT", "client_01", None, "ACTIVE"),
            ("usr_suresh", "Suresh Raina", "suresh@nagarkot.in", "STAFF", None, "branch_del", "INACTIVE"),
            ("usr_manish", "Manish Pandey", "manish@nagarkot.in", "STAFF", None, "branch_del", "ACTIVE"),
            ("usr_anita", "Anita Bose", "anita@nagarkot.in", "STAFF", None, "branch_kol", "ACTIVE")
        ]

        users_dict = {}
        for uid, name, email, utype, cid, bid, status in users_specs:
            user = User(
                id=uid,
                name=name,
                email=email,
                hashed_password=default_pw,
                user_type=utype,
                client_id=cid,
                branch_id=bid,
                status=status,
                created_at=now
            )
            db.add(user)
            users_dict[uid] = user

        db.flush()

        # 6. Seed Scoped Role Assignments (Valid from 60 days ago to cover historical inquiries like Oct 3rd)
        past_valid = now - timedelta(days=60)

        # Person A (Asha): Maker everywhere; Checker for Sun Pharma (client_03) and Dr. Reddy's (client_07)
        assignments = [
            RoleAssignment(id="asgn_asha_maker", user_id="usr_asha", role_id="MAKER", client_id="*", branch_id="*", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_asha_chk_03", user_id="usr_asha", role_id="CHECKER", client_id="client_03", branch_id="*", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_asha_chk_07", user_id="usr_asha", role_id="CHECKER", client_id="client_07", branch_id="*", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Person B (Ravi): Checker for Sun Pharma (client_03), Mumbai (branch_mum), Import only, all modes
            RoleAssignment(id="asgn_ravi_chk", user_id="usr_ravi", role_id="CHECKER", client_id="client_03", branch_id="branch_mum", direction="IMPORT", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Person C (Vikram - Absent): Supervisor for Delhi branch
            RoleAssignment(id="asgn_vikram_sup", user_id="usr_vikram", role_id="SUPERVISOR", client_id="*", branch_id="branch_del", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Person D (Priya): Maker at Mumbai
            RoleAssignment(id="asgn_priya_maker", user_id="usr_priya", role_id="MAKER", client_id="*", branch_id="branch_mum", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Person E (Client User Sameer): Client Viewer for Sun Pharma
            RoleAssignment(id="asgn_client_sun", user_id="usr_client_sun", role_id="CLIENT_VIEWER", client_id="client_03", branch_id="*", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Admin Rajesh: Full system admin
            RoleAssignment(id="asgn_admin_raj", user_id="usr_admin_raj", role_id="ADMIN", client_id="*", branch_id="*", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Parser Service: Parser role
            RoleAssignment(id="asgn_parser_svc", user_id="usr_parser_svc", role_id="PARSER", client_id="*", branch_id="*", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),

            # Other staff assignments for branch coverage
            RoleAssignment(id="asgn_kavita_filer", user_id="usr_kavita", role_id="FILER", client_id="*", branch_id="branch_cen", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_arjun_chk", user_id="usr_arjun", role_id="CHECKER", client_id="*", branch_id="branch_mum", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_sneha_filer", user_id="usr_sneha", role_id="FILER", client_id="*", branch_id="branch_blr", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_amit_sup", user_id="usr_amit", role_id="SUPERVISOR", client_id="*", branch_id="branch_kol", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_pooja_maker", user_id="usr_pooja", role_id="MAKER", client_id="*", branch_id="branch_del", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
            RoleAssignment(id="asgn_divya_filer", user_id="usr_divya", role_id="FILER", client_id="*", branch_id="branch_mum", direction="*", mode="*", valid_from=past_valid, status="ACTIVE", granted_by="usr_admin_raj"),
        ]
        db.add_all(assignments)

        # 7. Seed Delegation: Vikram (Absent) delegates to Priya (covers historical inquiry on 3rd)
        delegation = Delegation(
            id="del_vikram_to_priya",
            delegator_id="usr_vikram",
            delegate_id="usr_priya",
            valid_from=now - timedelta(days=20),
            valid_until=now + timedelta(days=10),
            status="ACTIVE",
            reason="Annual leave coverage for Delhi operations",
            created_at=now - timedelta(days=20)
        )
        db.add(delegation)

        # 8. Seed Key Jobs (Including Key Demonstration Edge Cases)
        jobs_to_seed = []
        events_to_seed = []

        # Case 1: Job prepared by Asha (for Sun Pharma, Mumbai, Import, Air)
        # Perfect for testing Maker-Checker conflict: Asha prepared it, so Asha CANNOT check it, but Ravi CAN!
        job_101 = Job(
            id="job_101",
            job_number="JOB-MUM-2026-0101",
            client_id="client_03",
            branch_id="branch_mum",
            direction="IMPORT",
            mode="AIR",
            stage="PREPARED",
            preparer_id="usr_asha",
            version=2,
            description="Active Pharmaceutical Ingredients (Temperature Controlled)",
            customs_entry_number="BE-2026-BOM-8801",
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=1)
        )
        jobs_to_seed.append(job_101)
        events_to_seed.append(JobEvent(id="ev_101_1", job_id="job_101", actor_id="usr_asha", action="create_job", from_stage=None, to_stage="CONFIRMED", reason="Created by Asha", timestamp=now - timedelta(hours=3)))
        events_to_seed.append(JobEvent(id="ev_101_2", job_id="job_101", actor_id="usr_asha", action="prepare_job", from_stage="CONFIRMED", to_stage="PREPARED", reason="Documents prepared and checklist verified", timestamp=now - timedelta(hours=1)))

        # Case 2: Job in CONFIRMED waiting to be prepared in Mumbai
        job_102 = Job(
            id="job_102",
            job_number="JOB-MUM-2026-0102",
            client_id="client_01",
            branch_id="branch_mum",
            direction="EXPORT",
            mode="OCEAN_FCL",
            stage="CONFIRMED",
            version=1,
            description="Commercial EV Chassis & Axles for European Hub",
            created_at=now - timedelta(hours=5),
            updated_at=now - timedelta(hours=5)
        )
        jobs_to_seed.append(job_102)
        events_to_seed.append(JobEvent(id="ev_102_1", job_id="job_102", actor_id="usr_parser_svc", action="parser_ingest", from_stage=None, to_stage="CONFIRMED", reason="Overnight manifest ingestion", timestamp=now - timedelta(hours=5)))

        # Case 3: Job in CHECKED stage waiting for Filer in Mumbai
        job_103 = Job(
            id="job_103",
            job_number="JOB-MUM-2026-0103",
            client_id="client_03",
            branch_id="branch_mum",
            direction="IMPORT",
            mode="AIR",
            stage="CHECKED",
            preparer_id="usr_priya",
            checker_id="usr_ravi",
            version=3,
            description="Sterile Injectables & Packaging Components",
            customs_entry_number="BE-2026-BOM-9921",
            created_at=now - timedelta(hours=8),
            updated_at=now - timedelta(minutes=45)
        )
        jobs_to_seed.append(job_103)
        events_to_seed.append(JobEvent(id="ev_103_1", job_id="job_103", actor_id="usr_priya", action="prepare_job", from_stage="CONFIRMED", to_stage="PREPARED", reason="Prepared by Priya", timestamp=now - timedelta(hours=4)))
        events_to_seed.append(JobEvent(id="ev_103_2", job_id="job_103", actor_id="usr_ravi", action="check_job", from_stage="PREPARED", to_stage="CHECKED", reason="Checked & Approved by Ravi", timestamp=now - timedelta(minutes=45)))

        # Case 4: Job already FILED (The incident case from the problem brief!)
        # Standard users cannot modify; only Admin can cancel/reopen with reason
        job_104 = Job(
            id="job_104",
            job_number="JOB-DEL-2026-0104",
            client_id="client_04",
            branch_id="branch_del",
            direction="IMPORT",
            mode="AIR",
            stage="FILED",
            preparer_id="usr_pooja",
            checker_id="usr_vikram",
            filer_id="usr_pooja",
            version=4,
            description="Critical Datacenter Server Racks",
            customs_entry_number="BE-2026-DEL-1049",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1)
        )
        jobs_to_seed.append(job_104)
        events_to_seed.append(JobEvent(id="ev_104_1", job_id="job_104", actor_id="usr_pooja", action="prepare_job", from_stage="CONFIRMED", to_stage="PREPARED", reason="Prepared", timestamp=now - timedelta(days=2)))
        events_to_seed.append(JobEvent(id="ev_104_2", job_id="job_104", actor_id="usr_vikram", action="check_job", from_stage="PREPARED", to_stage="CHECKED", reason="Checked by Vikram", timestamp=now - timedelta(days=2, hours=-2)))
        events_to_seed.append(JobEvent(id="ev_104_3", job_id="job_104", actor_id="usr_pooja", action="file_job", from_stage="CHECKED", to_stage="FILED", reason="Officially filed in ICEGATE", timestamp=now - timedelta(days=1)))

        # Case 5: Delhi Job actionable by Priya via Delegation from absent Vikram!
        job_105 = Job(
            id="job_105",
            job_number="JOB-DEL-2026-0105",
            client_id="client_02",
            branch_id="branch_del",
            direction="IMPORT",
            mode="OCEAN_FCL",
            stage="PREPARED",
            preparer_id="usr_pooja",
            version=2,
            description="Retail Consumer Electronics",
            created_at=now - timedelta(hours=6),
            updated_at=now - timedelta(hours=2)
        )
        jobs_to_seed.append(job_105)
        events_to_seed.append(JobEvent(id="ev_105_1", job_id="job_105", actor_id="usr_pooja", action="prepare_job", from_stage="CONFIRMED", to_stage="PREPARED", reason="Prepared by Pooja", timestamp=now - timedelta(hours=2)))

        # Generate ~120 more realistic jobs across branches, clients, stages
        stages_cycle = ["CONFIRMED", "PREPARED", "CHECKED", "FILED", "CANCELLED"]
        directions_cycle = ["IMPORT", "EXPORT"]
        modes_cycle = ["AIR", "OCEAN_FCL", "OCEAN_LCL"]
        branch_ids = [b.id for b in branches]
        client_ids = [c.id for c in clients]

        for i in range(6, 125):
            j_id = f"job_{100 + i}"
            b_id = branch_ids[i % len(branch_ids)]
            c_id = client_ids[i % len(client_ids)]
            stg = stages_cycle[i % len(stages_cycle)]
            dir_val = directions_cycle[i % len(directions_cycle)]
            mod_val = modes_cycle[i % len(modes_cycle)]

            b_code = b_id.split("_")[1].upper()
            j_num = f"JOB-{b_code}-2026-{1000 + i}"

            extra_job = Job(
                id=j_id,
                job_number=j_num,
                client_id=c_id,
                branch_id=b_id,
                direction=dir_val,
                mode=mod_val,
                stage=stg,
                preparer_id="usr_asha" if stg != "CONFIRMED" else None,
                checker_id="usr_arjun" if stg in ["CHECKED", "FILED"] else None,
                filer_id="usr_divya" if stg == "FILED" else None,
                version=1 if stg == "CONFIRMED" else 2,
                description=f"Automated cargo shipment consignments {i}",
                created_at=now - timedelta(days=(i % 15), hours=(i % 24)),
                updated_at=now - timedelta(hours=(i % 12))
            )
            jobs_to_seed.append(extra_job)

        db.add_all(jobs_to_seed)
        db.add_all(events_to_seed)
        db.commit()
        print(f"Successfully seeded demo database with 5 branches, 10 clients, 20 users, and {len(jobs_to_seed)} jobs!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NFPL Database Seeder")
    parser.add_argument("--scenario", choices=["demo", "scale"], default="demo", help="Scenario to seed: 'demo' or 'scale'")
    parser.add_argument("--users", type=int, default=500, help="Users count for scale scenario")
    parser.add_argument("--jobs", type=int, default=200000, help="Jobs count for scale scenario")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    if args.scenario == "demo":
        seed_initial_demo_data(force=True)
    elif args.scenario == "scale":
        # Import scale generator function
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts")))
        from generate_scale_data import generate_scale
        generate_scale(users_count=args.users, jobs_count=args.jobs)

