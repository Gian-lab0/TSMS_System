from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("TSMS_SECRET_KEY", "dev-only-change-this-secret-key-before-deployment")
DB_PATH = os.environ.get("TSMS_DB_PATH", "teacher_schedule_management.db")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SLOTS = [
    "7:30–8:30", "8:30–9:30", "9:30–10:00", "10:00–11:00",
    "11:00–12:00", "12:00–1:00", "1:00–2:00", "2:00–3:00",
    "3:00–3:15", "3:15–4:15"
]
BREAK_SLOTS = {"9:30–10:00": "Morning Recess", "12:00–1:00": "Lunch Break", "3:00–3:15": "Afternoon Recess"}
SHS_SLOTS = [
    "7:30–8:30", "8:30–9:30", "9:30–10:30", "10:30–11:00",
    "11:00–12:00", "12:00–1:00", "1:00–2:00", "2:00–3:00",
    "3:00–4:00", "4:00–4:30"
]
SHS_BREAK_SLOTS = {"10:30–11:00": "Recess", "12:00–1:00": "Lunch"}

def slots_for_level(level):
    return SHS_SLOTS if level == "Senior High School" else SLOTS

def breaks_for_level(level):
    return SHS_BREAK_SLOTS if level == "Senior High School" else BREAK_SLOTS

def teachers_for_level(level):
    return SHS_TEACHERS if level == "Senior High School" else TEACHERS

def teachers_on_leave(db, on_date=None):
    on_date = on_date or datetime.now().date().isoformat()
    rows = db.execute("""SELECT DISTINCT teacher_name FROM leave_requests
        WHERE teacher_name IS NOT NULL AND teacher_name != ''
        AND status != 'Declined' AND start_date <= ? AND end_date >= ?""",
        (on_date, on_date)).fetchall()
    return {r["teacher_name"].casefold() for r in rows}

