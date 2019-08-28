import os


# Config class for Application Factory
class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    # WARDEN_STATUS = "developer" will use a local database
    # To use this alternative DB, set the sql environment
    # variable below to point to your local
    #  sqlite:///:memory: (or, sqlite://)
    #  sqlite:///relative/path/to/file.db
    #  sqlite:////absolute/path/to/file.db
    WARDEN_STATUS = os.environ.get("WARDEN_STATUS")
    if WARDEN_STATUS == "developer":
        print("Using alternative settings for SQL database location")
        SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
        print("SQL URI = " + SQLALCHEMY_DATABASE_URI)
        if SQLALCHEMY_DATABASE_URI is None:
            print(
                "SQLALCHEMY_DATABASE_URI not found at environment - using default"
            )
            SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
                basedir, "alpha.db")

    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
            basedir, "alpha.db")

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
