from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flask_mail import Mail, Message
import json
import os
import random
import re
import time

app = Flask(__name__)
app.secret_key = "timcookies_super_secret_key_2026"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

# EMAIL OTP CONFIG
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "fatimahazzahra9603@gmail.com"
app.config["MAIL_PASSWORD"] = "limorpdjzjehplus"
app.config["MAIL_DEFAULT_SENDER"] = "fatimahazzahra9603@gmail.com"

OTP_RECEIVER_EMAIL = "fatimahazzahra9603@gmail.com"

mail = Mail(app)

OTP_EXPIRY_SECONDS = 30
MAX_OTP_ATTEMPTS = 3

prices = {
    "Chocolate Cookie": 5,
    "Strawberry Cookie": 6,
    "Oreo Cookie": 7,
    "Matcha Cookie": 8,
    "Red Velvet Cookie": 8,
    "Butter Cookie": 4
}

def send_otp_email(email, otp):
    msg = Message("Tim's Cookie OTP Verification", recipients=[email])
    msg.body = f"""
Hello,

Your Tim's Cookie OTP code is:

{otp}

This OTP will expire in 30 seconds.

Regards,
Tim's Cookie
"""
    mail.send(msg)

def load_users():
    if not os.path.exists("users.json"):
        return []
    try:
        with open("users.json", "r") as file:
            return json.load(file)
    except:
        return []

def save_users(users):
    with open("users.json", "w") as file:
        json.dump(users, file, indent=4)

def load_orders():
    if not os.path.exists("orders.json"):
        return []
    try:
        with open("orders.json", "r") as file:
            return json.load(file)
    except:
        return []

def save_orders(orders):
    with open("orders.json", "w") as file:
        json.dump(orders, file, indent=4)

def save_order(username, cart):
    orders = load_orders()
    total = sum(prices.get(item, 0) for item in cart)

    order = {
        "id": len(orders) + 1,
        "user": username,
        "items": cart,
        "total": total,
        "status": "Pending"
    }

    orders.append(order)
    save_orders(orders)
    return order

def sanitize_input(value):
    if not value:
        return ""
    return value.strip()

def valid_username(username):
    pattern = r"^[A-Za-z0-9_.@-]{3,30}$"
    return re.match(pattern, username) is not None

def valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def valid_password(password):
    if len(password) < 12 or len(password) > 14:
        return False, "Password must be between 12 and 14 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least 1 uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least 1 lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least 1 number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=/\\[\];']", password):
        return False, "Password must contain at least 1 special character."
    return True, "Valid password."

def find_user(username):
    users = load_users()
    for user in users:
        if user.get("username") == username:
            return user
    return None

def login_required():
    return "user" in session

def admin_required():
    return session.get("role") == "admin"

def clear_temp_auth():
    session.pop("temp_user", None)
    session.pop("otp_code", None)
    session.pop("otp_created_at", None)
    session.pop("otp_attempts", None)

def delete_user_by_username(username):
    users = load_users()
    users = [user for user in users if user.get("username") != username]
    save_users(users)

def update_user_role(username, new_role):
    users = load_users()
    for user in users:
        if user.get("username") == username:
            user["role"] = new_role
            break
    save_users(users)

def delete_order_by_index(index):
    orders = load_orders()
    if 0 <= index < len(orders):
        orders.pop(index)
        save_orders(orders)

def update_order_status(index, status):
    orders = load_orders()
    if 0 <= index < len(orders):
        orders[index]["status"] = status
        save_orders(orders)

