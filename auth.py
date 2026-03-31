import hashlib
import json
import os
import sys
import tkinter as tk
from tkinter import messagebox

# ============================================================
# Credentials stored as SHA-256 hashes — never plaintext.
# User database stored in users.json in the project folder.
# ============================================================

DB_PATH = os.path.join(os.path.dirname(__file__), "users.json")
MAX_ATTEMPTS = 3


def _hash(value: str) -> str:
    """Return SHA-256 hex digest of a string"""
    return hashlib.sha256(value.encode()).hexdigest()


def _load_db() -> dict:
    """Load users database from JSON file, return empty dict if not found"""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_db(db: dict):
    """Save users database to JSON file"""
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)


# ============================================================
# GUI
# ============================================================

class AuthApp:
    """
    Tkinter GUI for login and registration.

    Handles login, registration, and role-based access (admin vs user).
    """

    def __init__(self, root):
        self.root     = root
        self.role     = None          # Set on successful auth
        self.username = None
        self.attempts = 0

        self.root.title("Drone Control — Access Required")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self._build_main_screen()

    # ── Screens ──────────────────────────────────────────────────────────

    def _clear(self):
        """Destroy all widgets in the window"""
        for w in self.root.winfo_children():
            w.destroy()

    def _build_main_screen(self):
        """Initial screen — choose Login or Register"""
        self._clear()

        tk.Label(self.root, text="🚁  DRONE CONTROL SYSTEM",
                 font=("Arial", 16, "bold"), bg="#1a1a2e", fg="white"
                 ).pack(pady=(30, 5))

        tk.Label(self.root, text="Secure Drone Control System",
                 font=("Arial", 9), bg="#1a1a2e", fg="#888888"
                 ).pack(pady=(0, 25))

        tk.Button(self.root, text="  Login  ", font=("Arial", 13),
                  bg="#2e6db4", fg="white", relief="flat", cursor="hand2",
                  width=18, command=self._build_login_screen
                  ).pack(pady=8)

        tk.Button(self.root, text="  Register  ", font=("Arial", 13),
                  bg="#2e2e5e", fg="white", relief="flat", cursor="hand2",
                  width=18, command=self._build_register_screen
                  ).pack(pady=8)

        self.root.geometry("320x220")

    def _build_login_screen(self):
        """Login screen"""
        self._clear()
        self.attempts = 0

        tk.Label(self.root, text="Login", font=("Arial", 15, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=(25, 15))

        # Username
        tk.Label(self.root, text="Username", font=("Arial", 10),
                 bg="#1a1a2e", fg="#cccccc").pack()
        self.login_user = tk.Entry(self.root, font=("Arial", 11), width=22)
        self.login_user.pack(pady=(2, 10))
        self.login_user.focus()

        # Password / PIN
        tk.Label(self.root, text="Password / PIN", font=("Arial", 10),
                 bg="#1a1a2e", fg="#cccccc").pack()
        self.login_pass = tk.Entry(self.root, font=("Arial", 11),
                                   width=22, show="•")
        self.login_pass.pack(pady=(2, 5))
        self.login_pass.bind("<Return>", lambda e: self._do_login())

        self.login_msg = tk.Label(self.root, text="", font=("Arial", 9),
                                  bg="#1a1a2e", fg="#ff4444")
        self.login_msg.pack(pady=3)

        tk.Button(self.root, text="Login", font=("Arial", 11),
                  bg="#2e6db4", fg="white", relief="flat", width=14,
                  command=self._do_login).pack(pady=5)

        tk.Button(self.root, text="← Back", font=("Arial", 9),
                  bg="#1a1a2e", fg="#888888", relief="flat",
                  command=self._build_main_screen).pack()

        self.root.geometry("320x300")

    def _build_register_screen(self):
        """Registration screen"""
        self._clear()

        tk.Label(self.root, text="Register", font=("Arial", 15, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=(25, 15))

        tk.Label(self.root, text="Username", font=("Arial", 10),
                 bg="#1a1a2e", fg="#cccccc").pack()
        self.reg_user = tk.Entry(self.root, font=("Arial", 11), width=22)
        self.reg_user.pack(pady=(2, 10))
        self.reg_user.focus()

        tk.Label(self.root, text="Password / PIN", font=("Arial", 10),
                 bg="#1a1a2e", fg="#cccccc").pack()
        self.reg_pass = tk.Entry(self.root, font=("Arial", 11),
                                 width=22, show="•")
        self.reg_pass.pack(pady=(2, 10))

        tk.Label(self.root, text="Confirm Password / PIN", font=("Arial", 10),
                 bg="#1a1a2e", fg="#cccccc").pack()
        self.reg_confirm = tk.Entry(self.root, font=("Arial", 11),
                                    width=22, show="•")
        self.reg_confirm.pack(pady=(2, 5))
        self.reg_confirm.bind("<Return>", lambda e: self._do_register())

        self.reg_msg = tk.Label(self.root, text="", font=("Arial", 9),
                                bg="#1a1a2e", fg="#ff4444")
        self.reg_msg.pack(pady=3)

        tk.Button(self.root, text="Register", font=("Arial", 11),
                  bg="#2e6db4", fg="white", relief="flat", width=14,
                  command=self._do_register).pack(pady=5)

        tk.Button(self.root, text="← Back", font=("Arial", 9),
                  bg="#1a1a2e", fg="#888888", relief="flat",
                  command=self._build_main_screen).pack()

        self.root.geometry("320x370")

    # ── Logic ─────────────────────────────────────────────────────────────

    def _do_login(self):
        username = self.login_user.get().strip()
        password = self.login_pass.get()

        if not username or not password:
            self.login_msg.config(text="Please fill in all fields.")
            return

        db = _load_db()

        if username not in db:
            self.attempts += 1
            self._check_attempts("Invalid username or password.")
            return

        if db[username]["hash"] != _hash(password):
            self.attempts += 1
            self._check_attempts("Invalid username or password.")
            return

        # Successful login
        self.role     = db[username]["role"]
        self.username = username
        self.root.destroy()

    def _do_register(self):
        username = self.reg_user.get().strip()
        password = self.reg_pass.get()
        confirm  = self.reg_confirm.get()

        if not username or not password or not confirm:
            self.reg_msg.config(text="Please fill in all fields.")
            return

        if password != confirm:
            self.reg_msg.config(text="Passwords do not match.")
            return

        if len(password) < 4:
            self.reg_msg.config(text="Minimum 4 characters.")
            return

        db = _load_db()

        if username in db:
            self.reg_msg.config(text="Username already exists.")
            return

        # First ever account becomes admin, all others are users
        role = "admin" if len(db) == 0 else "user"

        db[username] = {
            "hash": _hash(password),
            "role": role
        }
        _save_db(db)

        messagebox.showinfo(
            "Registered",
            f"Account created!\nRole: {role.upper()}\n\nPlease log in."
        )
        self._build_login_screen()

    def _check_attempts(self, message: str):
        """Show error or exit after MAX_ATTEMPTS failures"""
        remaining = MAX_ATTEMPTS - self.attempts
        if remaining <= 0:
            messagebox.showerror(
                "Access Denied",
                "Maximum login attempts reached.\nExiting for security reasons."
            )
            self.root.destroy()
            sys.exit(1)
        else:
            self.login_msg.config(
                text=f"{message} {remaining} attempt(s) left."
            )
            self.login_pass.delete(0, tk.END)


# ============================================================
# Entry point
# ============================================================

def authenticate() -> str:
    """
    Launch the authentication GUI and return the authenticated role.

    Returns:
        'admin' or 'user'

    Exits if max attempts exceeded or window is closed without auth.
    """
    root = tk.Tk()
    app  = AuthApp(root)
    root.mainloop()

    if app.role is None:
        # Window was closed without logging in
        print("Authentication cancelled. Exiting.")
        sys.exit(1)

    return app.role, app.username