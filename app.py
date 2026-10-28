import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
database_url = os.environ.get("DATABASE_URL", "sqlite:///campusfix.db")
# Some hosts provide postgres://; SQLAlchemy expects postgresql://.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

CATEGORIES = ["Electrical", "Plumbing", "Furniture", "Cleanliness", "Wi-Fi / Network", "Other"]
STATUSES = ["Pending", "In Progress", "Resolved"]
PRIORITIES = ["Low", "Medium", "High"]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    complaints = db.relationship("Complaint", backref="reporter", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    location = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    status = db.Column(db.String(30), nullable=False, default="Pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"CATEGORIES": CATEGORIES, "STATUSES": STATUSES, "PRIORITIES": PRIORITIES}


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
        else:
            user = User(name=name, email=email, role="student")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome to CampusFix!", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("You are now signed in.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    else:
        complaints = Complaint.query.filter_by(user_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    counts = {
        "total": len(complaints),
        "pending": sum(c.status == "Pending" for c in complaints),
        "progress": sum(c.status == "In Progress" for c in complaints),
        "resolved": sum(c.status == "Resolved" for c in complaints),
    }
    return render_template("dashboard.html", complaints=complaints, counts=counts)


@app.route("/complaints/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    if current_user.role == "admin":
        flash("Administrator accounts cannot submit student complaints.", "warning")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "")
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        if not title or category not in CATEGORIES or not location or not description:
            flash("Please complete all fields using a valid category.", "danger")
        else:
            complaint = Complaint(user_id=current_user.id, title=title, category=category,
                                  location=location, description=description)
            db.session.add(complaint)
            db.session.commit()
            flash("Your complaint was submitted successfully.", "success")
            return redirect(url_for("dashboard"))
    return render_template("new_complaint.html")


@app.route("/admin/complaints/<int:complaint_id>", methods=["POST"])
@admin_required
def update_complaint(complaint_id):
    complaint = db.get_or_404(Complaint, complaint_id)
    status = request.form.get("status", "")
    priority = request.form.get("priority", "")
    if status not in STATUSES or priority not in PRIORITIES:
        flash("Invalid status or priority.", "danger")
    else:
        complaint.status = status
        complaint.priority = priority
        db.session.commit()
        flash(f"Complaint #{complaint.id} updated.", "success")
    return redirect(url_for("dashboard"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
