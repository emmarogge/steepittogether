import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from flask_wtf.file import FileField, FileRequired
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, coming_soon
from datetime import datetime

# Env Vars
UPLOAD_FOLDER = os.path.join('static', 'photos')

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["IMAGE_UPLOADS"] = UPLOAD_FOLDER
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["JPEG", "JPG", "PNG"]

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///teatime.db")

@app.route("/")
@login_required
def index():
    """Show collection of teas"""
    _items = get_teas_by_user()
    print("_items: {}".format(_items))
    return render_template("collection.html", items=_items)

@app.route("/input_tea", methods=["GET", "POST"])
@login_required
def input_tea():
    """Add information about tea to user's collection"""
    if request.method == "POST":
        # Get information input by the user.
        _preparation = request.form.get("preparation")
        _amount = request.form.get("amount")
        _brand = request.form.get("brand")
        _name = request.form.get("name")
        _type = request.form.get("type")
        _price = request.form.get("price")
        _location = request.form.get("location")
        _notes = "" #TODO: Allow user to input notes!

        # Get current date and time
        now = datetime.now()
        _time = datetime.strftime(now, "%I:%M %p")
        _date = datetime.strftime(now, "%m/%d/%Y")
        print("date: {} time {} \n".format(_date, _time))

        transaction_id = db.execute("INSERT INTO transactions (user_id, name, brand, type, preparation, amount, price, location, curr_date, curr_time) VALUES (:user_id, :name, :brand, :type, :preparation, :amount, :price, :location, :curr_date, :curr_time)", \
            user_id=session["user_id"], name=_name, brand=_brand, type=_type, preparation=_preparation, amount=_amount, price=_price, location=_location, curr_date=_date, curr_time=_time);

        print("Transaction: {} \n".format(transaction_id))

        if ((_preparation == "Loose Leaf") or (_preparation == "Matcha Powder")):
            unit = "ounce(s) of"
        elif (_preparation == "Tea Bags"):
            unit = "bag(s) of"
        else:
            unit = " "
        if (not (_brand == "" and _name == "")):
            congrats = "{} {} {} {} have been added to your collection."
            _message = congrats.format(_amount, unit, _brand, _name)
        else:
            _message = ""
        return render_template("input_tea.html", message=_message)

    else:
        return render_template("input_tea.html", message="")


@app.route("/log", methods=["GET", "POST"])
@login_required
def log():
    """Decrement amount of tea by one serving"""
    _items = get_teas_by_user()
    if request.method == "POST":
        # Get form input
        vars = request.form.get("tea-select").split("_");
        _owned = float(vars[0])
        _brand = vars[1]
        _name = vars[2]
        _notes = request.form.get("notes")
        _amt = float(request.form.get("amount"))
        info = get_tea_by_brand_and_name(_brand, _name)[0]

        # Get current date and time
        now = datetime.now()
        _time = datetime.strftime(now, "%I:%M %p")
        _date = datetime.strftime(now, "%m/%d/%Y")
        print("date: {} time {} \n".format(_date, _time))

        # Handle photo upload
        if request.files:
            image = request.files["photo"]
            image_addr = os.path.join(app.config["IMAGE_UPLOADS"], image.filename)
            image.save(image_addr)
            print("Image saved @ {}\n".format(image_addr))
        else:
            image_addr = ""

        if (_owned >= _amt):
            # Update db to reflect tea consumption.
            _transaction_id = db.execute("INSERT INTO transactions (user_id, name, brand, type, preparation, amount, curr_date, curr_time) VALUES (:user_id, :name, :brand, :type, :preparation, :amount, :curr_date, :curr_time)",
                user_id=session['user_id'], name=_name, brand=_brand, type=info['type'], amount=-float(_amt), preparation=info['preparation'], curr_date=_date, curr_time=_time)
            _log_id = db.execute("INSERT INTO logs (user_id, transaction_id, amount, notes, photopath, curr_date, curr_time) VALUES (:user_id, :transaction_id, :amount, :notes, :photopath, :curr_date, :curr_time)", \
                user_id=session['user_id'], transaction_id = _transaction_id, amount=float(_amt), notes=_notes, photopath=image_addr, curr_date=_date, curr_time=_time)
        return redirect("/")

    else:
        return render_template("log.html", items=_items)


@app.route("/journal", methods=["GET"])
@login_required
def journal():
    """Show history of tea interactions"""
    _logs = db.execute("SELECT * FROM logs JOIN transactions ON transactions.transaction_id = logs.transaction_id  WHERE logs.user_id=:user_id", user_id=session['user_id'])
    _notes = db.execute("SELECT logs.notes FROM logs JOIN transactions ON transactions.transaction_id = logs.transaction_id  WHERE logs.user_id=:user_id", user_id=session['user_id'])
    note_list = [x['notes'] for x in _notes]
    for index, l in enumerate(_logs):
        l['note'] = note_list[index]
    return render_template("journal.html", logs=_logs)


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/reminder", methods=["GET", "POST"])
@login_required
def quote():
    """Get reminders when you should refill your favorite teas."""
    return coming_soon()


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Validate the username has not been allocated already.
        exists = db.execute("SELECT EXISTS(SELECT * FROM users WHERE username = :username)", username=request.form.get("username"));
        if exists == 1:
            print("Username already exists")
        else:
            print("Username is fresh")
        if (exists != 1):
            # Validate agreement of password and confirmation.
            password_agreement = (request.form.get("password") == request.form.get("confirmation"))
            if (request.form.get("username") != None) and password_agreement:
                _username = request.form.get("username")
                print("USERNAME: {}".format(request.form.get("username")))
                rows = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get("username"), hash=generate_password_hash(request.form.get("password")))
                _message = "Congratulations, {}!\n Your account has been registered successfully.".format(request.form.get("username"))
                return render_template("success.html", message=_message)
            else:
                return apology("Username cannot be null. Password and confirmation must match.")
        else:
            return apology("Username already in use. Choose another.")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/utilities", methods=["GET", "POST"])
@login_required
def utilities():
    """Provide tea utilities such as steeping timers and measurement tools"""
    return render_template("utilities.html")

@login_required
def get_teas_by_user():
    print("REFRESHING TEA COLLECTION!")
    teas_by_user = db.execute("SELECT SUM(transactions.amount) as 'amount', user_id, name, brand, type, preparation FROM transactions WHERE user_id=:user_id GROUP BY user_id, name, brand, type, preparation", \
        user_id=session['user_id'])
    print(teas_by_user)
    return teas_by_user

@login_required
def get_tea_by_brand_and_name(_brand, _name):
    print("Getting {} {} from TEA COLLECTION!")
    teas_by_user = db.execute("SELECT * FROM (SELECT SUM(transactions.amount) as 'amount', user_id, name, brand, type, preparation FROM transactions WHERE user_id=:user_id GROUP BY user_id, name, brand, type, preparation) WHERE brand=:brand AND name=:name", \
        user_id=session['user_id'], brand=_brand, name=_name)
    return teas_by_user

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


app.run(host='0.0.0.0', debug=True, port=5000)
