from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId, InvalidId
import os
from functools import wraps
import config
from datetime import datetime

app = Flask(__name__)

# --- CONFIG ---
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- MONGO CONNECT ---
client = MongoClient(config.MONGO_URI)
db = client["boutique"]

users = db.users
products = db.products
comments = db.comments
contacts = db.contacts
orders = db.orders

# ======================
# AUTH DECORATOR
# ======================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated
# ======================
# HOME
# ======================
@app.route('/')
def home():
    query = {}
    search_text = request.args.get('q', '').strip()
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    # Filtrage par nom
    if search_text:
        query['name'] = {'$regex': search_text, '$options': 'i'}  # insensible à la casse

    # Filtrage par prix
    price_filter = {}
    if min_price:
        try:
            price_filter['$gte'] = float(min_price)
        except ValueError:
            pass
    if max_price:
        try:
            price_filter['$lte'] = float(max_price)
        except ValueError:
            pass
    if price_filter:
        query['price'] = price_filter

    prods = list(products.find(query).sort("created_at", -1))
    return render_template('home.html', products=prods)


# ======================
# PRODUCT DETAILS
# ======================
@app.route('/product/<pid>')
def product_page(pid):
    try:
        prod = products.find_one({"_id": ObjectId(pid)})
    except InvalidId:
        return redirect(url_for("home"))

    prod_comments = list(comments.find({"product_id": pid}))
    return render_template('product.html', product=prod, comments=prod_comments)


# ======================
# ADD PRODUCT (ADMIN)
# ======================
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    u = users.find_one({"_id": ObjectId(session['user_id'])})
    if not u or not u.get("is_admin"):
        flash("Accès refusé")
        return redirect(url_for("home"))

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        promo = request.form.get('promo', '')
        desc = request.form.get('description', '')

        file = request.files.get('image')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        prod = {
            "name": name,
            "price": price,
            "promo": promo,
            "description": desc,
            "image": filename,
            "created_at": datetime.utcnow()
        }

        products.insert_one(prod)
        flash("Produit ajouté")
        return redirect(url_for("home"))

    return render_template('add_product.html')


# ======================
# DELETE PRODUCT (ADMIN)
# ======================
@app.route('/delete_product/<pid>', methods=['POST'])
@login_required
def delete_product(pid):
    u = users.find_one({"_id": ObjectId(session['user_id'])})
    if not u or not u.get("is_admin"):
        flash("Accès refusé")
        return redirect(url_for("home"))

    try:
        products.delete_one({"_id": ObjectId(pid)})
        comments.delete_many({"product_id": pid})
    except InvalidId:
        pass

    flash("Produit supprimé")
    return redirect(url_for("home"))


# ======================
# CART
# ======================
@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = []
    total = 0

    for pid, qty in cart.items():
        try:
            obj_id = ObjectId(pid)
        except InvalidId:
            continue  # Ignore les ids invalides
        p = products.find_one({"_id": obj_id})
        if p:
            p['qty'] = qty
            p['subtotal'] = qty * p['price']
            total += p['subtotal']
            p['_id'] = str(p['_id'])  # convertir ObjectId en chaîne pour le template
            items.append(p)

    return render_template('cart.html', products=items, total=total)


@app.route('/cart/add/<pid>', methods=['POST'])
def cart_add(pid):
    qty = int(request.form.get("qty", 1))
    cart = session.get('cart', {})

    try:
        obj_id = ObjectId(pid)
        pid_str = str(obj_id)
    except InvalidId:
        flash("Produit invalide")
        return redirect(url_for('home'))

    cart[pid_str] = cart.get(pid_str, 0) + qty
    session['cart'] = cart
    flash("Ajouté au panier")
    return redirect(request.referrer or url_for('home'))


@app.route('/cart/remove/<pid>', methods=['POST'])
def cart_remove(pid):
    cart = session.get('cart', {})
    if pid in cart:
        del cart[pid]
        session['cart'] = cart
    return redirect(url_for('cart'))


# ======================
# POST COMMENT
# ======================
@app.route('/product/<pid>/comment', methods=['POST'])
@login_required
def post_comment(pid):
    text = request.form['comment']
    c = {
        "product_id": pid,
        "user_id": str(session['user_id']),
        "text": text,
        "created_at": datetime.utcnow()
    }
    comments.insert_one(c)
    return redirect(url_for('product_page', pid=pid))


# ======================
# ABOUT
# ======================
@app.route('/about')
def about():
    return render_template('about.html')


# ======================
# CONTACT
# ======================
@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        contacts.insert_one({
            "name": request.form['name'],
            "email": request.form['email'],
            "message": request.form['message'],
            "created_at": datetime.utcnow()
        })
        flash("Message reçu, merci !")
        return redirect(url_for('home'))

    return render_template('contact.html')


# ======================
# REGISTER
# ======================
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if users.find_one({"username": username}):
            flash("Nom d'utilisateur déjà utilisé")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)
        uid = users.insert_one({
            "username": username,
            "password": hashed,
            "is_admin": False
        }).inserted_id

        session['user_id'] = str(uid)
        flash("Compte créé avec succès")
        return redirect(url_for('home'))

    return render_template('register.html')


# ======================
# LOGIN
# ======================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        u = users.find_one({"username": username})
        if u and check_password_hash(u['password'], password):
            session['user_id'] = str(u['_id'])
            flash("Connecté")
            return redirect(url_for("home"))

        flash("Login/Password incorrect")

    return render_template("login.html")


# ======================
# LOGOUT
# ======================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home"))


# ======================
# STATIC UPLOADS
# ======================
@app.route('/uploads/<filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

#============== dachbord
# ======================
# ADMIN DASHBOARD
# ======================
@app.route('/admin')
@login_required
def admin_dashboard():
    u = users.find_one({"_id": ObjectId(session['user_id'])})
    if not u or not u.get("is_admin"):
        flash("Accès refusé")
        return redirect(url_for("home"))

    prods = list(products.find().sort("created_at", -1))
    return render_template("admin_dashboard.html", products=prods)


# ======================
# EDIT PRODUCT (ADMIN)
# ======================
@app.route('/edit_product/<pid>', methods=['GET', 'POST'])
@login_required
def edit_product(pid):
    u = users.find_one({"_id": ObjectId(session['user_id'])})
    if not u or not u.get("is_admin"):
        flash("Accès refusé")
        return redirect(url_for("home"))

    try:
        prod = products.find_one({"_id": ObjectId(pid)})
    except InvalidId:
        return redirect(url_for("admin_dashboard"))

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        promo = request.form.get('promo', '')
        desc = request.form.get('description', '')

        file = request.files.get('image')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = prod['image']  # garder l'ancienne image

        products.update_one(
            {"_id": ObjectId(pid)},
            {"$set": {
                "name": name,
                "price": price,
                "promo": promo,
                "description": desc,
                "image": filename
            }}
        )

        flash("Produit modifié")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_product.html", product=prod)


# ======================
# RUN
# ======================
if __name__ == '__main__':
    app.run(debug=True)
