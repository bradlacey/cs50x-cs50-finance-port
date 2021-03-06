from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from passlib.apps import custom_app_context as pwd_context
from passlib.context import CryptContext
from tempfile import mkdtemp
from sqlalchemy import and_

# why wouldn;t tbis just be 'import helpers'?
from decimal import *
from helpers import *

import datetime
import os
import time

# configure application
app = Flask(__name__)

# added from "Publishing Your Flask App to the Web (PYFAW)"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # bug-fixing (test)
    hash = db.Column(db.String(120), nullable=False)
    # hash = db.Column(db.String, nullable=False)
    cash = db.Column(db.Numeric, default=10000, nullable=False)

    def __init__(self, email, username, hash):
        self.email = email
        self.username = username
        self.hash = hash

class History(db.Model):
    uid = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, nullable=False)
    ps_price = db.Column(db.Numeric, nullable=False)
    quantity = db.Column(db.Integer, unique=False, nullable=False)
    stock = db.Column(db.String(80), unique=False, nullable=False)
    transaction_type = db.Column(db.String(12), unique=False, nullable=False)

    def __init__(self, id, timestamp, ps_price, quantity, stock, transaction_type):
        self.id = id
        self.timestamp = timestamp
        self.ps_price = ps_price
        self.quantity = quantity
        self.stock = stock
        self.transaction_type = transaction_type

class Portfolio(db.Model):
    uid = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, unique=False, nullable=False)
    stock = db.Column(db.String(80), unique=True, nullable=False)
    symbol = db.Column(db.String(80), unique=True, nullable=False)

    def __init__(self, id, quantity, stock, symbol):
        self.id = id
        self.quantity = quantity
        self.stock = stock
        self.symbol = symbol

# ensure responses aren't cached # so that we get fresh data every time
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# global (why?)
stock_names = []

