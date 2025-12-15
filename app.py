from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

# ================= APP INIT =================
app = Flask(__name__)
app.secret_key = "secret123"

OWNER_USERNAME = "Almer"
OWNER_PASSWORD = "Almer123"

# ================= DATABASE =================
def db():
    return sqlite3.connect("database.db")

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item TEXT PRIMARY KEY,
        unit TEXT,
        current_stock INTEGER,
        alarm_stock INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu TEXT,
        qty INTEGER,
        created_at TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ================= AUTH =================
def auth():
    return session.get("login")

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form["username"] == OWNER_USERNAME
            and request.form["password"] == OWNER_PASSWORD
        ):
            session["login"] = True
            return redirect("/dashboard")
    return render_template("login.html")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if not auth():
        return redirect("/")

    con = db()
    items = con.execute("SELECT * FROM items").fetchall()
    con.close()

    return render_template("dashboard.html", items=items)

# ================= PENJUALAN =================
@app.route("/penjualan", methods=["GET", "POST"])
def penjualan():
    if not auth():
        return redirect("/")

    if request.method == "POST":
        menu = request.form["menu"]
        qty = int(request.form["qty"])

        con = db()
        cur = con.cursor()

        # simpan penjualan
        cur.execute(
            "INSERT INTO sales (menu, qty, created_at) VALUES (?,?,?)",
            (menu, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

        con.commit()
        con.close()

        return redirect("/dashboard")

    return render_template("penjualan.html")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
