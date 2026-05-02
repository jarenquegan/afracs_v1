"""
Development seed script — drops and repopulates faculty, cabinet access, and access logs.
Run after `python -m afracs.db` has initialized the schema.

    python seed.py
"""
import random
from datetime import datetime, timedelta

from afracs import db

FACULTY = [
    {"id_number": "2015-00001", "name": "Dr. Maria Santos",        "position": "Professor",           "department": "College of Health", "cabinets": ["A", "B"]},
    {"id_number": "2016-00002", "name": "Prof. Jose Reyes",        "position": "Associate Professor", "department": "College of Health", "cabinets": ["A", "C"]},
    {"id_number": "2016-00003", "name": "Dr. Ana Dela Cruz",       "position": "Assistant Professor", "department": "College of Health", "cabinets": ["B", "D"]},
    {"id_number": "2017-00004", "name": "Prof. Ricardo Lim",       "position": "Professor",           "department": "College of Health", "cabinets": ["A", "B", "C"]},
    {"id_number": "2017-00005", "name": "Dr. Luz Fernandez",       "position": "Clinical Instructor", "department": "College of Health", "cabinets": ["C", "D"]},
    {"id_number": "2018-00006", "name": "Prof. Emmanuel Cruz",     "position": "Associate Professor", "department": "College of Health", "cabinets": ["B"]},
    {"id_number": "2018-00007", "name": "Dr. Carla Ramos",         "position": "Clinical Instructor", "department": "College of Health", "cabinets": ["A", "D"]},
    {"id_number": "2019-00008", "name": "Prof. Gilbert Torres",    "position": "Professor",           "department": "College of Health", "cabinets": ["A", "B", "C", "D"]},
    {"id_number": "2019-00009", "name": "Dr. Rowena Villanueva",   "position": "Assistant Professor", "department": "College of Health", "cabinets": ["A", "C"]},
    {"id_number": "2020-00010", "name": "Prof. Danilo Macaraeg",   "position": "Associate Professor", "department": "College of Health", "cabinets": ["B", "C"]},
    {"id_number": "2020-00011", "name": "Dr. Teresita Bautista",   "position": "Professor",           "department": "College of Health", "cabinets": ["A", "B"]},
    {"id_number": "2021-00012", "name": "Prof. Renato Pagdanganan","position": "Clinical Instructor", "department": "College of Health", "cabinets": ["D"]},
    {"id_number": "2021-00013", "name": "Dr. Felicitas Soriano",   "position": "Assistant Professor", "department": "College of Health", "cabinets": ["A", "D"]},
    {"id_number": "2022-00014", "name": "Prof. Eduardo Magbanua",  "position": "Associate Professor", "department": "College of Health", "cabinets": ["B", "C", "D"]},
    {"id_number": "2022-00015", "name": "Dr. Natividad Esguerra",  "position": "Professor",           "department": "College of Health", "cabinets": ["A", "B", "C"]},
]

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
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            cur.execute("TRUNCATE TABLE access_logs")
            cur.execute("TRUNCATE TABLE faculty_cabinet_access")
            cur.execute("TRUNCATE TABLE faculty")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("Cleared existing faculty and access logs.")

        faculty_ids = []
        with conn.cursor() as cur:
            for f in FACULTY:
                cur.execute(
                    "INSERT INTO faculty (id_number, name, position, department) VALUES (%s, %s, %s, %s)",
                    (f["id_number"], f["name"], f["position"], f["department"]),
                )
                fid = cur.lastrowid
                for cab in f["cabinets"]:
                    cur.execute("SELECT id FROM cabinets WHERE cabinet_id = %s", (cab,))
                    row = cur.fetchone()
                    if row:
                        cur.execute(
                            "INSERT IGNORE INTO faculty_cabinet_access (faculty_id, cabinet_id) VALUES (%s, %s)",
                            (fid, row["id"]),
                        )
                faculty_ids.append(fid)
        conn.commit()
        print(f"Seeded {len(FACULTY)} faculty members.")

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM cabinets")
            cab_pks = [r["id"] for r in cur.fetchall()]

        log_rows = []
        for days_ago in range(6, -1, -1):
            count = random.randint(40, 70)
            for _ in range(count):
                ts = _random_ts(days_ago)
                status = "granted" if random.random() < 0.55 else "denied"
                fac_id = random.choice(faculty_ids) if status == "granted" else None
                cab_pk = random.choice(cab_pks)
                note = None if status == "granted" else "Face not recognized"
                log_rows.append((fac_id, cab_pk, status, ts, note))

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO access_logs (faculty_id, cabinet_id, status, timestamp, note) VALUES (%s, %s, %s, %s, %s)",
                log_rows,
            )
        conn.commit()
        print(f"Seeded {len(log_rows)} access log entries.")

    finally:
        conn.close()


if __name__ == "__main__":
    seed()
