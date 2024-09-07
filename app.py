import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    d = {}
    sum = 0
    stocks = db.execute("SELECT id, symbol, SUM(number) AS total FROM stocks WHERE id = ? GROUP BY id, symbol", session["user_id"])
    for s in stocks:
        info = lookup(s["symbol"])
        d[s["symbol"]] = info["price"]
        sum += info["price"]*s["total"]

    return render_template("index.html", user=user, stocks=stocks, d=d, sum=sum)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        info = lookup(request.form.get("symbol"))
        time = datetime.now()
        if not info:
            return apology("Not a valid stock symbol", 400)
        elif not request.form.get("shares").isdigit():
            return apology("Cannot buy specified quantity of shares", 400)
        elif int(request.form.get("shares")) < 0:
            return apology("Cannot buy specified quantity of shares", 400)
        else:
            price = float(request.form.get("shares")) * (info["price"])
            rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
            balance = rows[0]["cash"] - price
            if balance >= 0:
                db.execute("INSERT INTO stocks (id, symbol, number, price, t, tt) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"],
                           request.form.get("symbol"), request.form.get("shares"), info["price"], "Buy", time)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"])
                return redirect("/")
            else:
                return apology("You dont have enough cash to buy these stocks", 403)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    e = db.execute("SELECT * FROM stocks WHERE id = ?", session["user_id"])
    return render_template("history.html", e=e)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        info = lookup(request.form.get("symbol"))
        if not info:
            return apology("Stock for given Symbol does not exist", 400)
        return render_template("quoted.html", info=info)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")
        if not username:
            return apology("Please enter username", 400)
        elif not password or not confirm_password:
            return apology("Please enter passwords", 400)
        elif password != confirm_password:
            return apology("Passwords entered do not match", 400)
        else:
            try:
                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))
                return redirect("/")
            except:
                return apology("Username already exists", 400)
    else:
        return render_template("register.html")


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    if request.method == "POST":
        cash = request.form.get("cash")
        initial = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        balance = int(cash) + initial[0]["cash"]
        db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"])
        return redirect("/addcash")
    else:
        f = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        final = f[0]["cash"]
        return render_template("addcash.html", final=final)



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        time = datetime.now()
        info = lookup(request.form.get("symbol"))
        price = float(request.form.get("shares")) * (info["price"])
        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        balance = rows[0]["cash"] + price
        sharesOwned = db.execute("SELECT SUM(number) AS total FROM stocks WHERE id = ? AND symbol = ? GROUP BY id, symbol", session["user_id"], request.form.get("symbol"))
        if not request.form.get("symbol"):
            return apology("No share to sell has been selected", 400)
        elif not request.form.get("shares").isdigit():
            return apology("Cannot sell specified quantity of shares", 400)
        elif int(request.form.get("shares")) < 0:
            return apology("Cannot sell specified quantity of shares", 400)
        elif int(request.form.get("shares")) > sharesOwned[0]["total"]:
            return apology("Not enough shares owned", 400)
        else:
            db.execute("INSERT INTO stocks (id, symbol, number, price, t, tt) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], request.form.get("symbol"), (-1*int(request.form.get("shares"))), info["price"], "Sell", time)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"])
            return redirect ("/")
    else:
        stocks = db.execute("SELECT id, symbol, SUM(number) AS total FROM stocks WHERE id = ? GROUP BY id, symbol", session["user_id"])
        return render_template("sell.html", stocks=stocks)




