"""
==========================================================
   CAR RENTAL MANAGEMENT SYSTEM  (Python + Tkinter + SQLite)
==========================================================
A complete desktop GUI application to manage a car rental
business: add/view/delete cars, rent cars to customers,
process returns, and view a colorful live dashboard.

Extra Python stdlib features used (beyond tkinter/sqlite3):
  - csv        -> export rental history to a .csv report
  - random/str -> generate unique booking reference codes
  - statistics -> average rental duration & average bill on dashboard
  - os         -> locate the database file next to this script
  - datetime   -> date math for due dates / days used

Requirements: Python 3.8+  (all modules above are built-in)
Run with:  python car_rental_system.py
==========================================================
"""

import os
import csv
import random
import string
import statistics
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "car_rental.db")

# ---------------------------------------------------------
# COLOR THEME  (each page gets its own soft background tint,
# and headers are drawn as a smooth left->right gradient)
# ---------------------------------------------------------
COLORS = {
    "sidebar": "#1E2A4A",
    "sidebar_active": "#2F4373",
    "sidebar_text": "#E8ECF7",
    "accent": "#4C6FFF",
    "white": "#FFFFFF",
    "text_dark": "#1F2937",
    "text_muted": "#6B7280",
    "success": "#22C55E",
    "success_dark": "#16A34A",
    "danger": "#EF4444",
    "danger_dark": "#DC2626",
    "warning": "#F59E0B",
    "warning_dark": "#D97706",
    "info": "#3B82F6",
    "info_dark": "#2563EB",
    "purple": "#8B5CF6",
    "purple_dark": "#7C3AED",
    "row_alt": "#F8FAFC",
}

# Distinct pastel page backgrounds (gives each screen its own identity)
PAGE_BG = {
    "Dashboard": "#EAF1FF",   # soft blue
    "AddCar":    "#EAFBF0",   # soft green
    "ViewCars":  "#FFF8E8",   # soft amber
    "RentCar":   "#F3EEFF",   # soft purple
    "ReturnCar": "#FFEFF0",   # soft rose
    "History":   "#EAF7F8",   # soft teal
}

# Header gradient pairs (left color -> right color) per page
HEADER_GRADIENT = {
    "Dashboard": ("#3B5CFF", "#7C3AED"),
    "AddCar":    ("#16A34A", "#22C55E"),
    "ViewCars":  ("#D97706", "#F59E0B"),
    "RentCar":   ("#7C3AED", "#4C6FFF"),
    "ReturnCar": ("#DC2626", "#F59E0B"),
    "History":   ("#0EA5A4", "#2563EB"),
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def blend(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    ))


def generate_booking_code():
    """Unique-ish booking reference, e.g. BK-7F3K9A (uses random + string)."""
    chars = string.ascii_uppercase + string.digits
    return "BK-" + "".join(random.choices(chars, k=6))


