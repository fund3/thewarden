import json
import logging
import math
import secrets
import requests
import csv
from datetime import datetime, timedelta

import simplejson
import numpy as np
import pandas as pd
from dateutil import parser
from bitmex import bitmex
from dateutil.relativedelta import relativedelta
from flask import Blueprint, jsonify, render_template, request, flash
from flask_login import current_user, login_required

from thewarden import db, test_tor
from thewarden import mhp as mrh
from thewarden.models import (
    Trades, listofcrypto, User, BitcoinAddresses, AccountInfo)
from thewarden.users.utils import (
    generate_pos_table,
    generatenav,
    heatmap_generator,
    rt_price_grab,
    price_ondate,
    regenerate_nav,
    transactions_fx,
    fxsymbol
)
from thewarden.node.utils import (
    dojo_auth,
    oxt_get_address,
    dojo_multiaddr,
    dojo_get_settings,
    dojo_get_txs,
    dojo_get_hd,
    tor_request,
)
from thewarden.users.decorators import MWT
from thewarden.pricing_engine.pricing import price_data_fx

api = Blueprint("api", __name__)


# Helper function: Make sure strings don't go into DB
def s_to_f(x):
    try:
        if x is None:
            x = 0
        x = float(x)
        return x
    except ValueError:
        return 0


@api.route("/cryptolist", methods=["GET", "POST"])
# List of available tickers. Also takes argument {term} so this can be used
# in autocomplete forms
def cryptolist():
    getlist = listofcrypto.query.all()

    if request.method == "GET":
        check = request.args.get("json")
        q = request.args.get("term")
        if check == "true":
            jsonlist = []
            for item in getlist:
                if (q.upper() in item.symbol) or (q in item.name):
                    tmp = {}
                    tmp["name"] = item.name
                    tmp["symbol"] = item.symbol
                    jsonlist.append(tmp)

            return jsonify(jsonlist)

    return render_template(
        "cryptolist.html",
        title="List of Crypto Currencies", listofcrypto=getlist
    )


@api.route("/aclst", methods=["GET", "POST"])
@login_required
# Returns JSON for autocomplete on account names.
# Gathers account names from trades and account_info tables
# Takes on input ?term - which is the string to be found
def aclst():
    list = []
    if request.method == "GET":

        tradeaccounts = Trades.query.filter_by(
            user_id=current_user.username).group_by(
            Trades.trade_account)

        accounts = AccountInfo.query.filter_by(
            user_id=current_user.username).group_by(
            AccountInfo.account_longname
        )

        q = request.args.get("term")
        for item in tradeaccounts:
            if q.upper() in item.trade_account.upper():
                list.append(item.trade_account)
        for item in accounts:
            if q.upper() in item.account_longname.upper():
                list.append(item.account_longname)

        list = json.dumps(list)

        return list


@api.route("/histvol", methods=["GET", "POST"])
@login_required
# Returns a json with data to create the vol chart
# takes inputs from get:
# ticker, meta (true returns only metadata), rolling (in days)
# metadata (max, mean, etc)
def histvol():
    # if there's rolling variable, get it, otherwise default to 30
    if request.method == "GET":
        try:
            q = int(request.args.get("rolling"))
        except ValueError:
            q = 30
    else:
        q = 30

    ticker = request.args.get("ticker")
    metadata = request.args.get("meta")

    # When ticker is not sent, will calculate for portfolio
    if not ticker:
        transactions = Trades.query.filter_by(
            user_id=current_user.username).order_by(
            Trades.trade_date
        )
        if transactions.count() == 0:
            return render_template("empty.html")

        data = generatenav(current_user.username)
        data["vol"] = (data["NAV_fx"].pct_change().rolling(q).std() *
                       (365 ** 0.5) * 100)
        # data.set_index('date', inplace=True)
        vollist = data[["vol"]]
        vollist.index = vollist.index.strftime("%Y-%m-%d")
        datajson = vollist.to_json()

    if ticker:
        filename = "thewarden/historical_data/" + ticker + ".json"

        try:
            with open(filename) as data_file:
                local_json = json.loads(data_file.read())
                data_file.close()
                prices = pd.DataFrame(
                    local_json["Time Series (Digital Currency Daily)"]
                ).T
                prices["4b. close (USD)"] = prices["4b. close (USD)"].astype(
                    np.float)
                prices["vol"] = (
                    prices["4b. close (USD)"].pct_change().rolling(q).std() *
                    (365 ** 0.5) * 100
                )
                pricelist = prices[["vol"]]
                datajson = pricelist.to_json()

        except (FileNotFoundError, KeyError):
            datajson = "Ticker Not Found"
            logging.message(f"File not Found Error: ID: {id}")

    if metadata is not None:
        metatable = {}
        metatable["mean"] = vollist.vol.mean()
        metatable["max"] = vollist.vol.max()
        metatable["min"] = vollist.vol.min()
        metatable["last"] = vollist.vol[-1]
        metatable["lastvsmean"] = (
            (vollist.vol[-1] / vollist.vol.mean()) - 1) * 100
        metatable = json.dumps(metatable)
        return metatable

    return datajson


@api.route("/tradedetails", methods=["GET"])
@login_required
# Function that returns a json with trade details given an id
# also, set tradesonly to true to only receive the
# asset side of transaction (buy or sell)
# id = trade hash
def tradedetails():
    if request.method == "GET":
        id = request.args.get("id")
        # if tradesonly is true then only look for buy and sells
        tradesonly = request.args.get("trades")
        df = pd.read_sql_table("trades", db.engine)
        # Filter only the trades for current user
        df = df[(df.user_id == current_user.username)]
        df = df[(df.trade_reference_id == id)]
        # Filter only buy and sells, ignore deposit / withdraw
        if tradesonly:
            df = df[(df.trade_operation == "B") | (df.trade_operation == "S")]
        # df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index("trade_reference_id", inplace=True)
        df.drop("user_id", axis=1, inplace=True)
        details = df.to_json()
        return details


@api.route("/portstats", methods=["GET", "POST"])
@login_required
# Function retuns summary statistics for portfolio NAV and values
def portstats():
    meta = {}
    # Looking to generate the following data here and return as JSON
    # for AJAX query on front page:
    # Start date, End Date, Start NAV, End NAV, Returns (1d, 1wk, 1mo, 1yr,
    # YTD), average daily return. Best day, worse day. Std dev of daily ret,
    # Higher NAV, Lower NAV + dates. Higher Port Value (date).
    data = generatenav(current_user.username)
    meta["start_date"] = (data.index.min()).date().strftime("%B %d, %Y")
    meta["end_date"] = data.index.max().date().strftime("%B %d, %Y")
    meta["start_nav"] = data["NAV_fx"][0]
    meta["end_nav"] = data["NAV_fx"][-1].astype(float)
    meta["max_nav"] = data["NAV_fx"].max().astype(float)
    meta["max_nav_date"] = data[data["NAV_fx"] == data["NAV_fx"].max()].index.strftime(
        "%B %d, %Y")[0]
    meta["min_nav"] = data["NAV_fx"].min().astype(float)
    meta["min_nav_date"] = data[data["NAV_fx"] == data["NAV_fx"].min()].index.strftime(
        "%B %d, %Y")[0]
    meta["end_portvalue"] = data["PORT_fx_pos"][-1].astype(float)
    meta["end_portvalue_usd"] = data["PORT_usd_pos"][-1].astype(float)
    meta["max_portvalue"] = data["PORT_fx_pos"].max().astype(float)
    meta["max_port_date"] = data[
        data["PORT_fx_pos"] == data["PORT_fx_pos"].max()
    ].index.strftime("%B %d, %Y")[0]
    meta["min_portvalue"] = round(data["PORT_fx_pos"].min(), 0).astype(float)
    meta["min_port_date"] = data[
        data["PORT_fx_pos"] == data["PORT_fx_pos"].min()
    ].index.strftime("%B %d, %Y")[0]
    meta["return_SI"] = (meta["end_nav"] / meta["start_nav"]) - 1
    # Temporary fix for an issue with portfolios that are just too new
    # Create a function to handle this
    try:
        meta["return_1d"] = (meta["end_nav"] / data["NAV_fx"][-2]) - 1
    except IndexError:
        meta["return_1d"] = "-"

    try:
        meta["return_1wk"] = (meta["end_nav"] / data["NAV_fx"][-7]) - 1
    except IndexError:
        meta["return_1wk"] = "-"

    try:
        meta["return_30d"] = (meta["end_nav"] / data["NAV_fx"][-30]) - 1
    except IndexError:
        meta["return_30d"] = "-"

    try:
        meta["return_90d"] = (meta["end_nav"] / data["NAV_fx"][-90]) - 1
    except IndexError:
        meta["return_90d"] = "-"

    try:
        meta["return_ATH"] = (meta["end_nav"] / meta["max_nav"]) - 1
    except IndexError:
        meta["return_ATH"] = "-"

    try:
        yr_ago = pd.to_datetime(datetime.today() - relativedelta(years=1))
        yr_ago_NAV = data.NAV_fx[data.index.get_loc(yr_ago, method="nearest")]
        meta["return_1yr"] = meta["end_nav"] / yr_ago_NAV - 1
    except IndexError:
        meta["return_1yr"] = "-"

    # create chart data for a small NAV chart
    return simplejson.dumps(meta, ignore_nan=True)


