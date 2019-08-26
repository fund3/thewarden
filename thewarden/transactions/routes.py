import os
import secrets
import logging
import threading
import hashlib
import pandas as pd
from flask import (render_template, url_for, flash, redirect, request, abort,
                   Blueprint)
from flask_login import current_user, login_required
from thewarden import db
from thewarden.transactions.forms import NewTrade, EditTransaction
from thewarden.models import Trades, AccountInfo
from datetime import datetime
from thewarden.users.utils import (cleancsv, generatenav, bitmex_orders,
                                   load_bitmex_json, regenerate_nav, is_currency)

transactions = Blueprint("transactions", __name__)


@transactions.route("/newtrade", methods=["GET", "POST"])
@login_required
def newtrade():
    form = NewTrade()

    acclist = AccountInfo.query.filter_by(user_id=current_user.username)
    accounts = []
    for item in acclist:
        accounts.append((item.account_longname, item.account_longname))
    form.trade_account.choices = accounts
    form.cash_account.choices = accounts

    if request.method == "POST":

        if form.validate_on_submit():
            # Need to include two sides of trade:
            if form.trade_operation.data in ("B", "D"):
                qop = 1
            elif form.trade_operation.data in ("S", "W"):
                qop = -1
            else:
                qop = 0
                flash("Trade Operation Error. Should be B, S, D or W.",
                      "warning")

            # Create a unique ID for this transaction
            random_hex = secrets.token_hex(21)

            # Calculate Trade's cash value
            cvfail = False

            if form.trade_type.data != "3":
                try:
                    p = float(cleancsv(form.trade_price.data))
                    q = float(cleancsv(form.trade_quantity.data))
                    f = float(cleancsv(form.trade_fees.data))
                    cv = qop * (q * p) + f

                except ValueError:
                    flash(
                        "Error on calculating fiat amount \
                    for transaction - TRADE NOT included",
                        "danger",
                    )
                    cvfail = True
                    cv = 0

            # Check what type of trade this is
            # Cash and/or Asset
            if form.trade_type.data == "1" or form.trade_type.data == "2":
                try:
                    tquantity = float(form.trade_quantity.data) * qop
                except ValueError:
                    tquantity = 0

                try:
                    tprice = float(form.trade_price.data)
                except ValueError:
                    tprice = 0

                trade = Trades(
                    user_id=current_user.username,
                    trade_date=form.trade_date.data,
                    trade_account=form.trade_account.data,
                    trade_currency=form.trade_currency.data,
                    trade_asset_ticker=form.trade_asset_ticker.data,
                    trade_quantity=tquantity,
                    trade_operation=form.trade_operation.data,
                    trade_price=tprice,
                    trade_fees=form.trade_fees.data,
                    trade_notes=form.trade_notes.data,
                    trade_reference_id=random_hex,
                    cash_value=cv,
                )
                if not cvfail:
                    db.session.add(trade)
                    db.session.commit()
                    regenerate_nav()

            if form.trade_type.data == "1":
                # First side is done, now for the matching side-financial only
                if form.trade_operation.data == "D":
                    acc = "W"
                elif form.trade_operation.data == "W":
                    acc = "D"
                elif form.trade_operation.data == "B":
                    acc = "W"
                elif form.trade_operation.data == "S":
                    acc = "D"
                else:
                    acc = ""
                trade = Trades(
                    user_id=current_user.username,
                    trade_date=form.trade_date.data,
                    trade_account=form.cash_account.data,
                    trade_currency=form.trade_currency.data,
                    trade_asset_ticker=form.trade_currency.data,
                    trade_operation=acc,
                    trade_price="1",
                    trade_quantity=float(cleancsv(form.cash_value.data)),
                    trade_fees=0,
                    cash_value=cv * (-1),
                    trade_notes=f"Matching Trade for trade id: \
                               <{random_hex} > - included as a pair",
                    trade_reference_id=random_hex,
                )
                db.session.add(trade)
                db.session.commit()
                regenerate_nav()

            if form.trade_type.data == "3":
                # Cash Only Transaction
                try:
                    cv = qop * (float(cleancsv(form.cash_value.data)))
                except ValueError:
                    flash("Error on calculating cash amount for transaction",
                          "warning")
                    cv = 0
                    cvfail = True

                trade = Trades(
                    user_id=current_user.username,
                    trade_date=form.trade_date.data,
                    trade_account=form.cash_account.data,
                    trade_currency=form.trade_currency.data,
                    trade_asset_ticker=form.trade_currency.data,
                    trade_quantity=cv,
                    trade_price=1,
                    trade_operation=form.trade_operation.data,
                    trade_fees=form.trade_fees.data,
                    trade_notes=form.trade_notes.data,
                    cash_value=cv,
                    trade_reference_id=random_hex,
                )
                if not cvfail:
                    db.session.add(trade)
                    db.session.commit()
                    regenerate_nav()

            if not cvfail:
                flash("Trade included", "success")
            return redirect(url_for("main.home"))
        else:
            flash("Trade Input failed. Something went wrong. Try Again.",
                  "danger")

    form.trade_currency.data = current_user.fx()
    form.trade_date.data = datetime.utcnow()
    return render_template("newtrade.html", form=form, title="New Trade")


