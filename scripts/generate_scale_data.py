import sys
import os
import time
import argparse
import random
from datetime import datetime, timedelta, timezone

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.organization import Branch, Client
from app.models.role import Role
from app.models.user import User
from app.models.role_assignment import RoleAssignment
from app.models.job import Job

def generate_scale(users_count: int = 500, jobs_count: int = 200000, batch_size: int = 10000):
    print(f"\n========================================================")
    print(f"  NFPL Scale Dataset Generator")
    print(f"  Target: {users_count} Users | {jobs_count:,} Jobs")
    print(f"  Batch Size: {batch_size:,}")
    print(f"========================================================\n")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    start_time = time.time()

    # 1. Verify branches and clients exist
    branches = db.query(Branch).all()
    clients = db.query(Client).all()
    roles = db.query(Role).all()

    if not branches or not clients or not roles:
        print("[!] Base entities not found. Running seed_initial_demo_data first...")
        from app.seed import seed_initial_demo_data
        seed_initial_demo_data(force=True)
        branches = db.query(Branch).all()
        clients = db.query(Client).all()
        roles = db.query(Role).all()

    branch_ids = [b.id for b in branches]
    client_ids = [c.id for c in clients]
    role_ids = [r.id for r in roles if r.id not in ["PARSER", "ADMIN"]]

    print(f"[*] Generating {users_count} Users & Scoped Assignments...")
    existing_user_count = db.query(User).count()
    users_to_add = []
    assignments_to_add = []
    default_hash = get_password_hash("password123")
    now = datetime.now(timezone.utc)

    for i in range(existing_user_count + 1, users_count + 1):
        uid = f"usr_scale_{i:04d}"
        b_id = random.choice(branch_ids)
        user_type = "CLIENT" if (i % 8 == 0) else "STAFF"
        c_id = random.choice(client_ids) if user_type == "CLIENT" else None

        users_to_add.append({
            "id": uid,
            "email": f"user.{i}@scale.internal",
            "name": f"Scale Staff {i}",
            "hashed_password": default_hash,
            "user_type": user_type,
            "client_id": c_id,
            "branch_id": b_id,
            "status": "ACTIVE",
            "created_at": now
        })

        # Role assignments
        assigned_role = "CLIENT_VIEWER" if user_type == "CLIENT" else random.choice(role_ids)
        assignments_to_add.append({
            "id": f"asgn_scale_{i:04d}",
            "user_id": uid,
            "role_id": assigned_role,
            "client_id": c_id or random.choice(["*", random.choice(client_ids)]),
            "branch_id": b_id if random.random() > 0.3 else "*",
            "direction": random.choice(["*", "IMPORT", "EXPORT"]),
            "mode": random.choice(["*", "AIR", "OCEAN_FCL", "OCEAN_LCL"]),
            "valid_from": now - timedelta(days=30),
            "valid_until": None,
            "status": "ACTIVE",
            "granted_by": "usr_admin_raj",
            "created_at": now
        })

    if users_to_add:
        db.bulk_insert_mappings(User, users_to_add)
        db.bulk_insert_mappings(RoleAssignment, assignments_to_add)
        db.commit()
    print(f"[✓] {users_count} Users and Role Assignments established.")

    # 2. Bulk insert Jobs
    print(f"[*] Bulk inserting {jobs_count:,} shipment jobs in batches of {batch_size:,}...")
    stages = ["CONFIRMED", "PREPARED", "CHECKED", "FILED", "CANCELLED"]
    directions = ["IMPORT", "EXPORT"]
    modes = ["AIR", "OCEAN_FCL", "OCEAN_LCL"]

    total_inserted = 0
    current_job_count = db.query(Job).count()

    while total_inserted < jobs_count:
        batch = []
        chunk = min(batch_size, jobs_count - total_inserted)
        for k in range(chunk):
            idx = current_job_count + total_inserted + k + 1
            b_id = random.choice(branch_ids)
            c_id = random.choice(client_ids)
            stg = random.choice(stages)
            direction = random.choice(directions)
            mode = random.choice(modes)
            b_code = b_id.split("_")[1].upper()

            batch.append({
                "id": f"job_s_{idx}",
                "job_number": f"SCALE-{b_code}-{idx:08d}",
                "client_id": c_id,
                "branch_id": b_id,
                "direction": direction,
                "mode": mode,
                "stage": stg,
                "preparer_id": "usr_asha" if stg != "CONFIRMED" else None,
                "checker_id": "usr_ravi" if stg in ["CHECKED", "FILED"] else None,
                "filer_id": "usr_kavita" if stg == "FILED" else None,
                "version": 1 if stg == "CONFIRMED" else 2,
                "description": f"Automated shipment batch record #{idx}",
                "customs_entry_number": f"BE-2026-{idx:06d}",
                "created_at": now - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23)),
                "updated_at": now
            })

        db.bulk_insert_mappings(Job, batch)
        db.commit()
        total_inserted += chunk
        pct = (total_inserted / jobs_count) * 100
        print(f"    --> Inserted {total_inserted:,} / {jobs_count:,} jobs ({pct:.1f}%)")

    total_elapsed = time.time() - start_time
    print(f"\n[✓] Scale Generation Complete!")
    print(f"    Total Time: {total_elapsed:.2f} seconds")
    print(f"    Throughput: {jobs_count / total_elapsed:.0f} jobs/second\n")

    # 3. Quick Index Performance Benchmark
    print("[*] Running Index Benchmark Query on 200k jobs...")
    bench_start = time.time()
    res = db.query(Job).filter(
        Job.client_id == "client_03",
        Job.branch_id == "branch_bom",
        Job.stage == "PREPARED"
    ).limit(50).all()
    bench_time = (time.time() - bench_start) * 1000
    print(f"[✓] Query returned {len(res)} results in {bench_time:.2f} ms!")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NFPL Scale Dataset Generator")
    parser.add_argument("--users", type=int, default=500, help="Number of users (default 500)")
    parser.add_argument("--jobs", type=int, default=200000, help="Number of jobs (default 200,000)")
    parser.add_argument("--batch-size", type=int, default=10000, help="Insert batch size (default 10,000)")
    args = parser.parse_args()

    generate_scale(users_count=args.users, jobs_count=args.jobs, batch_size=args.batch_size)