# ===========================================================
# DATABASE LAYER
# ===========================================================
class Database:
    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                plate_number TEXT NOT NULL UNIQUE,
                category TEXT,
                rent_per_day REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Available'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_code TEXT,
                car_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT,
                rent_date TEXT NOT NULL,
                due_date TEXT,
                return_date TEXT,
                total_amount REAL,
                status TEXT NOT NULL DEFAULT 'Active',
                FOREIGN KEY (car_id) REFERENCES cars(id)
            )
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """Self-heal older database files (e.g. from a previous version of
        this app) that are missing newer columns, instead of crashing."""
        cur = self.conn.cursor()
        existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(rentals)").fetchall()}
        if "booking_code" not in existing_cols:
            cur.execute("ALTER TABLE rentals ADD COLUMN booking_code TEXT")
        self.conn.commit()

    # ---- Car operations ----
    def add_car(self, brand, model, plate, category, rate):
        self.conn.execute(
            "INSERT INTO cars (brand, model, plate_number, category, rent_per_day, status) "
            "VALUES (?, ?, ?, ?, ?, 'Available')",
            (brand, model, plate, category, rate),
        )
        self.conn.commit()

    def delete_car(self, car_id):
        self.conn.execute("DELETE FROM cars WHERE id=?", (car_id,))
        self.conn.commit()

    def get_all_cars(self):
        return self.conn.execute("SELECT * FROM cars ORDER BY id DESC").fetchall()

    def get_available_cars(self):
        return self.conn.execute(
            "SELECT * FROM cars WHERE status='Available' ORDER BY brand"
        ).fetchall()

    def set_car_status(self, car_id, status):
        self.conn.execute("UPDATE cars SET status=? WHERE id=?", (status, car_id))
        self.conn.commit()

    # ---- Rental operations ----
    def create_rental(self, car_id, name, phone, rent_date, due_date, booking_code):
        self.conn.execute(
            "INSERT INTO rentals (booking_code, car_id, customer_name, phone, rent_date, due_date, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'Active')",
            (booking_code, car_id, name, phone, rent_date, due_date),
        )
        self.set_car_status(car_id, "Rented")
        self.conn.commit()

    def get_active_rentals(self):
        return self.conn.execute("""
            SELECT r.id, c.brand, c.model, c.plate_number, r.customer_name,
                   r.phone, r.rent_date, r.due_date, c.rent_per_day, c.id, r.booking_code
            FROM rentals r JOIN cars c ON r.car_id = c.id
            WHERE r.status='Active'
            ORDER BY r.id DESC
        """).fetchall()

    def get_all_rentals(self):
        return self.conn.execute("""
            SELECT r.id, c.brand, c.model, c.plate_number, r.customer_name,
                   r.rent_date, r.return_date, r.total_amount, r.status, r.booking_code
            FROM rentals r JOIN cars c ON r.car_id = c.id
            ORDER BY r.id DESC
        """).fetchall()

    def return_car(self, rental_id, car_id, total_amount, return_date):
        self.conn.execute(
            "UPDATE rentals SET status='Completed', return_date=?, total_amount=? WHERE id=?",
            (return_date, total_amount, rental_id),
        )
        self.set_car_status(car_id, "Available")
        self.conn.commit()

    # ---- Stats ----
    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0]
        available = self.conn.execute(
            "SELECT COUNT(*) FROM cars WHERE status='Available'"
        ).fetchone()[0]
        rented = self.conn.execute(
            "SELECT COUNT(*) FROM cars WHERE status='Rented'"
        ).fetchone()[0]
        revenue = self.conn.execute(
            "SELECT COALESCE(SUM(total_amount),0) FROM rentals WHERE status='Completed'"
        ).fetchone()[0]
        active_rentals = self.conn.execute(
            "SELECT COUNT(*) FROM rentals WHERE status='Active'"
        ).fetchone()[0]

        # Use the `statistics` module for a couple of quick analytics
        completed_amounts = [
            row[0] for row in self.conn.execute(
                "SELECT total_amount FROM rentals WHERE status='Completed' AND total_amount IS NOT NULL"
            ).fetchall()
        ]
        avg_bill = round(statistics.mean(completed_amounts), 2) if completed_amounts else 0.0

        duration_rows = self.conn.execute(
            "SELECT rent_date, return_date FROM rentals WHERE status='Completed' AND return_date IS NOT NULL"
        ).fetchall()
        durations = []
        for rd, retd in duration_rows:
            try:
                d1 = datetime.strptime(rd, "%Y-%m-%d").date()
                d2 = datetime.strptime(retd, "%Y-%m-%d").date()
                durations.append(max((d2 - d1).days, 1))
            except ValueError:
                continue
        avg_days = round(statistics.mean(durations), 1) if durations else 0.0

        return {
            "total": total,
            "available": available,
            "rented": rented,
            "revenue": revenue,
            "active_rentals": active_rentals,
            "avg_bill": avg_bill,
            "avg_days": avg_days,
        }