@transactions.route("/transactions")
@login_required
# List of all transactions
def list_transactions():
    transactions = Trades.query.filter_by(user_id=current_user.username)

    if transactions.count() == 0:
        return render_template("empty.html")

    return render_template("transactions.html",
                           title="Transaction History",
                           transactions=transactions)


@transactions.route("/edittransaction", methods=["GET", "POST"])
@login_required
# Edit transaction takes arguments {id} or {reference_id}
def edittransaction():
    form = EditTransaction()
    reference_id = request.args.get("reference_id")
    id = request.args.get("id")
    if reference_id:
        trade = Trades.query.filter_by(user_id=current_user.username).filter_by(
                    trade_reference_id=reference_id)
        if trade.count() == 0:
            abort(404)
        id = trade[0].id
    tmp = str(int(id) + 1)
    trade = Trades.query.filter_by(user_id=current_user.username).filter_by(
        id=id)
    trade_type = 0

    if trade.first() is None:
        abort(404)

    if trade[0].user_id != current_user.username:
        abort(403)

    acclist = AccountInfo.query.filter_by(user_id=current_user.username)
    accounts = []
    for item in acclist:
        accounts.append((item.account_longname, item.account_longname))
    form.trade_account.choices = accounts
    form.cash_account.choices = accounts

    matchok = True
    try:
        match = Trades.query.filter_by(id=tmp).filter_by(
            user_id=current_user.username)
        # check if match can be used (same user and hash)

        if match[0].user_id != trade[0].user_id:
            matchok = False
        if match[0].trade_reference_id != trade[0].trade_reference_id:
            matchok = False
        if not match[0].trade_reference_id:
            matchok = False

        if matchok is False:
            match = []
    except IndexError:
        matchok = False

    if matchok:
        trade_type = "1"

    if not matchok:
        if trade[0].trade_asset_ticker == "USD":
            trade_type = "3"
        else:
            trade_type = "2"

    if request.method == "POST":

        if form.validate_on_submit():
            # Write changes to database
            if form.trade_operation.data in ("B", "D"):
                qop = 1
            elif form.trade_operation.data in ("S", "W"):
                qop = -1
            else:
                qop = 0

            if form.trade_operation.data == "B":
                acc = "W"
            elif form.trade_operation.data == "S":
                acc = "D"
            else:
                acc = ""

            # Calculate Trade's cash value
            cvfail = False

            try:
                p = float(cleancsv(form.trade_price.data))
                q = float(cleancsv(form.trade_quantity.data))
                f = float(cleancsv(form.trade_fees.data))
                cv = qop * (q * p) + f

            except ValueError:
                flash(
                    "Error on calculating cash amount \
                for transaction - TRADE NOT edited. Try Again.",
                    "danger",
                )
                cvfail = True
                cv = 0

            trade[0].trade_date = form.trade_date.data
            trade[0].trade_asset_ticker = form.trade_asset_ticker.data
            trade[0].trade_currency = form.trade_currency.data
            trade[0].trade_operation = form.trade_operation.data
            trade[0].trade_quantity = float(form.trade_quantity.data) * qop
            trade[0].trade_price = form.trade_price.data
            trade[0].trade_fees = form.trade_fees.data
            trade[0].trade_account = form.trade_account.data
            trade[0].trade_notes = form.trade_notes.data
            trade[0].cash_value = cv

            if matchok:
                match[0].trade_asset_ticker = form.match_asset_ticker.data
                if trade_type == "1" and form.trade_asset_ticker.data != form.trade_currency.data:
                    match[0].trade_asset_ticker = form.trade_currency.data
                match[0].trade_currency = form.trade_currency.data
                match[0].trade_account = form.cash_account.data
                match[0].trade_operation = acc
                match[0].trade_date = form.trade_date.data
                match[0].trade_quantity = (qop * (-1) *
                                            ((float(form.trade_quantity.data) *
                                            float(form.trade_price.data) +
                                            float(form.trade_fees.data))))
                match[0].cash_value = cv * (-1)

            if not cvfail:
                db.session.commit()
                regenerate_nav()
                flash("Trade edit successful", "success")

            return redirect(url_for("main.home"))

        flash("Trade edit failed. Something went wrong. Try Again.", "danger")

    # Pre-populate the form
    form.trade_date.data = trade[0].trade_date
    form.trade_currency.data = trade[0].trade_currency
    form.trade_asset_ticker.data = trade[0].trade_asset_ticker
    form.trade_operation.data = trade[0].trade_operation
    form.trade_quantity.data = abs(float(trade[0].trade_quantity))
    form.trade_price.data = trade[0].trade_price
    form.trade_fees.data = trade[0].trade_fees
    form.trade_account.data = trade[0].trade_account
    form.trade_notes.data = trade[0].trade_notes
    form.trade_type.data = trade_type
    if matchok:
        form.match_asset_ticker.data = match[0].trade_asset_ticker
        form.cash_account.data = match[0].trade_account

    return render_template(
        "edittransaction.html",
        title="Edit Transaction",
        form=form,
        trade=trade,
        match=match,
        matchok=matchok,
        id=id,
        trade_type=trade_type,
    )




