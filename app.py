from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import requests
from datetime import date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gvs_secret_2024")

# ── Google Apps Script Web App URL ──────────────────────────────────────────
# Yahan apna deployed Apps Script URL daalo (setup guide mein bataya hai)
SCRIPT_URL = os.environ.get("GOOGLE_SCRIPT_URL", "")

def sheet_request(action, payload=None):
    """Google Apps Script se baat karo"""
    if not SCRIPT_URL:
        return {"error": "GOOGLE_SCRIPT_URL not set"}
    data = {"action": action}
    if payload:
        data.update(payload)
    try:
        resp = requests.post(SCRIPT_URL, json=data, timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

# ── Public pages ─────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("home.html", user=session.get("user"))

@app.route("/about")
def about():
    return render_template("about.html", user=session.get("user"))

@app.route("/contact")
def contact():
    return render_template("contact.html", user=session.get("user"))

@app.route("/courses")
def courses():
    return render_template("courses.html", user=session.get("user"))

# ── Auth ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        result = sheet_request("login", {"username": username, "password": password})
        if result.get("success"):
            session["user"] = {
                "username": username,
                "role": result["role"],
                "name": result["name"]
            }
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid username or password", user=None)
    return render_template("login.html", user=session.get("user"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ── Register (admin only) ─────────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if not session.get("user") or session["user"]["role"] != "admin":
        return redirect(url_for("home"))
    error = success = None
    users = []
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip()
        result = sheet_request("addUser", {
            "username": username, "password": password,
            "name": name, "role": "student"
        })
        if result.get("success"):
            success = f"Student '{name}' add ho gaya!"
        else:
            error = result.get("error", "Kuch galat hua, dobara try karo")
    all_users = sheet_request("getAllUsers")
    users = all_users.get("users", [])
    return render_template("register.html", user=session.get("user"),
                           error=error, success=success, users=users)

# ── Attendance ────────────────────────────────────────────────────────────────
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if not session.get("user"):
        return redirect(url_for("login"))
    today = str(date.today())
    user = session["user"]

    if request.method == "POST":
        if user["role"] == "student":
            mark_date = request.form.get("date")
            if mark_date != today:
                return jsonify({"error": "Sirf aaj ki attendance mark ho sakti hai!"}), 400
            result = sheet_request("markAttendance", {
                "username": user["username"], "date": today, "status": "P"
            })
            return jsonify(result)

        elif user["role"] == "admin":
            target_user = request.form.get("target_user")
            mark_date = request.form.get("date", today)
            status = request.form.get("status", "P")
            result = sheet_request("markAttendance", {
                "username": target_user, "date": mark_date, "status": status
            })
            return jsonify(result)

    # GET
    if user["role"] == "student":
        hist_result = sheet_request("getAttendance", {"username": user["username"]})
        history = hist_result.get("history", {})
        already_marked = today in history
        return render_template("attendance.html", user=user, history=history,
                               today=today, already_marked=already_marked)

    elif user["role"] == "admin":
        all_users = sheet_request("getAllUsers")
        students = [u for u in all_users.get("users", []) if u["role"] == "student"]
        all_att_result = sheet_request("getAllAttendance")
        all_att = all_att_result.get("attendance", {})
        return render_template("attendance_admin.html", user=user,
                               students=students, all_att=all_att, today=today)

    return redirect(url_for("home"))

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if not session.get("user") or session["user"]["role"] != "admin":
        return redirect(url_for("home"))
    all_users = sheet_request("getAllUsers")
    students = [u for u in all_users.get("users", []) if u["role"] == "student"]
    return render_template("dashboard.html", user=session.get("user"), students=students)

if __name__ == "__main__":
    app.run(debug=True)
