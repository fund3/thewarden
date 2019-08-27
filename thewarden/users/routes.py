from flask import render_template, url_for, flash, redirect, request, abort, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from thewarden import db, Config
from thewarden.users.forms import (RegistrationForm, LoginForm,
                                   UpdateAccountForm, RequestResetForm,
                                   ResetPasswordForm, ApiKeysForm)
from werkzeug.security import check_password_hash, generate_password_hash
from thewarden.models import User, Trades, AccountInfo
from thewarden.users.utils import send_reset_email, fx_list, generatenav, regenerate_nav
from thewarden.pricing_engine.pricing import api_keys_class

users = Blueprint("users", __name__)


@users.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hash = generate_password_hash(form.password.data)
        user = User(username=form.username.data,
                    email=form.email.data,
                    password=hash)
        db.session.add(user)
        db.session.commit()
        flash(f"Account created for {form.username.data}.", "success")
        return redirect(url_for("users.login"))
    return render_template("register.html", title="Register", form=form)


@users.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            # The get method below is actually very helpful
            # it returns None if empty. Better than using [] for a dictionary.
            next_page = request.args.get("next")  # get the original page
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for("main.home"))
        else:
            flash("Login failed. Please check e-mail and password", "danger")

    return render_template("login.html", title="Login", form=form)


@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@users.route("/account", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        # If currency is changed, recalculate the NAV
        print(form.basefx.data)
        print(current_user.fx())
        if form.basefx.data != current_user.fx():
            current_user.image_file = form.basefx.data
            regenerate_nav()
            db.session.commit()
            flash(
                f"NAV recalculated to use {form.basefx.data} as a base currency",
                "success")
        current_user.email = form.email.data
        current_user.image_file = form.basefx.data
        db.session.commit()
        flash("Your account has been updated", "success")
        return redirect(url_for("users.account"))

    elif request.method == "GET":
        form.email.data = current_user.email
        # Check if the current value is in list of fx
        # If not, default to USD
        fx = fx_list()
        found = [item for item in fx if current_user.image_file in item]
        if found != []:
            form.basefx.data = current_user.image_file
        else:
            form.basefx.data = "USD"

    return render_template("account.html", title="Account", form=form)


@users.route("/delacc", methods=["GET"])
@login_required
# Takes one argument {id} - user id for deletion
def delacc():
    if request.method == "GET":
        id = request.args.get("id")
        trade = Trades.query.filter_by(id=id)
        if trade[0].user_id != current_user.username:
            abort(403)

        AccountInfo.query.filter_by(account_id=id).delete()
        db.session.commit()
        flash("Account deleted", "danger")
        return redirect(url_for("transactions.tradeaccounts"))

    else:
        return redirect(url_for("transactions.tradeaccounts"))


@users.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash(
            "An email has been sent with instructions to reset your" +
            " password.",
            "info",
        )
        return redirect(url_for("users.login"))
    return render_template("reset_request.html",
                           title="Reset Password",
                           form=form)


@users.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token", "warning")
        return redirect(url_for("users.reset_request"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hash = generate_password_hash(form.password.data)
        user.password = hash
        db.session.commit()
        flash("Your password has been updated! You are now able to log in",
              "success")
        return redirect(url_for("users.login"))
    return render_template("reset_token.html",
                           title="Reset Password",
                           form=form)


@users.route("/services", methods=["GET"])
def services():
    return render_template("services.html", title="Services Available")


# API Keys Management
@users.route("/apikeys_management", methods=["GET", "POST"])
def apikeys_management():
    from thewarden.pricing_engine.pricing import api_keys_class
    api_keys_json = api_keys_class.loader()
    form = ApiKeysForm()

    if request.method == "GET":
        form.dojo_key.data = api_keys_json['dojo']['api_key']
        form.dojo_onion.data = api_keys_json['dojo']['onion']
        form.bitmex_key.data = api_keys_json['bitmex']['api_key']
        form.bitmex_secret.data = api_keys_json['bitmex']['api_secret']
        form.aa_key.data = api_keys_json['alphavantage']['api_key']

        return render_template("apikeys_management.html",
                               title="API Keys Management",
                               form=form)

    if request.method == "POST":
        api_keys_json['dojo']['api_key'] = form.dojo_key.data
        api_keys_json['dojo']['onion'] = form.dojo_onion.data
        api_keys_json['bitmex']['api_key'] = form.bitmex_key.data
        api_keys_json['bitmex']['api_secret'] = form.bitmex_secret.data
        api_keys_json['alphavantage']['api_key'] = form.aa_key.data
        api_keys_class.saver(api_keys_json)

        flash("Keys Updated Successfully", "success")
        return render_template("apikeys_management.html",
                               title="API Keys Management",
                               form=form)