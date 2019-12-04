import datetime
import os
import random
import smtplib

from cs50 import SQL
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from flask_session import Session
from flask_wtf.file import FileField, FileRequired
from helpers import apology, login_required, coming_soon
from itsdangerous import URLSafeTimedSerializer
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


# Env Vars
UPLOAD_FOLDER = os.path.join('static', 'photos')

# Configure application
app = Flask(__name__)

# Load the configuration from the instance folder
app.config.from_pyfile('instance/config.py')

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Set up folder for uploading images
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

ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])
Session(app)

# Set up mail instance
mail = Mail(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///teatime.db")

@app.route("/")
@login_required
def index():
    """Show collection of teas"""
    _items = get_teas_by_user()
    print("_items: {}".format(_items))
    return render_template("collection.html", items=_items)

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = ts.loads(token, salt="email-confirm-key", max_age=86400)
    except:
        return redirect(url_for("login"))

    # Set user email confirmed in the database.
    rows = db.execute("update users set email_confirmed=true where email=:email", email)

    # Update session variables to store information about logged-in user.
    session["user_id"] = rows[0]["id"]
    session["email"] = rows[0]["email"]
    session["username"] = rows[0]["username"]
    return redirect(url_for('login'))

@app.route("/feed", methods=["GET"])
@login_required
def feed():
    """Show history of tea interactions"""
    _logs = db.execute("SELECT users.username, transactions.curr_date, transactions.curr_time, transactions.brand, transactions.name, logs.photopath FROM logs JOIN transactions ON transactions.transaction_id = logs.transaction_id JOIN users ON users.id = transactions.user_id")
    _notes = db.execute("SELECT logs.notes FROM logs JOIN transactions ON transactions.transaction_id = logs.transaction_id JOIN users ON users.id=transactions.user_id")
    note_list = [x['notes'] for x in _notes]
    for index, l in enumerate(_logs):
        l['note'] = note_list[index]
    return render_template("feed.html", logs=_logs)

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

        # Get current date and time
        now = datetime.now()
        _time = datetime.strftime(now, "%I:%M %p")
        _date = datetime.strftime(now, "%m/%d/%Y")

        # Insert transaction information into database
        transaction_id = db.execute("INSERT INTO transactions (user_id, name, brand, type, preparation, amount, price, location, curr_date, curr_time) VALUES (:user_id, :name, :brand, :type, :preparation, :amount, :price, :location, :curr_date, :curr_time)", \
            user_id=session["user_id"], name=_name, brand=_brand, type=_type, preparation=_preparation, amount=_amount, price=_price, location=_location, curr_date=_date, curr_time=_time);

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
        if "photo" in request.files:
            image = request.files["photo"]
            if image.filename != "":
                image_addr = os.path.join(app.config["IMAGE_UPLOADS"], image.filename)
                print("image.filename: " + image.filename)
                image.save(image_addr)
                print("Image saved @ {}\n".format(image_addr))
            else:
                image_addr = ""
        else:
            image_addr = ""

        if (_owned >= _amt):
            # Update db to reflect tea consumption.
            _transaction_id = db.execute("INSERT INTO transactions (user_id, name, brand, type, preparation, amount, curr_date, curr_time) VALUES (:user_id, :name, :brand, :type, :preparation, :amount, :curr_date, :curr_time)",
                user_id=session['user_id'], name=_name, brand=_brand, type=info['type'], amount=-float(_amt), preparation=info['preparation'], curr_date=_date, curr_time=_time)

            if image_addr != "":
                _log_id = db.execute("INSERT INTO logs (user_id, transaction_id, amount, notes, photopath, curr_date, curr_time) VALUES (:user_id, :transaction_id, :amount, :notes, :photopath, :curr_date, :curr_time)", \
                    user_id=session['user_id'], transaction_id = _transaction_id, amount=float(_amt), notes=_notes, photopath=image_addr, curr_date=_date, curr_time=_time)
            else:
                random_bun = get_random_bun()
                print("RANDOM BUN: {}".format(random_bun))
                image_addr = os.path.join(app.config["IMAGE_UPLOADS"], random_bun)
                print("IMAGE ADDR: {}".format(image_addr))
                _log_id = db.execute("INSERT INTO logs (user_id, transaction_id, amount, notes, photopath, curr_date, curr_time) VALUES (:user_id, :transaction_id, :amount, :notes, :photopath, :curr_date, :curr_time)", \
                    user_id=session['user_id'], transaction_id = _transaction_id, amount=float(_amt), notes=_notes, photopath=image_addr, curr_date=_date, curr_time=_time)
        return redirect("/")
    else:
        return render_template("log.html", items=_items)

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
        session["email"] = rows[0]["email"]
        session["username"] = rows[0]["username"]

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

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Validate the username has not been allocated already.
        exists = db.execute("SELECT EXISTS(SELECT * FROM users WHERE username = :username)", username=request.form.get("username"));

        if (exists != 1):
            # Validate agreement of password and confirmation.
            password_agreement = (request.form.get("password") == request.form.get("confirmation"))
            if (request.form.get("username") != None) and password_agreement:
                # Insert new account information into users table
                _username = request.form.get("username")
                _email = request.form.get("email")
                rows = db.execute("INSERT INTO users (username, hash, email) VALUES(:username, :hash, :email)", \
                    username=_username, hash=generate_password_hash(request.form.get("password")), email=_email)

                # Send confirmation email with secret link
                subject = "Steep It Together account confirmation"
                token = ts.dumps(_email, salt="email-confirmation-key")
                confirm_url = "http://steepittogether.com/confirm/{}".format(token)
                html = render_template('confirmation.html', confirm_url=confirm_url)
                _message = "Congratulations, {}!\n Your account has been registered successfully.\n Check your email for a confirmation link.".format(_username)
                print(_message)
                send_email(_email, subject, html)
                # Render success message.
                return render_template("success.html", message=_message)
            else:
                return apology("Username cannot be null. Password and confirmation must match.")
        else:
            return apology("Username already in use. Choose another.")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route('/reset', methods=['GET','POST'])
def reset():
    if request.method == "POST":
        users = db.execute("select * from users where email=:email", email=request.form.get("email"))
        print("LEN OF USERS: {}".format(len(users)))
        _message = "No account matching that email address exists.\n Please try again."
        if len(users) == 0:
            return render_template("reset.html", message=_message)
        else:
            user = users[0]
            subject = "SteepItTogether: Password Reset Requested"
            token = ts.dumps(user['email'], salt='recover-password-key')

            reset_url = "http://steepittogether.com/reset/{}".format(token)
            print("reset_url: {}".format(reset_url))

            html = render_template('account-reset.html', reset_url=reset_url)
            send_email(user['email'], subject, html)

            _message = "Success! Check your email for the link to reset your account password."
            return render_template("success.html", message=_message)

    else:
        return render_template("reset.html")

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    if request.method == "POST":
        _email = ts.loads(token, salt='recover-password-key')
        db.execute("UPDATE users SET hash=:hash WHERE email=:email", hash=generate_password_hash(request.form.get("password")), email=_email)
        _message = "Congratulations! You've reset your password."
        return render_template("success.html", message=_message)
    else:
        return render_template("reset_with_token.html", token=token)

@app.route("/utilities", methods=["GET", "POST"])
@login_required
def utilities():
    """Provide tea utilities such as steeping timers and measurement tools"""
    return render_template("utilities.html")

@login_required
def get_teas_by_user():
    teas_by_user = db.execute("SELECT SUM(transactions.amount) as 'amount', user_id, name, brand, type, preparation FROM transactions WHERE user_id=:user_id GROUP BY user_id, name, brand, type, preparation", \
        user_id=session['user_id'])
    teas_in_stock = []
    for tea in teas_by_user:
        if tea['amount'] > 0:
            teas_in_stock.append(tea)
    return teas_in_stock

@login_required
def get_tea_by_brand_and_name(_brand, _name):
    teas_by_user = db.execute("SELECT * FROM (SELECT SUM(transactions.amount) as 'amount', user_id, name, brand, type, preparation FROM transactions WHERE user_id=:user_id GROUP BY user_id, name, brand, type, preparation) WHERE brand=:brand AND name=:name", \
        user_id=session['user_id'], brand=_brand, name=_name)
    return teas_by_user

def send_email(email, subject, html_message):
    sender_email = app.config['EMAIL_ADDRESS']
    sender_pw = escape(app.config['EMAIL_PASSWORD'])
    dest_email = email

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = dest_email
    body =  MIMEText(html_message, 'html')
    msg.attach(body)

    s = smtplib.SMTP_SSL('smtp.gmail.com')
    s.login(sender_email, sender_pw)

    s.sendmail(sender_email, dest_email, msg.as_string())
    print("EMAIL SENT\n")
    s.quit()

def get_random_bun():
    x = random.randint(6,23)
    return "buns_in_teacups/bun_in_teacup_{}.jpg".format(x)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


app.run(host='0.0.0.0', debug=True, port=5000)
