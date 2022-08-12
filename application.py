import os
from datetime import datetime, timedelta
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, lookup_stat

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get('IEX_TOKEN'):
   raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    stocks_owned = db.execute("SELECT * FROM stocks_owned WHERE user_id =? ORDER BY number_of_stocks_owned DESC", session["user_id"])

    index = []
    grand_total = round(user_cash, 2)

    for row in stocks_owned:
            stock_lookup = lookup(row["symbol"])
            info = []
            info.extend((stock_lookup["symbol"], stock_lookup["name"], round(stock_lookup["price"],2), row["number_of_stocks_owned"], round(stock_lookup["price"] * row["number_of_stocks_owned"], 2)))
            grand_total += round(info[4],2)
            index.append(info)

    return render_template("index.html", index=index, user_cash=round(user_cash, 2), grand_total=round(grand_total, 2))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            return apology("Please enter a valid company's stock symbol", 400)

        price = symbol["price"]
        if price is None:
            return apology("Please enter a valid company's stock symbol", 400)

        shares = request.form.get("shares")

        try:
            shares = int(shares)
            if shares <=0:
                return apology("Please enter a positive integer", 400)
        except:
            return apology("Please enter a positive integer", 400)

        user_cash = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])[0]["cash"]

        shares = int(shares)
        total_price = price * shares
        if user_cash < total_price:
            return apology("You do not have enough cash to purchase all these shares for this stock", 400)
        else:
            db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_price, session["user_id"])

            now = datetime.now()
            delta = timedelta(hours=-4)
            present = now+delta
            time = present.strftime('%m/%d/%Y %I:%M:%S')

            db.execute("INSERT INTO stock_transactions(user_id, time, symbol, shares, price, total_price, action) VALUES(?, ?, ?, ?, ?, ?, ?)", session["user_id"], time, symbol["symbol"], shares, price, total_price, "buy")

            stocks = db.execute("SELECT number_of_stocks_owned FROM stocks_owned WHERE user_id=? AND symbol=?", session["user_id"], symbol["symbol"])
            if not stocks:
                db.execute("INSERT INTO stocks_owned(user_id, symbol, number_of_stocks_owned) VALUES(?, ?, ?)", session["user_id"], symbol["symbol"], shares)
            else:
                db.execute("UPDATE stocks_owned SET number_of_stocks_owned = ? WHERE user_id = ? AND symbol=?", shares+stocks[0]["number_of_stocks_owned"], session["user_id"], symbol["symbol"])

        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    transactions = db.execute("SELECT time, symbol, shares, price, total_price, action FROM stock_transactions WHERE user_id=?", session["user_id"])
    history = []

    for row in transactions:
            stock_lookup = lookup(row["symbol"])
            info = []
            info.extend((row["time"], stock_lookup["symbol"], stock_lookup["name"], row["shares"], row["price"], round(row["total_price"], 2), row["action"]))
            history.append(info)

    return render_template("history.html", history=history)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
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

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure user inputed a valid stock
        quote = lookup(request.form.get("symbol"))
        stat = lookup_stat(request.form.get("symbol"))
        if quote is None:
            return apology("Could not find the stock", 400)
        if stat is None:
            return apology("Could not find the stock", 400)
        #else:
        return render_template("quoted.html", symbol=quote["symbol"], name=quote["name"], price=usd(quote["price"]), change=usd(quote["change"]), changePercent=quote['changePercent'], previousClose=usd(quote["previousClose"]), open="bugged", week52High=usd(quote["week52High"]), week52Low=usd(quote["week52Low"]), latestVolume=quote["latestVolume"], marketCap=quote["marketCap"], ytdChange=quote["ytdChange"], peRatio=quote["peRatio"], beta=stat["beta"], sharesOutstanding=stat["sharesOutstanding"], avg10Volume=stat["avg10Volume"], ttmEPS=stat["ttmEPS"], ttmDividendRate=stat["ttmDividendRate"], dividendYield=stat["dividendYield"], nextEarningsDate=stat["nextEarningsDate"])

    # Render quote.html if the user used a GET method to visit this route (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirmation password was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 403)

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        # Ensure username has not been taken
        elif db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username")):
            return apology("username is already taken", 403)

        # Add the username and password to the database if all went well then redirect user to login page
        else:
            db.execute("INSERT INTO users(username, hash) VALUES(?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))
            return redirect("/login")

    # Render register.html if the user used a GET method to visit this route (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
        # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        symbol = lookup(request.form.get("symbol"))
        if not symbol:
            return apology("Please enter a company's stock symbol", 400)

        price = symbol["price"]
        if price is None:
            return apology("Please enter a valid company's stock symbol", 400)

        shares = request.form.get("shares")

        try:
            shares = int(shares)
            if shares <=0:
                return apology("Please enter a positive integer", 400)
        except:
            return apology("Please enter a positive integer", 400)

        stocks = db.execute("SELECT number_of_stocks_owned FROM stocks_owned WHERE user_id=? AND symbol=?", session["user_id"], symbol["symbol"])[0]["number_of_stocks_owned"]

        shares = int(shares)
        total_price = price * shares
        if shares > stocks:
            return apology("You do not have enough shares", 400)
        else:
            db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_price, session["user_id"])

            now = datetime.now()
            delta = timedelta(hours=-4)
            present = now+delta
            time = present.strftime('%m/%d/%Y %I:%M:%S')

            db.execute("INSERT INTO stock_transactions(user_id, time, symbol, shares, price, total_price, action) VALUES(?, ?, ?, ?, ?, ?, ?)", session["user_id"], time, symbol["symbol"], shares, price, total_price, "sell")
            db.execute("UPDATE stocks_owned SET number_of_stocks_owned = ? WHERE user_id = ? AND symbol=?", stocks-shares, session["user_id"], symbol["symbol"])

            if db.execute("SELECT number_of_stocks_owned FROM stocks_owned WHERE user_id=? AND symbol=?", session["user_id"], symbol["symbol"])[0]["number_of_stocks_owned"] == 0:
                db.execute("DELETE FROM stocks_owned WHERE user_id=? AND symbol=?", session["user_id"], symbol["symbol"])

        flash("Sold!")
        return redirect("/")

    else:
        stocks_owned = db.execute("SELECT symbol, number_of_stocks_owned FROM stocks_owned WHERE user_id=?", session["user_id"])
        stock_dict = {}

        for stock in stocks_owned:
            stock_dict[stock["symbol"]] = stock["number_of_stocks_owned"]

        return render_template("sell.html", stock_dict = stock_dict)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
