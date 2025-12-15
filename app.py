from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime

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
        ("Matcha", "GR", 2000, 1000, 50),
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
        if request.form["username"] == OWNER_USERNAME and request.form["password"] == OWNER_PASSWORD:
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

    if request.method == "POST":
        item = request.form["item"]
        qty = int(request.form["qty"])

        con = db()
        cur = con.cursor()

        # ambil porsi
        cur.execute("SELECT portion, current_stock FROM items WHERE item=?", (item,))
        row = cur.fetchone()

        if row:
            portion, stock = row
            used = portion * qty
            new_stock = stock - used

            cur.execute(
                "UPDATE items SET current_stock=? WHERE item=?",
                (new_stock, item)
            )

            cur.execute(
                "INSERT INTO sales (menu, qty, created_at) VALUES (?,?,?)",
                (item, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

        con.commit()
        con.close()

        return redirect("/dashboard")

    con = db()
    items = con.execute("SELECT item FROM items").fetchall()
    con.close()

    return render_template("penjualan.html", items=items)

if __name__ == "__main__":
    app.run(debug=True)