@transactions.route("/deltrade", methods=["GET"])
@login_required
# Deletes a trade - takes one argument: {id}
def deltrade():
    if request.method == "GET":
        id = request.args.get("id")
        trade = Trades.query.filter_by(id=id).first()

        if trade is None:
            flash(f"Trade id: {id} not found. Nothing done.", "warning")
            return redirect(url_for("main.home"))

        if trade.user_id != current_user.username:
            abort(403)

        reference_id = trade.trade_reference_id

        Trades.query.filter_by(trade_reference_id=reference_id).delete()
        db.session.commit()
        regenerate_nav()
        flash("Trade deleted", "danger")
        return redirect(url_for("main.home"))

    else:
        return redirect(url_for("main.home"))


@transactions.route("/delalltrades", methods=["GET"])
@login_required
# This deletes all trades from database - use with caution. Should not
# be called directly as it will delete all trades without confirmation!
def delalltrades():

    transactions = Trades.query.filter_by(
        user_id=current_user.username).order_by(Trades.trade_date)

    if transactions.count() == 0:
        return render_template("empty.html")

    if request.method == "GET":
        Trades.query.filter_by(user_id=current_user.username).delete()
        db.session.commit()
        regenerate_nav()
        flash("ALL TRANSACTIONS WERE DELETED", "danger")
        return redirect(url_for("main.home"))

    else:
        return redirect(url_for("main.home"))


@transactions.route("/account_positions", methods=["GET", "POST"])
@login_required
# Creates a table with current custody of positions
# Also enables user to re-allocate to different accounts
def account_positions():
    transactions = Trades.query.filter_by(user_id=current_user.username)
    if transactions.count() == 0:
        return render_template("empty.html")
    df = pd.read_sql_table("trades", db.engine)
    df = df[(df.user_id == current_user.username)]
    df["trade_date"] = pd.to_datetime(df["trade_date"])

    account_table = df.groupby(["trade_account", "trade_asset_ticker"
                                ])[["trade_quantity"]].sum()
    # All accounts
    all_accounts = (account_table.query(
        "trade_asset_ticker != '" + current_user.fx() +
        "'").index.get_level_values("trade_account").unique().tolist())
    # Trim the account list only for accounts that currently hold a position
    account_table = account_table[account_table.trade_quantity != 0]
    # Remove accounts with USD only Positions
    account_table = account_table.query("trade_asset_ticker != 'USD'")

    # account_table = account_table['trade_asset_ticker' != 'USD']
    accounts = account_table.index.get_level_values(
        "trade_account").unique().tolist()
    tickers = (account_table.index.get_level_values(
        "trade_asset_ticker").unique().tolist())
    # if 'USD' in tickers:
    #     tickers.remove('USD')

    return render_template(
        "account_positions.html",
        title="Account Positions",
        accounts=accounts,
        tickers=tickers,
        account_table=account_table,
        all_accounts=all_accounts,
    )


def check_trade_included(id):
    # Checks if a transaction id is already in database
    # Returns True or False
    df = pd.read_sql_table("trades", db.engine)
    # Filter only the trades for current user
    df = df[(df.user_id == current_user.username)]
    df = df[(df.trade_blockchain_id == id)]
    if df.empty:
        return False
    return True


@transactions.route("/bitmex_transactions", methods=["GET", "POST"])
@login_required
def bitmex_transactions():
    logging.info(f"Started Bitmex Transaction method")
    meta = {}
    testnet = False
    transactions = {}
    transactions["error"] = ""
    meta["success"] = False
    meta["n_txs"] = 0
    bitmex_credentials = load_bitmex_json()
    if ("api_key" in bitmex_credentials) and (
            "api_secret" in bitmex_credentials):
        data = bitmex_orders(bitmex_credentials['api_key'],
                             bitmex_credentials['api_secret'], testnet)
        try:
            # Create a DataFrame to return
            data_df = pd.DataFrame.from_dict(data[0])
            data_df['fiat_fee'] = data_df['execComm'] * data_df[
                'lastPx'] / 100000000
            # Check if the transactions are included in the database already
            data_df['exists'] = data_df['execID'].apply(check_trade_included)
            transactions["data"] = data_df
            meta["success"] = "success"
        except ValueError:
            meta["success"] = "error"

    return render_template("bitmex_transactions.html",
                           title="Bitmex Transactions",
                           meta=meta,
                           transactions=transactions,
                           bitmex_credentials=bitmex_credentials)