@app.route("/")
def home():
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = sanitize_input(request.form.get("username", ""))
        email = sanitize_input(request.form.get("email", ""))
        password = request.form.get("password", "")

        if not valid_username(username):
            flash("Username contains invalid characters.", "error")
            return redirect("/register")

        if not valid_email(email):
            flash("Please enter a valid email address.", "error")
            return redirect("/register")

        password_ok, password_msg = valid_password(password)
        if not password_ok:
            flash(password_msg, "error")
            return redirect("/register")

        users = load_users()

        for user in users:
            if user.get("username") == username:
                flash("Username already exists.", "error")
                return redirect("/register")
            if user.get("email") == email:
                flash("Email already exists.", "error")
                return redirect("/register")

        hashed_password = generate_password_hash(password)

        users.append({
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": "customer"
        })

        save_users(users)
        flash("Registration successful. Please login.", "success")
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = sanitize_input(request.form.get("username", ""))
        password = request.form.get("password", "")

        if not valid_username(username):
            flash("Login Failed", "error")
            return redirect("/login")

        user = find_user(username)

        if not user:
            flash("Login Failed", "error")
            return redirect("/login")

        if not check_password_hash(user.get("password"), password):
            flash("Login Failed", "error")
            return redirect("/login")

    

        user_email = OTP_RECEIVER_EMAIL


        otp = str(random.randint(100000, 999999))

        session["temp_user"] = username
        session["otp_code"] = otp
        session["otp_created_at"] = time.time()
        session["otp_attempts"] = 0

        try:
            send_otp_email(user_email, otp)
            flash("OTP has been sent to your email. Please verify within 30 seconds.", "success")
        except Exception as e:
            flash("Failed to send OTP email. Please check email configuration.", "error")
            print("Email error:", e)
            return redirect("/login")

        return redirect("/login-otp")

    return render_template("login.html")

@app.route("/login-otp", methods=["GET", "POST"])
def login_otp():
    if "temp_user" not in session or "otp_code" not in session:
        flash("Please login first.", "error")
        return redirect("/login")

    if request.method == "POST":
        otp_input = sanitize_input(request.form.get("otp", ""))
        created_time = session.get("otp_created_at", 0)

        if time.time() - created_time > OTP_EXPIRY_SECONDS:
            clear_temp_auth()
            flash("OTP expired. Please login again.", "error")
            return redirect("/login")

        attempts = session.get("otp_attempts", 0)

        if otp_input == session.get("otp_code"):
            username = session.get("temp_user")
            user = find_user(username)

            session.permanent = True
            session["user"] = username
            session["role"] = user.get("role", "customer")
            session["show_cookie_popup"] = True

            clear_temp_auth()
            flash("Login successful.", "success")
            return redirect("/dashboard")

        session["otp_attempts"] = attempts + 1

        if session["otp_attempts"] >= MAX_OTP_ATTEMPTS:
            clear_temp_auth()
            flash("OTP attempt limit reached. Please login again.", "error")
            return redirect("/login")

        remaining = MAX_OTP_ATTEMPTS - session["otp_attempts"]
        flash(f"Invalid OTP. Attempts left: {remaining}", "error")
        return redirect("/login-otp")

    return render_template("login_otp.html")

@app.route("/dashboard")
def dashboard():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    return render_template("dashboard.html", role=session.get("role"))

@app.route("/dismiss-cookie-popup")
def dismiss_cookie_popup():
    session["show_cookie_popup"] = False
    return redirect("/dashboard")

@app.route("/admin")
def admin():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    users = load_users()
    orders = load_orders()

    total_users = len(users)
    total_orders = len(orders)
    total_admins = len([u for u in users if u.get("role") == "admin"])
    total_customers = len([u for u in users if u.get("role") == "customer"])

    return render_template(
        "admin.html",
        users=users,
        orders=orders,
        total_users=total_users,
        total_orders=total_orders,
        total_admins=total_admins,
        total_customers=total_customers
    )

@app.route("/admin-profile")
def admin_profile():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    username = session.get("user")
    admin_user = find_user(username)

    total_users = len(load_users())
    total_orders = len(load_orders())

    return render_template(
        "admin_profile.html",
        admin=admin_user,
        total_users=total_users,
        total_orders=total_orders
    )

@app.route("/admin/delete-user/<username>")
def admin_delete_user(username):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    if username == session.get("user"):
        flash("You cannot delete your own admin account.", "error")
        return redirect("/admin")

    delete_user_by_username(username)
    flash("User deleted successfully.", "success")
    return redirect("/admin")

