from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from passlib.context import CryptContext
from tempfile import mkdtemp

# why wouldn;t tbis just be 'import helpers'?
from decimal import *
from helpers import *

import time

# configure application
app = Flask(__name__)

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

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# global
stock_names = []

@app.route("/")
@login_required
def index():
    id = session.get("user_id")
    
    cash_in = db.execute("SELECT cash FROM users WHERE id = :id", id = id)
    cash = round(cash_in[0]['cash'], 2)
    grand_total = 0.0
    portfolio = 0.0
    stocks = db.execute("SELECT symbol, stock, quantity FROM portfolio WHERE id = :id", id = id)
    
    for stock in stocks:
        temp = lookup(stock['symbol'])
        stock['current_price'] = temp['price']
        stock['symbol'] = temp['symbol']
        stock['stock_name'] = temp['name']
        # make new 'value' key for each stock
        stock['value'] = round(stock['current_price'], 2) * round(float(stock['quantity']), 2)
        # update grand_total
        portfolio += round(stock['value'], 2)
        stock['current_price'] = usd(round(float(stock['current_price']), 2))
        stock['value'] = usd(round(stock['value'], 2))
    # update grand total
    grand_total = round(portfolio, 2) + round(cash, 2)
    return render_template("index.html", balance = usd(round(cash, 2)), grand_total = usd(round(grand_total, 2)), portfolio = usd(round(portfolio, 2)), stocks = stocks)

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    id = session.get("user_id") # id = session['user_id']
    
    if request.method == "POST":
        # ensure old password was submitted
        if not request.form.get("password"):
            return apology("must provide new password")
            
        # ensure new password was submitted
        if not request.form.get("password"):
            return apology("must provide new password")

        # ensure new password was submitted twice
        if not request.form.get("password_confirmed"):
            return apology("must provide new password twice")

        # ensure new passwords match
        if request.form.get("password") != request.form.get("password_confirmed"):
            # nothin'
        # else:
            return apology("new passwords do not match")
            
        rows = db.execute("SELECT cash, hash, username FROM users WHERE id = :id", id = id)
        username = rows[0]['username']
        cash = round(rows[0]['cash'], 2)
        
        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password_old"), rows[0]["hash"]):
            return apology("you have entered your old password incorrectly")

        # encrypt and write new password to database
        hash = pwd_context.hash(request.form.get("password"))
        db.execute("UPDATE users SET hash = :hash WHERE id = :id", hash = hash, id = id)
        # return apology(str(hash))
        return render_template("account.html", username = username)
        
    else:
        # CONTENT
        rows = db.execute("SELECT username FROM users WHERE id = :id", id = id)
        username = rows[0]['username']
        return render_template("account.html", username = username)

    
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
        
        quantity = request.form.get("quantity")
        total_owned = 0
        type = "purchase"
        
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id = id)
        cash = round(rows[0]['cash'], 2)
        # ensure valid submission
        if stock == None:
            return apology("must provide valid stock symbol")
        quantity = int(quantity)
        if quantity == None or quantity <= 0:
            return apology("must provide valid quantity")
        # ensure stock code is valid
        if information == None:
            return apology("must enter a valid stock symbol")
        # set values from received
        stock_name = information['name']
        price = round(information['price'], 2)
        symbol = information['symbol']
        cost = round(float(price), 2) * round(float(quantity), 2)
        
        # check that the user can afford the quantity requested
        if cost > cash:
            return apology("account balance too low for purchase")
        # subtract money from account
        # db.execute("UPDATE portfolio SET cash = cash - :cost WHERE id = :id")
        # remove the cost from our cash BOTH in the database and from our variable here
        db.execute("UPDATE users SET cash = cash - :cost WHERE id = :id", cost = round(cost, 2), id = id)
        cash -= round(cost, 2)
        test = db.execute("SELECT * FROM portfolio WHERE id = :id AND symbol = :symbol", id = id, symbol = symbol)
        if len(test) == 0:
            db.execute("INSERT INTO portfolio (id, quantity, stock, symbol) VALUES (:id, :quantity, :stock_name, :symbol)", id = id, quantity = int(quantity), stock_name = stock_name, symbol = symbol)        
        # else, if it's there
        else:
            db.execute("UPDATE portfolio SET quantity = quantity + :quantity WHERE id = :id AND stock = :stock_name AND symbol = :symbol", quantity = int(quantity), id = id, stock_name = stock_name, symbol = symbol)
        
        # populate list of (dicts of) all stocks / quantity owned by current user
        stocks = db.execute("SELECT symbol, stock, quantity FROM portfolio WHERE id = :id", id = id)
        
        portfolio = 0.0
        grand_total = 0.0
        
        
        # update history
        db.execute("INSERT INTO history (id, stock, quantity, purchase_price, type) VALUES (:id, :symbol, :quantity, :purchase_price, :type)", id = id, symbol = symbol, quantity = quantity, purchase_price = price, type = type)
        for stock in stocks:
            # make new 'current_price' key for each stock
            # return apology(stock['stock'])
            temp = lookup(stock['symbol'])
            stock['current_price'] = temp['price']
            stock['symbol'] = temp['symbol']
            stock['stock_name'] = temp['name']
            stock['value'] = round(stock['current_price'], 2) * round(float(stock['quantity']), 2)
            # update grand_total
            portfolio += round(stock['value'], 2)
            stock['current_price'] = usd(round(float(stock['current_price']), 2))
            stock['value'] = usd(round(stock['value'], 2))
            # update total_owned
            total_owned += stock['quantity']

        # debugging: we never get to this point
        # debugging: oop, we did just get to this point...
        # return apology("here?") 
        
        # update grand total
        grand_total = round(portfolio, 2) + round(cash, 2)
        
        # USD things
        # stock['current_price'] = usd(stock['current_price'])
        # stock['value'] = usd(stock['value'])
        
        
        # adjust user's cash holdings
        # ? ? ?
        # from here: https://stackoverflow.com/questions/6699360/flask-sqlalchemy-update-a-rows-information
        # user = users.query.get(5)
        # user.name = 'New 
        # db.session.commit()
        
        
        # return apology(str(cash))
        # return apology(usd(cash))

        # variable to control index.html
        buying = True
        
        # debugging: we never get to this point
        # return apology("here?") 
        # return redirect(url_for("index")) #, balance = usd(round(cash, 2)), buying = buying, cost = usd(round(cost, 2)), grand_total = usd(round(grand_total, 2)), portfolio = usd(round(portfolio, 2)), quantity = int(quantity), stocks = stocks, symbol = symbol, total_owned = total_owned, type = type)
        return render_template("index.html", balance = usd(round(cash, 2)), buying = buying, cost = usd(round(cost, 2)), grand_total = usd(round(grand_total, 2)), portfolio = usd(round(portfolio, 2)), quantity = int(quantity), stocks = stocks, symbol = symbol, total_owned = total_owned, type = type)
        
        
    # load page as normal
    else:
        return render_template("buy.html")
            
            