@MWT(20)
@api.route("/navchartdatajson", methods=["GET", "POST"])
@login_required
#  Creates a table with dates and NAV values
def navchartdatajson():
    data = generatenav(current_user.username)
    # Generate data for NAV chart
    navchart = data[["NAV_fx"]]
    # dates need to be in Epoch time for Highcharts
    navchart.index = (navchart.index - datetime(1970, 1, 1)).total_seconds()
    navchart.index = navchart.index * 1000
    navchart.index = navchart.index.astype(np.int64)
    navchart = navchart.to_dict()
    navchart = navchart["NAV_fx"]
    navchart = json.dumps(navchart)
    return navchart


@api.route("/manage_custody", methods=["GET"])
@login_required
# Back-end function to manage positions after requests are sent from
# the edit position tool from account_positions.html
# Takes arguments:
# action:
#     delete_dust,move_dust,adjust_dust,position_move,position_adjust)
# ticker
# quant_before
# from_account
# to_account
def manage_custody():
    tradedetails = "EMPTY"
    # If method is post then do actions
    if request.method == "GET":
        action = request.args.get("action")
        if action == "delete_dust":
            try:
                ticker = request.args.get("ticker")
                quant_before = request.args.get("quant_before")
                from_account = request.args.get("from_account")
                # Implement the trade and write to dbase
                tradedetails = (
                    f"Trade included to wipe out {ticker} " +
                    f"dust amount of {quant_before} from " +
                    f"{from_account}"
                )

                tradedate = datetime.now()
                # Create a unique ID
                random_hex = secrets.token_hex(21)
                if float(quant_before) < 0:
                    acc = "B"
                else:
                    acc = "S"
                trade = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=from_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=float(quant_before) * (-1),
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails,
                    trade_reference_id=random_hex,
                )
                db.session.add(trade)
                db.session.commit()
                regenerate_nav()

            except KeyError:
                tradedetails = "Error"

        elif action == "move_dust":
            try:
                ticker = request.args.get("ticker")
                quant_before = request.args.get("quant_before")
                from_account = request.args.get("from_account")
                to_account = request.args.get("to_account")

                tradedetails = (
                    f"Trade included to move dust amount of " +
                    f"{quant_before} from {from_account} to {to_account}"
                )
                tradedate = datetime.now()
                if float(quant_before) < 0:
                    acc = "D"
                else:
                    acc = "W"

                # There are two sides to this trade. A deposit and withdraw.
                # First Original Account - Create a unique ID
                random_hex = secrets.token_hex(21)
                trade = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=from_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=float(quant_before) * (-1),
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails + " (Original Account)",
                    trade_reference_id=random_hex,
                )
                db.session.add(trade)
                db.session.commit()
                regenerate_nav()

                # Now the new Account
                if float(quant_before) < 0:
                    acc = "W"
                else:
                    acc = "D"

                random_hex = secrets.token_hex(21)
                trade_2 = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=to_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=float(quant_before) * (1),
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails + " (Target Account)",
                    trade_reference_id=random_hex,
                )
                db.session.add(trade_2)
                db.session.commit()
                regenerate_nav()

            except KeyError:
                tradedetails = "Error"

        elif action == "adjust_dust":
            try:
                ticker = request.args.get("ticker")
                quant_before = request.args.get("quant_before")
                from_account = request.args.get("from_account")
                to_quant = request.args.get("to_quant")
                tradedetails = (
                    f"Trade included to adjust dust amount " +
                    f"of {quant_before} from to {to_quant} at {from_account}"
                )
                tradedate = datetime.now()
                # Create a unique ID
                random_hex = secrets.token_hex(21)
                quant_adjust = float(to_quant) - float(quant_before)
                if quant_adjust > 0:
                    acc = "B"
                else:
                    acc = "S"
                trade = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=from_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=quant_adjust,
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails,
                    trade_reference_id=random_hex,
                )
                db.session.add(trade)
                db.session.commit()
                regenerate_nav()

            except KeyError:
                tradedetails = "Error"

        elif action == "position_move":
            try:
                ticker = request.args.get("ticker")
                quant_before = request.args.get("quant_before")
                from_account = request.args.get("from_account")
                to_account = request.args.get("to_account")
                tradedetails = (
                    f"Trade included to move {quant_before} " +
                    f"{ticker} from account {from_account} to " +
                    f"account {to_account}"
                )
                tradedate = datetime.now()
                if float(quant_before) < 0:
                    acc = "D"
                else:
                    acc = "W"

                # There are two sides to this trade. A deposit and withdraw.
                # First Original Account - Create a unique ID
                random_hex = secrets.token_hex(21)
                trade = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=from_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=float(quant_before) * (-1),
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails + " (Original Account)",
                    trade_reference_id=random_hex,
                )
                db.session.add(trade)
                db.session.commit()
                regenerate_nav()

                # Now the new Account
                if float(quant_before) < 0:
                    acc = "W"
                else:
                    acc = "D"

                random_hex = secrets.token_hex(21)
                trade_2 = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=to_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=float(quant_before) * (1),
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails + " (Target Account)",
                    trade_reference_id=random_hex,
                )
                db.session.add(trade_2)
                db.session.commit()
                regenerate_nav()

            except KeyError:
                tradedetails = "Error"
            tradedetails = (
                f"Trade included to move position from " +
                f"{from_account} to {to_account}"
            )

        elif action == "position_adjust":
            try:
                ticker = request.args.get("ticker")
                quant_before = request.args.get("quant_before")
                from_account = request.args.get("from_account")
                to_quant = request.args.get("to_quant")
                tradedetails = (
                    f"Trade included to adjust position from " +
                    f"{quant_before} to to {to_quant}"
                )
                tradedate = datetime.now()
                # Create a unique ID
                random_hex = secrets.token_hex(21)
                quant_adjust = float(to_quant) - float(quant_before)
                if quant_adjust > 0:
                    acc = "B"
                else:
                    acc = "S"
                trade = Trades(
                    user_id=current_user.username,
                    trade_date=tradedate,
                    trade_account=from_account,
                    trade_asset_ticker=ticker,
                    trade_operation=acc,
                    trade_price="0",
                    trade_quantity=quant_adjust,
                    trade_fees=0,
                    cash_value=0,
                    trade_notes=tradedetails,
                    trade_reference_id=random_hex,
                )
                db.session.add(trade)
                db.session.commit()
                regenerate_nav()

            except KeyError:
                tradedetails = "Error"

    return json.dumps(tradedetails)


