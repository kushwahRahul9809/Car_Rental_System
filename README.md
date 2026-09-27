# 🚗 DriveEasy — Car Rental Management System

A desktop GUI application for managing a car rental business, built entirely with Python's standard library — **Tkinter** for the interface and **SQLite3** for data storage. No paid services, no external database server, no internet connection required.

---

## ✨ Features

- **Colorful Dashboard** — live stat cards (total cars, available, rented, revenue, average rental duration, average bill) with a gradient header banner
- **Add Car** — register new cars with brand, model, plate number, category, and daily rate
- **Manage Cars** — searchable, sortable table of the whole fleet with delete support
- **Rent a Car** — pick an available car, enter customer details, get an instant cost estimate, and generate a unique booking reference code
- **Return a Car** — automatically calculates the final bill based on days used
- **Rental History** — full log of active and completed rentals, exportable to CSV
- Each page has its own color theme and gradient header for a modern, easy-to-navigate look
- Click any table column heading to sort; type in the search box to filter live

---

## 🛠 Requirements

- **Python 3.8 or newer**
- No external packages needed — `tkinter`, `sqlite3`, `csv`, `random`, `string`, `statistics`, `os`, and `datetime` are all part of the Python standard library

> **Note (Linux users):** Tkinter sometimes isn't bundled with Python by default. If you get a `ModuleNotFoundError: No module named 'tkinter'`, install it with:
> ```bash
> sudo apt install python3-tk        # Debian/Ubuntu
> sudo dnf install python3-tkinter   # Fedora
> ```

---

## 🚀 Getting Started

1. Download `car_rental_system.py` and place it in a folder of your choice.
2. Open a terminal / command prompt in that folder.
3. Run:

   ```bash
   python car_rental_system.py
   ```

   (On some systems you may need `python3` instead of `python`.)

4. The app window will open, and a `car_rental.db` file will be created automatically in the same folder on first run — this is your database, and it persists between sessions.

---

## 📁 Project Structure

```
your-folder/
├── car_rental_system.py   # the entire application (GUI + database logic)
├── car_rental.db          # auto-created SQLite database (holds your data)
└── README.md              # this file
```

The whole app lives in a single Python file for simplicity — no build steps, no packaging required.

---

## 🖥️ Using the App

| Section | What it does |
|---|---|
| **Dashboard** | See fleet stats and currently active rentals at a glance |
| **Add Car** | Fill in the form and click "Add Car" to register a new vehicle |
| **Manage Cars** | Search by brand/model/plate, click headings to sort, delete cars that aren't currently rented |
| **Rent a Car** | Select an available car, enter the customer's name/phone and number of days, click "Calculate" to preview the price, then "Confirm Rental" |
| **Return Car** | Select the active rental to close out — the app calculates the bill from the rental date to today |
| **Rental History** | Browse every past and current rental; click "Export to CSV" to save a report file |

---

## 🗄️ Database

All data is stored locally in `car_rental.db` (SQLite). Two tables are used:

- **cars** — id, brand, model, plate_number, category, rent_per_day, status
- **rentals** — id, booking_code, car_id, customer_name, phone, rent_date, due_date, return_date, total_amount, status

If you're upgrading from an older version of this app, the app automatically adds any missing columns to your existing database the next time you run it — your data is preserved.

---

## 🧩 Customization Ideas

- Change the color palette in the `COLORS`, `PAGE_BG`, and `HEADER_GRADIENT` dictionaries near the top of the file
- Add a login/authentication screen for staff
- Add late-return penalty fees in the `return_car` calculation
- Add car images using an `images/` folder and `PhotoImage`

---

## ❓ Troubleshooting

**"no such column" error on startup**
This means you have an older `car_rental.db` from a previous version. The app now self-migrates automatically — just run it again and it will patch the database for you.

**App window looks too small / cards look squeezed**
Resize the window — the dashboard cards and tables are responsive and will adjust automatically.

**Nothing happens when I click a button**
Make sure all required fields are filled in; the app will show a warning popup for missing or invalid input.

---

## 📄 License

Free to use, modify, and share for personal or educational purposes.
