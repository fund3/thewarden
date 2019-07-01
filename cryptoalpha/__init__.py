import logging
import os
import datetime
from logging.handlers import RotatingFileHandler

# DEBUG: Detailed information, typically of interest only when diagnosing
# problems.
# INFO: Confirmation that things are working as expected.
# WARNING: An indication that something unexpected happened, or indicative of
# some problem in the near future (e.g. ‘disk space low’). The software is
# still working as expected.
# ERROR: Due to a more serious problem, the software has not been able
# to perform some function.
# CRITICAL: A serious error, indicating that the program itself may be unable
# to continue running.
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from cryptoalpha.config import Config

# Check size of debug.log file if it exists
try:
    debugfile = os.stat("debug.log")
    maxsize = 1 * 1024 * 1024  # 1MB max size - increase if needed more history
    if debugfile.st_size > maxsize:
        print("Startup message: Debug File size is larger than maxsize")
        print("Moving into archive")
        # rename file to include archive time and date
        archive_file = (
            "debug_" + datetime.datetime.now().strftime("%I%M%p_on_%B_%d_%Y") + ".log"
        )
        archive_file = os.path.join("./debug_archive/", archive_file)
        os.rename("debug.log", archive_file)
except FileNotFoundError:
    pass


format_str = "%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s"
handler = RotatingFileHandler("debug.log", maxBytes=1 * 1024 * 1024, backupCount=2)
logging.basicConfig(filename="debug.log", level=logging.DEBUG, format=format_str)
handler.setFormatter(format_str)
logging.captureWarnings(True)


# Create the DB instance
logging.info("Initializing Database")
db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()

# If login required - go to login:
login_manager.login_view = "users.login"
# To display messages - info class (Bootstrap)
login_manager.login_message_category = "info"
logging.info("Starting main program...")

# CLS + Welcome
print("\033[1;32;40m")
for _ in range(50):
    print("")
print(
    """
\033[1;32;40m-----------------------------------------------------------------
  ____                  _        ____  _       _   _
 / ___|_ __ _   _ _ __ | |_ ___ | __ )| | ___ | |_| |_ ___ _ __
| |   | '__| | | | '_ \| __/ _ \|  _ \| |/ _ \| __| __/ _ \ '__|
| |___| |  | |_| | |_) | || (_) | |_) | | (_) | |_| ||  __/ |
 \____|_|   \__, | .__/ \__\___/|____/|_|\___/ \__|\__\___|_|
            |___/|_|

-----------------------------------------------------------------
               \033[1;37;40mPrivacy Focused Portfolio Tracker
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m
Application loaded...
You can access it at your browser
Just go to:
\033[1;32;40mhttp://127.0.0.1:5000/
\033[1;37;40mTO EXIT HIT CTRL+C a couple of times
You can minimize this window now...

\033[1;32;40m-----------------------------------------------------------------
\033[1;31;40m                  Always go for the red pill
\033[1;32;40m-----------------------------------------------------------------
\033[1;37;40m
"""
)


def create_app(config_class=Config):
    logging.info("[create_app] Started create_app function")
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from cryptoalpha.users.routes import users
    from cryptoalpha.transactions.routes import transactions
    from cryptoalpha.api.routes import api
    from cryptoalpha.portfolio.routes import portfolio
    from cryptoalpha.main.routes import main
    from cryptoalpha.errors.handlers import errors

    app.register_blueprint(users)
    app.register_blueprint(transactions)
    app.register_blueprint(api)
    app.register_blueprint(portfolio)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    return app