@api.route("/portfolio_compare_json", methods=["GET"])
@login_required
# Compare portfolio performance to a list of assets
# Takes arguments:
# tickers  - (comma separated. ex: BTC,ETH,AAPL)
# start    - start date in the format YYMMDD
# end      - end date in the format YYMMDD
# method   - "chart": returns NAV only data for charts
#          - "all": returns all data (prices and NAV)
#          - "meta": returns metadata information
def portfolio_compare_json():
    if request.method == "GET":
        tickers = request.args.get("tickers").upper()
        tickers = tickers.split(",")
        start_date = request.args.get("start")
        method = request.args.get("method")

        # Check if start and end dates exist, if not assign values
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(
                f"[portfolio_compare_json] Error: {e}, " +
                "setting start_date to zero"
            )
            start_date = 0

        end_date = request.args.get("end")

        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(
                f"[portfolio_compare_json] Error: {e}, " +
                "setting end_date to now"
            )
            end_date = datetime.now()
    data = {}

    logging.info(
        "[portfolio_compare_json] NAV requested in list of " +
        "tickers, requesting generatenav."
    )
    nav = generatenav(current_user.username)
    nav_only = nav["NAV_fx"]

    # Now go over tickers and merge into nav_only df
    messages = {}
    meta_data = {}
    for ticker in tickers:
        if ticker == "NAV":
            # Ticker was NAV, skipped
            continue

        # Generate price Table now for the ticker and trim to match portfolio
        data = price_data_fx(ticker)
        # If notification is an error, skip this ticker
        if data is None:
            messages = data.errors
            return jsonify(messages)
        data = data.rename(columns={'close_converted': ticker+'_price'})
        data = data[ticker+'_price']
        nav_only = pd.merge(nav_only, data, on="date", how="left")
        nav_only[ticker + "_price"].fillna(method="bfill", inplace=True)
        messages[ticker] = "ok"
        logging.info(
            f"[portfolio_compare_json] {ticker}: Success - Merged OK")

    nav_only.fillna(method="ffill", inplace=True)

    # Trim this list only to start_date to end_date:
    mask = (nav_only.index >= start_date) & (nav_only.index <= end_date)
    nav_only = nav_only.loc[mask]

    # Now create the list of normalized Returns for the available period
    # Plus create a table with individual analysis for each ticker and NAV
    nav_only["NAV_norm"] = (nav_only["NAV_fx"] / nav_only["NAV_fx"][0]) * 100
    nav_only["NAV_ret"] = nav_only["NAV_norm"].pct_change()
    table = {}
    table["meta"] = {}
    table["meta"]["start_date"] = (nav_only.index[0]).strftime("%m-%d-%Y")
    table["meta"]["end_date"] = nav_only.index[-1].strftime("%m-%d-%Y")
    table["meta"]["number_of_days"] = (
        (nav_only.index[-1] - nav_only.index[0])).days
    table["meta"]["count_of_points"] = nav_only["NAV_fx"].count().astype(float)
    table["NAV"] = {}
    table["NAV"]["start"] = nav_only["NAV_fx"][0]
    table["NAV"]["end"] = nav_only["NAV_fx"][-1]
    table["NAV"]["return"] = (nav_only["NAV_fx"][-1] / nav_only["NAV_fx"][0]) - 1
    table["NAV"]["avg_return"] = nav_only["NAV_ret"].mean()
    table["NAV"]["ann_std_dev"] = nav_only["NAV_ret"].std() * math.sqrt(365)
    for ticker in tickers:
        if messages[ticker] == "ok":
            # Include new columns for return and normalized data
            nav_only[ticker + "_norm"] = (
                nav_only[ticker + "_price"] / nav_only[ticker + "_price"][0]
            ) * 100
            nav_only[ticker + "_ret"] = nav_only[ticker + "_norm"].pct_change()
            # Create Metadata
            table[ticker] = {}
            table[ticker]["start"] = nav_only[ticker + "_price"][0]
            table[ticker]["end"] = nav_only[ticker + "_price"][-1]
            table[ticker]["return"] = (
                nav_only[ticker + "_price"][-1] /
                nav_only[ticker + "_price"][0]
            ) - 1
            table[ticker]["comp2nav"] = table[ticker]["return"] - \
                table["NAV"]["return"]
            table[ticker]["avg_return"] = nav_only[ticker + "_ret"].mean()
            table[ticker]["ann_std_dev"] = nav_only[ticker + "_ret"].std() * math.sqrt(
                365
            )

    logging.info("[portfolio_compare_json] Success")

    # Create Correlation Matrix
    filter_col = [col for col in nav_only if col.endswith("_ret")]
    nav_matrix = nav_only[filter_col]
    corr_matrix = nav_matrix.corr(method="pearson").round(2)
    corr_html = corr_matrix.to_html(
        classes="table small text-center", border=0, justify="center"
    )

    # Now, let's return the data in the correct format as requested
    if method == "chart":
        return jsonify(
            {
                "data": nav_only.to_json(),
                "messages": messages,
                "meta_data": meta_data,
                "table": table,
                "corr_html": corr_html,
            }
        )

    return nav_only.to_json()


@MWT(20)
@api.route("/generatenav_json", methods=["GET", "POST"])
@login_required
# Creates a table with dates and NAV values
# Takes 2 arguments:
# force=False (default) : Forces the NAV generation without reading saved file
# filter=None (default): Filter to be applied to Pandas df (df.query(filter))
def generatenav_json():
    if request.method == "GET":
        filter = request.args.get("filter")
        force = request.args.get("force")
        if not filter:
            filter = ""
        if not force:
            force = False
        nav = generatenav(current_user.username, force, filter)
        return nav.to_json()


@MWT(10)
@api.route("/portfolio_tickers_json", methods=["GET", "POST"])
@login_required
# Returns a list of all tickers ever traded in this portfolio
def portfolio_tickers_json():
    if request.method == "GET":
        df = pd.read_sql_table("trades", db.engine)
        df = df[(df.user_id == current_user.username)]
        list_of_tickers = df.trade_asset_ticker.unique().tolist()
        try:
            list_of_tickers.remove(current_user.fx())
        except ValueError:
            pass
        return jsonify(list_of_tickers)


@api.route("/generate_pos_table_json", methods=["GET", "POST"])
@login_required
# Creates a table with PnL summary for positions
def generate_pos_table_json():
    if request.method == "GET":
        pos_table, _ = generate_pos_table(current_user.username, "USD", False)
        # SimpleJson needs to be used here since Pandas DF are returning
        # values like NaN and inf which are nor JSON compatible and would
        # result in parse error at javascript
        return simplejson.dumps(pos_table, ignore_nan=True, default=datetime.isoformat)


