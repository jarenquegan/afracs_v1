"""MySQL schema and connection helpers."""
import pymysql
from pymysql.cursors import DictCursor

from afracs import config

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS admins (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        username      VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name     VARCHAR(255) DEFAULT '',
        email         VARCHAR(255) DEFAULT '',
        created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS cabinets (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        cabinet_id  VARCHAR(50) UNIQUE NOT NULL,
        description VARCHAR(255),
        location    VARCHAR(255),
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS faculty (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        id_number   VARCHAR(50) UNIQUE NOT NULL,
        name        VARCHAR(255) NOT NULL,
        position    VARCHAR(255) NOT NULL DEFAULT '',
        department  VARCHAR(255) NOT NULL DEFAULT '',
        encoding    BLOB NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS faculty_cabinet_access (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        faculty_id  INT NOT NULL,
        cabinet_id  INT NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
        FOREIGN KEY (cabinet_id) REFERENCES cabinets(id) ON DELETE CASCADE,
        UNIQUE KEY (faculty_id, cabinet_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS access_logs (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        faculty_id  INT NULL,
        cabinet_id  INT NOT NULL,
        status      ENUM('granted','denied') NOT NULL,
        timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        note        TEXT,
        FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL,
        FOREIGN KEY (cabinet_id) REFERENCES cabinets(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

_MIGRATIONS = [
    "ALTER TABLE faculty ADD COLUMN IF NOT EXISTS id_number VARCHAR(50) UNIQUE",
    "ALTER TABLE faculty ADD COLUMN IF NOT EXISTS position VARCHAR(255) DEFAULT ''",
    "ALTER TABLE faculty ADD COLUMN IF NOT EXISTS department VARCHAR(255) DEFAULT ''",
    "ALTER TABLE access_logs ADD COLUMN IF NOT EXISTS cabinet_id INT",
    "ALTER TABLE faculty MODIFY COLUMN encoding BLOB NULL",
    "ALTER TABLE admins ADD COLUMN IF NOT EXISTS full_name VARCHAR(255) DEFAULT ''",
    "ALTER TABLE admins ADD COLUMN IF NOT EXISTS email VARCHAR(255) DEFAULT ''",
]

_BOOTSTRAP = [
    "INSERT IGNORE INTO cabinets (cabinet_id, description, location) "
    "VALUES ('A', 'Cabinet A', 'College of Health - Room A')",
    "INSERT IGNORE INTO cabinets (cabinet_id, description, location) "
    "VALUES ('B', 'Cabinet B', 'College of Health - Room B')",
    "INSERT IGNORE INTO cabinets (cabinet_id, description, location) "
    "VALUES ('C', 'Cabinet C', 'College of Health - Room C')",
    "INSERT IGNORE INTO cabinets (cabinet_id, description, location) "
    "VALUES ('D', 'Cabinet D', 'College of Health - Room D')",
]


def connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DB,
        cursorclass=DictCursor,
        charset="utf8mb4",
        autocommit=False,
    )


def init_db() -> None:
    server = pymysql.connect(
        host=config.MYSQL_HOST,
        port=config.MYSQL_PORT,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        charset="utf8mb4",
    )
    try:
        with server.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DB}` "
                "DEFAULT CHARSET=utf8mb4"
            )
        server.commit()
    finally:
        server.close()

    conn = connect()
    try:
        with conn.cursor() as cur:
            for stmt in SCHEMA:
                cur.execute(stmt)
            for migration in _MIGRATIONS:
                try:
                    cur.execute(migration)
                except Exception:
                    pass
            for bootstrap in _BOOTSTRAP:
                try:
                    cur.execute(bootstrap)
                except Exception:
                    pass
        conn.commit()

        from werkzeug.security import generate_password_hash
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM admins")
            if cur.fetchone()["n"] == 0:
                create_admin(conn, config.ADMIN_USERNAME, generate_password_hash(config.ADMIN_PASSWORD))
                print(f"  Seeded default admin: {config.ADMIN_USERNAME}")
    finally:
        conn.close()


def get_cabinets(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, cabinet_id, description, location FROM cabinets ORDER BY cabinet_id")
        return cur.fetchall()


def load_known_faces(conn) -> list[dict]:
    result = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, id_number, name, position, department, encoding FROM faculty ORDER BY id"
        )
        rows = cur.fetchall()
        for row in rows:
            cur.execute(
                """SELECT c.cabinet_id FROM cabinets c
                   INNER JOIN faculty_cabinet_access fca ON c.id = fca.cabinet_id
                   WHERE fca.faculty_id = %s ORDER BY c.cabinet_id""",
                (row["id"],)
            )
            cabinets = [r["cabinet_id"] for r in cur.fetchall()]
            row["cabinets"] = cabinets
            result.append(row)
    return result


def save_faculty(
    conn,
    id_number: str,
    name: str,
    position: str,
    department: str,
    encoding_bytes: bytes | None = None,
    cabinet_ids: list[str] | None = None,
) -> int:
    if cabinet_ids is None:
        cabinet_ids = []

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO faculty (id_number, name, position, department, encoding) "
            "VALUES (%s, %s, %s, %s, %s)",
            (id_number, name, position, department, encoding_bytes),
        )
        faculty_id = cur.lastrowid

        for cabinet_id in cabinet_ids:
            cur.execute(
                "SELECT id FROM cabinets WHERE cabinet_id = %s",
                (cabinet_id,)
            )
            cabinet = cur.fetchone()
            if cabinet:
                cur.execute(
                    "INSERT IGNORE INTO faculty_cabinet_access (faculty_id, cabinet_id) "
                    "VALUES (%s, %s)",
                    (faculty_id, cabinet["id"])
                )

    conn.commit()
    return faculty_id


def update_faculty_cabinets(conn, faculty_id: int, cabinet_ids: list[str]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM faculty_cabinet_access WHERE faculty_id = %s",
            (faculty_id,)
        )
        for cabinet_id in cabinet_ids:
            cur.execute(
                "SELECT id FROM cabinets WHERE cabinet_id = %s",
                (cabinet_id,)
            )
            cabinet = cur.fetchone()
            if cabinet:
                cur.execute(
                    "INSERT IGNORE INTO faculty_cabinet_access (faculty_id, cabinet_id) "
                    "VALUES (%s, %s)",
                    (faculty_id, cabinet["id"])
                )
    conn.commit()


def log_access(
    conn,
    faculty_id: int | None,
    cabinet_id: str | None,
    status: str,
    note: str = "",
) -> None:
    import logging as _logging
    _log = _logging.getLogger(__name__)

    resolved_cabinet_pk: int | None = None
    if cabinet_id:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM cabinets WHERE cabinet_id = %s", (cabinet_id,))
            cabinet = cur.fetchone()
        if cabinet:
            resolved_cabinet_pk = cabinet["id"]
        else:
            _log.warning("log_access: cabinet_id %r not found — logging without cabinet", cabinet_id)

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO access_logs (faculty_id, cabinet_id, status, note) "
            "VALUES (%s, %s, %s, %s)",
            (faculty_id, resolved_cabinet_pk, status, note or None),
        )
    conn.commit()


def get_admin_by_username_or_email(conn, identifier: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, username, full_name, email, password_hash "
            "FROM admins WHERE username = %s OR email = %s",
            (identifier, identifier)
        )
        return cur.fetchone()

def get_admin_by_username(conn, username: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, full_name, email, password_hash FROM admins WHERE username = %s", (username,))
        return cur.fetchone()


def create_admin(conn, username: str, password_hash: str, full_name: str = "", email: str = "") -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT IGNORE INTO admins (username, password_hash, full_name, email) VALUES (%s, %s, %s, %s)",
            (username, password_hash, full_name, email),
        )
    conn.commit()


def get_all_admins(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, full_name, email, created_at FROM admins ORDER BY username")
        return cur.fetchall()


def delete_admin(conn, admin_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM admins WHERE id = %s", (admin_id,))
    conn.commit()


def update_admin(conn, admin_id: int, username: str, full_name: str, email: str, password_hash: str | None = None) -> None:
    with conn.cursor() as cur:
        if password_hash:
            cur.execute(
                "UPDATE admins SET username=%s, full_name=%s, email=%s, password_hash=%s WHERE id=%s",
                (username, full_name, email, password_hash, admin_id),
            )
        else:
            cur.execute(
                "UPDATE admins SET username=%s, full_name=%s, email=%s WHERE id=%s",
                (username, full_name, email, admin_id),
            )
    conn.commit()


def get_admin_by_id(conn, admin_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, full_name, email, created_at FROM admins WHERE id = %s", (admin_id,))
        return cur.fetchone()


def update_faculty(
    conn,
    faculty_id: int,
    id_number: str,
    name: str,
    position: str,
    department: str,
    cabinet_ids: list[str] | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE faculty SET id_number=%s, name=%s, position=%s, department=%s WHERE id=%s",
            (id_number, name, position, department, faculty_id),
        )
    if cabinet_ids is not None:
        update_faculty_cabinets(conn, faculty_id, cabinet_ids)
    conn.commit()


def delete_faculty(conn, faculty_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM faculty WHERE id = %s", (faculty_id,))
    conn.commit()


def get_faculty_by_id(conn, faculty_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, id_number, name, position, department, encoding, created_at "
            "FROM faculty WHERE id = %s",
            (faculty_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """SELECT c.cabinet_id FROM cabinets c
               INNER JOIN faculty_cabinet_access fca ON c.id = fca.cabinet_id
               WHERE fca.faculty_id = %s ORDER BY c.cabinet_id""",
            (faculty_id,)
        )
        row["cabinets"] = [r["cabinet_id"] for r in cur.fetchall()]
        row["has_face"] = row["encoding"] is not None
        row.pop("encoding", None)
        return row


def get_faculty_by_id_number(conn, id_number: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, id_number, name, position, department, encoding, created_at "
            "FROM faculty WHERE id_number = %s",
            (id_number,)
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """SELECT c.cabinet_id FROM cabinets c
               INNER JOIN faculty_cabinet_access fca ON c.id = fca.cabinet_id
               WHERE fca.faculty_id = %s ORDER BY c.cabinet_id""",
            (row["id"],)
        )
        row["cabinets"] = [r["cabinet_id"] for r in cur.fetchall()]
        row["has_face"] = row["encoding"] is not None
        row.pop("encoding", None)
        return row


def update_faculty_encoding(conn, faculty_id: int, encoding_bytes: bytes) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE faculty SET encoding = %s WHERE id = %s",
            (encoding_bytes, faculty_id)
        )
    conn.commit()


def get_all_faculty(conn) -> list[dict]:
    result = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, id_number, name, position, department, "
            "(encoding IS NOT NULL) AS has_face, created_at "
            "FROM faculty ORDER BY name"
        )
        rows = cur.fetchall()
        for row in rows:
            cur.execute(
                """SELECT c.cabinet_id FROM cabinets c
                   INNER JOIN faculty_cabinet_access fca ON c.id = fca.cabinet_id
                   WHERE fca.faculty_id = %s ORDER BY c.cabinet_id""",
                (row["id"],)
            )
            row["cabinets"] = [r["cabinet_id"] for r in cur.fetchall()]
            result.append(row)
    return result


def save_cabinet(conn, cabinet_id: str, description: str, location: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO cabinets (cabinet_id, description, location) VALUES (%s, %s, %s)",
            (cabinet_id, description, location),
        )
        row_id = cur.lastrowid
    conn.commit()
    return row_id


def update_cabinet(conn, id: int, cabinet_id: str, description: str, location: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cabinets SET cabinet_id=%s, description=%s, location=%s WHERE id=%s",
            (cabinet_id, description, location, id),
        )
    conn.commit()


def delete_cabinet(conn, id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM cabinets WHERE id = %s", (id,))
    conn.commit()


def get_access_logs(conn, page: int = 1, per_page: int = 50) -> tuple[list[dict], int]:
    offset = (page - 1) * per_page
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM access_logs")
        total = cur.fetchone()["total"]
        cur.execute(
            """SELECT al.id, al.status, al.timestamp, al.note,
                      f.name AS faculty_name, f.id_number,
                      c.cabinet_id AS cabinet
               FROM access_logs al
               LEFT JOIN faculty f ON al.faculty_id = f.id
               LEFT JOIN cabinets c ON al.cabinet_id = c.id
               ORDER BY al.timestamp DESC
               LIMIT %s OFFSET %s""",
            (per_page, offset),
        )
        rows = cur.fetchall()
    return rows, total


def get_filtered_logs(
    conn,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    cabinet_id: str | None = None,
    faculty_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    query = """
        SELECT al.id, al.status, al.timestamp, al.note,
               f.name AS faculty_name, f.id_number,
               c.cabinet_id AS cabinet
        FROM access_logs al
        LEFT JOIN faculty f ON al.faculty_id = f.id
        LEFT JOIN cabinets c ON al.cabinet_id = c.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND DATE(al.timestamp) >= %s"
        params.append(start_date)
    if end_date:
        query += " AND DATE(al.timestamp) <= %s"
        params.append(end_date)
    if start_time:
        query += " AND TIME(al.timestamp) >= %s"
        params.append(start_time)
    if end_time:
        query += " AND TIME(al.timestamp) <= %s"
        params.append(end_time)
    if cabinet_id:
        query += " AND c.id = %s"
        params.append(cabinet_id)
    if faculty_id:
        query += " AND f.id = %s"
        params.append(faculty_id)
    if status:
        query += " AND al.status = %s"
        params.append(status)

    query += " ORDER BY al.timestamp DESC"

    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()

if __name__ == "__main__":
    init_db()
    print(f"Initialized MySQL database `{config.MYSQL_DB}` on {config.MYSQL_HOST}:{config.MYSQL_PORT}")
