import tkinter as tk
from tkinter import messagebox
import sqlite3

# ======================
# DATABASE
# ======================
conn = sqlite3.connect("boutique.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    is_admin INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL
)
""")

conn.commit()

# ======================
# GLOBALS
# ======================
current_user = None
cart = {}
dark_mode = False

# ======================
# THEMES
# ======================
def apply_theme(widget):
    bg = "#1e1e1e" if dark_mode else "white"
    fg = "white" if dark_mode else "black"

    try:
        widget.configure(bg=bg, fg=fg)
    except:
        widget.configure(bg=bg)

    for child in widget.winfo_children():
        apply_theme(child)

def toggle_dark_mode():
    global dark_mode
    dark_mode = not dark_mode
    apply_theme(root)

# ======================
# UTILS
# ======================
def clear():
    for w in main_frame.winfo_children():
        w.destroy()

# ======================
# LOGIN
# ======================
def login():
    global current_user
    cur.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (entry_user.get(), entry_pass.get())
    )
    user = cur.fetchone()

    if user:
        current_user = user
        show_products()
    else:
        messagebox.showerror("Erreur", "Login incorrect")

def register():
    try:
        cur.execute(
            "INSERT INTO users(username,password,is_admin) VALUES(?,?,0)",
            (entry_user.get(), entry_pass.get())
        )
        conn.commit()
        messagebox.showinfo("OK", "Compte créé")
    except:
        messagebox.showerror("Erreur", "Utilisateur existe")

# ======================
# PRODUCTS
# ======================
def show_products():
    clear()

    tk.Label(main_frame, text="🛒 Produits",
             font=("Arial", 16, "bold")).pack(pady=10)

    for p in cur.execute("SELECT * FROM products"):
        frame = tk.Frame(main_frame, bd=1, relief="solid", padx=10, pady=5)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text=p[1]).grid(row=0, column=0, sticky="w")
        tk.Label(frame, text=f"{p[2]} DH").grid(row=0, column=1, padx=10)

        tk.Button(frame, text="➕",
                  command=lambda pid=p[0]: add_cart(pid)).grid(row=0, column=2)

        tk.Button(frame, text="✏",
                  command=lambda pid=p[0]: show_edit_product(pid)).grid(row=0, column=3)

        tk.Button(frame, text="❌",
                  command=lambda pid=p[0]: delete_product(pid)).grid(row=0, column=4)

    tk.Button(main_frame, text="🧾 Panier", command=show_cart).pack(pady=5)
    tk.Button(main_frame, text="➕ Ajouter Produit",
              command=show_add_product).pack(pady=5)

    apply_theme(main_frame)

def add_cart(pid):
    cart[pid] = cart.get(pid, 0) + 1
    messagebox.showinfo("Panier", "Produit ajouté")

# ======================
# ADD PRODUCT
# ======================
def show_add_product():
    clear()

    tk.Label(main_frame, text="➕ Ajouter Produit",
             font=("Arial", 16, "bold")).pack(pady=10)

    form = tk.Frame(main_frame)
    form.pack()

    tk.Label(form, text="Nom").grid(row=0, column=0, pady=5)
    entry_name = tk.Entry(form)
    entry_name.grid(row=0, column=1)

    tk.Label(form, text="Prix").grid(row=1, column=0, pady=5)
    entry_price = tk.Entry(form)
    entry_price.grid(row=1, column=1)

    def save():
        try:
            cur.execute(
                "INSERT INTO products(name,price) VALUES(?,?)",
                (entry_name.get(), float(entry_price.get()))
            )
            conn.commit()
            show_products()
        except:
            messagebox.showerror("Erreur", "Erreur ajout")

    tk.Button(main_frame, text="💾 Enregistrer", command=save).pack(pady=5)
    tk.Button(main_frame, text="⬅ Retour", command=show_products).pack()

    apply_theme(main_frame)

# ======================
# EDIT PRODUCT
# ======================
def show_edit_product(pid):
    clear()

    cur.execute("SELECT name,price FROM products WHERE id=?", (pid,))
    p = cur.fetchone()

    tk.Label(main_frame, text="✏ Modifier Produit",
             font=("Arial", 16, "bold")).pack(pady=10)

    form = tk.Frame(main_frame)
    form.pack()

    tk.Label(form, text="Nom").grid(row=0, column=0)
    entry_name = tk.Entry(form)
    entry_name.grid(row=0, column=1)
    entry_name.insert(0, p[0])

    tk.Label(form, text="Prix").grid(row=1, column=0)
    entry_price = tk.Entry(form)
    entry_price.grid(row=1, column=1)
    entry_price.insert(0, p[1])

    def update():
        cur.execute(
            "UPDATE products SET name=?, price=? WHERE id=?",
            (entry_name.get(), float(entry_price.get()), pid)
        )
        conn.commit()
        show_products()

    tk.Button(main_frame, text="💾 Modifier", command=update).pack(pady=5)
    tk.Button(main_frame, text="⬅ Retour", command=show_products).pack()

    apply_theme(main_frame)

def delete_product(pid):
    if messagebox.askyesno("Confirmation", "Supprimer ce produit ?"):
        cur.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        show_products()

# ======================
# CART
# ======================
def show_cart():
    clear()
    total = 0

    tk.Label(main_frame, text="🧾 Panier",
             font=("Arial", 16, "bold")).pack(pady=10)

    for pid, qty in list(cart.items()):
        cur.execute("SELECT name,price FROM products WHERE id=?", (pid,))
        p = cur.fetchone()

        subtotal = qty * p[1]
        total += subtotal

        frame = tk.Frame(main_frame)
        frame.pack(fill="x")

        tk.Label(frame, text=f"{p[0]} x{qty} = {subtotal} DH").grid(row=0, column=0)
        tk.Button(frame, text="➖",
                  command=lambda pid=pid: remove_cart(pid)).grid(row=0, column=1)

    tk.Label(main_frame, text=f"TOTAL : {total} DH",
             font=("Arial", 14)).pack(pady=10)

    tk.Button(main_frame, text="⬅ Retour", command=show_products).pack()
    apply_theme(main_frame)

def remove_cart(pid):
    if cart[pid] > 1:
        cart[pid] -= 1
    else:
        del cart[pid]
    show_cart()

# ======================
# INIT DATA
# ======================
if not cur.execute("SELECT * FROM products").fetchall():
    cur.execute("INSERT INTO products(name,price) VALUES('PC',5000)")
    cur.execute("INSERT INTO products(name,price) VALUES('Téléphone',3000)")
    conn.commit()

# ======================
# UI
# ======================
root = tk.Tk()
root.title("Boutique Tkinter")
root.geometry("500x600")

tk.Button(root, text="🌙 Dark Mode",
          command=toggle_dark_mode).pack(anchor="ne", padx=10, pady=5)

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True, padx=20, pady=20)

tk.Label(main_frame, text="🔐 Connexion",
         font=("Arial", 16, "bold")).pack(pady=10)

form = tk.Frame(main_frame)
form.pack()

tk.Label(form, text="Username").grid(row=0, column=0)
entry_user = tk.Entry(form)
entry_user.grid(row=0, column=1)

tk.Label(form, text="Password").grid(row=1, column=0)
entry_pass = tk.Entry(form, show="*")
entry_pass.grid(row=1, column=1)

btns = tk.Frame(main_frame)
btns.pack(pady=10)

tk.Button(btns, text="Login", command=login).grid(row=0, column=0, padx=5)
tk.Button(btns, text="Register", command=register).grid(row=0, column=1, padx=5)

apply_theme(root)
root.mainloop()