@api.route("/scatter_json", methods=["GET"])
@login_required
# Compare portfolio performance to a list of assets
# Takes arguments:
# tickers  - (comma separated. ex: BTC,ETH,AAPL)
# market   - which ticker is assumed to be the market (default = BTC)
# start    - start date in the format YYMMDD
# end      - end date in the format YYMMDD
# method   - "chart": returns NAV only data for charts
#          - "all": returns all data (prices and NAV)
#          - "meta": returns metadata information
def scatter_json():
    if request.method == "GET":
        tickers = request.args.get("tickers").upper()
        tickers = tickers.split(",")
        start_date = request.args.get("start")
        market = request.args.get("market").upper()

        # Check if market was sent. If not, default=BTC
        if not market:
            market = "BTC"

        # Check if start and end dates exist, if not assign values
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(
                f"[scatter_json] Error: {e}, " + "setting start_date to zero")
            start_date = 0

        end_date = request.args.get("end")

        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(
                f"[scatter_json] Error: {e}, " + "setting end_date to now")
            end_date = datetime.now()
    data = {}

    logging.info(
        "[scatter_json] NAV requested in list of " +
        "tickers, requesting generatenav."
    )
    nav = generatenav(current_user.username)
    nav_only = nav["NAV_fx"]
    # Append market ticker to list of tickers, remove duplicates
    tickers.append(market)
    tickers = list(set(tickers))
    # Now go over tickers and merge into nav_only df
    messages = {}
    meta_data = {}
    for ticker in tickers:
        if ticker == "NAV":
            # Ticker was NAV, skipped
            continue
        data = price_data_fx(ticker)
        # If notification is an error, skip this ticker
        if data is None:
            messages = data.errors
            return jsonify(messages)

        data = data.rename(columns={'close_converted': ticker+'_price'})
        data = data[[ticker+'_price']]
        data = data.astype(float)

        # Fill dailyNAV with prices for each ticker
        nav_only = pd.merge(nav_only, data, on="date", how="left")
        nav_only[ticker + "_price"].fillna(method="bfill", inplace=True)
        messages[ticker] = "ok"
        logging.info(f"[scatter_json] {ticker}: Success - Merged OK")

    nav_only.fillna(method="ffill", inplace=True)

    # Trim this list only to start_date to end_date:
    mask = (nav_only.index >= start_date) & (nav_only.index <= end_date)
    nav_only = nav_only.loc[mask]

    # Now create the scatter plot data
    # Plus create a table with individual analysis for each ticker and NAV
    nav_only["NAV_norm"] = (nav_only["NAV_fx"] / nav_only["NAV_fx"][0]) * 100
    nav_only["NAV_ret"] = nav_only["NAV_norm"].pct_change()
    table = {}
    table["meta"] = {}
    table["meta"]["start_date"] = (nav_only.index[0]).strftime("%m-%d-%Y")
    table["meta"]["end_date"] = nav_only.index[-1].strftime("%m-%d-%Y")
    table["meta"]["number_of_days"] = (
        (nav_only.index[-1] - nav_only.index[0])).days
    table["meta"]["count_of_points"] = nav_only["NAV_fx"].count().astype(float)
    table["NAV"] = {}
    table["NAV"]["start"] = nav_only["NAV_fx"][0]
    table["NAV"]["end"] = nav_only["NAV_fx"][-1]
    table["NAV"]["return"] = (nav_only["NAV_fx"][-1] / nav_only["NAV_fx"][0]) - 1
    table["NAV"]["avg_return"] = nav_only["NAV_ret"].mean()
    table["NAV"]["ann_std_dev"] = nav_only["NAV_ret"].std() * math.sqrt(365)
    # Include avg return + and -
    for ticker in tickers:
        if messages[ticker] == "ok":
            # Include new columns for return and normalized data
            nav_only[ticker + "_norm"] = (
                nav_only[ticker + "_price"] / nav_only[ticker + "_price"][0]
            ) * 100
            nav_only[ticker + "_ret"] = nav_only[ticker + "_norm"].pct_change()
            # Create Metadata
            table[ticker] = {}
            table[ticker]["start"] = nav_only[ticker + "_price"][0]
            table[ticker]["end"] = nav_only[ticker + "_price"][-1]
            table[ticker]["return"] = (
                nav_only[ticker + "_price"][-1] /
                nav_only[ticker + "_price"][0]
            ) - 1
            table[ticker]["comp2nav"] = table[ticker]["return"] - \
                table["NAV"]["return"]
            table[ticker]["avg_return"] = nav_only[ticker + "_ret"].mean()
            table[ticker]["ann_std_dev"] = nav_only[ticker + "_ret"].std() * math.sqrt(
                365
            )

    logging.info("[scatter_json] Success")

    # Create Correlation Matrix
    filter_col = [col for col in nav_only if col.endswith("_ret")]
    nav_matrix = nav_only[filter_col]
    corr_matrix = nav_matrix.corr(method="pearson").round(2)
    corr_html = corr_matrix.to_html(
        classes="table small text-center", border=0, justify="center"
    )

    # Create series data for HighCharts in scatter plot format
    # series : [{
    #           name: 'NAV / BTC',
    #           color: '[blue]',
    #           data: [[-0.01,-0.02], [0.02, 0.04]]
    # },{
    #           name: .....}]
    series_hc = []
    # Append NAV ticker to list of tickers, remove duplicates
    tickers.append("NAV")
    tickers = list(set(tickers))
    for ticker in tickers:
        tmp_dict = {}
        if ticker == market:
            continue
        tmp_dict["name"] = "x: " + market + ", y: " + ticker
        tmp_dict["regression"] = 1
        tmp_df = nav_matrix[[market + "_ret", ticker + "_ret"]]
        tmp_df.fillna(0, inplace=True)
        tmp_dict["data"] = list(
            zip(tmp_df[market + "_ret"], tmp_df[ticker + "_ret"]))
        series_hc.append(tmp_dict)

    # Now, let's return the data in the correct format as requested
    return jsonify(
        {
            "chart_data": series_hc,
            "messages": messages,
            "meta_data": meta_data,
            "table": table,
            "corr_html": corr_html,
        }
    )


