"""Admin web dashboard (Flask)."""
import base64
import os
from functools import wraps

import cv2
import numpy as np
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from afracs import config, db

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

_face_engine = None


def _get_face_engine():
    global _face_engine
    if _face_engine is None:
        from afracs.recognition import FaceEngine
        _face_engine = FaceEngine()
    return _face_engine


def _extract_face_from_form() -> bytes | None:
    face_data = request.form.get("face_data", "").strip()
    if not face_data:
        return None
    try:
        b64 = face_data.split(",", 1)[1] if "," in face_data else face_data
        img_bytes = base64.b64decode(b64)
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        return _get_face_engine().encode_from_image(img)
    except Exception:
        return None



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_db():
    from flask import g
    if "db_conn" not in g:
        g.db_conn = db.connect()
    return g.db_conn


@app.teardown_appcontext
def close_db(exc):
    from flask import g
    conn = g.pop("db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            conn = get_db()
            admin = db.get_admin_by_username(conn, username)
        except Exception:
            admin = None

        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/")
@login_required
def index():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM faculty")
        faculty_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM cabinets")
        cabinet_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM access_logs")
        log_count = cur.fetchone()["n"]
        cur.execute(
            """SELECT al.status, al.timestamp,
                      f.name AS faculty_name, c.cabinet_id AS cabinet
               FROM access_logs al
               LEFT JOIN faculty f ON al.faculty_id = f.id
               LEFT JOIN cabinets c ON al.cabinet_id = c.id
               ORDER BY al.timestamp DESC LIMIT 10"""
        )
        recent_logs = cur.fetchall()
    return render_template(
        "index.html",
        faculty_count=faculty_count,
        cabinet_count=cabinet_count,
        log_count=log_count,
        recent_logs=recent_logs,
    )



@app.route("/faculty")
@login_required
def faculty_list():
    faculty = db.get_all_faculty(get_db())
    return render_template("faculty/list.html", faculty=faculty)


@app.route("/faculty/add", methods=["GET", "POST"])
@login_required
def faculty_add():
    conn = get_db()
    cabinets = db.get_cabinets(conn)
    if request.method == "POST":
        id_number  = request.form.get("id_number", "").strip()
        name       = request.form.get("name", "").strip()
        position   = request.form.get("position", "").strip()
        department = request.form.get("department", "").strip()
        cabinet_ids = request.form.getlist("cabinets")

        if not id_number or not name:
            flash("ID number and name are required.", "danger")
        else:
            encoding_bytes = _extract_face_from_form()
            try:
                db.save_faculty(conn, id_number, name, position, department,
                                encoding_bytes=encoding_bytes, cabinet_ids=cabinet_ids)
                msg = f"{name} added successfully."
                if encoding_bytes:
                    msg += " Face enrolled."
                else:
                    msg += " Face not enrolled — you can add it later via Edit."
                flash(msg, "success")
                return redirect(url_for("faculty_list"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
    return render_template("faculty/form.html", cabinets=cabinets, faculty=None, action="Add")


@app.route("/faculty/<int:faculty_id>/edit", methods=["GET", "POST"])
@login_required
def faculty_edit(faculty_id):
    conn = get_db()
    faculty = db.get_faculty_by_id(conn, faculty_id)
    if not faculty:
        flash("Faculty not found.", "warning")
        return redirect(url_for("faculty_list"))
    cabinets = db.get_cabinets(conn)

    if request.method == "POST":
        id_number  = request.form.get("id_number", "").strip()
        name       = request.form.get("name", "").strip()
        position   = request.form.get("position", "").strip()
        department = request.form.get("department", "").strip()
        cabinet_ids = request.form.getlist("cabinets")

        if not id_number or not name:
            flash("ID number and name are required.", "danger")
        else:
            try:
                db.update_faculty(conn, faculty_id, id_number, name,
                                  position, department, cabinet_ids)
                encoding_bytes = _extract_face_from_form()
                if encoding_bytes:
                    db.update_faculty_encoding(conn, faculty_id, encoding_bytes)
                    flash(f"{name} updated. Face re-enrolled.", "success")
                else:
                    flash(f"{name} updated.", "success")
                return redirect(url_for("faculty_list"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
    return render_template("faculty/form.html", cabinets=cabinets, faculty=faculty, action="Edit")


@app.route("/faculty/<int:faculty_id>/delete", methods=["POST"])
@login_required
def faculty_delete(faculty_id):
    conn = get_db()
    faculty = db.get_faculty_by_id(conn, faculty_id)
    if faculty:
        db.delete_faculty(conn, faculty_id)
        flash(f"{faculty['name']} deleted.", "success")
    return redirect(url_for("faculty_list"))


@app.route("/faculty/<int:faculty_id>/enroll")
@login_required
def faculty_enroll(faculty_id):
    conn = get_db()
    faculty = db.get_faculty_by_id(conn, faculty_id)
    if not faculty:
        abort(404)
    return render_template("faculty/enroll.html", faculty=faculty)


@app.route("/faculty/<int:faculty_id>/enroll/upload", methods=["POST"])
@login_required
def faculty_enroll_upload(faculty_id):
    conn = get_db()
    if not db.get_faculty_by_id(conn, faculty_id):
        abort(404)

    if "photo" not in request.files or request.files["photo"].filename == "":
        return jsonify({"ok": False, "error": "No file selected."}), 400

    file = request.files["photo"]
    img_bytes = file.read()
    arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"ok": False, "error": "Could not decode image."}), 400

    try:
        encoding = _get_face_engine().encode_from_image(img)
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    if encoding is None:
        return jsonify({"ok": False, "error": "No face detected. Use a clear, well-lit photo."}), 400

    with conn.cursor() as cur:
        cur.execute("UPDATE faculty SET encoding = %s WHERE id = %s", (encoding, faculty_id))
    conn.commit()
    return jsonify({"ok": True})


@app.route("/faculty/<int:faculty_id>/enroll/capture", methods=["POST"])
@login_required
def faculty_enroll_capture(faculty_id):
    conn = get_db()
    if not db.get_faculty_by_id(conn, faculty_id):
        abort(404)

    data = request.get_json(silent=True)
    if not data or "image" not in data:
        return jsonify({"ok": False, "error": "No image data received."}), 400

    image_b64 = data["image"]
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(image_b64)
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return jsonify({"ok": False, "error": "Invalid image data."}), 400

    if img is None:
        return jsonify({"ok": False, "error": "Could not decode image."}), 400

    try:
        encoding = _get_face_engine().encode_from_image(img)
    except FileNotFoundError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    if encoding is None:
        return jsonify({"ok": False, "error": "No face detected. Center your face and try again."}), 400

    with conn.cursor() as cur:
        cur.execute("UPDATE faculty SET encoding = %s WHERE id = %s", (encoding, faculty_id))
    conn.commit()
    return jsonify({"ok": True})



@app.route("/cabinets")
@login_required
def cabinet_list():
    cabinets = db.get_cabinets(get_db())
    return render_template("cabinets/list.html", cabinets=cabinets)


@app.route("/cabinets/add", methods=["GET", "POST"])
@login_required
def cabinet_add():
    if request.method == "POST":
        cabinet_id  = request.form.get("cabinet_id", "").strip().upper()
        description = request.form.get("description", "").strip()
        location    = request.form.get("location", "").strip()
        if not cabinet_id:
            flash("Cabinet ID is required.", "danger")
        else:
            try:
                db.save_cabinet(get_db(), cabinet_id, description, location)
                flash(f"Cabinet {cabinet_id} added.", "success")
                return redirect(url_for("cabinet_list"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
    return render_template("cabinets/form.html", cabinet=None, action="Add")


@app.route("/cabinets/<int:cabinet_id>/edit", methods=["GET", "POST"])
@login_required
def cabinet_edit(cabinet_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM cabinets WHERE id = %s", (cabinet_id,))
        cabinet = cur.fetchone()
    if not cabinet:
        flash("Cabinet not found.", "warning")
        return redirect(url_for("cabinet_list"))

    if request.method == "POST":
        cid         = request.form.get("cabinet_id", "").strip().upper()
        description = request.form.get("description", "").strip()
        location    = request.form.get("location", "").strip()
        if not cid:
            flash("Cabinet ID is required.", "danger")
        else:
            try:
                db.update_cabinet(conn, cabinet_id, cid, description, location)
                flash(f"Cabinet {cid} updated.", "success")
                return redirect(url_for("cabinet_list"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
    return render_template("cabinets/form.html", cabinet=cabinet, action="Edit")


@app.route("/cabinets/<int:cabinet_id>/delete", methods=["POST"])
@login_required
def cabinet_delete(cabinet_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT cabinet_id FROM cabinets WHERE id = %s", (cabinet_id,))
        row = cur.fetchone()
    if row:
        db.delete_cabinet(conn, cabinet_id)
        flash(f"Cabinet {row['cabinet_id']} deleted.", "success")
    return redirect(url_for("cabinet_list"))



@app.route("/about")
@login_required
def about():
    return render_template("about.html")



@app.route("/logs")
@login_required
def logs():
    page = int(request.args.get("page", 1))
    per_page = 50
    rows, total = db.get_access_logs(get_db(), page=page, per_page=per_page)
    pages = (total + per_page - 1) // per_page
    return render_template("logs/list.html", logs=rows, page=page, pages=pages, total=total)


if __name__ == "__main__":
    # HTTPS required so browsers allow camera access (navigator.mediaDevices) on LAN
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=True, ssl_context="adhoc")