# ===========================================================
# MAIN APPLICATION
# ===========================================================
class CarRentalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DriveEasy — Car Rental Management System")
        self.geometry("1200x700")
        self.minsize(1050, 620)

        self.db = Database()
        self._build_style()
        self._build_layout()
        self.show_frame("Dashboard")

    # -------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Treeview",
                         background=COLORS["white"],
                         fieldbackground=COLORS["white"],
                         foreground=COLORS["text_dark"],
                         rowheight=30,
                         font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                         background=COLORS["text_dark"],
                         foreground="white",
                         font=("Segoe UI", 10, "bold"),
                         relief="flat")
        style.map("Treeview.Heading", background=[("active", COLORS["accent"])])
        style.map("Treeview", background=[("selected", COLORS["accent"])],
                  foreground=[("selected", "white")])

        style.configure("TNotebook", borderwidth=0)
        style.configure("TCombobox", padding=6)

    # -------------------------------------------------
    def _build_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = tk.Label(self.sidebar, text="🚗 DriveEasy",
                         bg=COLORS["sidebar"], fg="white",
                         font=("Segoe UI", 17, "bold"), pady=25)
        logo.pack(fill="x")

        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", "📊  Dashboard"),
            ("AddCar", "➕  Add Car"),
            ("ViewCars", "🚘  Manage Cars"),
            ("RentCar", "🔑  Rent a Car"),
            ("ReturnCar", "↩️  Return Car"),
            ("History", "🧾  Rental History"),
        ]
        for key, label in nav_items:
            btn = tk.Button(self.sidebar, text=label, anchor="w",
                             bg=COLORS["sidebar"], fg=COLORS["sidebar_text"],
                             activebackground=COLORS["sidebar_active"],
                             activeforeground="white",
                             font=("Segoe UI", 11), bd=0, padx=25, pady=12,
                             cursor="hand2",
                             command=lambda k=key: self.show_frame(k))
            btn.pack(fill="x")
            self.nav_buttons[key] = btn

        footer = tk.Label(self.sidebar, text="© 2026 DriveEasy Rentals",
                           bg=COLORS["sidebar"], fg="#8896B8",
                           font=("Segoe UI", 8))
        footer.pack(side="bottom", pady=14)

        # Main container
        self.container = tk.Frame(self)
        self.container.pack(side="right", fill="both", expand=True)

        self.frames = {}
        self.frames["Dashboard"] = DashboardFrame(self.container, self)
        self.frames["AddCar"] = AddCarFrame(self.container, self)
        self.frames["ViewCars"] = ViewCarsFrame(self.container, self)
        self.frames["RentCar"] = RentCarFrame(self.container, self)
        self.frames["ReturnCar"] = ReturnCarFrame(self.container, self)
        self.frames["History"] = HistoryFrame(self.container, self)

        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    # -------------------------------------------------
    def show_frame(self, key):
        for k, btn in self.nav_buttons.items():
            btn.configure(bg=COLORS["sidebar_active"] if k == key else COLORS["sidebar"])
        frame = self.frames[key]
        if hasattr(frame, "refresh"):
            frame.refresh()
        frame.tkraise()

    def refresh_all(self):
        for frame in self.frames.values():
            if hasattr(frame, "refresh"):
                frame.refresh()


# ===========================================================
# REUSABLE WIDGETS
# ===========================================================
def gradient_header(parent, title, subtitle, color_left, color_right, height=80):
    """Draws a smooth left->right color gradient banner using a Canvas
    (pure tkinter, no image libraries needed)."""
    canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0)
    canvas.pack(fill="x", side="top")

    def redraw(event=None):
        canvas.delete("grad")
        w = canvas.winfo_width()
        if w <= 1:
            w = 1200
        steps = 120
        for i in range(steps):
            t = i / steps
            color = blend(color_left, color_right, t)
            x0 = int(w * i / steps)
            x1 = int(w * (i + 1) / steps)
            canvas.create_rectangle(x0, 0, x1, height, outline="", fill=color, tags="grad")
        canvas.create_text(30, height * 0.4, anchor="w", text=title,
                            fill="white", font=("Segoe UI", 18, "bold"), tags="grad")
        if subtitle:
            canvas.create_text(30, height * 0.75, anchor="w", text=subtitle,
                                fill="#EAECFB", font=("Segoe UI", 10), tags="grad")

    canvas.bind("<Configure>", redraw)
    return canvas


