import logging
import os
from datetime import datetime
import requests
import urllib.parse
from time import time
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from thewarden.config import Config
from sqlalchemy import MetaData


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create the empty instances
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
mail = Mail()
login_manager = LoginManager()

# Check size of debug.log file if it exists
try:
    debugfile = os.stat("debug.log")
    maxsize = 1 * 1024 * 1024  # 1MB max size - increase if needed more history
    if debugfile.st_size > maxsize:
        print("Startup message: Debug File size is larger than maxsize")
        print("Moving into archive")
        # rename file to include archive time and date
        archive_file = "debug_" + datetime.now().strftime("%I%M%p_on_%B_%d_%Y") + ".log"
        archive_file = os.path.join("./debug_archive/", archive_file)
        os.rename("debug.log", archive_file)
except FileNotFoundError:
    pass

format_str = "%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s"
handler = RotatingFileHandler("debug.log", maxBytes=1 * 1024 * 1024, backupCount=2)
logging.basicConfig(filename="debug.log", level=logging.DEBUG, format=format_str)
handler.setFormatter(format_str)
logging.captureWarnings(True)


# If login required - go to login:
login_manager.login_view = "users.login"
# To display messages - info class (Bootstrap)
login_manager.login_message_category = "info"
logging.info("Starting main program...")


# Tests if IP is being concealled by using Tor
# Returns Status, IPs (with and withour Tor) and Tor request delay
# This test should be run here. When put inside node.util
# it raised errors as node.util uses db that it's still not
# declared the first time Flask launches.
def test_tor():
    response = {}
    logging.info("Testing Tor")
    session = requests.session()
    try:
        time_before = time()  # Save Ping time to compare
        r = session.get("http://httpbin.org/ip")
        time_after = time()
        pre_proxy_ping = time_after - time_before
        pre_proxy = r.json()
    except:
        pre_proxy = pre_proxy_ping = "Connection Error"

    # Activate TOR proxies
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        time_before = time()  # Save Ping time to compare
        r = session.get("http://httpbin.org/ip")
        time_after = time()
        post_proxy_ping = time_after - time_before
        post_proxy_difference = post_proxy_ping / pre_proxy_ping
        post_proxy = r.json()

        if pre_proxy["origin"] != post_proxy["origin"]:
            logging.info("Tor seems to be enabled")
            response = {
                "pre_proxy": pre_proxy,
                "post_proxy": post_proxy,
                "post_proxy_ping": "{0:.2f} seconds".format(post_proxy_ping),
                "pre_proxy_ping": "{0:.2f} seconds".format(pre_proxy_ping),
                "difference": "{0:.2f}".format(post_proxy_difference),
                "status": True,
            }

            return response
    except:
        post_proxy_ping = post_proxy = "Failed checking TOR status"

    response = {
        "pre_proxy": pre_proxy,
        "post_proxy": post_proxy,
        "post_proxy_ping": post_proxy_ping,
        "pre_proxy_ping": pre_proxy_ping,
        "difference": "-",
        "status": False,
    }
    logging.warn("Tor seems disabled! Check your Tor connection.")
    return response


# Store TOR Status here to avoid having to check on all http requests
tor_test = test_tor()
TOR = tor_test

# Application Factory
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    from thewarden.users.routes import users
    from thewarden.transactions.routes import transactions
    from thewarden.api.routes import api
    from thewarden.portfolio.routes import portfolio
    from thewarden.main.routes import main
    from thewarden.errors.handlers import errors
    from thewarden.node.routes import node

    app.register_blueprint(users)
    app.register_blueprint(transactions)
    app.register_blueprint(api)
    app.register_blueprint(portfolio)
    app.register_blueprint(main)
    app.register_blueprint(errors)
    app.register_blueprint(node)

    # Jinja2 filter to format time to a nice string
    @app.template_filter()
    # Formating function, takes self +
    # number of decimal places + a divisor
    def jformat(n, places, divisor=1):
        if n is None:
            return "-"
        else:
            try:
                n = float(n)
                n = n / divisor
                if n == 0:
                    return "-"
            except ValueError:
                return "-"
            try:
                form_string = "{0:,.{prec}f}".format(n, prec=places)
                return form_string
            except (ValueError, KeyError):
                return "-"

    @app.template_filter()
    def jencode(url):
        return urllib.parse.quote_plus(url)

    @app.template_filter()
    def epoch(epoch):
        time_r = datetime.fromtimestamp(epoch).strftime("%m-%d-%Y (%H:%M)")
        return time_r

    @app.template_filter()
    def time_ago(time=False):
        if type(time) is str:
            try:
                time = int(time)
            except TypeError:
                return ""
        now = datetime.now()
        if type(time) is int:
            diff = now - datetime.fromtimestamp(time)
        elif isinstance(time, datetime):
            diff = now - time
        elif not time:
            diff = now - now
        else:
            return ("")
        second_diff = diff.seconds
        day_diff = diff.days

        if day_diff < 0:
            return ""

        if day_diff == 0:
            if second_diff < 10:
                return "Just Now"
            if second_diff < 60:
                return str(int(second_diff)) + " seconds ago"
            if second_diff < 120:
                return "a minute ago"
            if second_diff < 3600:
                return str(int(second_diff / 60)) + " minutes ago"
            if second_diff < 7200:
                return "an hour ago"
            if second_diff < 86400:
                return str(int(second_diff / 3600)) + " hours ago"
        if day_diff == 1:
            return "Yesterday"
        if day_diff < 7:
            return str(int(day_diff)) + " days ago"
        if day_diff < 31:
            return str(int(day_diff / 7)) + " weeks ago"
        if day_diff < 365:
            return str(int(day_diff / 30)) + " months ago"
        return str(int(day_diff / 365)) + " years ago"

    return app