SECTIONS = {
    "Junior High School": {
        "Regular": ["7-Flores", "7-Ocampo", "8-Love", "8-Hope", "9-Yakal", "9-Narra", "10-Rizal", "10-Luna"],
        "ICT": ["AI", "Cybernauts", "Azure", "Python"],
    },
    "Senior High School": {
        "Acads": ["Philippians", "Corinthians", "Ephesians", "Thessalonians", "Maka-Diyos", "Makabansa", "Makatao"],
        "Tech-Pro": ["Philippians", "Corinthians", "Ephesians", "Thessalonians", "Maka-Diyos", "Makabansa", "Makatao"],
    }
}
TEACHERS = [
    "Amelia Lopez", "Ronald Domingo", "Jomalyn Caparal", "Precious Pascua",
    "Cornelio Marquez", "Nemencio Muralla", "Elaiza Vinluan", "Vicky Morales",
    "Jayjay Grospe", "Maureen Angeles", "Aprilyn Pascua", "Marisol Quiming",
    "Maribel Pascua", "Conrad Cayanga", "Elvin Alcaide", "Lester Peralta",
    "Arlene Mendillo", "May Sebido", "Alvin Cunanan", "Elvin Alcaide", "Jenna Granada",
    "Bryan Esmeria", "Marlon Santiago", "Mary Joy Bruan", "Rhea Joy Vallejos"
]
SHS_TEACHERS = ["May Sebido", "Alvin Cunanan", "Elvin Alcaide", "Jenna Granada", "Bryan Esmeria", "Marlon Santiago", "Mary Joy Bruan", "Rhea Joy Vallejos"]
SHS_SUBJECTS = ["Effective Communication", "General Science", "General Mathematics", "Life and Career Skills", "Mabisang Komunikasyon", "Pag-aaral ng Kasaysayan at Lipunang Pilipino", "Introduction to Philosophy", "Introduction to Organization and Management", "Citizenship and Civic Engagement", "Biology 1", "Biology 2", "Advanced Mathematics 1", "Filipino 1 (Wika at Komunikasyon sa Akademikong Filipino)", "Filipino 2 (Filipino para sa Larang Teknikal-Propesyonal)", "Social Sciences (Theory and Practice)", "Entrepreneurship", "Philippine Governance (Philippine Politics and Governance)", "Leadership Management in the Arts", "Contemporary Literature 1", "Contemporary Literature 2", "Empowerment Technologies", "Pre-calculus 1", "Pre-Calculus 2", "Advanced Mathematics 2", "Chemistry 1", "Chemistry 2", "Physics 1", "Physics 2", "Computer System Servicing", "Computer Programming (.NET Technology)", "Visual Graphic Design", "Kitchen Operation", "Events Management Services", "Bakery Operation"]
SUBJECTS = ["Mathematics", "English", "Science", "Araling Panlipunan", "TLE", "MAPEH", "Filipino", "Computer"]

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with con() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            program TEXT NOT NULL,
            section TEXT NOT NULL,
            day TEXT NOT NULL,
            slot TEXT NOT NULL,
            subject TEXT NOT NULL,
            teacher TEXT NOT NULL,
            owner_email TEXT,
            approved INTEGER NOT NULL DEFAULT 0,
            UNIQUE(level, program, section, day, slot)
        )""")
        # Migration for databases created before schedule ownership was added.
        schedule_columns = {row["name"] for row in db.execute("PRAGMA table_info(schedules)").fetchall()}
        if "owner_email" not in schedule_columns:
            db.execute("ALTER TABLE schedules ADD COLUMN owner_email TEXT")

        cols = {row["name"] for row in db.execute("PRAGMA table_info(schedules)").fetchall()}
        if "approved" not in cols:
            db.execute("ALTER TABLE schedules ADD COLUMN approved INTEGER NOT NULL DEFAULT 0")
        db.execute("""CREATE TABLE IF NOT EXISTS section_approvals (
            level TEXT NOT NULL, program TEXT NOT NULL, section TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0, approved_by TEXT, approved_at TEXT,
            PRIMARY KEY(level, program, section)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS password_resets (email TEXT PRIMARY KEY, reset_code TEXT NOT NULL)""")
        user_cols = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in user_cols:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'teacher'")
        db.execute("""CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, logged_at TEXT NOT NULL, success INTEGER NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, teacher_name TEXT,
            leave_type TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
            note TEXT, status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL
        )""")
        leave_cols = {row["name"] for row in db.execute("PRAGMA table_info(leave_requests)").fetchall()}
        if "teacher_name" not in leave_cols:
            db.execute("ALTER TABLE leave_requests ADD COLUMN teacher_name TEXT")
        admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        if admin_email:
            db.execute("UPDATE users SET role='admin' WHERE lower(email)=?", (admin_email,))
        elif db.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] == 0:
            first = db.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
            if first:
                db.execute("UPDATE users SET role='admin' WHERE id=?", (first["id"],))

init_db()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access is required.", "error")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            flash("Please log in to access Teacher Schedule Management System.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def all_sections():
    rows = []
    for level, programs in SECTIONS.items():
        for program, names in programs.items():
            for name in names:
                rows.append({"level": level, "program": program, "section": name})
    return rows

@app.context_processor
def inject_globals():
    return {"days": DAYS, "slots": SLOTS, "break_slots": BREAK_SLOTS, "section_groups": SECTIONS,
            "teacher_names": TEACHERS, "subject_names": SUBJECTS, "shs_teacher_names": SHS_TEACHERS, "shs_subject_names": SHS_SUBJECTS,
            "shs_slots": SHS_SLOTS, "shs_break_slots": SHS_BREAK_SLOTS}

@app.route("/")
def index():
    return redirect(url_for("home") if "user_email" in session else url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email.endswith("@gmail.com") or len(email) < 11:
            flash("Please enter a valid Gmail address ending in @gmail.com.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            try:
                with con() as db:
                    role = "admin" if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 else "teacher"
                    db.execute("INSERT INTO users(email, password_hash, role) VALUES (?, ?, ?)",
                               (email, generate_password_hash(password), role))
                flash("Account created as " + role + ". You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That Gmail account is already registered.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with con() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        ok = bool(user and check_password_hash(user["password_hash"], password))
        with con() as db:
            db.execute("INSERT INTO login_logs(email, logged_at, success) VALUES (?, ?, ?)",
                       (email, datetime.now().isoformat(timespec="seconds"), int(ok)))
        if ok:
            session["user_email"] = email
            session["role"] = user["role"] if "role" in user.keys() else "teacher"
            flash("Welcome to Teacher Schedule Management System!", "success")
            return redirect(url_for("home"))
        flash("Incorrect email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        if not email.endswith("@gmail.com"):
            flash("Enter the Gmail address used for your account.", "error")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
        else:
            with con() as db:
                user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                if user:
                    db.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                               (generate_password_hash(new_password), email))
                    flash("Password updated. Please log in.", "success")
                    return redirect(url_for("login"))
            flash("No account was found for that Gmail address.", "error")
    return render_template("auth.html", mode="forgot")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    with con() as db:
        total = db.execute("SELECT COUNT(*) AS n FROM schedules").fetchone()["n"]
        teachers = db.execute("SELECT COUNT(DISTINCT teacher) AS n FROM schedules").fetchone()["n"]
        sections = db.execute("SELECT COUNT(DISTINCT section) AS n FROM schedules").fetchone()["n"]
        pending = db.execute("SELECT COUNT(*) FROM (SELECT s.level,s.program,s.section FROM schedules s LEFT JOIN section_approvals a ON a.level=s.level AND a.program=s.program AND a.section=s.section GROUP BY s.level,s.program,s.section HAVING COALESCE(MAX(a.approved),0)=0)").fetchone()[0] if session.get("role") == "admin" else 0
        leave_pending = db.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'").fetchone()[0] if session.get("role") == "admin" else 0
    return render_template("home.html", total=total, teacher_count=teachers, section_count=sections, pending=pending, leave_pending=leave_pending)

@app.route("/timetable")
@login_required
def timetable():
    # Include both predefined sections and any sections actually entered by teachers.
    section_groups = {lev: {prog: list(names) for prog, names in programs.items()}
                      for lev, programs in SECTIONS.items()}
    with con() as db:
        saved_sections = db.execute(
            "SELECT DISTINCT level, program, section FROM schedules ORDER BY level, program, section"
        ).fetchall()
        for saved in saved_sections:
            section_groups.setdefault(saved["level"], {}).setdefault(saved["program"], [])
            if saved["section"] not in section_groups[saved["level"]][saved["program"]]:
                section_groups[saved["level"]][saved["program"]].append(saved["section"])

        level = request.args.get("level") or "Junior High School"
        if level not in section_groups and section_groups:
            level = next(iter(section_groups))
        program = request.args.get("program") or next(iter(section_groups.get(level, {"Regular": []})))
        if program not in section_groups.get(level, {}):
            program = next(iter(section_groups.get(level, {"Regular": []})))
        section = request.args.get("section") or next(iter(section_groups.get(level, {}).get(program, [""])))
        if section not in section_groups.get(level, {}).get(program, []):
            section = next(iter(section_groups.get(level, {}).get(program, [""])))
        entries = db.execute("""SELECT * FROM schedules
            WHERE level=? AND program=? AND section=?""", (level, program, section)).fetchall()
        approval = db.execute("SELECT approved,approved_by,approved_at FROM section_approvals WHERE level=? AND program=? AND section=?", (level, program, section)).fetchone()
        leave_names = teachers_on_leave(db)
    grid = {(r["day"], r["slot"]): r for r in entries}
    is_approved = bool(approval and approval["approved"])
    return render_template("timetable.html", level=level, program=program, section=section,
                           grid=grid, section_groups=section_groups, is_approved=is_approved,
                           approval=approval, entry_count=len(entries), leave_names=leave_names,
                           display_slots=slots_for_level(level), display_break_slots=breaks_for_level(level))

@app.route("/teachers")
@login_required
def teachers():
    with con() as db:
        rows = db.execute("""SELECT s.teacher, COUNT(*) AS periods
            FROM schedules s JOIN section_approvals a ON a.level=s.level AND a.program=s.program AND a.section=s.section AND a.approved=1
            GROUP BY s.teacher ORDER BY s.teacher""").fetchall()
    return render_template("teachers.html", rows=rows)

@app.route("/available")
@login_required
def available():
    day = request.args.get("day", "Monday")
    slot = request.args.get("slot", SLOTS[0])
    level = request.args.get("level", "Junior High School")
    on_date = request.args.get("date", datetime.now().date().isoformat())
    with con() as db:
        occupied = db.execute("SELECT DISTINCT teacher FROM schedules WHERE day=? AND slot=?", (day, slot)).fetchall()
        on_leave = teachers_on_leave(db, on_date)
    busy = {r["teacher"].casefold() for r in occupied}
    teacher_list = teachers_for_level(level)
    free = [t for t in teacher_list if t.casefold() not in busy and t.casefold() not in on_leave]
    busy_names = sorted({r["teacher"] for r in occupied})
    leave_names = sorted(t for t in teacher_list if t.casefold() in on_leave)
    return render_template("available.html", day=day, slot=slot, free=free, busy=busy_names, leave_names=leave_names, on_date=on_date, level=level)

@app.route("/manage", methods=["GET", "POST"])
@login_required
def manage():
    if request.method == "POST":
        action = request.form.get("action", "add")
        with con() as db:
            if action in ("approve", "reject", "admin_delete", "edit", "approve_section"):
                if session.get("role") != "admin":
                    flash("Only an admin can approve, edit, or remove schedule entries.", "error")
                    return redirect(url_for("manage"))
                try: sid = int(request.form.get("schedule_id", "0"))
                except ValueError: sid = 0
                if action == "approve_section":
                    level=request.form.get("level", ""); program=request.form.get("program", ""); section=request.form.get("section", "")
                    count=db.execute("SELECT COUNT(*) FROM schedules WHERE level=? AND program=? AND section=?", (level,program,section)).fetchone()[0]
                    if count == 0:
                        flash("Cannot approve an empty timetable. Add schedule entries first.", "error")
                    else:
                        db.execute("INSERT INTO section_approvals(level,program,section,approved,approved_by,approved_at) VALUES(?,?,?,1,?,?) ON CONFLICT(level,program,section) DO UPDATE SET approved=1,approved_by=excluded.approved_by,approved_at=excluded.approved_at", (level,program,section,session["user_email"],datetime.now().isoformat(timespec="seconds")))
                        flash("The complete section timetable is approved and can now be printed.", "success")
                elif action == "approve":
                    flash("Approve the complete timetable by section, not individual periods.", "warning")
                elif action == "reject":
                    flash("Individual schedule entries are kept as drafts; edit or delete them instead.", "warning")
                elif action == "admin_delete":
                    old=db.execute("SELECT level,program,section FROM schedules WHERE id=?", (sid,)).fetchone()
                    db.execute("DELETE FROM schedules WHERE id=?", (sid,))
                    if old:
                        db.execute("UPDATE section_approvals SET approved=0,approved_by=NULL,approved_at=NULL WHERE level=? AND program=? AND section=?", (old["level"],old["program"],old["section"]))
                    flash("Schedule entry deleted. The timetable is marked incomplete until reviewed again.", "success")
                elif action == "edit":
                    teacher=request.form.get("teacher", "").strip()
                    old=db.execute("SELECT id,level,program,section,day,slot,teacher FROM schedules WHERE id=?", (sid,)).fetchone()
                    allowed_teachers = teachers_for_level(old["level"]) if old else []
                    if not old or teacher not in allowed_teachers:
                        flash("Invalid teacher selection.", "error")
                    else:
                        conflict=db.execute("SELECT id FROM schedules WHERE lower(teacher)=lower(?) AND day=? AND slot=? AND id<>?", (teacher,old["day"],old["slot"],sid)).fetchone()
                        if conflict:
                            flash("That teacher is already assigned to another class at this day and time.", "error")
                        else:
                            db.execute("UPDATE schedules SET teacher=? WHERE id=?", (teacher,sid))
                            flash("Teacher changed. All other schedule details and the section approval status remain unchanged.", "success")
                return redirect(url_for("manage"))
            if action == "delete":
                try: sid = int(request.form.get("schedule_id", "0"))
                except ValueError: sid = 0
                owned = db.execute("SELECT id FROM schedules WHERE id=? AND lower(owner_email)=lower(?)", (sid,session["user_email"])).fetchone()
                if not owned:
                    flash("You can only delete schedule entries that you added.", "error")
                else:
                    old=db.execute("SELECT level,program,section FROM schedules WHERE id=?", (sid,)).fetchone()
                    approval=db.execute("SELECT approved FROM section_approvals WHERE level=? AND program=? AND section=?", (old["level"],old["program"],old["section"])).fetchone() if old else None
                    if approval and approval["approved"]:
                        flash("This timetable is approved. Only the admin can change it.", "error")
                    else:
                        db.execute("DELETE FROM schedules WHERE id=?", (sid,))
                        if old:
                            db.execute("UPDATE section_approvals SET approved=0,approved_by=NULL,approved_at=NULL WHERE level=? AND program=? AND section=?", (old["level"],old["program"],old["section"]))
                        flash("Schedule entry deleted. The timetable is now marked incomplete.", "success")
                return redirect(url_for("manage"))

            level=request.form.get("level","").strip()
            program=request.form.get("program","").strip()
            section=request.form.get("section","").strip()
            selected_days=request.form.getlist("day")
            slot=request.form.get("slot","").strip()
            subject=request.form.get("subject","").strip()
            teacher=request.form.get("teacher","").strip()
            valid_sections = SECTIONS.get(level, {}).get(program, [])
            allowed_subjects = SHS_SUBJECTS if level == "Senior High School" else SUBJECTS
            allowed_teachers = SHS_TEACHERS if level == "Senior High School" else TEACHERS
            if not valid_sections or section not in valid_sections or not selected_days or any(d not in DAYS for d in selected_days) or slot not in slots_for_level(level) or slot in breaks_for_level(level) or subject not in allowed_subjects or teacher not in allowed_teachers:
                flash("Please select valid schedule details from the lists.", "error")
                return redirect(url_for("manage"))
            existing_approval=db.execute("SELECT approved FROM section_approvals WHERE level=? AND program=? AND section=?", (level,program,section)).fetchone()
            if existing_approval and existing_approval["approved"] and session.get("role") != "admin":
                flash("This section timetable is approved. Only the admin can change it.", "error")
                return redirect(url_for("manage"))
            saved = 0
            for day in selected_days:
                section_conflict=db.execute("SELECT id FROM schedules WHERE level=? AND program=? AND section=? AND day=? AND slot=?",(level,program,section,day,slot)).fetchone()
                teacher_conflict=db.execute("SELECT section FROM schedules WHERE lower(teacher)=lower(?) AND day=? AND slot=?",(teacher,day,slot)).fetchone()
                if section_conflict or teacher_conflict:
                    flash(f"{day}: conflict detected; this day was skipped.", "error")
                    continue
                try:
                    db.execute("INSERT INTO schedules(level,program,section,day,slot,subject,teacher,owner_email,approved) VALUES(?,?,?,?,?,?,?,?,0)",
                               (level,program,section,day,slot,subject,teacher,session["user_email"]))
                    saved += 1
                    db.execute("INSERT INTO section_approvals(level,program,section,approved) VALUES(?,?,?,0) ON CONFLICT(level,program,section) DO UPDATE SET approved=0,approved_by=NULL,approved_at=NULL", (level,program,section))
                except sqlite3.IntegrityError:
                    flash(f"{day}: duplicate schedule skipped.", "error")
            if saved:
                flash(f"{saved} schedule day(s) saved as draft. The admin can edit the timetable and approve the complete section when it is finished.", "success")
        return redirect(url_for("manage"))
    with con() as db:
        rows=db.execute("SELECT * FROM schedules ORDER BY level,program,section,day,slot").fetchall()
        section_statuses=db.execute("SELECT s.level,s.program,s.section,COUNT(*) AS entry_count,COALESCE(a.approved,0) AS complete,a.approved_by,a.approved_at FROM schedules s LEFT JOIN section_approvals a ON a.level=s.level AND a.program=s.program AND a.section=s.section GROUP BY s.level,s.program,s.section ORDER BY s.level,s.program,s.section").fetchall()
    return render_template("manage.html", rows=rows, section_rows=all_sections(), section_statuses=section_statuses)

@app.route("/admin/cover-teachers")
@login_required
@admin_required
def cover_teachers():
    day=request.args.get("day", "Monday")
    slot=request.args.get("slot", "")
    level=request.args.get("level", "Junior High School")
    on_date=request.args.get("date", datetime.now().date().isoformat())
    absent=request.args.get("absent", "")
    with con() as db:
        occupied=db.execute("SELECT DISTINCT teacher FROM schedules WHERE day=? AND slot=?", (day,slot)).fetchall()
        on_leave=teachers_on_leave(db,on_date)
    busy={r["teacher"].casefold() for r in occupied if r["teacher"].casefold()!=absent.casefold()}
    teachers=teachers_for_level(level)
    free=[t for t in teachers if t.casefold() not in busy and t.casefold() not in on_leave and t.casefold()!=absent.casefold()]
    leave=[t for t in teachers if t.casefold() in on_leave]
    return render_template("cover_teachers.html", day=day, slot=slot, level=level, on_date=on_date, absent=absent, free=free, busy=sorted({r["teacher"] for r in occupied if r["teacher"].casefold()!=absent.casefold()}), leave_names=leave)

@app.route("/teacher-periods/<teacher>")
@login_required
def teacher_periods(teacher):
    with con() as db:
        rows=db.execute("SELECT s.level,s.program,s.section,s.day,s.slot,s.subject FROM schedules s JOIN section_approvals a ON a.level=s.level AND a.program=s.program AND a.section=s.section AND a.approved=1 WHERE s.teacher=? ORDER BY CASE s.day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 ELSE 5 END,s.slot",(teacher,)).fetchall()
    return render_template("teacher_periods.html", teacher=teacher, rows=rows)

@app.route("/leave-request", methods=["GET", "POST"])
@login_required
def leave_request():
    if request.method == "POST":
        leave_type=request.form.get("leave_type","")
        start=request.form.get("start_date","")
        end=request.form.get("end_date","")
        note=request.form.get("note","").strip()
        teacher_name=request.form.get("teacher_name", "").strip()
        valid_names=set(TEACHERS + SHS_TEACHERS)
        if teacher_name not in valid_names or leave_type not in ["Sick Leave", "Wellness Break"] or not start or not end or end < start:
            flash("Please enter valid leave details.", "error")
        else:
            with con() as db:
                db.execute("INSERT INTO leave_requests(email,teacher_name,leave_type,start_date,end_date,note,created_at) VALUES(?,?,?,?,?,?,?)",
                    (session["user_email"],teacher_name,leave_type,start,end,note,datetime.now().isoformat(timespec="seconds")))
            flash("Your request was sent to the admin.", "success")
            return redirect(url_for("leave_request"))
    with con() as db:
        rows=db.execute("SELECT * FROM leave_requests WHERE lower(email)=lower(?) ORDER BY id DESC",(session["user_email"],)).fetchall()
    return render_template("leave_request.html", rows=rows, teacher_names=sorted(set(TEACHERS + SHS_TEACHERS)))

@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    with con() as db:
        users=db.execute("SELECT id,email,role FROM users ORDER BY email").fetchall()
        pending=db.execute("SELECT s.level,s.program,s.section,COUNT(*) AS entry_count FROM schedules s LEFT JOIN section_approvals a ON a.level=s.level AND a.program=s.program AND a.section=s.section GROUP BY s.level,s.program,s.section HAVING COALESCE(MAX(a.approved),0)=0 ORDER BY s.level,s.program,s.section").fetchall()
        section_statuses=db.execute("SELECT s.level,s.program,s.section,COUNT(*) AS entry_count,COALESCE(a.approved,0) AS complete,a.approved_by,a.approved_at FROM schedules s LEFT JOIN section_approvals a ON a.level=s.level AND a.program=s.program AND a.section=s.section GROUP BY s.level,s.program,s.section ORDER BY s.level,s.program,s.section").fetchall()
        leaves=db.execute("SELECT * FROM leave_requests ORDER BY CASE status WHEN 'Pending' THEN 0 ELSE 1 END,id DESC").fetchall()
        logs=db.execute("SELECT * FROM login_logs ORDER BY id DESC LIMIT 200").fetchall()
        all_schedules=db.execute("SELECT * FROM schedules ORDER BY level,program,section,day,slot").fetchall()
    return render_template("admin.html", users=users, pending=pending, section_statuses=section_statuses, leaves=leaves, logs=logs, all_schedules=all_schedules)

@app.route("/admin/reset-password", methods=["POST"])
@login_required
@admin_required
def admin_reset_password():
    email=request.form.get("email","").strip().lower()
    password=request.form.get("new_password","")
    if len(password)<8:
        flash("New password must be at least 8 characters.", "error")
    else:
        with con() as db:
            cur=db.execute("UPDATE users SET password_hash=? WHERE lower(email)=?",(generate_password_hash(password),email))
        flash("Password reset successfully." if cur.rowcount else "Account not found.", "success" if cur.rowcount else "error")
    return redirect(url_for("admin"))

@app.route("/admin/leave-status", methods=["POST"])
@login_required
@admin_required
def leave_status():
    status=request.form.get("status","")
    try: rid=int(request.form.get("request_id","0"))
    except ValueError: rid=0
    if status not in ["Approved","Declined"]:
        flash("Invalid status.", "error")
    else:
        with con() as db: db.execute("UPDATE leave_requests SET status=? WHERE id=?",(status,rid))
        flash("Leave request updated.", "success")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