@api.route("/transactionsandcost_json", methods=["GET"])
@login_required
# Return daily data on transactions and cost for a single ticker
# Takes arguments:
# ticker   - single ticker for filter
# start    - start date in the format YYMMDD (defaults to 1st transaction on ticker)
# end      - end date in the format YYMMDD (defaults to today)
def transactionsandcost_json():
    # Get arguments and assign values if needed
    if request.method == "GET":
        start_date = request.args.get("start")
        ticker = request.args.get("ticker")

        # Check if start and end dates exist, if not assign values
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(
                f"[transactionsandcost_json] Warning: {e}, " +
                "setting start_date to zero"
            )
            start_date = datetime(2000, 1, 1)

        end_date = request.args.get("end")

        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(
                f"[transactionsandcost_json] Warning: {e}, " +
                "setting end_date to now"
            )
            end_date = datetime.now()

    # Get Transaction List
    df = transactions_fx()
    # Filter only to requested ticker
    # if no ticker, use BTC as default, if not BTC then the 1st in list
    tickers = df.trade_asset_ticker.unique().tolist()
    try:
        tickers.remove(current_user.fx())
    except ValueError:
        pass

    if not ticker:
        if "BTC" in tickers:
            ticker = "BTC"
        else:
            ticker = tickers[0]

    # Filter only the trades for current user
    df = df[(df.trade_asset_ticker == ticker)]
    # Filter only buy and sells, ignore deposit / withdraw
    # For now, including Deposits and Withdrawns as well but
    # may consider only B and S as line below.
    df = df[(df.trade_operation == "B") | (df.trade_operation == "S")]
    df.drop("user_id", axis=1, inplace=True)
    # Create a cash_flow column - so we can calculate
    # average price for days with multiple buys and/or sells
    df["cash_flow"] = df["trade_quantity"] * \
        df["trade_price_fx"] + df["trade_fees_fx"]

    # Consolidate all transactions from a single day by grouping
    df = df.groupby(["date"])[["cash_value", "trade_fees",
                                     "trade_quantity", "cash_value_fx"]].agg([
                                        "sum", "count"])
    # Remove the double index for column and consolidate under one row
    df.columns = ["_".join(col).strip() for col in df.columns.values]

    # Filter to Start and End Dates passed as arguments
    mask = (df.index >= start_date) & (df.index <= end_date)
    df = df.loc[mask]

    # ---------------------------------------------------------
    # Get price of ticker passed as argument and merge into df
    message = {}
    data = price_data_fx(ticker)
    # If notification is an error, skip this ticker
    if data is None:
        messages = data.errors
        return jsonify(messages)

    data = data.rename(columns={'close_converted': ticker})
    data = data.astype(float)

    # Create a DF, fill with dates and fill with operation and prices
    start_date = df.index.min()
    daily_df = pd.DataFrame(columns=["date"])
    daily_df["date"] = pd.date_range(start=start_date, end=end_date)
    daily_df = daily_df.set_index("date")
    # Fill dailyNAV with prices for each ticker
    daily_df = pd.merge(daily_df, df, on="date", how="left")
    daily_df.fillna(0, inplace=True)
    if type(daily_df) != type(data):
        data = data.to_frame()

    daily_df = pd.merge(daily_df, data, on="date", how="left")
    daily_df[ticker].fillna(method="ffill", inplace=True)
    message = "ok"
    logging.info(f"[transactionandcost_json] {ticker}: Success - Merged OK")
    # ---------------------------------------------------------
    # Create additional columns on df
    # ---------------------------------------------------------
    daily_df.loc[daily_df.trade_quantity_sum > 0, "traded"] = 1
    daily_df.loc[daily_df.trade_quantity_sum <= 0, "traded"] = 0
    daily_df["q_cum_sum"] = daily_df["trade_quantity_sum"].cumsum()
    daily_df["cv_cum_sum"] = daily_df["cash_value_sum"].cumsum()
    daily_df["cv_fx_cum_sum"] = daily_df["cash_value_fx_sum"].cumsum()
    daily_df["avg_cost"] = daily_df["cv_fx_cum_sum"] / daily_df["q_cum_sum"]
    daily_df["price_over_cost_usd"] = daily_df[ticker] - daily_df["avg_cost"]
    daily_df["price_over_cost_perc"] = (
        daily_df[ticker] / daily_df["avg_cost"]) - 1
    daily_df["impact_on_cost_usd"] = daily_df["avg_cost"].diff()
    daily_df["impact_on_cost_per"] = daily_df["impact_on_cost_usd"] / \
        daily_df[ticker]
    # Remove cost if position is too small - this avoids large numbers
    # Also, remove cost calculation if positions are open (from zero)
    daily_df.loc[daily_df.q_cum_sum <= 0.009, "price_over_cost_usd"] = np.NaN
    daily_df.loc[daily_df.q_cum_sum <= 0.009, "avg_cost"] = np.NaN
    daily_df.loc[daily_df.q_cum_sum.shift(
        1) <= 0.009, "impact_on_cost_usd"] = np.NaN
    daily_df.loc[daily_df.q_cum_sum <= 0.009, "impact_on_cost_usd"] = np.NaN
    daily_df.loc[daily_df.q_cum_sum <= 0.009, "impact_on_cost_per"] = np.NaN

    return_dict = {}
    return_dict["data"] = daily_df.to_json()
    return_dict["message"] = message
    return_dict["fx"] = fxsymbol(current_user.fx())
    logging.info(f"[transactionandcost_json] Success generating data")
    return jsonify(return_dict)


@api.route("/heatmapbenchmark_json", methods=["GET"])
@login_required
# Return Monthly returns for Benchmark and Benchmark difference from NAV
# Takes arguments:
# ticker   - single ticker for filter
def heatmapbenchmark_json():

    # Get portfolio data first
    heatmap_gen, heatmap_stats, years, cols = heatmap_generator()

    # Now get the ticker information and run comparison
    if request.method == "GET":
        ticker = request.args.get("ticker")
        # Defaults to king BTC
        if not ticker:
            ticker = "BTC"

    # Gather the first trade date in portfolio and store
    # used to match the matrixes later
    # Panda dataframe with transactions
    df = pd.read_sql_table("trades", db.engine)
    df = df[(df.user_id == current_user.username)]
    # Filter the df acccoring to filter passed as arguments
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    start_date = df["trade_date"].min()
    start_date -= timedelta(days=1)  # start on t-1 of first trade

    # Generate price Table now for the ticker and trim to match portfolio
    data = price_data_fx(ticker)
    mask = data.index >= start_date
    data = data.loc[mask]

    # If notification is an error, skip this ticker
    if data is None:
        messages = data.errors
        return jsonify(messages)

    data = data.rename(columns={'close_converted': ticker+'_price'})
    data = data[[ticker+'_price']]
    data.sort_index(ascending=True, inplace=True)
    data["pchange"] = (data / data.shift(1)) - 1
    # Run the mrh function to generate heapmap table
    heatmap = mrh.get(data["pchange"], eoy=True)
    heatmap_stats = heatmap
    cols = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "eoy",
    ]
    cols_months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    years = heatmap.index.tolist()
    # Create summary stats for the Ticker
    heatmap_stats["MAX"] = heatmap_stats[heatmap_stats[cols_months] != 0].max(
        axis=1)
    heatmap_stats["MIN"] = heatmap_stats[heatmap_stats[cols_months] != 0].min(
        axis=1)
    heatmap_stats["POSITIVES"] = heatmap_stats[heatmap_stats[cols_months] > 0].count(
        axis=1
    )
    heatmap_stats["NEGATIVES"] = heatmap_stats[heatmap_stats[cols_months] < 0].count(
        axis=1
    )
    heatmap_stats["POS_MEAN"] = heatmap_stats[heatmap_stats[cols_months] > 0].mean(
        axis=1
    )
    heatmap_stats["NEG_MEAN"] = heatmap_stats[heatmap_stats[cols_months] < 0].mean(
        axis=1
    )
    heatmap_stats["MEAN"] = heatmap_stats[heatmap_stats[cols_months] != 0].mean(
        axis=1)

    # Create the difference between the 2 df - Pandas is cool!
    heatmap_difference = heatmap_gen - heatmap

    # return (heatmap, heatmap_stats, years, cols, ticker, heatmap_diff)
    return simplejson.dumps(
        {
            "heatmap": heatmap.to_dict(),
            "heatmap_stats": heatmap_stats.to_dict(),
            "cols": cols,
            "years": years,
            "ticker": ticker,
            "heatmap_diff": heatmap_difference.to_dict(),
        },
        ignore_nan=True,
        default=datetime.isoformat,
    )


