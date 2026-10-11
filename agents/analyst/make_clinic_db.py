"""Build agents/analyst/clinic.db: a held-out database the supervisor never saw (tasks/analyst_heldout.json).

    python agents/analyst/make_clinic_db.py

A different domain and schema from shop.db, with its own traps: no-shows and cancellations, completed
appointments that are unpaid or paid in parts, a doctor who has left, a patient with no city, two patients
with the same name, and dates on both sides of a year boundary. Deterministic (seeded).
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "clinic.db"


def build(path: Path = DB) -> None:
    rnd = random.Random(7)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE patients (id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT, born DATE NOT NULL);
    CREATE TABLE doctors (id INTEGER PRIMARY KEY, name TEXT NOT NULL, specialty TEXT NOT NULL, active INTEGER NOT NULL);
    CREATE TABLE appointments (id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patients(id),
                               doctor_id INTEGER NOT NULL REFERENCES doctors(id), appt_date DATE NOT NULL,
                               status TEXT NOT NULL CHECK (status IN ('completed', 'no_show', 'cancelled')), fee REAL NOT NULL);
    CREATE TABLE payments (appointment_id INTEGER NOT NULL REFERENCES appointments(id), paid_on DATE NOT NULL, amount REAL NOT NULL);
    """)
    cities = ["Pune", "Pune", "Mysore", "Kochi", None, "Mysore", "Kochi", "Pune"]
    names = ["Ravi", "Meera", "Arjun", "Sara", "Ravi", "Lena", "Omar", "Priya", "Tom", "Zoya", "Kiran", "Anil", "Bela", "Dev"]
    for i, n in enumerate(names, 1):
        con.execute("INSERT INTO patients VALUES (?, ?, ?, ?)",
                    (i, n, cities[i % len(cities)], str(date(1950, 1, 1) + timedelta(days=rnd.randrange(25000)))))
    doctors = [("Dr Rao", "cardiology", 1), ("Dr Iyer", "dermatology", 1), ("Dr Shah", "pediatrics", 1),
               ("Dr Nair", "cardiology", 0), ("Dr Bose", "orthopedics", 1), ("Dr Khan", "dermatology", 1)]
    con.executemany("INSERT INTO doctors VALUES (?, ?, ?, ?)", [(i, *d) for i, d in enumerate(doctors, 1)])
    fee = {1: 1200.0, 2: 700.0, 3: 500.0, 4: 1100.0, 5: 900.0, 6: 650.0}
    for aid in range(1, 151):
        d = date(2025, 9, 1) + timedelta(days=rnd.randrange(240))  # spans the 2025/2026 boundary
        doc = rnd.randrange(1, len(doctors) + 1)
        status = rnd.choices(["completed", "no_show", "cancelled"], [0.75, 0.15, 0.10])[0]
        f = round(fee[doc] * rnd.choice([1.0, 1.0, 1.0, 1.15]), 2)  # follow-ups cost more
        con.execute("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)",
                    (aid, rnd.randrange(1, len(names) + 1), doc, str(d), status, f))
        if status == "completed":
            paid = rnd.choices(["full", "split", "part", "none"], [0.6, 0.15, 0.15, 0.10])[0]
            later = lambda k: str(d + timedelta(days=k))  # noqa: E731
            if paid == "full":
                con.execute("INSERT INTO payments VALUES (?, ?, ?)", (aid, later(rnd.randrange(0, 20)), f))
            elif paid == "split":
                con.executemany("INSERT INTO payments VALUES (?, ?, ?)", [(aid, later(1), round(f / 2, 2)), (aid, later(30), f - round(f / 2, 2))])
            elif paid == "part":
                con.execute("INSERT INTO payments VALUES (?, ?, ?)", (aid, later(5), round(f * 0.4, 2)))
    con.commit()
    con.close()


if __name__ == "__main__":
    build()
    print(f"wrote {DB}")
