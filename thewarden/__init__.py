import logging
import os
import json
from datetime import datetime
import urllib.parse
import webbrowser
import platform
from time import time
import requests

from flask import Flask, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from logging.handlers import RotatingFileHandler
from sqlalchemy import MetaData
from thewarden.config import Config

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
    maxsize = 5 * 1024 * 1024  # 5MB max size - increase if needed more history
    if debugfile.st_size > maxsize:
        print("Startup message: Debug File size is larger than maxsize")
        print("Moving into archive")
        # rename file to include archive time and date
        archive_file = "debug_" + datetime.now().strftime(
            "%I%M%p_on_%B_%d_%Y") + ".log"
        archive_file = os.path.join("./debug_archive/", archive_file)
        os.rename("debug.log", archive_file)
except FileNotFoundError:
    pass

format_str = "%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s"
handler = RotatingFileHandler("debug.log",
                              maxBytes=1 * 1024 * 1024,
                              backupCount=2)
logging.basicConfig(filename="debug.log",
                    level=logging.DEBUG,
                    format=format_str)
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
    except Exception:
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
    except Exception:
        post_proxy_ping = post_proxy = "Failed checking TOR status"

    response = {
        "pre_proxy": pre_proxy,
        "post_proxy": post_proxy,
        "post_proxy_ping": post_proxy_ping,
        "pre_proxy_ping": pre_proxy_ping,
        "difference": "-",
        "status": False,
    }
    logging.warning("Tor seems disabled! Check your Tor connection.")
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

    # This will run only once at the first request
    @app.before_first_request
    def before_first_request():
        if current_user.is_authenticated:
            from thewarden.users.utils import fx_list
            fx = fx_list()
            found = [item for item in fx if current_user.image_file in item]
            if found == []:
                current_user.image_file = "USD"
                db.session.commit()
                flash("No currency found for portfolio. Defaulted to USD.",
                      "warning")
            # Try to open the WARden URL - only when not in development mode
            # In development mode this is disabled otherwise a page reloads
            # on every code change and save if Flask is running.
            if Config.WARDEN_STATUS != 'developer':
                try:
                    os_platform = platform.system()
                    url = "http://127.0.0.1:5000/"
                    if os_platform == 'Darwin':
                        chrome_path = "open -a /Applications/Google\ Chrome.app %s"
                    elif os_platform == 'Windows':
                        chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'
                    elif os_platform == 'Linux':
                        chrome_path = '/usr/bin/google-chrome %s'

                    webbrowser.get(chrome_path).open(url)

                except Exception:
                    pass

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
    def fxsymbol(fx, output='symbol'):
        # Gets an FX 3 letter symbol and returns the HTML symbol
        # Sample outputs are:
        # "EUR": {
        # "symbol": "€",
        # "name": "Euro",
        # "symbol_native": "€",
        # "decimal_digits": 2,
        # "rounding": 0,
        # "code": "EUR",
        # "name_plural": "euros"
        try:
            with open('thewarden/static/json_files/currency.json') as fx_json:
                fx_list = json.load(fx_json, encoding='utf-8')
            out = fx_list[fx][output]
        except Exception:
            out = fx

        return (out)

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