@api.route("/drawdown_json", methods=["GET"])
@login_required
# Return the largest drawdowns in a time period
# Takes arguments:
# ticker:       Single ticker for filter (default = NAV)
# start_date:   If none, defaults to all available
# end_date:     If none, defaults to today
# n_dd:         Top n drawdowns to be calculated
# chart:        Boolean - return data for chart
def drawdown_json():
    # Get the arguments and store
    if request.method == "GET":
        start_date = request.args.get("start")
        ticker = request.args.get("ticker")
        n_dd = request.args.get("n_dd")
        chart = request.args.get("chart")
        if not ticker:
            ticker = "NAV"
        ticker = ticker.upper()
        if n_dd:
            try:
                n_dd = int(n_dd)
            except TypeError:
                n_dd = 2
        if not n_dd:
            n_dd = 2
        # Check if start and end dates exist, if not assign values
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(f"Warning: {e}, " + "setting start_date to zero")
            start_date = datetime(2000, 1, 1)

        end_date = request.args.get("end")
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logging.info(f"Warning: {e}, " + "setting end_date to now")
            end_date = datetime.now()

    # Create a df with either NAV or ticker prices
    if ticker == "NAV":
        data = generatenav(current_user.username)
        data = data[["NAV_fx"]]
        data = data.rename(columns={'NAV_fx': 'close'})
    else:
        # Get price of ticker passed as argument
        message = {}
        data = price_data_fx(ticker)
        # If notification is an error, skip this ticker
        if data is None:
            messages = data.errors
            return jsonify(messages)
        data = data.rename(columns={'close_converted': ticker+'_price'})
        data = data[[ticker+'_price']]
        data = data.astype(float)
        data.sort_index(ascending=True, inplace=True)
        data = data.rename(columns={ticker+'_price': 'close'})
    # Trim the df only to start_date to end_date:
    mask = (data.index >= start_date) & (data.index <= end_date)
    data = data.loc[mask]
    # # Calculate drawdowns
    # df = 100 * (1 + data / 100).cumprod()

    df = pd.DataFrame()
    df["close"] = data['close']
    df["ret"] = df.close / df.close[0]
    df["modMax"] = df.ret.cummax()
    df["modDD"] = (df.ret / df["modMax"]) - 1
    # Starting date of the currency modMax
    df["end_date"] = df.index
    # is this the first occurence of this modMax?
    df["dup"] = df.duplicated(["modMax"])

    # Now, exclude the drawdowns that have overlapping data, keep only highest
    df_group = df.groupby(["modMax"]).min().sort_values(
        by="modDD", ascending=True)
    # Trim to fit n_dd
    df_group = df_group.head(n_dd)
    # Format a dict for return
    return_list = []
    for index, row in df_group.iterrows():
        # access data using column names
        tmp_dict = {}
        tmp_dict["dd"] = row["modDD"]
        tmp_dict["start_date"] = row["end_date"].strftime("%Y-%m-%d")
        tmp_dict["end_value"] = row["close"]
        tmp_dict["recovery_date"] = (
            df[df.modMax == index].tail(1).end_date[0].strftime("%Y-%m-%d")
        )
        tmp_dict["end_date"] = (
            df[df.close == row["close"]].tail(
                1).end_date[0].strftime("%Y-%m-%d")
        )
        tmp_dict["start_value"] = df[df.index ==
                                     row["end_date"]].tail(1).close[0]
        tmp_dict["days_to_recovery"] = (
            df[df.modMax == index].tail(1).end_date[0] - row["end_date"]
        ).days
        tmp_dict["days_to_bottom"] = (
            df[df.close == row["close"]].tail(1).end_date[0] - row["end_date"]
        ).days
        tmp_dict["days_bottom_to_recovery"] = (
            df[df.modMax == index].tail(1).end_date[0] -
            df[df.close == row["close"]].tail(1).end_date[0]
        ).days
        return_list.append(tmp_dict)

    if chart:
        start_date = data.index.min()
        total_days = (end_date - start_date).days
        # dates need to be in Epoch time for Highcharts
        data.index = (data.index - datetime(1970, 1, 1)).total_seconds()
        data.index = data.index * 1000
        data.index = data.index.astype(np.int64)
        data = data.to_dict()
        # Generate the flags for the chart
        # {
        #         x: 1500076800000,
        #         title: 'TEST',
        #         text: 'TEST text'
        # }
        flags = []
        plot_bands = []
        # Create a dict for flags and plotBands on chart
        total_recovery_days = 0
        total_drawdown_days = 0
        for item in return_list:
            # First the start date for all dd
            tmp_dict = {}
            start_date = datetime.strptime(item["start_date"], "%Y-%m-%d")
            start_date = (start_date - datetime(1970, 1, 1)
                          ).total_seconds() * 1000
            tmp_dict["x"] = start_date
            tmp_dict["title"] = "TOP"
            tmp_dict["text"] = "Start of drawdown"
            flags.append(tmp_dict)
            # Now the bottom for all dd
            tmp_dict = {}
            end_date = datetime.strptime(item["end_date"], "%Y-%m-%d")
            end_date = (end_date - datetime(1970, 1, 1)
                        ).total_seconds() * 1000
            tmp_dict["x"] = end_date
            tmp_dict["title"] = "BOTTOM"
            tmp_dict["text"] = "Bottom of drawdown"
            flags.append(tmp_dict)
            # Now the bottom for all dd
            tmp_dict = {}
            recovery_date = datetime.strptime(
                item["recovery_date"], "%Y-%m-%d")
            recovery_date = (
                recovery_date - datetime(1970, 1, 1)
            ).total_seconds() * 1000
            tmp_dict["x"] = recovery_date
            tmp_dict["title"] = "RECOVERED"
            tmp_dict["text"] = "End of drawdown Cycle"
            flags.append(tmp_dict)
            # Now create the plot bands
            drop_days = (end_date - start_date) / 1000 / 60 / 60 / 24
            recovery_days = (recovery_date - end_date) / 1000 / 60 / 60 / 24
            total_drawdown_days += round(drop_days, 0)
            total_recovery_days += round(recovery_days, 0)
            tmp_dict = {}
            tmp_dict["label"] = {}
            tmp_dict["label"]["align"] = "center"
            tmp_dict["label"]["textAlign"] = "left"
            tmp_dict["label"]["rotation"] = 90
            tmp_dict["label"]["text"] = "Lasted " + \
                str(round(drop_days, 0)) + " days"
            tmp_dict["label"]["style"] = {}
            tmp_dict["label"]["style"]["color"] = "white"
            tmp_dict["label"]["style"]["fontWeight"] = "bold"
            tmp_dict["color"] = "#E6A68E"
            tmp_dict["from"] = start_date
            tmp_dict["to"] = end_date
            plot_bands.append(tmp_dict)
            tmp_dict = {}
            tmp_dict["label"] = {}
            tmp_dict["label"]["rotation"] = 90
            tmp_dict["label"]["align"] = "center"
            tmp_dict["label"]["textAlign"] = "left"
            tmp_dict["label"]["text"] = (
                "Lasted " + str(round(recovery_days, 0)) + " days"
            )
            tmp_dict["label"]["style"] = {}
            tmp_dict["label"]["style"]["color"] = "white"
            tmp_dict["label"]["style"]["fontWeight"] = "bold"
            tmp_dict["color"] = "#8CADE1"
            tmp_dict["from"] = end_date
            tmp_dict["to"] = recovery_date
            plot_bands.append(tmp_dict)

        return jsonify(
            {
                "chart_data": data['close'],
                "messages": "OK",
                "chart_flags": flags,
                "plot_bands": plot_bands,
                "days": {
                    "recovery": total_recovery_days,
                    "drawdown": total_drawdown_days,
                    "trending": total_days - total_drawdown_days - total_recovery_days,
                    "non_trending": total_drawdown_days + total_recovery_days,
                    "total": total_days,
                },
            }
        )

    return simplejson.dumps(return_list)


@MWT(10)
@api.route("/test_tor", methods=["GET"])
# Tests for Tor and sends back stats
# response = {
#         "pre_proxy": [pre_proxy IP],
#         "post_proxy": [post_proxy IP],
#         "post_proxy_ping": [post_proxy_ping time],
#         "pre_proxy_ping": [pre_proxy_ping time],
#         "difference": [in seconds],
#         "status": [True or False],
#     }
def test_tor_api():
    response = test_tor()
    return simplejson.dumps(response)


@MWT(10)
@api.route("/test_dojo", methods=["GET"])
# Test for DOJO and makes some tests
def test_dojo():
    logging.info("[API] Testing Dojo")
    auto = dojo_auth(True)
    try:
        user_info = User.query.filter_by(
            username=current_user.username).first()
    except AttributeError:
        return "User not logged in"
    onion = user_info.dojo_onion
    apikey = user_info.dojo_apikey

    if not onion:
        onion = "empty"

    if not apikey:
        apikey = "empty"

    response = {"onion_address": onion, "APIKey": apikey, "dojo_auth": auto}
    return simplejson.dumps(response)


