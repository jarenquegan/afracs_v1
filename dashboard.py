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
from werkzeug.security import check_password_hash, generate_password_hash

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


def _get_pi_temp() -> str:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
            return f"{temp:.1f}°C"
    except Exception:
        return "38.5°C (Simulated)"


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
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            conn = get_db()
            admin = db.get_admin_by_username_or_email(conn, identifier)
        except Exception:
            admin = None

        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session["admin_full_name"] = admin.get("full_name", "")
            session["admin_email"] = admin.get("email", "")
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

        # Fetch daily access counts for the last 7 days for the chart
        cur.execute(
            """SELECT DATE(timestamp) as date, status, COUNT(*) as count
               FROM access_logs
               WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
               GROUP BY DATE(timestamp), status
               ORDER BY date ASC"""
        )
        daily_counts = cur.fetchall()

        # Format chart data
        import datetime
        from datetime import timedelta
        
        today = datetime.date.today()
        dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
        labels = [d.strftime("%b %d") for d in dates]
        
        # Map SQL results to dates
        granted_dict = {row['date']: row['count'] for row in daily_counts if row['status'] == 'granted'}
        denied_dict = {row['date']: row['count'] for row in daily_counts if row['status'] == 'denied'}
        
        data_granted = [granted_dict.get(d, 0) for d in dates]
        data_denied = [denied_dict.get(d, 0) for d in dates]
        
        system_temp = _get_pi_temp()

    return render_template(
        "index.html",
        faculty_count=faculty_count,
        cabinet_count=cabinet_count,
        log_count=log_count,
        system_temp=system_temp,
        recent_logs=recent_logs,
        chart_labels=labels,
        chart_data_granted=data_granted,
        chart_data_denied=data_denied,
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
    search = request.args.get("q", "").strip()
    per_page = 50
    rows, total = db.get_access_logs(get_db(), page=page, per_page=per_page, search=search)
    pages = (total + per_page - 1) // per_page
    return render_template("logs/list.html", logs=rows, page=page, pages=pages, total=total, search=search)


@app.route("/reports")
@login_required
def reports():
    conn = get_db()
    cabinets = db.get_cabinets(conn)
    faculty = db.get_all_faculty(conn)
    
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    cabinet_id = request.args.get("cabinet_id", "")
    faculty_id = request.args.get("faculty_id", "")
    status = request.args.get("status", "")

    logs = []
    if request.args:
        logs = db.get_filtered_logs(
            conn,
            start_date=start_date or None,
            end_date=end_date or None,
            start_time=start_time or None,
            end_time=end_time or None,
            cabinet_id=cabinet_id or None,
            faculty_id=faculty_id or None,
            status=status or None,
        )

    return render_template(
        "reports/index.html",
        cabinets=cabinets,
        faculty=faculty,
        logs=logs,
        args=request.args,
    )

@app.route("/reports/export")
@login_required
def reports_export():
    import csv
    from io import StringIO
    from flask import Response
    
    conn = get_db()
    logs = db.get_filtered_logs(
        conn,
        start_date=request.args.get("start_date") or None,
        end_date=request.args.get("end_date") or None,
        start_time=request.args.get("start_time") or None,
        end_time=request.args.get("end_time") or None,
        cabinet_id=request.args.get("cabinet_id") or None,
        faculty_id=request.args.get("faculty_id") or None,
        status=request.args.get("status") or None,
    )
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Timestamp', 'Faculty', 'ID Number', 'Cabinet', 'Status', 'Note'])
    for log in logs:
        cw.writerow([
            log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if log['timestamp'] else '',
            log['faculty_name'] or 'Unknown',
            log['id_number'] or '',
            log['cabinet'] or '?',
            log['status'].upper(),
            log['note'] or ''
        ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=afracs_report.csv"}
    )

@app.route("/reports/print")
@login_required
def reports_print():
    conn = get_db()
    logs = db.get_filtered_logs(
        conn,
        start_date=request.args.get("start_date") or None,
        end_date=request.args.get("end_date") or None,
        start_time=request.args.get("start_time") or None,
        end_time=request.args.get("end_time") or None,
        cabinet_id=request.args.get("cabinet_id") or None,
        faculty_id=request.args.get("faculty_id") or None,
        status=request.args.get("status") or None,
    )
    return render_template("reports/print.html", logs=logs, args=request.args)

@app.route("/admins")
@login_required
def admin_list():
    admins = db.get_all_admins(get_db())
    return render_template("admins/list.html", admins=admins)


@app.route("/admins/add", methods=["GET", "POST"])
@login_required
def admin_add():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        if not username or not password:
            flash("Username and password are required.", "danger")
        else:
            try:
                db.create_admin(get_db(), username, generate_password_hash(password), full_name, email)
                flash(f"Admin {username} added.", "success")
                return redirect(url_for("admin_list"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
    return render_template("admins/form.html", admin=None, action="Add")


@app.route("/admins/<int:admin_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit(admin_id):
    conn = get_db()
    admin = db.get_admin_by_id(conn, admin_id)
    if not admin:
        flash("Admin not found.", "warning")
        return redirect(url_for("admin_list"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        if not username:
            flash("Username is required.", "danger")
        else:
            try:
                pw_hash = generate_password_hash(password) if password else None
                db.update_admin(conn, admin_id, username, full_name, email, pw_hash)
                flash(f"Admin {username} updated.", "success")
                return redirect(url_for("admin_list"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")
    return render_template("admins/form.html", admin=admin, action="Edit")


@app.route("/admins/<int:admin_id>/delete", methods=["POST"])
@login_required
def admin_delete(admin_id):
    if admin_id == session.get("admin_id"):
        flash("You cannot delete your own account.", "danger")
    else:
        db.delete_admin(get_db(), admin_id)
        flash("Admin deleted.", "success")
    return redirect(url_for("admin_list"))


if __name__ == "__main__":
    # HTTPS required so browsers allow camera access (navigator.mediaDevices) on LAN
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=True, ssl_context="adhoc")
