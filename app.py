from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

OWNER_USERNAME = "Almer"
OWNER_PASSWORD = "Almer123"

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
        alarm_stock INTEGER,
        portioning INTEGER,
        menu TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        menu TEXT,
        qty INTEGER,
        date TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == OWNER_USERNAME and request.form["password"] == OWNER_PASSWORD:
            session["login"] = True
            return redirect("/dashboard")
    return render_template("login.html")

def auth():
    return session.get("login")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if not auth(): return redirect("/")
    con = db()
    items = con.execute("SELECT * FROM items").fetchall()
    con.close()
    return render_template("dashboard.html", items=items)

# ================= PENJUALAN =================
@app.route("/penjualan", methods=["GET","POST"])
def penjualan():
    if not auth(): return redirect("/")

    con = db()
    menus = con.execute("SELECT DISTINCT menu FROM items").fetchall()

    if request.method == "POST":
        menu = request.form["menu"]
        qty = int(request.form["qty"])

        item = con.execute("SELECT item, portioning FROM items WHERE menu=?", (menu,)).fetchone()
        penggunaan = item[1] * qty

        con.execute("""
        UPDATE items SET current_stock = current_stock - ?
        WHERE menu = ?
        """,(penggunaan, menu))

        con.execute("INSERT INTO sales VALUES (NULL,?,?,?)",
            (menu, qty, datetime.now().strftime("%Y-%m-%d %H:%M")))

        con.commit()
        con.close()
        return redirect("/dashboard")

    con.close()
    return render_template("penjualan.html", menus=menus)