def stat_card(parent, icon, title, value, color, color_dark):
    """A stat card that always keeps its title and value fully visible:
    fixed minimum height, wrapped title text, and a value font that
    shrinks automatically if the number/text is long."""
    card = tk.Frame(parent, bg=color, height=132)
    card.grid_propagate(False)
    card.pack_propagate(False)

    icon_row = tk.Frame(card, bg=color)
    icon_row.pack(fill="x", padx=16, pady=(12, 2))
    tk.Label(icon_row, text=icon, bg=color, fg="white",
              font=("Segoe UI", 20)).pack(anchor="w")

    # Shrink the value font automatically for longer strings (e.g. ₹ amounts)
    value_str = str(value)
    if len(value_str) > 12:
        value_font_size = 14
    elif len(value_str) > 8:
        value_font_size = 17
    else:
        value_font_size = 21

    value_label = tk.Label(card, text=value_str, bg=color, fg="white",
                            font=("Segoe UI", value_font_size, "bold"),
                            anchor="w", justify="left")
    value_label.pack(fill="x", padx=16)

    title_label = tk.Label(card, text=title, bg=color, fg="white",
                            font=("Segoe UI", 10, "bold"),
                            anchor="w", justify="left")
    title_label.pack(fill="x", padx=16, pady=(1, 10))

    # Wrap the title/value text to the card's actual width so nothing
    # gets clipped, and keep it updated as the window is resized.
    def on_resize(event):
        wrap = max(event.width - 32, 80)
        title_label.config(wraplength=wrap)
        value_label.config(wraplength=wrap)

    card.bind("<Configure>", on_resize)

    strip = tk.Frame(card, bg=color_dark, height=5)
    strip.pack(fill="x", side="bottom")
    return card


def styled_entry(parent, bg, textvariable=None, width=28):
    e = tk.Entry(parent, textvariable=textvariable, width=width,
                 font=("Segoe UI", 11), relief="solid", bd=1,
                 highlightthickness=1, highlightbackground="#D1D5DB",
                 highlightcolor=COLORS["accent"])
    return e


def styled_button(parent, text, command, bg, fg="white"):
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                   font=("Segoe UI", 11, "bold"), relief="flat",
                   padx=18, pady=8, cursor="hand2", activebackground=bg)
    return b


def make_sortable(tree, columns):
    """Attach click-to-sort behaviour to a Treeview's column headings.
    Uses sorted() + a lambda key, and toggles ascending/descending."""
    sort_state = {"col": None, "reverse": False}

    def sort_by(col):
        items = [(tree.set(k, col), k) for k in tree.get_children("")]

        def keyfunc(pair):
            val = pair[0]
            cleaned = val.replace("₹", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return val.lower()

        reverse = sort_state["col"] == col and not sort_state["reverse"]
        items = sorted(items, key=keyfunc, reverse=reverse)
        for index, (_, k) in enumerate(items):
            tree.move(k, "", index)
        sort_state["col"] = col
        sort_state["reverse"] = reverse

    for col in columns:
        tree.heading(col, text=col, command=lambda c=col: sort_by(c))


# ===========================================================
# DASHBOARD FRAME
# ===========================================================
class DashboardFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAGE_BG["Dashboard"])
        self.app = app
        l, r = HEADER_GRADIENT["Dashboard"]
        gradient_header(self, "Dashboard", "Overview of your car rental business", l, r)

        self.cards_area = tk.Frame(self, bg=PAGE_BG["Dashboard"])
        self.cards_area.pack(fill="x", padx=30, pady=20)

        self.cards_area2 = tk.Frame(self, bg=PAGE_BG["Dashboard"])
        self.cards_area2.pack(fill="x", padx=30, pady=(0, 15))

        self.info_area = tk.Frame(self, bg=PAGE_BG["Dashboard"])
        self.info_area.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        self.refresh()

    def refresh(self):
        for w in self.cards_area.winfo_children():
            w.destroy()
        for w in self.cards_area2.winfo_children():
            w.destroy()
        for w in self.info_area.winfo_children():
            w.destroy()

        s = self.app.db.stats()

        row1 = [
            ("🚙", "Total Cars", str(s["total"]), COLORS["info"], COLORS["info_dark"]),
            ("✅", "Available Cars", str(s["available"]), COLORS["success"], COLORS["success_dark"]),
            ("🔑", "Currently Rented", str(s["rented"]), COLORS["warning"], COLORS["warning_dark"]),
            ("💰", "Total Revenue", f"₹{s['revenue']:.2f}", COLORS["purple"], COLORS["purple_dark"]),
        ]
        for col, (icon, title, value, color, dark) in enumerate(row1):
            self.cards_area.grid_columnconfigure(col, weight=1, uniform="dash_row1")
            card = stat_card(self.cards_area, icon, title, value, color, dark)
            card.grid(row=0, column=col, padx=8, sticky="nsew")

        row2 = [
            ("📅", "Avg. Rental Duration", f"{s['avg_days']} days", "#0EA5A4", "#0F766E"),
            ("🧾", "Avg. Bill (completed)", f"₹{s['avg_bill']:.2f}", "#EC4899", "#DB2777"),
        ]
        for col, (icon, title, value, color, dark) in enumerate(row2):
            self.cards_area2.grid_columnconfigure(col, weight=1, uniform="dash_row2")
            card = stat_card(self.cards_area2, icon, title, value, color, dark)
            card.grid(row=0, column=col, padx=8, sticky="nsew")

        # Active rentals preview panel
        panel = tk.Frame(self.info_area, bg="white", relief="solid", bd=1)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text=f"  Active Rentals ({s['active_rentals']})",
                  bg="white", fg=COLORS["text_dark"], font=("Segoe UI", 13, "bold"),
                  anchor="w").pack(fill="x", pady=(12, 6))

        cols = ("Booking", "Car", "Plate", "Customer", "Rent Date", "Due Date", "Rate/Day")
        tree = ttk.Treeview(panel, columns=cols, show="headings", height=9)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=130)
        tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        rentals = self.app.db.get_active_rentals()
        for i, r in enumerate(rentals):
            rid, brand, model, plate, cust, phone, rdate, ddate, rate, car_id, code = r
            tag = "odd" if i % 2 else "even"
            tree.insert("", "end", values=(code or "—", f"{brand} {model}", plate, cust, rdate, ddate, f"₹{rate:.2f}"), tags=(tag,))
        tree.tag_configure("even", background=COLORS["row_alt"])
        tree.tag_configure("odd", background="white")

        if not rentals:
            tk.Label(panel, text="No active rentals right now.", bg="white",
                      fg=COLORS["text_muted"], font=("Segoe UI", 10)).pack(pady=10)


