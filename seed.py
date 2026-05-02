"""
Development seed script — populates faculty, cabinet access, and access logs.
Run after `python -m afracs.db` has initialized the schema.

    python seed.py
"""
import random
from datetime import datetime, timedelta

import pymysql

from afracs import db

FACULTY = [
    {
        "id_number": "2019-00001",
        "name": "Dr. Maria Santos",
        "position": "Professor",
        "department": "College of Health",
        "cabinets": ["A", "B"],
    },
    {
        "id_number": "2018-00042",
        "name": "Prof. Jose Reyes",
        "position": "Associate Professor",
        "department": "College of Health",
        "cabinets": ["A", "C"],
    },
    {
        "id_number": "2020-00015",
        "name": "Dr. Ana Dela Cruz",
        "position": "Assistant Professor",
        "department": "College of Health",
        "cabinets": ["B", "D"],
    },
    {
        "id_number": "2017-00088",
        "name": "Prof. Ricardo Lim",
        "position": "Professor",
        "department": "College of Health",
        "cabinets": ["A", "B", "C"],
    },
    {
        "id_number": "2021-00033",
        "name": "Dr. Luz Fernandez",
        "position": "Clinical Instructor",
        "department": "College of Health",
        "cabinets": ["C", "D"],
    },
    {
        "id_number": "2016-00077",
        "name": "Prof. Emmanuel Cruz",
        "position": "Associate Professor",
        "department": "College of Health",
        "cabinets": ["B"],
    },
    {
        "id_number": "2022-00009",
        "name": "Dr. Carla Ramos",
        "position": "Clinical Instructor",
        "department": "College of Health",
        "cabinets": ["A", "D"],
    },
    {
        "id_number": "2015-00055",
        "name": "Prof. Gilbert Torres",
        "position": "Professor",
        "department": "College of Health",
        "cabinets": ["A", "B", "C", "D"],
    },
]

# Access log volume ramps up toward today (mirrors the chart shape)
DAILY_EVENTS = {
    6: 1,
    5: 1,
    4: 1,
    3: 2,
    2: 2,
    1: 4,
    0: 55,
}

CABINETS = ["A", "B", "C", "D"]
HOURS = list(range(7, 18))


def _random_ts(days_ago: int) -> datetime:
    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    base -= timedelta(days=days_ago)
    return base + timedelta(
        hours=random.choice(HOURS),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )


def seed() -> None:
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM faculty")
            if cur.fetchone()["n"] > 0:
                print("Faculty already seeded — skipping faculty insert.")
                faculty_rows = []
                cur.execute("SELECT id, id_number FROM faculty")
                faculty_rows = cur.fetchall()
            else:
                faculty_rows = []
                for f in FACULTY:
                    cur.execute(
                        "INSERT IGNORE INTO faculty (id_number, name, position, department) "
                        "VALUES (%s, %s, %s, %s)",
                        (f["id_number"], f["name"], f["position"], f["department"]),
                    )
                    fid = cur.lastrowid
                    for cab in f["cabinets"]:
                        cur.execute("SELECT id FROM cabinets WHERE cabinet_id = %s", (cab,))
                        row = cur.fetchone()
                        if row:
                            cur.execute(
                                "INSERT IGNORE INTO faculty_cabinet_access (faculty_id, cabinet_id) "
                                "VALUES (%s, %s)",
                                (fid, row["id"]),
                            )
                    faculty_rows.append({"id": fid, "id_number": f["id_number"]})
                conn.commit()
                print(f"Seeded {len(FACULTY)} faculty members.")

        fac_ids = [r["id"] for r in faculty_rows]

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM cabinets")
            cab_pks = [r["id"] for r in cur.fetchall()]

        log_rows = []
        for days_ago, count in DAILY_EVENTS.items():
            for _ in range(count):
                ts = _random_ts(days_ago)
                fac_id = random.choice(fac_ids) if fac_ids else None
                cab_pk = random.choice(cab_pks)
                status = "granted" if random.random() < 0.55 else "denied"
                note = None if status == "granted" else "Face not recognized"
                log_rows.append((fac_id if status == "granted" else None, cab_pk, status, ts, note))

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO access_logs (faculty_id, cabinet_id, status, timestamp, note) "
                "VALUES (%s, %s, %s, %s, %s)",
                log_rows,
            )
        conn.commit()
        print(f"Seeded {len(log_rows)} access log entries.")

    finally:
        conn.close()


if __name__ == "__main__":
    seed()