@app.route("/admin/make-admin/<username>")
def make_admin(username):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    update_user_role(username, "admin")
    flash("User promoted to admin.", "success")
    return redirect("/admin")

@app.route("/admin/make-customer/<username>")
def make_customer(username):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    if username == session.get("user"):
        flash("You cannot change your own role.", "error")
        return redirect("/admin")

    update_user_role(username, "customer")
    flash("User changed to customer.", "success")
    return redirect("/admin")

@app.route("/admin/delete-order/<int:order_index>")
def admin_delete_order(order_index):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    delete_order_by_index(order_index)
    flash("Order deleted successfully.", "success")
    return redirect("/admin")

@app.route("/admin/update-order/<int:order_index>/<status>")
def admin_update_order(order_index, status):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if not admin_required():
        flash("Access denied. Admin only.", "error")
        return redirect("/dashboard")

    allowed_status = ["Pending", "Completed", "Cancelled"]

    if status not in allowed_status:
        flash("Invalid order status.", "error")
        return redirect("/admin")

    update_order_status(order_index, status)
    flash("Order status updated successfully.", "success")
    return redirect("/admin")

@app.route("/increase-cart/<item>")
def increase_cart(item):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if item not in prices:
        flash("Invalid product.", "error")
        return redirect("/cart")

    cart = session.get("cart", [])
    cart.append(item)
    session["cart"] = cart

    return redirect("/cart")

@app.route("/decrease-cart/<item>")
def decrease_cart(item):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    cart = session.get("cart", [])

    if item in cart:
        cart.remove(item)
        session["cart"] = cart

    return redirect("/cart")

@app.route("/add-to-cart/<item>")
def add_to_cart(item):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    if item not in prices:
        flash("Invalid product.", "error")
        return redirect("/dashboard")

    if "cart" not in session:
        session["cart"] = []

    cart = session["cart"]
    cart.append(item)
    session["cart"] = cart

    flash(f"{item} added to cart.", "success")
    return redirect("/dashboard")

@app.route("/cart")
def cart():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    cart = session.get("cart", [])
    cart_summary = {}
    total = 0

    for item in cart:
        if item in cart_summary:
            cart_summary[item]["qty"] += 1
        else:
            cart_summary[item] = {
                "qty": 1,
                "price": prices.get(item, 0)
            }

    for item in cart_summary:
        qty = cart_summary[item]["qty"]
        price = cart_summary[item]["price"]
        cart_summary[item]["subtotal"] = qty * price
        total += cart_summary[item]["subtotal"]

    return render_template(
        "cart.html",
        cart=cart_summary,
        total=total,
        role=session.get("role")
    )

@app.route("/remove-from-cart/<item>")
def remove_from_cart(item):
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    cart = session.get("cart", [])

    if item in cart:
        cart.remove(item)
        session["cart"] = cart
        flash(f"{item} removed from cart.", "success")
    else:
        flash("Item not found in cart.", "error")

    return redirect("/cart")

@app.route("/clear-cart")
def clear_cart():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    session["cart"] = []
    flash("Cart cleared.", "success")
    return redirect("/cart")

@app.route("/checkout")
def checkout():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    cart = session.get("cart", [])

    if not cart:
        flash("Cart is empty.", "error")
        return redirect("/cart")

    total = sum(prices.get(item, 0) for item in cart)

    return render_template(
        "checkout.html",
        cart=cart,
        total=total,
        role=session.get("role")
    )

@app.route("/confirm-order")
def confirm_order():
    if not login_required():
        flash("Please login first.", "error")
        return redirect("/login")

    cart = session.get("cart", [])

    if not cart:
        flash("Cart is empty.", "error")
        return redirect("/cart")

    order = save_order(session["user"], cart)
    session["cart"] = []

    flash("Order placed successfully.", "success")
    return render_template("receipt.html", order=order, prices=prices)

@app.route("/check-session")
def check_session():
    return f"User: {session.get('user')}, Role: {session.get('role')}"

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