# ===========================================================
# ADD CAR FRAME
# ===========================================================
class AddCarFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAGE_BG["AddCar"])
        self.app = app
        l, r = HEADER_GRADIENT["AddCar"]
        gradient_header(self, "Add New Car", "Register a new car into the fleet", l, r)

        form = tk.Frame(self, bg="white", relief="solid", bd=1)
        form.pack(padx=40, pady=30, fill="x")

        self.brand_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.plate_var = tk.StringVar()
        self.category_var = tk.StringVar(value="Sedan")
        self.rate_var = tk.StringVar()

        fields = [
            ("Brand", self.brand_var, "entry"),
            ("Model", self.model_var, "entry"),
            ("Plate Number", self.plate_var, "entry"),
            ("Category", self.category_var, "combo"),
            ("Rent per Day (₹)", self.rate_var, "entry"),
        ]

        for i, (label, var, kind) in enumerate(fields):
            tk.Label(form, text=label, bg="white", fg=COLORS["text_dark"],
                      font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky="w", padx=25, pady=14)
            if kind == "entry":
                styled_entry(form, "white", textvariable=var).grid(row=i, column=1, padx=25, pady=14, sticky="w")
            else:
                combo = ttk.Combobox(form, textvariable=var, state="readonly", width=25,
                                      values=["Sedan", "SUV", "Hatchback", "Luxury", "Van", "Electric"])
                combo.grid(row=i, column=1, padx=25, pady=14, sticky="w")

        btn_row = tk.Frame(form, bg="white")
        btn_row.grid(row=len(fields), column=0, columnspan=2, pady=20)
        styled_button(btn_row, "➕ Add Car", self.add_car, COLORS["success"]).pack(side="left", padx=10)
        styled_button(btn_row, "Clear", self.clear_form, COLORS["text_muted"]).pack(side="left", padx=10)

    def add_car(self):
        # strip() on every text field, all() to check none are empty
        brand = self.brand_var.get().strip()
        model = self.model_var.get().strip()
        plate = self.plate_var.get().strip().upper()
        category = self.category_var.get().strip()
        rate = self.rate_var.get().strip()

        if not all([brand, model, plate, rate]):
            messagebox.showwarning("Missing Info", "Please fill in all required fields.")
            return
        try:
            rate_val = float(rate)
            if rate_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Rate", "Rent per day must be a positive number.")
            return

        try:
            self.app.db.add_car(brand, model, plate, category, rate_val)
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate Plate", "A car with this plate number already exists.")
            return

        messagebox.showinfo("Success", f"{brand} {model} added to the fleet!")
        self.clear_form()
        self.app.refresh_all()

    def clear_form(self):
        self.brand_var.set("")
        self.model_var.set("")
        self.plate_var.set("")
        self.category_var.set("Sedan")
        self.rate_var.set("")