@app.route("/")
@login_required
def index():
    id = session.get("user_id")
    grand_total = 0.0
    portfolio = 0.0


    # debugging
    # source: https://stackoverflow.com/questions/16947276/flask-sqlalchemy-iterate-column-values-on-a-single-row
    stock = Users.query.filter_by(id = id).first()
    stocks = Users.query.filter_by(id = id).all()

    # update grand total
    # grand_total = round(portfolio, 2) + round(cash, 2)
    username = "friend"
    return render_template("index.html", username = username) #, balance = usd(round(cash, 2)), grand_total = usd(round(grand_total, 2)), portfolio = usd(round(portfolio, 2)), stocks = stocks)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    id = session.get("user_id") # id = session['user_id']

    if request.method == "POST":
        # ensure old password was submitted
        if not request.form.get("password_old"):
            return apology("you must provide your old password")

        # ensure new password was submitted
        if not request.form.get("password"):
            return apology("you must provide a new password")

        # ensure new password was submitted twice
        if not request.form.get("password_confirmed"):
            return apology("you must provide your new password twice")

        # ensure new passwords match
        if request.form.get("password") != request.form.get("password_confirmed"):
            # nothin'
        # else:
            return apology("the new passwords do not match")

        # raw SQL
        # rows = db.execute("SELECT cash, hash, username FROM users WHERE id = :id", id = id)
        # ORM
        rows = Users.query.get(id)

        username = rows.username
        cash = round(rows.cash, 2)

        # for item in rows:
        #     hash = item.hash
        hash = rows.hash

        # ensure username exists and password is correct
        # if len(rows) != 1 or not pwd_context.verify(request.form.get("password_old"), rows[0]["hash"]):
        if rows is None:
            return apology("None [username not found]")
        if not pwd_context.verify(request.form.get("password_old"), hash):
            return apology()
            return apology("you have entered your old password incorrectly")

        # encrypt and write new password to database
        hash = pwd_context.hash(request.form.get("password"))
        user = Users.query.get(id)
        user.hash = hash
        db.session.commit()

        # return apology(str(hash))
        return render_template("account.html", username = username)

    else:
        # CONTENT
        # raw SQL
        # rows = db.execute("SELECT username FROM users WHERE id = :id", id = id)
        rows = Users.query.get(id)

        # username = rows.username
        return render_template("account.html", username = rows.username)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""

    id = session.get("user_id")
    if id == None:
        return apology("please log in")
    if request.method == "POST":
        # get stock request from user; look up price
        stock = request.form.get("stock")
        stock = stock.upper()
        information = lookup(stock)

        if not request.form.get("quantity"):
            return apology("there was an error with the quantity entered. Please try again")
        quantity = int(request.form.get("quantity"))
        total_owned = 0
        transaction_type = "purchase"

        rows = Users.query.get(id)
        cash = round(rows.cash, 2)
        # ensure valid submission
        if stock == None:
            return apology("you must provide a valid stock symbol (sometimes this error appears inadvertently!)")
        # ensure quantity is valid
        if quantity == None or quantity <= 0:
            return apology("you must provide a valid quantity")
        # ensure stock code / lookup is valid
        if information == None:
            return apology("something happened! Please try again")
        # set values from received
        # stock_name = information['name']
        ps_price = round(information['price'], 2)
        symbol = information['symbol']
        cost = round(float(ps_price) * float(quantity), 2)

        # check that the user can afford the quantity requested
        if cost > cash:
            return apology("your account balance is too low for your intended purchase")

        # subtract money from account
        user = Users.query.get(id)
        user.cash = round(Decimal(user.cash) - Decimal(cost), 2)
        cash = round(Decimal(user.cash) - Decimal(cost), 2)
        db.session.commit()

        test = Portfolio.query.filter_by(id = id, symbol = symbol).first()

        if test is None:
            # raw SQL
            # db.execute("INSERT INTO portfolio (id, quantity, stock, symbol) VALUES (:id, :quantity, :stock_name, :symbol)", id = id, quantity = int(quantity), stock_name = stock_name, symbol = symbol)
            # ORM
            # debugging
            # quantity is not updating...
            new_entry = Portfolio(id = id, quantity = quantity, stock = stock, symbol = symbol)
            db.session.add(new_entry)
            db.session.commit()
        # else, if it's there
        else:
            # raw SQL
            # db.execute("UPDATE portfolio SET quantity = quantity + :quantity WHERE id = :id AND stock = :stock_name AND symbol = :symbol", quantity = int(quantity), id = id, stock_name = stock_name, symbol = symbol)
            # Flask-SQLAlchemy
            update = Portfolio.query.filter_by(id = id, stock = stock).first()
            # new_entry.quantity = new_entry.quantity + quantity
            update.quantity += quantity
            db.session.commit()

        portfolio = 0.0
        grand_total = 0.0

        timestamp = '{date:%Y.%m.%d_%H:%M:%S}'.format(date=datetime.datetime.now())
        # debugging
        # return apology(timestamp)

        # update history
        update = History(id = id, timestamp = timestamp, ps_price = ps_price, quantity = quantity, stock = stock, transaction_type = transaction_type)
        db.session.add(update)
        db.session.commit()


        # populate list of (dicts of) all stocks / quantity owned by current user
        stocks = Portfolio.query.filter_by(id = id).all()

        # get current prices
        current_prices = {}
        portfolio = 0.0

        # TO DO
        # this is code that is duplicated later; it needs to be a function
        for stock in stocks:
            #
            temp = lookup(stock.symbol)
            # stock.symbol = temp['symbol']
            # stock.stock_name = temp['name']
            # stock.value = round(stock.current_price, 2) * round(float(stock.quantity), 2)
            # update portfolio for grand_total
            if temp is None:
                # would skipping past or retrying on error be better UX (instead of halting completely)?
                return apology("an error occurred when retrieving the price. Please try again")
            portfolio += round(temp['price'] * stock.quantity, 2)

        # update grand total
        grand_total = round(Decimal(portfolio) + Decimal(cash), 2)

        # variable to control index.html
        buying = True

        # return redirect(url_for("index")) #, balance = usd(round(cash, 2)), buying = buying, cost = usd(round(cost, 2)), grand_total = usd(round(grand_total, 2)), portfolio = usd(round(portfolio, 2)), quantity = int(quantity), stocks = stocks, symbol = symbol, total_owned = total_owned, transaction_type = transaction_type)
        return render_template("index.html", balance = usd(round(cash, 2)), buying = buying, cost = usd(round(cost, 2)), current_prices = current_prices, grand_total = usd(grand_total), portfolio = usd(portfolio), quantity = int(quantity), stocks = stocks, symbol = symbol, total_owned = total_owned, transaction_type = transaction_type)

    # load page as normal
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions."""

    id = session.get("user_id") # id = session['user_id']
    # use distinct so that rows contains no duplicates
    rows = History.query.filter_by(id = id).all()
    stocks = History.query.filter_by(id = id).all()
    current_prices = {}

    if stocks is None:
        return apology("there's nothing to show here yet")
    for stock in stocks:
        # debugging
        # return apology(str(type(stock)) + ' ' + str(stock) + ' ' + str(stock.stock))
        # => Sorry, <class 'application.History'> <History 8> SNAP.
        temp = lookup(stock.stock)
        if temp is None:
            # would skipping past or retrying on error be better UX (instead of halting completely)?
            return apology("an error occurred when retrieving prices. Please try again")
        # return apology(str(type(current_prices)) + ' ' + str())   # dict
        current_prices[stock.stock] = temp['price'] # usd(round(temp['price'], 2))

    """
    # from before

    # populate list of (dicts of) all stocks / quantity owned by current user
    stocks = Portfolio.query.filter_by(id = id).all()

    # get current current prices
    current_price = {}

    for stock in stocks:
        # make ...
        temp = lookup(stock.symbol)
        current_price[stock.symbol] = temp['price']
        stock.symbol = temp['symbol']
        # stock.stock_name = temp['name']
        # stock.value = round(stock.current_price, 2) * round(float(stock.quantity), 2)
        # update grand_total
        # won't I need to do something else with this portfolio variable?
        portfolio += round(stock.value, 2)
        # unneeded?
        # stock.current_price = usd(round(float(stock.current_price), 2))
        # I don't think this ecen exists
        # stock.value = usd(round(stock.value, 2))
        # update total_owned
        stock.quantity += stock.quantity
        # db.session.commit()
    """

    # replacing this--
    """
    for row in rows:
        row['ps_price'] = usd(float(format(round(row['ps_price'], 2), '.2f')))
    """
    # --with this:
    for stock in stocks:
        stock.ps_price = usd(float(format(round(stock.ps_price, 2), '.2f')))

    return render_template("history.html", rows = rows,  current_prices = current_prices)
    # if error:
    return apology("there was an unknown error [0x02]")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("you must provide a valid username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("the password you provided was incorrect")

        username = request.form.get("username")
        rows = Users.query.filter_by(username = username)

        # ensure username exists and password is correct
        # debugging


        for item in rows:
            hash = item.hash
            id = item.id


        # hash = rows.hash
        # id = rows.id

        # if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
        if rows is None or not pwd_context.verify(request.form.get("password"), hash):
            return apology("invalid username and/or password")

        # remember which user has logged in
        # debugging
        # session["user_id"] = rows[0]["id"]
        session["user_id"] = id

        # redirect user to home page
        return render_template("index.html", username = username)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/password_reset", methods=["GET", "POST"])
def password_reset():

    id = session.get("user_id") # id = session['user_id']

    if request.method == "POST":

        return apology("there was an unknown error [0x02]")

    else:
        return render_template("password_reset.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    id = session.get("user_id") # id = session['user_id']

    # WT: For quote we have three to-dos

    # WT: display the form for the user to look up the stock

    # WT: retrieve the quote for the stock

    # WT: display the current price for the stock

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        stock = request.form.get("stock")
        # ensure stock was submitted
        if stock == None:
            return apology("you must provide a stock to look up")

        information = lookup(stock)

        # ensure stock code is valid
        if information == None:
            return apology("you must provide a valid stock symbol")
        else:
            # set values from received
            # name = information[row[1]] # name
            name = information['name']
            # price = information[price]
            ps_price = information['price']
            # symbol = information[row[0].upper()] # symbol
            symbol = information['symbol']

            # print(name, price, symbol)

        # return redirect("http://www.google.com")


        # do I need to do this?
        # WT:
        # "when we call render_template() we're allowed to pass in values"
        # return render_template(url_for('quoted')) # , name = name, price = price, symbol = symbol)
        # return redirect("/quoted.html") # , name = name, price = price, symbol = symbol)
        return render_template("quoted.html", name = name, ps_price = ps_price, symbol = symbol)

    # else if user reached route via GET (as by clicking a link or via redirect)
    # When a user visits /quote via GET, render one of those templates, inside of
    # which should be an HTML form that submits to /quote via POST.
    else:
        return render_template("quote.html")  # , name = name, price = price, symbol = symbol)


    return apology("no stock with the code you entered exists")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("you must provide a username")

        # ensure email address was submitted
        if not request.form.get("email"):
            return apology("you must provide an email address")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("you must provide a password")

        # ensure second password was submitted
        elif not request.form.get("password_confirmed"):
            return apology("you must enter your password twice")

        # is this the same as what I do with the SQL code above?
        # registrant = Registrant(request.form["username"], request.form["password"])
        # "this adds to [your] database session so to speak" ...okay
        # db.session.add(user)
        # db.session.commit()

        # ensure password is correct
        # not working for unknown reasons so...
        # if (pwd_context.verify(request.form.get("password"), request.form.get("password_confirmed"), user=request.form.get("username"))) == False:
        if request.form.get("password") != request.form.get("password_confirmed"):
            # nothin'
        # else:
            return apology("the passwords you entered do not match")

        # encrypt password (how secure is this?)
        # this one is from the WT
        hash = pwd_context.hash(request.form.get("password"))
        result = Users(request.form.get("email"), request.form.get("username"), hash)
        db.session.add(result)
        db.session.commit()
        if not result:
            return apology("that username is taken")

        # DO WE NEED THIS?
        new_entry = Users(request.form.get("email"), request.form.get("username"), hash)
        db.session.add(new_entry)
        db.session.commit()

        # remember which user has been created and is logged in
        session['user_id'] = result

        # redirect user to home page
        return render_template("success.html", username = request.form.get("username"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""

    id = session.get("user_id") # id = session['user_id']
    transaction_type = "sale"

    if request.method == "POST":

        # get stock request from user; look up price
        # could this just be request.form.get("stock").upper() ?
        stock = request.form.get("stock")
        stock = stock.upper()
        quantity = request.form.get("quantity")
        quantity_on_hand = 0
        information = lookup(stock)

        # debugging
        # return apology(str(type(information)))
        # since the above returns "class 'dict'" the
        # "string indices must be integers" TypeErrors
        # are a mystery to me (and they seem to have
        # stopped as mysteriously as they began)


        if id == None:
            """
            i = 0
            for value in session.values():
                session_thing[i] = value
                i += 1
            """
            return apology("please log in")

        # rows_user = Users.query.filter_by(id = id).all()
        rows_user = Users.query.get(id)
        # rows_portfolio = Portfolio.query.filter_by(id = id, symbol = stock).all()
        rows_portfolio = Portfolio.query.filter_by(id = id, symbol = stock).first()
        # cash = round(rows_user[0]['cash'], 2)
        cash = rows_user.cash
        # quantity_on_hand = rows_portfolio[0]['quantity']
        quantity_on_hand = rows_portfolio.quantity

        # ensure stock was submitted
        if stock == None:
            return apology("you must provide a valid stock symbol")
        if quantity == None:
            return apology("you must provide a valid quantity [0x01]")
        # return apology(str(transaction_type(quantity)))
        quantity = int(quantity)
        if quantity == None or quantity <= 0:
            return apology("you must provide a valid quantity [0x02]")
        if information == None:
            return apology("an error occurred when retrieving the price. Please try again")

        # set values from received
        name = information['name']
        ps_price = round(information['price'], 2)
        symbol = information['symbol']

        sale_value = round(Decimal(ps_price) * Decimal(quantity), 2)

        # error check
        if quantity_on_hand == None:
            return apology("an unknown error has occurred [0x03]. Please try again")
        # check that the user has enough of the stock to sell
        if quantity > quantity_on_hand:
            return apology(str(quantity) + " " + str(quantity_on_hand) + " " + "you cannot sell that which you do not own")

        # add cash back to user
        user = Users.query.get(id)
        user.cash = user.cash + sale_value
        db.session.commit()

        cash += round(sale_value, 2)

        # remove shares from user's portfolio
        # rows = Portfolio.query.filter_by(id = id, stock = stock).all()
        rows = Portfolio.query.filter_by(id = id, stock = stock).first()
        rows.quantity = rows.quantity - quantity
        db.session.commit()

        portfolio = 0.0
        grand_total = 0.0

        timestamp = '{date:%Y.%m.%d_%H:%M:%S}'.format(date=datetime.datetime.now())

        # update history
        new_entry = History(id = id, timestamp = timestamp, ps_price = ps_price, quantity = quantity, stock = name, transaction_type = transaction_type)
        db.session.add(new_entry)
        db.session.commit()

        # populate list of (dicts of) all stocks / quantity owned by current user
        stocks = Portfolio.query.filter_by(id = id).all()

        # TO DO
        # this is code that is duplicated earlier; it needs to be a function
        for stock in stocks:
            temp = lookup(stock.symbol)
            if not temp:
                return apology("there was an error looking up the price. Please try again")
            portfolio += round(temp['price'] * stock.quantity, 2)

        # update grand total
        grand_total = round(Decimal(portfolio) + Decimal(cash), 2)

        # variable to control index.html
        selling = True

        return render_template("index.html", balance = usd(cash), cost = usd(sale_value), grand_total = usd(grand_total), portfolio = usd(portfolio), quantity = quantity, timestamp = timestamp, selling = selling, stocks = stocks, symbol = symbol)

    # else if GET: load page as normal
    else:
        return render_template("sell.html")


@app.route("/success")
def success():
    """Declare registration success."""

    id = session.get("user_id") # id = session['user_id']

    return render_template("success.html")
