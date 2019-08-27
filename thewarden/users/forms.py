from flask_wtf import FlaskForm
from flask_login import current_user
from thewarden.models import User
from thewarden.users.utils import fx_list
from wtforms.widgets import PasswordInput
from wtforms import (StringField, PasswordField, SubmitField, BooleanField,
                     ValidationError, SelectField)
from wtforms.validators import (DataRequired, Length, Email, EqualTo, Optional)


class RegistrationForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(),
                                       Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(),
                                        EqualTo("password")])
    submit = SubmitField("Register")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("User already exists. Please Login.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("E-mail already registered. Please Login.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class UpdateAccountForm(FlaskForm):
    email = StringField("Email", [DataRequired(), Email()])
    basefx = SelectField("Your selected base currency", [Optional()],
                         choices=fx_list())
    submit = SubmitField("Update")

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError("\
                Email already exists. Use a different one.")


class RequestResetForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError("There is no account with that email." +
                                  " You must register first.")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(),
                                        EqualTo("password")])
    submit = SubmitField("Reset Password")


class ApiKeysForm(FlaskForm):
    aa_key = StringField("AlphaVantage API Key")
    bitmex_secret = StringField("Bitmex Secret Key")
    bitmex_key = StringField("Bitmex API Key")
    dojo_onion = StringField("DOJO Onion Address")
    dojo_key = StringField("DOJO API Key")
    submit = SubmitField("Update")