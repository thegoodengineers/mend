"""Build agents/analyst/shop.db: a small shop database with the traps real analytics questions hit.

    python agents/analyst/make_db.py

Deterministic (seeded), so every reference answer in tasks/analyst.json is fixed. Traps on purpose:
cancelled and refunded orders, a NULL country, two customers with the same name, inactive products,
orders on both sides of a year boundary, and prices that change between orders (unit_price is per order line).
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "shop.db"


def build(path: Path = DB) -> None:
    rnd = random.Random(42)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT, joined DATE NOT NULL);
    CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, active INTEGER NOT NULL);
    CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
                         order_date DATE NOT NULL, status TEXT NOT NULL CHECK (status IN ('paid', 'cancelled', 'refunded')));
    CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id),
                              qty INTEGER NOT NULL, unit_price REAL NOT NULL);
    """)
    countries = ["India", "India", "Germany", "USA", "USA", "Brazil", None]
    names = ["Asha", "Ben", "Chen", "Dara", "Eli", "Farah", "Gus", "Hana", "Ivan", "Asha", "Jon", "Kemi"]
    for i, n in enumerate(names, 1):
        con.execute("INSERT INTO customers VALUES (?, ?, ?, ?)",
                    (i, n, countries[i % len(countries)], str(date(2025, 1, 1) + timedelta(days=rnd.randrange(300)))))
    products = [("Kettle", "kitchen", 1), ("Toaster", "kitchen", 1), ("Mug", "kitchen", 1), ("Lamp", "home", 1),
                ("Rug", "home", 0), ("Desk", "office", 1), ("Chair", "office", 1), ("Notebook", "office", 0)]
    con.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", [(i, *p) for i, p in enumerate(products, 1)])
    base = {1: 30.0, 2: 45.0, 3: 8.0, 4: 25.0, 5: 60.0, 6: 150.0, 7: 90.0, 8: 4.0}
    for oid in range(1, 121):
        d = date(2025, 10, 1) + timedelta(days=rnd.randrange(200))  # spans the 2025/2026 boundary
        status = rnd.choices(["paid", "cancelled", "refunded"], [0.8, 0.12, 0.08])[0]
        con.execute("INSERT INTO orders VALUES (?, ?, ?, ?)", (oid, rnd.randrange(1, len(names) + 1), str(d), status))
        for pid in rnd.sample(range(1, 9), rnd.randrange(1, 4)):
            price = round(base[pid] * rnd.choice([1.0, 1.0, 0.9, 1.1]), 2)  # price changes over time
            con.execute("INSERT INTO order_items VALUES (?, ?, ?, ?)", (oid, pid, rnd.randrange(1, 5), price))
    con.commit()
    con.close()


if __name__ == "__main__":
    build()
    print(f"wrote {DB}")