@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    
    id = session.get("user_id") # id = session['user_id']
    # use distinct so that rows contains no duplicates
    rows = db.execute("SELECT * FROM history WHERE id = :id", id = id)
    stocks = db.execute("SELECT DISTINCT stock FROM history WHERE id = :id", id = id)
    current_prices = {}
    
    # counter_if = 0
    # counter_el = 0
    
    for stock in stocks:
        temp = lookup(stock['stock'])
        current_prices[stock['stock']] = usd(float(format(round(temp['price'], 2), '.2f')))
        
    for row in rows:
        row['purchase_price'] = usd(float(format(round(row['purchase_price'], 2), '.2f')))
    
    return render_template("history.html", rows = rows,  current_prices = current_prices)
    # if error:
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        username = request.form.get("username")
        
        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username = username)

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
    
    # CONTENT
    id = session.get("user_id") # id = session['user_id']
    
    if request.method == "POST":
        
        # CONTENT
        return apology("soz")
        
    else:
        # CONTENT
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

        # set values from received
        # name = information.name
        # price = information.price
        # symbol = information.symbol     # stock should == symbol though, right?

        # print(name, price, symbol)
        
        
        
        stock = request.form.get("stock")
        
        # ensure stock was submitted
        if stock == None:
            return apology("must provide stock to look up")
        
        information = lookup(stock)
        
        # ensure stock code is valid
        if information == None:
            return apology("must provide a valid stock symbol")
        else:
            # set values from received
            # name = information[row[1]] # name
            name = information['name']
            # price = information[price]
            price = information['price']
            # symbol = information[row[0].upper()] # symbol
            symbol = information['symbol']
            
            # print(name, price, symbol)  

        # return redirect("http://www.google.com")
            

        # do I need to do this?
        # WT:
        # "when we call render_template() we're allowed to pass in values"
        # return render_template(url_for('quoted')) # , name = name, price = price, symbol = symbol)
        # return redirect("/quoted.html") # , name = name, price = price, symbol = symbol)
        return render_template("quoted.html", name = name, price = price, symbol = symbol)

    # else if user reached route via GET (as by clicking a link or via redirect)
    # When a user visits /quote via GET, render one of those templates, inside of
    # which should be an HTML form that submits to /quote via POST. 
    else:
        return render_template("quote.html")  # , name = name, price = price, symbol = symbol)
    
    
    return apology("no stock with the code ____ exists")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
        
        # ensure email address was submitted
        if not request.form.get("email"):
            return apology("must provide email address")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # ensure second password was submitted
        elif not request.form.get("password_confirmed"):
            return apology("must provide password twice")

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
            return apology("passwords do not match")

        # encrypt password (how secure is this?)
        # this one is from the WT
        hash = pwd_context.hash(request.form.get("password"))
        # crypt_obj = CryptContext(schemes = ["sha256_crypt", "md5_crypt", "des_crypt"], default="des_crypt")
        # hash = crypt_obj.hash(request.form.get("password"))
        # add new user to database / ensure username does not exist
        # this line won't work but the idea is right
        # if (request.form.get("username")) == db.execute("SELECT * FROM users WHERE username = :username", username = request.form.get("username")):
        # WT:
        # apparently this is the correct way:
        result = db.execute("INSERT INTO users (email, username, hash) VALUES (:email, :username, :hash)", email = request.form.get("email"), username = request.form.get("username"), hash = hash)
        if not result:
            return apology("username taken")
        # do I need this line? or will it actually already happen above? I think this actually is needed!
        # easy to test though
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username = request.form.get("username"), hash = hash)
        # na not this
        # rows = db.execute("INSERT INTO users (username, password) VALUES (:username, :password), username = request.form.get("username")), password = password)

        # remember which user has been created and is logged in
        # this can't be right!
        # session["user_id"] = "id"
        # debugging
        # return apology(str(result))
        # session['user_id'] = result[0]['id']
        session['user_id'] = result
        
        # redirect user to home page
        # TemplateNotFound error
        # return redirect(url_for("index"))
        # return render_template("index.html")
        # return redirect(url_for("success"))
        return render_template("success.html", username = request.form.get("username"))
        # return redirect(url_for("/")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
    

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    
    id = session.get("user_id") # id = session['user_id']
    type = "sale"

    if request.method == "POST":
            
        # get stock request from user; look up price
        stock = request.form.get("stock")
        stock = stock.upper()
        quantity = request.form.get("quantity")
        quantity_on_hand = 0
        information = lookup(stock)
        
        if id == None:
            """
            i = 0
            for value in session.values():
                session_thing[i] = value
                i += 1
            """
            return apology("Please Log In")

        rows_user = db.execute("SELECT cash FROM users WHERE id = :id", id = id)
        rows_portfolio = db.execute("SELECT * FROM portfolio WHERE id = :id AND symbol = :stock", id = id, stock = stock)
        cash = round(rows_user[0]['cash'], 2)
        # debugging
        # return apology(str(type(rows_portfolio)))
        quantity_on_hand = rows_portfolio[0]['quantity']
        
        
        
        # ensure stock was submitted
        if stock == None:
            return apology("must provide valid stock symbol")
        if quantity == None:
            return apology("must provide stock symbol and quantity to buy, stock tho: {}".format(stock))
        # return apology(str(type(quantity)))
        quantity = int(quantity)
        if quantity == None or quantity <= 0:
            return apology("must provide valid quantity")
        if information == None:
            return apology("must ender a valid stock symbol")

        # set values from received
        name = information['name']
        price = round(information['price'], 2)
        symbol = information['symbol']
        
        sale_value = round(float(price), 2) * round(float(quantity), 2)
        
        # check that the user has enough of the stock to sell
        if quantity > quantity_on_hand or quantity_on_hand == None:
            return apology("you cannot sell that which you do not own")

        # add cash back to user
        db.execute("UPDATE users SET cash = cash + :sale_value WHERE id = :id", sale_value = sale_value, id = id)
        cash += round(sale_value, 2)

        # remove shares from user's portfolio
        db.execute("UPDATE portfolio SET quantity = quantity - :quantity WHERE id = :id AND stock = :stock AND symbol = :symbol", quantity = int(quantity), id = id, stock = stock, symbol = symbol)
        
        # populate list of (dicts of) all stocks / quantity owned by current user
        stocks = db.execute("SELECT stock, quantity FROM portfolio WHERE id = :id", id = id)
        
        portfolio = 0.0
        grand_total = 0.0

        # update history
        db.execute("INSERT INTO history (id, purchase_price, quantity, stock, type) VALUES (:id, :purchase_price, :quantity, :name, :type)", id = id, purchase_price = price, quantity = quantity, name = name, type = type)

        # fill list so we can populate our HTML table
        for stock in stocks:
            # make new 'current_price' key for each stock
            temp = lookup(stock['stock'])
            stock['current_price'] = temp['price']
            stock['symbol'] = temp['symbol']
            stock['name'] = temp['name']
            
            # make new 'value' key for each stock
            stock['value'] = stock['current_price'] * float(stock['quantity'])
            
            # update grand_total
            portfolio += stock['value']
            stock['current_price'] = usd(stock['current_price'])
            stock['value'] = usd(stock['value'])

        # update grand total
        grand_total = portfolio + cash
        
        # variable to control index.html
        selling = True
        
        return render_template("index.html", balance = usd(cash), cost = usd(sale_value), grand_total = usd(grand_total), portfolio = usd(portfolio), quantity = quantity, selling = selling, stocks = stocks, symbol = symbol)
    
    # else if GET: load page as normal
    else:
        return render_template("sell.html")
    

@app.route("/success")
def success():
    """Declare registration success."""
    
    id = session.get("user_id") # id = session['user_id']

    return render_template("success.html")
