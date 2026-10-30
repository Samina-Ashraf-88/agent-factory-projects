"""Write the synthetic test wallet to data/sample_wallet.csv.

Everything here is fictional: the currency is "CR" (Credits, 1 CR has no
real-world value) and no row describes a real person or account. The file holds
raw rows only - no categories or totals - so the analysis has to work them out.
"""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_wallet.csv"
OPENING_BALANCE = 6000# pass as --opening-balance; the export itself has no balance column
Y = 2026


def d(month: int, day: int) -> str:
    return f"{Y}-{month:02d}-{day:02d}"


rows: list[tuple[str, str, str, int]] = []  # date, time, description, amount


def add(month, day, description, amount, time="12:00"):
    rows.append((d(month, day), time, description, amount))


# --- Money in -----------------------------------------------------------------
for m in (7, 8, 9, 10):
    add(m, 15, "Pocket money - Family", 5000, "09:00")
add(8, 22, "Tutoring - Student A", 1500, "18:00")
add(10, 3, "Tutoring - Student B", 1500, "18:00")

# --- Subscriptions ------------------------------------------------------------
for m, label in ((7, "PRIMEVIDEO*MEMBERSHIP"), (8, "PrimeVideo"), (9, "Prime Video"), (10, "PRIMEVIDEO")):
    add(m, 12, label, -199, "02:15")
for m in (7, 8, 9, 10):
    add(m, 3, "Spotify Premium", -129, "03:40")
add(8, 20, "Canva Pro", -150, "04:00")  # two charges, then it stops
add(9, 20, "Canva Pro", -150, "04:00")

# --- Food delivery ------------------------------------------------------------
add(7, 8, "Foodpanda", -450, "13:02")  # the matching pair
add(7, 8, "Foodpanda", -450, "13:04")
for m, day, label, amount in (
    (7, 15, "FOODPANDA*ORDER 88213", 320), (7, 24, "Uber Eats", 380),
    (8, 3, "Foodpanda", 290), (8, 14, "Food Panda", 410), (8, 27, "UBER EATS", 260),
    (9, 6, "Foodpanda", 350), (9, 19, "FOODPANDA*ORDER 90447", 300), (9, 29, "Uber Eats", 240),
    (10, 4, "Foodpanda", 330), (10, 15, "Food Panda", 270),
):
    add(m, day, label, -amount, "20:30")

# --- Essentials ---------------------------------------------------------------
for m in (7, 8, 9, 10):
    add(m, 1, "Jazz Monthly Bundle", -500, "08:00")
for m, day in ((7, 6), (7, 13), (7, 20), (7, 27), (8, 3), (8, 10), (8, 17), (8, 24), (8, 31),
               (9, 7), (9, 14), (9, 21), (9, 28), (10, 5), (10, 12), (10, 19), (10, 26)):
    add(m, day, "Metro Bus Weekly Pass", -150, "07:30")
add(9, 10, "Metro Bus Fare", -60, "08:10")  # legitimate return trip, same amount
add(9, 10, "Metro Bus Fare", -60, "17:45")
add(7, 18, "Careem Ride", -280)
add(9, 5, "Careem Ride", -340)
for m, day, label, amount in (
    (7, 4, "Daily Mart", 420), (7, 19, "DAILYMART #22", 380), (8, 1, "Daily Mart", 450),
    (8, 18, "DailyMart", 390), (9, 3, "Daily Mart", 360), (9, 12, "DAILYMART #22", 410),
    (9, 27, "Daily Mart", 440), (10, 11, "DailyMart", 370), (10, 24, "Daily Mart", 400),
):
    add(m, day, label, -amount, "17:00")
add(7, 22, "City Book Store", -650)
add(8, 25, "Online Course Fee", -900)
add(9, 16, "Exam Registration", -600)
add(10, 7, "Stationery", -180)
add(7, 29, "Green Pharmacy", -240)
add(9, 22, "Clinic Visit", -600)

# --- Discretionary ------------------------------------------------------------
add(8, 8, "Daraz Online Shopping", -1200)
add(8, 15, "Refund - Daraz order", 400)
add(9, 18, "Khaadi Clothing", -600)
add(10, 14, "Daraz Online Shopping", -480)
add(7, 25, "Cinema Tickets", -350)
add(8, 29, "Steam Games", -450)
add(9, 12, "Cinema Tickets", -350)
add(10, 17, "Concert Tickets", -500)
for m, day, amount, time in (
    (7, 2, 90, "10:00"), (7, 10, 110, "10:30"), (7, 23, 85, "11:00"), (8, 6, 95, "10:15"),
    (8, 12, 120, "09:00"), (8, 12, 120, "16:00"),  # two coffees, hours apart
    (8, 26, 75, "10:40"), (9, 9, 100, "10:20"), (9, 24, 80, "11:10"), (10, 8, 105, "10:05"),
    (10, 22, 120, "10:50"), (10, 30, 90, "10:10"),
):
    add(m, day, "Campus Cafe", -amount, time)

# --- Unclear or needs a human -------------------------------------------------
for m, day in ((7, 10), (8, 9), (9, 8), (10, 20)):
    add(m, day, "Laundry Service", -200, "15:00")  # roughly monthly, last gap is long
add(8, 11, "POS 8841 XYZ TRADERS", -350)
add(9, 2, "ATM Cash Withdrawal", -500)

# --- Internal movements: neither income nor spending ---------------------------
add(9, 16, "Transfer to Savings", -1500)
add(10, 20, "Transfer from Savings", 500)

rows.sort(key=lambda r: (r[0], r[1]))


def main() -> None:
    balance = OPENING_BALANCE
    for row in rows:
        balance += row[3]
        if balance < 0:
            raise SystemExit(f"Sample wallet is inconsistent: balance below zero at {row}")
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Date", "Time", "Description", "Amount"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}; closing balance with opening {OPENING_BALANCE}: {balance}")


if __name__ == "__main__":
    main()
