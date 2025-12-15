from flask import Flask, render_template, request, redirect, session, send_file, jsonify
import sqlite3
from datetime import datetime
import pandas as pd
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
        ("Marjan Strawberry", "ML", 4000, 800, 80),
        ("Marjan Lychee", "ML", 4400, 800, 20),
        ("Gula Aren", "ML", 3000, 2600, 130),
        ("Calamansi", "ML", 5700, 2000, 50),
        ("Fanta Soda", "ML", 5250, 1500, 130),
        ("Gula Putih Cair", "ML", 4500, 1000, 1000),
        ("Monin Green Apple", "ML", 3500, 700, 35),
        ("Monin Wild Mint", "ML", 3500, 700, 35),
        ("Monin Blue Lagoon", "ML", 3500, 700, 140),
        ("Monin Tiramisu", "ML", 2100, 700, 35),
        ("Sunquick Lemon", "ML", 3300, 900, 20),
        ("Sunquick Orange", "ML", 3300, 900, 53),
        ("Beans Espresso", "GR", 4000, 2000, 33),
        ("Cocoa Powder", "GR", 2500, 1000, 50),
        ("Matcha", "GR", 2000, 1000, 20),   # 1000gr = 50 cup → 20gr / cup
        ("Fresh Milk", "ML", 20900, 6000, 8),
        ("Susu Kental Manis", "ML", 490, 980, 16),
        ("Strawberry", "GR", 2000, 1000, 10),
        ("Naga", "GR", 2000, 1000, 8),
        ("Mangga", "GR", 2000, 1000, 6),
        ("Sirsak", "GR", 2000, 1000, 8),
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

        cur.execute("""
            SELECT current_stock, portion
            FROM items WHERE item = ?
        """, (item,))
        row = cur.fetchone()

        if row:
            current_stock, portion = row
            used_stock = portion * qty
            new_stock = current_stock - used_stock

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

# ================= EXCEL GENERATOR =================
def generate_excel():
    con = db()
    df = pd.read_sql_query("""
        SELECT
            item AS Item,
            current_stock || ' ' || unit AS 'Stok Bahan',
            CAST(current_stock / portion AS INT) || ' cup' AS 'Cup Tersedia',
            alarm_stock AS Alarm
        FROM items
    """, con)
    con.close()

    file_path = "stok_resto.xlsx"
    df.to_excel(file_path, index=False)
    return file_path

# ================= EXPORT MANUAL =================
@app.route("/export-excel")
def export_excel():
    if not auth():
        return redirect("/")
    file_path = generate_excel()
    return send_file(file_path, as_attachment=True)

# ================= AUTO EMAIL (LANGKAH 3) =================
def send_email_report():
    file_path = generate_excel()

    msg = EmailMessage()
    msg["Subject"] = f"Laporan Stok Resto - {datetime.now().strftime('%d-%m-%Y')}"
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = os.getenv("EMAIL_TO")
    msg.set_content("Terlampir laporan stok resto terbaru (otomatis).")

    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="stok_resto.xlsx"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        smtp.send_message(msg)

@app.route("/send-report")
def send_report():
    send_email_report()
    return jsonify({"status": "email sent"})

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