# ===========================================================
# VIEW / MANAGE CARS FRAME
# ===========================================================
class ViewCarsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAGE_BG["ViewCars"])
        self.app = app
        l, r = HEADER_GRADIENT["ViewCars"]
        gradient_header(self, "Manage Cars", "View, search and remove cars from the fleet", l, r)

        toolbar = tk.Frame(self, bg=PAGE_BG["ViewCars"])
        toolbar.pack(fill="x", padx=30, pady=(15, 5))

        tk.Label(toolbar, text="🔍 Search:", bg=PAGE_BG["ViewCars"],
                  font=("Segoe UI", 10, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        styled_entry(toolbar, PAGE_BG["ViewCars"], textvariable=self.search_var, width=25).pack(side="left", padx=(8, 20))

        styled_button(toolbar, "🗑 Delete Selected", self.delete_selected, COLORS["danger"]).pack(side="left")
        styled_button(toolbar, "🔄 Refresh", self.refresh, COLORS["info"]).pack(side="left", padx=10)

        table_frame = tk.Frame(self, bg="white", relief="solid", bd=1)
        table_frame.pack(fill="both", expand=True, padx=30, pady=15)

        cols = ("ID", "Brand", "Model", "Plate", "Category", "Rate/Day", "Status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        widths = (50, 120, 120, 110, 100, 100, 110)
        for c, w in zip(cols, widths):
            self.tree.column(c, anchor="center", width=w)
        make_sortable(self.tree, cols)  # click any heading to sort
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.tag_configure("available", background="#E7F9EE", foreground=COLORS["success_dark"])
        self.tree.tag_configure("rented", background="#FEF3E2", foreground=COLORS["warning_dark"])

        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        query = self.search_var.get().strip().lower()
        all_cars = self.app.db.get_all_cars()

        # filter() + lambda: keep only cars whose brand/model/plate match the search box
        if query:
            all_cars = list(filter(
                lambda car: query in car[1].lower() or query in car[2].lower() or query in car[3].lower(),
                all_cars,
            ))

        for car in all_cars:
            cid, brand, model, plate, category, rate, status = car
            tag = "available" if status == "Available" else "rented"
            self.tree.insert("", "end", values=(cid, brand, model, plate, category, f"₹{rate:.2f}", status), tags=(tag,))

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a car to delete.")
            return
        values = self.tree.item(sel[0], "values")
        car_id, status = values[0], values[6]
        if status == "Rented":
            messagebox.showerror("Cannot Delete", "This car is currently rented out.")
            return
        if messagebox.askyesno("Confirm Delete", f"Delete car #{car_id}?"):
            self.app.db.delete_car(car_id)
            self.app.refresh_all()


# ===========================================================
# RENT A CAR FRAME
# ===========================================================
class RentCarFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAGE_BG["RentCar"])
        self.app = app
        l, r = HEADER_GRADIENT["RentCar"]
        gradient_header(self, "Rent a Car", "Assign an available car to a customer", l, r)

        form = tk.Frame(self, bg="white", relief="solid", bd=1)
        form.pack(padx=40, pady=30, fill="x")

        tk.Label(form, text="Select Car", bg="white", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w", padx=25, pady=14)
        self.car_var = tk.StringVar()
        self.car_combo = ttk.Combobox(form, textvariable=self.car_var, state="readonly", width=40)
        self.car_combo.grid(row=0, column=1, padx=25, pady=14, sticky="w")

        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.days_var = tk.StringVar(value="1")

        labels = ["Customer Name", "Phone Number", "Number of Days"]
        vars_ = [self.name_var, self.phone_var, self.days_var]
        for i, (lab, var) in enumerate(zip(labels, vars_), start=1):
            tk.Label(form, text=lab, bg="white", font=("Segoe UI", 11, "bold")).grid(
                row=i, column=0, sticky="w", padx=25, pady=14)
            styled_entry(form, "white", textvariable=var).grid(row=i, column=1, padx=25, pady=14, sticky="w")

        self.estimate_label = tk.Label(form, text="Estimated Cost: ₹0.00", bg="white",
                                        fg=COLORS["accent"], font=("Segoe UI", 12, "bold"))
        self.estimate_label.grid(row=4, column=0, columnspan=2, pady=(0, 10))

        btn_row = tk.Frame(form, bg="white")
        btn_row.grid(row=5, column=0, columnspan=2, pady=15)
        styled_button(btn_row, "🔑 Confirm Rental", self.confirm_rent, COLORS["accent"]).pack(side="left", padx=10)
        styled_button(btn_row, "Calculate", self.calculate, COLORS["info"]).pack(side="left", padx=10)

        self._car_map = {}
        self.refresh()

    def refresh(self):
        cars = self.app.db.get_available_cars()
        self._car_map = {}
        display_values = []
        for car in cars:
            cid, brand, model, plate, category, rate, status = car
            label = f"{brand} {model} ({plate}) — ₹{rate:.2f}/day"
            display_values.append(label)
            self._car_map[label] = (cid, rate)
        self.car_combo["values"] = display_values
        if display_values:
            self.car_var.set(display_values[0])
        else:
            self.car_var.set("")

    def calculate(self):
        sel = self.car_var.get()
        if sel not in self._car_map:
            messagebox.showwarning("No Car", "Please select an available car.")
            return
        _, rate = self._car_map[sel]
        try:
            days = int(self.days_var.get())
            if days <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Days", "Enter a valid positive number of days.")
            return
        total = rate * days
        self.estimate_label.config(text=f"Estimated Cost: ₹{total:.2f}")
        return total

    def confirm_rent(self):
        sel = self.car_var.get()
        if sel not in self._car_map:
            messagebox.showwarning("No Car", "Please select an available car.")
            return
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        if not name:
            messagebox.showwarning("Missing Info", "Please enter the customer's name.")
            return
        try:
            days = int(self.days_var.get())
            if days <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Days", "Enter a valid positive number of days.")
            return

        car_id, rate = self._car_map[sel]
        rent_date = date.today()
        due_date = date.fromordinal(rent_date.toordinal() + days)
        booking_code = generate_booking_code()  # random + string module

        self.app.db.create_rental(car_id, name, phone,
                                   rent_date.isoformat(), due_date.isoformat(), booking_code)
        messagebox.showinfo(
            "Rented!",
            f"Booking Ref: {booking_code}\nCar rented to {name}.\nDue back on {due_date.isoformat()}."
        )

        self.name_var.set("")
        self.phone_var.set("")
        self.days_var.set("1")
        self.estimate_label.config(text="Estimated Cost: ₹0.00")
        self.app.refresh_all()


# ===========================================================
# RETURN CAR FRAME
# ===========================================================
class ReturnCarFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAGE_BG["ReturnCar"])
        self.app = app
        l, r = HEADER_GRADIENT["ReturnCar"]
        gradient_header(self, "Return a Car", "Process a car return and calculate final bill", l, r)

        table_frame = tk.Frame(self, bg="white", relief="solid", bd=1)
        table_frame.pack(fill="both", expand=True, padx=30, pady=(20, 10))

        cols = ("RentalID", "Booking", "Car", "Plate", "Customer", "Rent Date", "Due Date", "Rate/Day")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.column(c, anchor="center", width=125)
        make_sortable(self.tree, cols)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.tag_configure("even", background=COLORS["row_alt"])
        self.tree.tag_configure("odd", background="white")

        btn_row = tk.Frame(self, bg=PAGE_BG["ReturnCar"])
        btn_row.pack(pady=15)
        styled_button(btn_row, "↩️ Return Selected Car", self.return_car, COLORS["danger"]).pack(side="left", padx=10)
        styled_button(btn_row, "🔄 Refresh", self.refresh, COLORS["info"]).pack(side="left", padx=10)

        self._data = {}
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._data = {}
        rentals = self.app.db.get_active_rentals()
        for i, r in enumerate(rentals):
            rid, brand, model, plate, cust, phone, rdate, ddate, rate, car_id, code = r
            tag = "odd" if i % 2 else "even"
            item = self.tree.insert("", "end", values=(rid, code or "—", f"{brand} {model}", plate, cust, rdate, ddate, f"₹{rate:.2f}"), tags=(tag,))
            self._data[item] = (rid, car_id, rate, rdate)

    def return_car(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a rental to return.")
            return
        rental_id, car_id, rate, rent_date_str = self._data[sel[0]]
        rent_date = datetime.strptime(rent_date_str, "%Y-%m-%d").date()
        today = date.today()
        days_used = max((today - rent_date).days, 1)
        total = days_used * rate

        if messagebox.askyesno("Confirm Return",
                                f"Days used: {days_used}\nTotal amount: ₹{total:.2f}\n\nConfirm return?"):
            self.app.db.return_car(rental_id, car_id, total, today.isoformat())
            messagebox.showinfo("Returned", f"Car returned successfully.\nAmount charged: ₹{total:.2f}")
            self.app.refresh_all()


# ===========================================================
# HISTORY FRAME
# ===========================================================
class HistoryFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=PAGE_BG["History"])
        self.app = app
        l, r = HEADER_GRADIENT["History"]
        gradient_header(self, "Rental History", "Complete log of all rentals — active and completed", l, r)

        toolbar = tk.Frame(self, bg=PAGE_BG["History"])
        toolbar.pack(fill="x", padx=30, pady=(15, 5))
        styled_button(toolbar, "⬇ Export to CSV", self.export_csv, COLORS["purple"]).pack(side="left")
        styled_button(toolbar, "🔄 Refresh", self.refresh, COLORS["info"]).pack(side="left", padx=10)

        table_frame = tk.Frame(self, bg="white", relief="solid", bd=1)
        table_frame.pack(fill="both", expand=True, padx=30, pady=15)

        self.cols = ("ID", "Booking", "Car", "Plate", "Customer", "Rent Date", "Return Date", "Amount", "Status")
        self.tree = ttk.Treeview(table_frame, columns=self.cols, show="headings")
        for c in self.cols:
            self.tree.column(c, anchor="center", width=115)
        make_sortable(self.tree, self.cols)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.tag_configure("active", background="#FEF3E2", foreground=COLORS["warning_dark"])
        self.tree.tag_configure("completed", background="#E7F9EE", foreground=COLORS["success_dark"])

        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for r in self.app.db.get_all_rentals():
            rid, brand, model, plate, cust, rdate, retdate, amount, status, code = r
            tag = "active" if status == "Active" else "completed"
            amount_str = f"₹{amount:.2f}" if amount else "—"
            retdate_str = retdate if retdate else "—"
            self.tree.insert("", "end", values=(rid, code or "—", f"{brand} {model}", plate, cust, rdate, retdate_str, amount_str, status), tags=(tag,))

    def export_csv(self):
        """Write every rental row currently in the table out to a CSV file
        using Python's built-in csv module."""
        rows = self.app.db.get_all_rentals()
        if not rows:
            messagebox.showinfo("Nothing to Export", "There is no rental history yet.")
            return

        default_name = f"rental_history_{date.today().isoformat()}.csv"
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.cols)
            for r in rows:
                rid, brand, model, plate, cust, rdate, retdate, amount, status, code = r
                writer.writerow([
                    rid, code or "", f"{brand} {model}", plate, cust,
                    rdate, retdate or "", f"{amount:.2f}" if amount else "", status,
                ])

        messagebox.showinfo("Exported", f"Rental history exported to:\n{path}")


# ===========================================================
# ENTRY POINT
# ===========================================================
if __name__ == "__main__":
    app = CarRentalApp()
    app.mainloop()