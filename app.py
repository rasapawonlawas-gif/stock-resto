from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime
import csv
import smtplib
import os
from email.message import EmailMessage

# ================= APP INIT =================
app = Flask(__name__)
app.secret_key = "secret123"

OWNER_USERNAME = "Almer"
OWNER_PASSWORD = "Almer123"

# ================= DATABASE =================
def db():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item TEXT PRIMARY KEY,
        unit TEXT,
        current_stock INTEGER,
        alarm_stock INTEGER,
        portion INTEGER
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

def seed_items():
    con = db()
    cur = con.cursor()

    data = [
        ("Matcha", "GR", 2000, 1000, 20),
        ("Fresh Milk", "ML", 20900, 6000, 8),
        ("Susu Kental Manis", "ML", 490, 980, 16),
    ]

    for d in data:
        cur.execute("""
        INSERT OR IGNORE INTO items
        (item, unit, current_stock, alarm_stock, portion)
        VALUES (?,?,?,?,?)
        """, d)

    con.commit()
    con.close()

init_db()
seed_items()

# ================= AUTH =================
def auth():
    return session.get("login") is True

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

    con = db()
    cur = con.cursor()
    items = cur.execute("SELECT item FROM items").fetchall()

    if request.method == "POST":
        item = request.form["item"]
        qty = int(request.form["qty"])

        if qty <= 0:
            con.close()
            return "Qty tidak valid"

        cur.execute("""
            SELECT current_stock, portion
            FROM items WHERE item = ?
        """, (item,))
        row = cur.fetchone()

        if not row:
            con.close()
            return "Item tidak ditemukan"

        used_stock = row["portion"] * qty
        new_stock = row["current_stock"] - used_stock

        if new_stock < 0:
            con.close()
            return "Stok tidak mencukupi"

        cur.execute("""
            UPDATE items
            SET current_stock = ?
            WHERE item = ?
        """, (new_stock, item))

        cur.execute("""
            INSERT INTO sales (menu, qty, created_at)
            VALUES (?,?,?)
        """, (item, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        con.commit()
        con.close()
        return redirect("/dashboard")

    con.close()
    return render_template("penjualan.html", items=items)

# ================= AUTO REPORT (CSV + EMAIL) =================
@app.route("/send-report")
def send_report():
    try:
        con = db()
        rows = con.execute("""
            SELECT item, unit, current_stock, alarm_stock, portion
            FROM items
        """).fetchall()
        con.close()

        file_path = "/tmp/stok_resto.csv"

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Item", "Unit", "Stok", "Alarm", "Porsi/Cup"])
            for r in rows:
                writer.writerow([
                    r["item"],
                    r["unit"],
                    r["current_stock"],
                    r["alarm_stock"],
                    r["portion"]
                ])

        EMAIL_USER = os.getenv("EMAIL_USER")
        EMAIL_PASS = os.getenv("EMAIL_PASS")
        EMAIL_TO   = os.getenv("EMAIL_TO")

        if not EMAIL_USER or not EMAIL_PASS or not EMAIL_TO:
            return jsonify({"error": "Email env not set"}), 500

        msg = EmailMessage()
        msg["Subject"] = f"Laporan Stok Resto {datetime.now().strftime('%d-%m-%Y')}"
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg.set_content("Laporan stok otomatis terlampir.")

        with open(file_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="text",
                subtype="csv",
                filename="stok_resto.csv"
            )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        return jsonify({"status": "email sent"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