@api.route("/oxt_get_address", methods=["GET"])
# Takes argument [addr] and returns OXT output
# The request is sent through Tor only and fails if Tor is not enabled
def gettransaction_oxt():
    addr = request.args.get("addr")
    if not addr:
        return "Error: Address needs to be provided"
    return json.dumps((oxt_get_address(addr)))


@api.route("/get_address", methods=["GET", "POST"])
# Check address on database, get request method and return values
# If success, include the last check data in the database
# Return new updated values and alert if changes detected
# If success, returns:
# address_data:     . previous_check
#                   . previous_balance
#                   . last_check
#                   . last_balance
# change:           boolean (if changed)
# success:          boolean
# method:           Dojo or OXT
def get_address():
    if request.method == "GET":
        return "This method does not accept GET requests"
    meta = {}
    # get address from POST request
    address = request.form["address"]
    # Check if this is an HD address
    hd_address_list = ("xpub", "ypub", "zpub")
    if address.lower().startswith(hd_address_list):
        hd_address = True
        # Get address data from DB
        address_data = (
            AccountInfo.query.filter_by(user_id=current_user.username)
            .filter_by(account_blockchain_id=address)
            .first()
        )
    else:
        hd_address = False
        # Get address data from DB
        address_data = (
            BitcoinAddresses.query.filter_by(user_id=current_user.username)
            .filter_by(address_hash=address)
            .first()
        )
    # methods: 1: Dojo, 2: OXT, 3: Dojo then OXT
    # START DOJO Method
    if address_data is None:
        return "(error) address method is invalid."
    try_again = False
    if (address_data.check_method == "1") or (address_data.check_method == "3"):
        at = dojo_get_settings()["token"]
        if hd_address:
            dojo = dojo_get_hd(address, at)
            # Response:
            # {"status":"ok","data":{"balance":0,"unused":{"external":0,"internal":0},"derivation":"BIP44","created":1563110509}}
        else:
            dojo = dojo_get_txs(address, at)
        method = "Dojo"

        # Store current check into previous fields to detect changes
        ad = {}
        ad["previous_check"] = address_data.previous_check = address_data.last_check
        ad["previous_balance"] = address_data.previous_balance = s_to_f(
            address_data.last_balance
        )
        ad["last_check"] = address_data.last_check = datetime.now()

        try:
            if hd_address:
                try:
                    dojo = dojo.json()
                    dojo_balance = s_to_f(dojo["data"]["balance"])
                    meta["xpub_data"] = dojo["data"]
                    meta["xpub_status"] = dojo["status"]
                    address_data.xpub_derivation = dojo["data"]["derivation"]
                    address_data.xpub_created = dojo["data"]["created"]
                except (AttributeError, KeyError):
                    logging.error("Error when passing Dojo data as json")

            else:
                dojo_balance = s_to_f(dojo["balance"])
        except (KeyError, TypeError):
            if address_data.check_method == "3":
                address_data.check_method = "2"
                try_again = True  # Bump next steps and try with OXT
            else:
                return "error"
        if not try_again:
            ad["last_balance"] = address_data.last_balance = s_to_f(
                dojo_balance)
            if address_data.last_balance != address_data.previous_balance:
                change = True
            else:
                change = False
            db.session.commit()
            regenerate_nav()
            success = True
            return jsonify(
                {
                    "address_data": ad,
                    "change": change,
                    "success": success,
                    "method": method,
                    "meta": meta,
                }
            )

    if address_data.check_method == "2":
        oxt = oxt_get_address(address)
        method = "OXT"
        if "message" in oxt:
            if oxt["message"] == "Nothing found for this address. Please try later.":
                return "error"

        if "status" in oxt:
            return "error"
        # Store current check into previous fields to detect changes
        ad = {}
        ad["previous_check"] = address_data.previous_check = address_data.last_check
        ad[
            "previous_balance"
        ] = address_data.previous_balance = address_data.last_balance
        ad["last_check"] = address_data.last_check = datetime.now()
        data_oxt = oxt["data"]
        ad["last_balance"] = address_data.last_balance = s_to_f(
            data_oxt[0]["stats"]["bl"]
        )
        if address_data.last_balance != address_data.previous_balance:
            change = True
        else:
            change = False
        db.session.commit()
        regenerate_nav()
        success = True

        return jsonify(
            {"address_data": ad, "change": change,
                "success": success, "method": method}
        )

    return "error"


@api.route("/getprice_ondate", methods=["GET"])
@login_required
# Return the price of a ticker on a given date
# Takes arguments:
# ticker:       Single ticker for filter (default = NAV)
# date:         date to get price
def getprice_ondate():
    # Get the arguments and store
    if request.method == "GET":
        date_input = request.args.get("date")
        ticker = request.args.get("ticker")
        if (not ticker) or (not date_input):
            return 0
        ticker = ticker.upper()
        get_date = datetime.strptime(date_input, "%Y-%m-%d")
        return price_ondate(ticker, get_date)


@api.route("/import_transaction", methods=["POST"])
@login_required
# Imports transactions into the database using a post method
# Values expected
def import_transaction():
    # Convert to json
    jsonData = request.get_json()
    # Import into the database
    for item in jsonData:
        # Check if in database
        transaction_id = jsonData[item]["trade_blockchain_id"]
        find_match = (
            Trades.query.filter_by(user_id=current_user.username)
            .filter_by(trade_blockchain_id=transaction_id)
            .first()
        )
        if find_match is not None:
            flash(
                f"Transaction not imported. Exists in database: {transaction_id[0:6]}...",
                "danger",
            )
            continue

        try:
            try:
                price = float(jsonData[item]["trade_price"].replace(",", ""))
            except KeyError:
                flash(
                    f"Error: No price found when importing transaction {jsonData[item]['trade_blockchain_id'][0:6]}",
                    "danger",
                )
                continue
            quant = jsonData[item]["trade_quantity"]
            cv = price * quant
        except (AttributeError, ValueError):
            cv = 0

        # Create the database object
        # Check if date in epoch or not
        try:
            trade_date = datetime.fromtimestamp(
                int(jsonData[item]["trade_date"]))  # Epoch worked
        except ValueError:
            trade_date = parser.parse(jsonData[item]["trade_date"])

        new_trade = Trades(
            user_id=current_user.username,
            trade_inputon=parser.parse(jsonData[item]["trade_inputon"]),
            trade_quantity=quant,
            trade_operation=jsonData[item]["trade_operation"],
            trade_currency=jsonData[item]["trade_currency"],
            trade_fees=jsonData[item]["trade_fees"],
            trade_asset_ticker=jsonData[item]["trade_asset_ticker"],
            trade_price=price,
            trade_date=trade_date,  # epoch date to dateTime
            trade_blockchain_id=jsonData[item]["trade_blockchain_id"],
            trade_account=jsonData[item]["trade_account"],
            trade_notes=jsonData[item]["trade_notes"],
            cash_value=cv,
            trade_reference_id=secrets.token_hex(21),
        )

        try:
            db.session.add(new_trade)
            db.session.commit()
            regenerate_nav()
            flash(
                f"Transaction included. {transaction_id[0:6]}...", "success")
        except Exception as e:
            flash(
                f"Error: {e} when importing transaction {jsonData[item]['trade_blockchain_id'][0:6]}",
                "danger",
            )

    logging.info("Import done")
    # logging.info(get_flashed_messages())
    # return json.dumps(get_flashed_messages(with_categories=true))
    return json.dumps("OK")


