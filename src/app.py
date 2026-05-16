from flask import Flask, render_template, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = 'x' # dont change
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



@app.route("/")
def home():
    return render_template("main.html")