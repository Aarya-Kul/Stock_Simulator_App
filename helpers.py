import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
import apikey

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("IEX_TOKEN")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None


    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"],
            "change": float(quote["change"]),
            "changePercent": float(quote["changePercent"]),
            "previousClose": float(quote["previousClose"]),
            # "open": float(quote["iexOpen"]),
            "week52High": float(quote["week52High"]),
            "week52Low": float(quote["week52Low"]),
            "latestVolume": quote["latestVolume"],
            "marketCap" : quote["marketCap"],
            "ytdChange": float(quote["ytdChange"]),
            "peRatio": float(quote["peRatio"]),
        }
    except (KeyError, TypeError, ValueError):
        return None

def lookup_stat(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("IEX_TOKEN")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/stats?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None


    # Parse response
    try:
        stat = response.json()
        return {
            "beta": float(stat["beta"]),
            "sharesOutstanding": stat["sharesOutstanding"],
            "avg10Volume": stat["avg10Volume"],
            "ttmEPS":stat["ttmEPS"],
            "ttmDividendRate":stat["ttmDividendRate"],
            "dividendYield": stat["dividendYield"],
            "nextEarningsDate":stat["nextEarningsDate"]
        }
    except (KeyError, TypeError, ValueError):
        return None



def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