@api.route("/addresses_importer", methods=["POST"])
@login_required
# Imports transactions into the database using a post method
# Values expected
def addresses_importer():
    if request.method == "GET":
        return "This method does not accept GET requests"
    data = request.form
    for item in data:
        loader = json.loads(item)
    main_account = loader["account"]
    # Dojo takes a pipe separated string as input for multiaddress
    dojo_list = loader["address_list"].replace(",", "|")
    address_list = loader["address_list"].split(",")
    meta = {}
    meta["main_account"] = main_account
    meta["address_list"] = address_list
    # send a multiaddress request to Dojo
    at = dojo_get_settings()["token"]
    dojo = dojo_multiaddr(dojo_list, "active", at)
    try:
        dojo = dojo.json()
    except AttributeError:
        pass

    meta["dojo"] = dojo
    # If data received back ok, import addresses into the db, if not return error
    if "error" in dojo:
        return json.dumps(meta)
    meta["status"] = {}
    # Loop through addresses found in Dojo and include in monitor database
    counter = 0
    for item in dojo["addresses"]:
        address_info = {}
        address_info["message"] = "Found and Imported"
        # Is this a pubkey address or HD address?
        # HD addresses are included as accounts (since they can hold pubkey addresses)
        # pubkey addresses included in the bitcoinaddress table
        hd_address_list = ("xpub", "ypub", "zpub")
        address = item["address"]

        # HD Address Handling
        if address.lower().startswith(hd_address_list):
            address_info["hd"] = True
            search_add = AccountInfo.query.filter_by(
                user_id=current_user.username
            ).filter_by(account_blockchain_id=address)
            if search_add.count() > 0:
                address_info["message"] = "NOT imported. Already in database."
                meta["status"][item["address"]] = address_info
                continue
            counter += 1
            bitcoin_address = AccountInfo(
                user_id=current_user.username,
                account_longname="HD Wallet " + str(counter),
                check_method="1",
                auto_check=True,
                account_blockchain_id=address,
                last_check=datetime.now(),
                last_balance=s_to_f(item["final_balance"]),
                notes="Account imported using the Dojo through multi address import page",
            )
        # Bitcoin Address Handling - Not HD
        else:
            # check if this address is already in the database
            address_info["hd"] = False
            search_add = BitcoinAddresses.query.filter_by(
                user_id=current_user.username
            ).filter_by(address_hash=address)
            if search_add.count() > 0:
                address_info["message"] = "NOT imported. Already in database."
                meta["status"][item["address"]] = address_info
                continue
            bitcoin_address = BitcoinAddresses(
                user_id=current_user.username,
                address_hash=address,
                check_method="1",
                account_id=meta["main_account"],
                auto_check=True,
                imported_from_hdaddress="",
                last_check=datetime.now(),
                last_balance=s_to_f(item["final_balance"]),
                notes="Imported using the Dojo through multi address import page",
            )

        try:
            db.session.add(bitcoin_address)
            db.session.commit()
            regenerate_nav()
            address_info["message"] = "Found and Imported"
        except Exception as e:
            logging.info(f"Error importing: {e}")
            address_info["message"] = f"NOT imported. Error: {e}."
        meta["status"][item["address"]] = address_info

    # return a list of addresses not found in the Dojo
    for add in address_list:
        if add not in meta["status"]:
            meta["status"][add] = "Not found"

    return json.dumps(meta)


@api.route("/test_aakey", methods=["GET"])
# gets key argument and returns test results
# {status: "success", message:"price on .... is...."}
# {status: "failed", message:"NO API Key"}
# {status: "failed", message:"Connection Error"}
# {status: "failed", message:"{e}"}
# https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=BTC&to_currency=USD&apikey=ddd
def test_aakey():
    # Test Variables
    api_key = request.args.get("key")
    data = {"status": "failed", "message": "Empty"}
    if api_key is not None:
        baseURL = "https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=BTC&to_currency=USD&apikey="
        globalURL = baseURL + api_key
        try:
            logging.info(f"[ALPHAVANTAGE] Requesting URL: {globalURL}")
            api_request = tor_request(globalURL)
            data["status"] = "success"
        except requests.exceptions.ConnectionError:
            logging.error(
                "[ALPHAVANTAGE] Connection ERROR " +
                "while trying to download prices"
            )
            data["status"] = "failed"
            data["message"] = "Connection Error"
        try:
            data["message"] = api_request.json()
            # Success - store this in database
            current_user.aa_apikey = api_key
            db.session.commit()
            regenerate_nav()
        except AttributeError:
            data["message"] = api_request
    return json.dumps(data)


@api.route("/dojo_autoconfig", methods=["GET"])
# Registers an onion and api key to the database and saves for this username
def dojo_autoconfig():
    if (request.args.get("onion") != "") and (request.args.get("api_key") != ""):
        current_user.dojo_onion = request.args.get("onion")
        current_user.dojo_apikey = request.args.get("api_key")
        db.session.commit()
        return json.dumps("Success")
    else:
        return json.dumps("Failed. Empty field.")


@api.route("/fx_lst", methods=["GET"])
# Receiver argument ?term to return a list of fx (fiat and digital)
# Searches the list both inside the key as well as value of dict
def fx_list():
    fx_dict = {}
    with open('thewarden/static/csv_files/physical_currency_list.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        fx_dict = {rows[0]: rows[1] for rows in reader}
    q = request.args.get("term")
    if q is None:
        q = ""
    list_key = {key: value for key, value in fx_dict.items() if q.upper() in key.upper()}
    list_value = {key: value for key, value in fx_dict.items() if q.upper() in value.upper()}
    list = {**list_key, **list_value}
    list = json.dumps(list)
    return list

# ------------------------------------
# API Helpers for Bitmex start here
# ------------------------------------


@api.route("/test_bitmex", methods=["GET"])
# receives api_key and api_secret then saves to a local json for later use
# returns in message - user details
def test_bitmex():
    api_key = request.args.get("api_key")
    api_secret = request.args.get("api_secret")
    if (api_key is None) or (api_secret is None):
        return ({'status': 'error', 'message': 'API credentials not found'})

    # First test and return result
    testnet = False
    mex = bitmex(test=testnet, api_key=api_key, api_secret=api_secret)
    try:
        resp = mex.User.User_get().result()[0]
        # Save locally to json
        bitmex_data = {"api_key": api_key, "api_secret": api_secret}
        with open('thewarden/api/bitmex.json', 'w') as fp:
            json.dump(bitmex_data, fp)
        logging.info("Credentials saved to bitmex.json")
        return ({'status': 'success', 'message': resp})
    except Exception as e:
        return ({'status': 'error', 'message': f'Error when connecting to Bitmex. Check credentials. Error: {e}'})


@api.route("/load_bitmex_json", methods=["GET"])
# returns current stored keys if any
def load_bitmex_json():
    # First check if API key and secret are stored locally
    try:
        with open('thewarden/api/bitmex.json', 'r') as fp:
            data = json.load(fp)
            return (data)
    except (FileNotFoundError, KeyError):
        return ({'status': 'error', 'message': 'API credentials not found'})


@MWT(20)
@api.route("/realtime_user", methods=["GET"])
# Returns current BTC price and FX rate for current user
def realtime_user():
    try:
        # get fx rate
        fx_rate = rt_price_grab('BTC', current_user.fx())
        fx_rate['base'] = current_user.fx()
        fx_rate['fx_rate'] = fx_rate[current_user.fx()] / fx_rate['USD']
        fx_rate['cross'] = "USD" + " / " + current_user.fx()
        return json.dumps(fx_rate)
    except Exception as e:
        return (f"Error: {e}")


@api.route("/test_pricing", methods=["GET"])
def test_pricing():
    from thewarden.pricing_engine.pricing import PROVIDER_LIST, PriceData
    provider = PROVIDER_LIST['cc_digital']
    fx_provider = PROVIDER_LIST['cc_fx']
    a = PriceData("BTC", provider)
    print (a.df)
    print (a.errors)
    print (provider.errors)
    merge_fx = a.df_fx('BRL', fx_provider)
    print (merge_fx)
    return ("OK")