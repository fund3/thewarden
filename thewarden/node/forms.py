from thewarden.models import AccountInfo, Trades
from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    DateTimeField,
    TextAreaField,
    SelectField,
    BooleanField,
    ValidationError,
)
from wtforms.widgets import PasswordInput
from wtforms.validators import DataRequired, ValidationError, Optional


class DojoForm(FlaskForm):
    dojo_onion = StringField("Dojo Onion Address")
    dojo_token = StringField("Dojo Authentication Token")
    dojo_apikey = PasswordField("Dojo API Key", widget=PasswordInput(hide_value=False))
    submit = SubmitField("Update")


class AddressForm(FlaskForm):
    access_methods = (
        ("0", ""),
        ("1", "Dojo Only"),
        ("2", "OXT (over Tor)"),
        ("3", "Dojo then OXT"),
    )

    address = StringField("Bitcoin Address")
    last_check = DateTimeField("Last check on the Blockchain")
    check_method = SelectField(
        "Select Method to monitor balance", choices=access_methods, default=""
    )
    auto_check = BooleanField("Monitor")
    account = StringField("Linked to Account")
    hd_parent = StringField("Parent HD Address")
    notes = TextAreaField("Notes")
    submit = SubmitField("Submit")

    def validate_address(self, address):
        add = address.data
        if add == "":
            raise ValidationError("Address cannot be empty")
        if "xpub" in add.lower():
            raise ValidationError("XPUBs not accepted here")
        if "ypub" in add.lower():
            raise ValidationError("YPUBs not accepted here")

    def validate_check_method(self, check_method):
        if check_method.data == "0":
            raise ValidationError("Please choose one method")

    def validate_account(self, account):
        # Only accept accounts already registered in trades or accountinfo
        found = False
        tradeaccounts = Trades.query.filter_by(user_id=current_user.username).group_by(
            Trades.trade_account
        )

        accounts = AccountInfo.query.filter_by(user_id=current_user.username).group_by(
            AccountInfo.account_longname
        )

        for item in tradeaccounts:
            if account.data.upper() in item.trade_account.upper():
                found = True
        for item in accounts:
            if account.data.upper() in item.account_longname.upper():
                found = True

        if not found:
            raise ValidationError(
                "Choose an existing account. If account is not registered, include first."
            )


class Custody_Account(FlaskForm):
    account_longname = StringField("Account Name", [DataRequired()])
    account_blockchain_id = StringField("HD Address (XPUB, YPUB, others)")
    access_methods = (
        ("0", ""),
        ("1", "Dojo Only"),
        ("2", "OXT (over Tor)"),
        ("3", "Dojo then OXT"),
    )
    check_method = SelectField(
        "Select Method to monitor balance", choices=access_methods, default=""
    )
    auto_check = BooleanField("Monitor")
    notes = TextAreaField("Notes")
    submit = SubmitField("Submit")
