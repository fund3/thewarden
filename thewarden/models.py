from datetime import datetime

from flask import current_app
from flask_login import UserMixin  # Manages session (anon, etc)
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from thewarden import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class listofcrypto(db.Model):
    __tablename__ = "listofcrypto"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    symbol = db.Column(db.String(20))
    website_slug = db.Column(db.String(100))

    def __repr__(self):
        return f"('{self.id}', '{self.symbol}','{self.name}')"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="USD")
    password = db.Column(db.String(60), nullable=False)
    creation_date = db.Column(db.DateTime,
                              nullable=False,
                              default=datetime.utcnow)
    trades = db.relationship("Trades", backref="trade_inputby", lazy=True)
    account = db.relationship("AccountInfo",
                              backref="account_owner",
                              lazy=True)
    bitcoin_address = db.relationship("BitcoinAddresses",
                                      backref="address_owner",
                                      lazy=True)

    def get_reset_token(self, expires_sec=300):
        s = Serializer(current_app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": self.id}).decode("utf-8")

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token)["user_id"]
        except (KeyError, TypeError):
            return None
        return User.query.get(user_id)

    def fx(self):
        # This is just the FX ticker
        return (f'{self.image_file}')

    def fx_rate_data(self):
        # This includes a dict with more data about the fx:
        # {
        # "base": "USD",
        # "symbol": "$",
        # "name": "US Dollar",
        # "name_plural": "US dollars",
        # "cross": "USD / USD",
        # "fx_rate": 1
        # }
        from thewarden.pricing_engine.pricing import fx_rate
        return fx_rate()

    def fx_rate_USD(self):
        # This includes purely the latest fx conversion rate
        # returns 1 if there's an error
        from thewarden.pricing_engine.pricing import fx_rate
        try:
            return float(fx_rate['fx_rate'])
        except Exception:
            return (1)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Trades(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150),
                        db.ForeignKey("user.id"),
                        nullable=False)
    trade_inputon = db.Column(db.DateTime,
                              nullable=False,
                              default=datetime.utcnow)
    trade_date = db.Column(db.DateTime,
                           nullable=False,
                           default=datetime.utcnow)
    trade_currency = db.Column(db.String(3), nullable=False, default="USD")
    trade_asset_ticker = db.Column(db.String(20), nullable=False)
    trade_account = db.Column(db.String(20), nullable=False)
    trade_quantity = db.Column(db.Float)
    trade_operation = db.Column(db.String(2), nullable=False)
    trade_price = db.Column(db.Float)
    trade_fees = db.Column(db.Float, default=0)
    trade_notes = db.Column(db.Text)
    trade_reference_id = db.Column(db.String(50))
    trade_blockchain_id = db.Column(db.String(150))
    cash_value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"Trades('{self.trade_date}', '{self.trade_asset_ticker}', \
                        '{self.trade_quantity}', '{self.trade_price}', \
                        '{self.trade_fees}')"


class AccountInfo(db.Model):
    account_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    account_longname = db.Column(db.String(255))
    account_type = db.Column(db.String(255))
    check_method = db.Column(db.String(255))
    account_blockchain_id = db.Column(db.String(256))
    last_check = db.Column(db.DateTime)
    last_balance = db.Column(db.Float)
    previous_check = db.Column(db.DateTime)
    previous_balance = db.Column(db.Float)
    auto_check = db.Column(db.Boolean)
    notes = db.Column(db.Text)
    child_addresses = db.relationship("BitcoinAddresses",
                                      backref="parent_account")
    xpub_derivation = db.Column(db.String(255))
    xpub_created = db.Column(db.String(255))


class Contact(db.Model):
    contact_id = db.Column(db.Integer, primary_key=True)
    message_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    email = db.Column(db.String(255))
    message = db.Column(db.Text)


class BitcoinAddresses(db.Model):
    address_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    account_id = db.Column(db.Integer,
                           db.ForeignKey("account_info.account_id"))
    address_hash = db.Column(db.String(256), nullable=False)
    last_check = db.Column(db.DateTime)
    last_balance = db.Column(db.Float)
    previous_check = db.Column(db.DateTime)
    previous_balance = db.Column(db.Float)
    auto_check = db.Column(db.Boolean)
    check_method = db.Column(db.String(255))
    imported_from_hdaddress = db.Column(db.String(255))
    notes = db.Column(db.Text)
