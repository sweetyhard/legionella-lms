import os, json, sqlite3, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH  = os.path.join(DATA_DIR, "app.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pw_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            details TEXT NOT NULL,
            taken_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

def seed_users_if_empty():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM users")
    n = cur.fetchone()["n"]
    if n == 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # admin
        cur.execute(
            "INSERT INTO users(username, pw_hash, is_admin, created_at) VALUES(?,?,?,?)",
            ("admin", generate_password_hash("Admin!2345"), 1, now)
        )
        # 10 assistants
        for i in range(1, 11):
            u = f"asistan{i:02d}"
            cur.execute(
                "INSERT INTO users(username, pw_hash, is_admin, created_at) VALUES(?,?,?,?)",
                (u, generate_password_hash("Asistan!2345"), 0, now)
            )
        conn.commit()
    conn.close()

def load_cases():
    with open(os.path.join(DATA_DIR, "vaka_bankasi.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def load_quiz():
    with open(os.path.join(DATA_DIR, "quiz.json"), "r", encoding="utf-8") as f:
        return json.load(f)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.is_admin = bool(row["is_admin"])
        self.created_at = row["created_at"]

@login_manager.user_loader
def load_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return User(row) if row else None

@app.before_request
def _bootstrap():
    # ensure db exists
    if not os.path.exists(DB_PATH):
        init_db()
        seed_users_if_empty()

@app.route("/", methods=["GET"])
@login_required
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        conn.close()
        if row and check_password_hash(row["pw_hash"], password):
            login_user(User(row))
            return redirect(url_for("home"))
        flash("Hatalı kullanıcı adı veya şifre.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/lessons")
@login_required
def lessons():
    return render_template("lessons.html")

@app.route("/cases")
@login_required
def cases():
    cases = load_cases()
    return render_template("cases.html", cases=cases)

@app.route("/cases/<int:case_id>")
@login_required
def case_detail(case_id):
    cases = load_cases()
    c = next((x for x in cases if x["id"] == case_id), None)
    if not c:
        flash("Vaka bulunamadı.")
        return redirect(url_for("cases"))
    return render_template("case_detail.html", c=c)

@app.route("/quiz", methods=["GET","POST"])
@login_required
def quiz():
    quiz = load_quiz()
    if request.method == "POST":
        score = 0
        review = []
        for q in quiz["questions"]:
            key = f"q{q['id']}"
            chosen = int(request.form.get(key))
            correct = int(q["answer_index"])
            if chosen == correct:
                score += 20
            review.append({
                "stem": q["stem"],
                "your": q["choices"][chosen],
                "correct": q["choices"][correct],
                "explain": q["explain"]
            })
        taken_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        details = " | ".join([f"Q{idx+1}:{'D' if (int(request.form.get('q'+str(q['id'])))==q['answer_index']) else 'Y'}"
                              for idx, q in enumerate(quiz["questions"])])
        # save
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO results(user_id, score, details, taken_at) VALUES(?,?,?,?)",
                    (current_user.id, score, details, taken_at))
        conn.commit()
        conn.close()
        return render_template("quiz_result.html", score=score, review=review)
    return render_template("quiz.html", quiz=quiz)

@app.route("/me")
@login_required
def me():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT score, details, taken_at FROM results WHERE user_id=? ORDER BY id DESC", (current_user.id,))
    rows = cur.fetchall()
    conn.close()
    return render_template("me.html", rows=rows)

def require_admin():
    if not current_user.is_admin:
        flash("Bu sayfa için admin yetkisi gerekiyor.")
        return False
    return True

@app.route("/admin")
@login_required
def admin():
    if not require_admin():
        return redirect(url_for("home"))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, is_admin, created_at FROM users ORDER BY username")
    users = cur.fetchall()
    cur.execute("""
        SELECT r.taken_at, u.username, r.score, r.details
        FROM results r JOIN users u ON r.user_id=u.id
        ORDER BY r.id DESC
    """)
    results = cur.fetchall()
    conn.close()
    return render_template("admin.html", users=users, results=results)

@app.route("/admin/export.csv")
@login_required
def admin_export_csv():
    if not require_admin():
        return redirect(url_for("home"))
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.taken_at, u.username, r.score, r.details
        FROM results r JOIN users u ON r.user_id=u.id
        ORDER BY r.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    # CSV
    out = "taken_at,username,score,details\n"
    for r in rows:
        out += f"{r['taken_at']},{r['username']},{r['score']},{r['details']}\n"
    return Response(out, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=sinav_sonuclari.csv"})

@app.route("/admin/reset-demo-passwords")
@login_required
def admin_reset_demo_passwords():
    if not require_admin():
        return redirect(url_for("home"))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET pw_hash=? WHERE username='admin'",
                (generate_password_hash("Admin!2345"),))
    for i in range(1, 11):
        u = f"asistan{i:02d}"
        cur.execute("UPDATE users SET pw_hash=? WHERE username=?",
                    (generate_password_hash("Asistan!2345"), u))
    conn.commit()
    conn.close()
    flash("Demo şifreleri sıfırlandı.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    # internetten erişim: host=0.0.0.0
    app.run(host="0.0.0.0", port=5000, debug=False)
@app.route("/change-password", methods=["GET","POST"])
@login_required
def change_password():
    if request.method == "POST":
        old = request.form.get("old")
        new = request.form.get("new")
        new2 = request.form.get("new2")

        if not old or not new or not new2:
            flash("Tüm alanları doldurun.")
            return redirect(url_for("change_password"))

        if new != new2:
            flash("Yeni şifreler uyuşmuyor.")
            return redirect(url_for("change_password"))

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT pw_hash FROM users WHERE id=?", (current_user.id,))
        row = cur.fetchone()

        if not check_password_hash(row["pw_hash"], old):
            conn.close()
            flash("Eski şifre yanlış.")
            return redirect(url_for("change_password"))

        cur.execute("UPDATE users SET pw_hash=? WHERE id=?",
                    (generate_password_hash(new), current_user.id))
        conn.commit()
        conn.close()

        flash("Şifreniz değiştirildi.")
        return redirect(url_for("home"))

    return render_template("change_password.html")
