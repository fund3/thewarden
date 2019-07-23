import os

# Config class for Application Factory
class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "alpha.db")

    # You should change this secret key. But make sure it's done before any data
    # is included in the database
    SECRET_KEY = "24feff264ec3bbdb1bad4affc7bd68f4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Used for password recovery. Not needed in most cases.
    MAIL_SERVER = "smtp.googlemail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("EMAIL_USER")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    DOJO_SETTINGS = None
