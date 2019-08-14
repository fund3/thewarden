import configparser
import csv
import hashlib
import json
import logging
import os
import pickle
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
from flask import flash, url_for
from flask_login import current_user
from flask_mail import Message

from thewarden import db, mail
from thewarden import mhp as mrh
from thewarden.models import Trades, User
from thewarden.node.utils import tor_request
from thewarden.users.decorators import MWT, memoized, timing

# ---------------------------------------------------------
# Helper Functions start here
# ---------------------------------------------------------

# --------------------------------------------
# Read Global Variables from config(s)
# Include global variables and error handling
# --------------------------------------------
config = configparser.ConfigParser()
config.read('config.ini')
try:
    RENEW_NAV = config['MAIN']['RENEW_NAV']
except KeyError:
    RENEW_NAV = 10
    logging.error("Could not find RENEW_NAV at config.ini. Defaulting to 60.")
try:
    PORTFOLIO_MIN_SIZE_NAV = config['MAIN']['PORTFOLIO_MIN_SIZE_NAV']
except KeyError:
    PORTFOLIO_MIN_SIZE_NAV = 5
    logging.error("Could not find PORTFOLIO_MIN_SIZE_NAV at config.ini." +
                  " Defaulting to 5.")


@memoized
@timing
def multiple_price_grab(tickers, fx):
    # tickers should be in comma sep string format like "BTC,ETH,LTC"
    baseURL = \
        "https://min-api.cryptocompare.com/data/pricemultifull?fsyms="\
        + tickers+"&tsyms="+fx+",BTC"
    try:
        request = tor_request(baseURL)
    except requests.exceptions.ConnectionError:
        return ("ConnectionError")
    try:
        data = request.json()
    except AttributeError:
        data = "ConnectionError"
    return (data)


def rt_price_grab(ticker, user_fx='USD'):
    baseURL =\
        "https://min-api.cryptocompare.com/data/price?fsym=" + ticker + \
        "&tsyms=USD,BTC," + user_fx
    request = tor_request(baseURL)
    try:
        data = request.json()
    except AttributeError:
        data = "ConnectionError"
    return (data)


@MWT(timeout=30)
@timing
def cost_calculation(user, ticker):
    # This function calculates the cost basis assuming 3 different methods
    # FIFO, LIFO and avg. cost
    # found = [item for item in fx_list() if ticker in item]
    # if found != []:
    #     return (0)

    # Gets all transactions in local currency terms
    df = transactions_fx()
    df = df[(df.trade_asset_ticker == ticker)]

    # Find current open position on asset
    summary_table = df.groupby(['trade_asset_ticker', 'trade_operation'])[
        ["cash_value", "cash_value_fx", "trade_fees", "trade_quantity"]].sum()

    open_position = summary_table.sum()['trade_quantity']

    # Drop Deposits and Withdraws - keep only Buy and Sells
    if open_position > 0:
        df = df[df.trade_operation.str.match('B')]
    elif open_position < 0:
        df = df[df.trade_operation.str.match('S')]

    # Let's return a dictionary for this user with FIFO, LIFO and Avg. Cost
    cost_matrix = {}

    # ---------------------------------------------------
    # FIFO
    # ---------------------------------------------------
    fifo_df = df.sort_index(ascending=False)
    fifo_df['acum_Q'] = fifo_df['trade_quantity'].cumsum()
    fifo_df['acum_Q'] = np.where(fifo_df['acum_Q'] < open_position,
                                 fifo_df['acum_Q'], open_position)
    # Keep only the number of rows needed for open position
    fifo_df = fifo_df.drop_duplicates(subset="acum_Q", keep='first')
    fifo_df['Q'] = fifo_df['acum_Q'].diff()
    fifo_df['Q'] = fifo_df['Q'].fillna(fifo_df['trade_quantity'])
    # if fifo_df['acum_Q'].count() == 1:
    #     fifo_df['Q'] = fifo_df['acum_Q']
    # Adjust Cash Value only to account for needed position
    fifo_df['adjusted_cv'] = fifo_df['cash_value_fx'] * fifo_df['Q'] /\
        fifo_df['trade_quantity']
    cost_matrix['FIFO'] = {}
    cost_matrix['FIFO']['cash'] = fifo_df['adjusted_cv'].sum()
    cost_matrix['FIFO']['quantity'] = open_position
    cost_matrix['FIFO']['count'] = int(fifo_df['trade_operation'].count())
    cost_matrix['FIFO']['average_cost'] = fifo_df['adjusted_cv'].sum()\
        / open_position

    # ---------------------------------------------------
    #  LIFO
    # ---------------------------------------------------
    lifo_df = df.sort_index(ascending=True)
    lifo_df['acum_Q'] = lifo_df['trade_quantity'].cumsum()
    lifo_df['acum_Q'] = np.where(lifo_df['acum_Q'] < open_position,
                                 lifo_df['acum_Q'], open_position)
    # Keep only the number of rows needed for open position
    lifo_df = lifo_df.drop_duplicates(subset="acum_Q", keep='first')
    lifo_df['Q'] = lifo_df['acum_Q'].diff()
    lifo_df['Q'] = lifo_df['Q'].fillna(lifo_df['trade_quantity'])
    # if lifo_df['acum_Q'].count() == 1:
    #     lifo_df['Q'] = lifo_df['acum_Q']
    # Adjust Cash Value only to account for needed position
    lifo_df['adjusted_cv'] = lifo_df['cash_value_fx'] * lifo_df['Q'] /\
        lifo_df['trade_quantity']

    cost_matrix['LIFO'] = {}
    cost_matrix['LIFO']['cash'] = lifo_df['adjusted_cv'].sum()
    cost_matrix['LIFO']['quantity'] = open_position
    cost_matrix['LIFO']['count'] = int(lifo_df['trade_operation'].count())
    cost_matrix['LIFO']['average_cost'] = lifo_df['adjusted_cv'].sum() / open_position
    return (cost_matrix)


@MWT(timeout=30)
@timing
def fx_rate():
    # To avoid multiple requests to grab a new FX, the data is
    # saved to a local json file and only refreshed if older than
    # This grabs the current currency against USD
    # REFRESH seconds
    REFRESH = 60
    filename = "thewarden/dailydata/USD_" + current_user.fx() + ".json"
    logging.info(f"[FX] Requesting data for {current_user.fx()}")
    try:
        # Check if NAV saved file is recent enough to be used
        # Local file has to have a saved time less than RENEW_NAV min old
        # See config.ini to change RENEW_NAV
        modified = datetime.utcfromtimestamp(os.path.getmtime(filename))
        elapsed_seconds = (datetime.utcnow() - modified).total_seconds()
        logging.info(f"[FX] Last time file was modified {modified} is " +
                     f" {elapsed_seconds} seconds ago")
        if (elapsed_seconds) < int(REFRESH):
            with open(filename, 'r') as json_data:
                rate = json.load(json_data)
            logging.info(f"[FX] Success: Open {filename} - no need to request")
            return (rate)
        else:
            logging.info("[FX] File found but too old - sending request")

    except FileNotFoundError:
        logging.warn(f"[FX] File not found" +
                     " - rebuilding")
    try:
        # get fx rate
        rate = rt_price_grab('BTC', current_user.fx())
        rate['base'] = current_user.fx()
        rate['fx_rate'] = rate[current_user.fx()] / rate['USD']
        rate['cross'] = "USD" + " / " + current_user.fx()
        with open(filename, 'w') as outfile:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            json.dump(rate, outfile)
            logging.info("[FX] Success - requested fx and saved")
        return (rate)
    except Exception as e:
        rate = {}
        flash(f"An error occured getting fx rate: {e}", "danger")
        rate['error'] = (f"Error: {e}")
        rate['fx_rate'] = 1
        return json.dumps(rate)


@MWT(timeout=10)
def fx():
    # Returns a float with the conversion of fx in the format of
    # Currency / USD
    return (float(fx_rate()['fx_rate']))


@memoized
def to_epoch(in_date):
    return str(int((in_date - datetime(1970, 1, 1)).total_seconds()))


def find_fx(row, fx=None):
    return price_ondate(current_user.fx(), row.name, row['trade_currency'])


@MWT(timeout=20)
@timing
def transactions_fx():
    # Gets the transaction table and fills with fx information
    # Note that it uses the currency exchange for the date of transaction
    # Get all transactions from db and format
    df = pd.read_sql_table('trades', db.engine)
    df = df[(df.user_id == current_user.username)]
    # df = df[(df.trade_operation == "B") | (df.trade_operation == "S")]
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.set_index('trade_date')
    # Ignore times in df to merge - keep only dates
    df.index = df.index.floor('d')
    df.index.rename('date', inplace=True)
    # The current fx needs no conversion, set to 1
    df[current_user.fx()] = 1
    # Need to get currencies into the df in order to normalize
    # let's load a list of currencies needed and merge
    list_of_fx = df.trade_currency.unique().tolist()
    # loop through currency list
    for currency in list_of_fx:
        if currency == current_user.fx():
            continue
        # Make a price request
        df[currency] = df.apply(find_fx, axis=1)
    # Now create a cash value in the preferred currency terms
    df['fx'] = df.apply(lambda x: x[x['trade_currency']], axis=1)
    df['cash_value_fx'] = df['cash_value'].astype(float) / df['fx'].astype(float)
    df['trade_fees_fx'] = df['trade_fees'].astype(float) / df['fx'].astype(float)
    return (df)


@MWT(timeout=5)
@timing
def generate_pos_table(user, fx, hidesmall):
    # This function creates all relevant data for the main page
    # Including current positions, cost and other market info
    # Gets all transactions
    df = transactions_fx()

    # Create string of tickers and grab all prices in one request
    list_of_tickers = df.trade_asset_ticker.unique().tolist()
    ticker_str = ""
    for ticker in list_of_tickers:
        ticker_str = ticker_str + "," + ticker
    price_list = multiple_price_grab(ticker_str, fx)
    if price_list == "ConnectionError":
        return ("ConnectionError", "ConnectionError")

    summary_table = df.groupby(['trade_asset_ticker', 'trade_operation'])[
                                ["cash_value", "trade_fees", "trade_quantity",
                                 "cash_value_fx", "trade_fees_fx"]].sum()

    summary_table['count'] = df.groupby([
        'trade_asset_ticker', 'trade_operation'])[
        "cash_value_fx"].count()

    consol_table = df.groupby(['trade_asset_ticker'])[
                                ["cash_value", "trade_fees",
                                 "trade_quantity", "cash_value_fx",
                                 "trade_fees_fx"]].sum()

    consol_table['symbol'] = consol_table.index.values
    try:
        consol_table = consol_table.drop('USD')
        consol_table = consol_table.drop(current_user.fx())
        if consol_table.empty:
            return ("empty", "empty")

    except KeyError:
        logging.info(f"[generate_pos_table] No USD or {current_user.fx()} positions found")

    def find_price_data(ticker):
        price_data = price_list["RAW"][ticker]['USD']
        return (price_data)

    def find_price_data_BTC(ticker):
        try:
            price_data = price_list["RAW"][ticker]['BTC']
            return (price_data)
        except KeyError:
            return (0)

    consol_table['price_data_USD'] = consol_table['symbol'].\
        apply(find_price_data)
    consol_table['price_data_BTC'] = consol_table['symbol'].\
        apply(find_price_data_BTC)

    consol_table['usd_price'] =\
        consol_table.price_data_USD.map(lambda v: v['PRICE'])
    consol_table['fx_price'] = consol_table['usd_price'] * current_user.fx_rate_USD()

    consol_table['chg_pct_24h'] =\
        consol_table.price_data_USD.map(lambda v: v['CHANGEPCT24HOUR'])
    try:
        consol_table['btc_price'] =\
            consol_table.price_data_BTC.map(lambda v: v['PRICE'])
    except TypeError:
        consol_table['btc_price'] = 0

    consol_table['usd_position'] = consol_table['usd_price'] *\
        consol_table['trade_quantity']
    consol_table['btc_position'] = consol_table['btc_price'] *\
        consol_table['trade_quantity']
    consol_table['fx_position'] = consol_table['usd_position'] * current_user.fx_rate_USD()

    consol_table['chg_usd_24h'] =\
        consol_table['chg_pct_24h']/100*consol_table['usd_position']
    consol_table['chg_fx_24h'] =\
        consol_table['chg_pct_24h']/100*consol_table['fx_position']

    consol_table['usd_perc'] = consol_table['usd_position']\
        / consol_table['usd_position'].sum()
    consol_table['btc_perc'] = consol_table['btc_position']\
        / consol_table['btc_position'].sum()
    consol_table['fx_perc'] = consol_table['fx_position']\
        / consol_table['fx_position'].sum()

    consol_table.loc[consol_table.fx_perc <= 0.01, 'small_pos'] = 'True'
    consol_table.loc[consol_table.fx_perc >= 0.01, 'small_pos'] = 'False'

    # Should rename this to breakeven:
    consol_table['average_cost'] = consol_table['cash_value']\
        / consol_table['trade_quantity']
    consol_table['average_cost_fx'] = consol_table['cash_value_fx']\
        / consol_table['trade_quantity']

    consol_table['total_pnl_gross_USD'] = consol_table['usd_position'] -\
        consol_table['cash_value']
    consol_table['total_pnl_gross_fx'] = consol_table['fx_position'] -\
        consol_table['cash_value_fx']

    consol_table['total_pnl_net_USD'] = consol_table['usd_position'] -\
        consol_table['cash_value'] - consol_table['trade_fees']
    consol_table['total_pnl_net_fx'] = consol_table['fx_position'] -\
        consol_table['cash_value_fx'] - consol_table['trade_fees_fx']

    summary_table['symbol_operation'] = summary_table.index.values
    # This is wrong:
    summary_table['average_price'] = summary_table['cash_value'] /\
        summary_table['trade_quantity']
    summary_table['average_price_fx'] = summary_table['cash_value_fx'] /\
        summary_table['trade_quantity']

    # create a dictionary in a better format to deliver to html table
    table = {}
    table['TOTAL'] = {}
    table['TOTAL']['cash_flow_value'] = summary_table.sum()['cash_value']
    table['TOTAL']['cash_flow_value_fx'] = summary_table.sum()['cash_value_fx']
    table['TOTAL']['avg_fx_rate'] = table['TOTAL']['cash_flow_value_fx'] /\
        table['TOTAL']['cash_flow_value']
    table['TOTAL']['trade_fees'] = summary_table.sum()['trade_fees']
    table['TOTAL']['trade_fees_fx'] = summary_table.sum()['trade_fees_fx']
    table['TOTAL']['trade_count'] = summary_table.sum()['count']
    table['TOTAL']['usd_position'] = consol_table.sum()['usd_position']
    table['TOTAL']['btc_position'] = consol_table.sum()['btc_position']
    table['TOTAL']['fx_position'] = consol_table.sum()['fx_position']
    table['TOTAL']['chg_usd_24h'] = consol_table.sum()['chg_usd_24h']
    table['TOTAL']['chg_fx_24h'] = consol_table.sum()['chg_fx_24h']
    table['TOTAL']['chg_perc_24h'] = ((table['TOTAL']['chg_usd_24h']
                                       / table['TOTAL']['usd_position']))*100
    table['TOTAL']['chg_perc_24h_fx'] = ((table['TOTAL']['chg_fx_24h']
                                       / table['TOTAL']['fx_position']))*100
    table['TOTAL']['total_pnl_gross_USD'] =\
        consol_table.sum()['total_pnl_gross_USD']
    table['TOTAL']['total_pnl_gross_fx'] =\
        consol_table.sum()['total_pnl_gross_fx']
    table['TOTAL']['total_pnl_net_USD'] =\
        consol_table.sum()['total_pnl_net_USD']
    table['TOTAL']['total_pnl_net_fx'] =\
        consol_table.sum()['total_pnl_net_fx']
    table['TOTAL']['refresh_time'] = datetime.now()
    pie_data = []

    # Drop small positions if hidesmall (small position = <0.01%)
    if hidesmall:
        consol_table = consol_table[consol_table.small_pos == 'False']
        list_of_tickers = consol_table.index.unique().tolist()

    for ticker in list_of_tickers:
        # Check if this is a fiat currency. If so, ignore
        found = [item for item in fx_list() if ticker in item]
        if found != []:
            continue

        table[ticker] = {}
        table[ticker]['breakeven'] = 0
        if consol_table['small_pos'][ticker] == 'False':
            tmp_dict = {}
            tmp_dict['y'] = consol_table['fx_perc'][ticker]*100
            tmp_dict['name'] = ticker
            pie_data.append(tmp_dict)
            table[ticker]['breakeven'] = \
                (consol_table['price_data_USD'][ticker]['PRICE'] *
                current_user.fx_rate_USD()) -\
                (consol_table['total_pnl_net_fx'][ticker] /
                 consol_table['trade_quantity'][ticker])

        table[ticker]['cost_matrix'] = cost_calculation(user, ticker)
        table[ticker]['cost_matrix']['LIFO']['unrealized_pnl'] = \
            (consol_table['fx_price'][ticker] -
             table[ticker]['cost_matrix']['LIFO']['average_cost']) * \
            consol_table['trade_quantity'][ticker]
        table[ticker]['cost_matrix']['FIFO']['unrealized_pnl'] = \
            (consol_table['fx_price'][ticker] -
             table[ticker]['cost_matrix']['FIFO']['average_cost']) * \
            consol_table['trade_quantity'][ticker]

        table[ticker]['cost_matrix']['LIFO']['realized_pnl'] = \
            consol_table['total_pnl_net_fx'][ticker] -\
            table[ticker]['cost_matrix']['LIFO']['unrealized_pnl']
        table[ticker]['cost_matrix']['FIFO']['realized_pnl'] = \
            consol_table['total_pnl_net_fx'][ticker] -\
            table[ticker]['cost_matrix']['FIFO']['unrealized_pnl']

        table[ticker]['cost_matrix']['LIFO']['unrealized_be'] =\
            (consol_table['price_data_USD'][ticker]['PRICE'] *
            current_user.fx_rate_USD()) - \
            (table[ticker]['cost_matrix']['LIFO']['unrealized_pnl'] /
             consol_table['trade_quantity'][ticker])
        table[ticker]['cost_matrix']['FIFO']['unrealized_be'] =\
            (consol_table['price_data_USD'][ticker]['PRICE'] *
            current_user.fx_rate_USD()) - \
            (table[ticker]['cost_matrix']['FIFO']['unrealized_pnl'] /
             consol_table['trade_quantity'][ticker])

        table[ticker]['position'] = consol_table['trade_quantity'][ticker]
        table[ticker]['usd_position'] = consol_table['usd_position'][ticker]
        table[ticker]['fx_position'] = consol_table['fx_position'][ticker]
        table[ticker]['chg_pct_24h'] = consol_table['chg_pct_24h'][ticker]
        table[ticker]['chg_usd_24h'] = consol_table['chg_usd_24h'][ticker]
        table[ticker]['chg_fx_24h'] = consol_table['chg_fx_24h'][ticker]
        table[ticker]['usd_perc'] = consol_table['usd_perc'][ticker]
        table[ticker]['btc_perc'] = consol_table['btc_perc'][ticker]
        table[ticker]['fx_perc'] = consol_table['fx_perc'][ticker]
        table[ticker]['total_fees'] = consol_table['trade_fees'][ticker]
        table[ticker]['total_fees_fx'] = consol_table['trade_fees_fx'][ticker]

        table[ticker]['usd_price_data'] =\
            consol_table['price_data_USD'][ticker]
        try:
            table[ticker]['usd_price_data']['LASTUPDATE'] =\
                    (datetime.utcfromtimestamp(table[ticker]['usd_price_data']['LASTUPDATE']).strftime('%H:%M:%S'))
        except TypeError:
            table[ticker]['usd_price_data']['LASTUPDATE'] = 0
        table[ticker]['btc_price'] = consol_table['price_data_BTC'][ticker]
        table[ticker]['total_pnl_gross_USD'] =\
            consol_table['total_pnl_gross_USD'][ticker]
        table[ticker]['total_pnl_gross_fx'] =\
            consol_table['total_pnl_gross_fx'][ticker]
        table[ticker]['total_pnl_net_USD'] =\
            consol_table['total_pnl_net_USD'][ticker]
        table[ticker]['total_pnl_net_fx'] =\
            consol_table['total_pnl_net_fx'][ticker]
        table[ticker]['small_pos'] = consol_table['small_pos'][ticker]
        table[ticker]['cash_flow_value'] =\
            summary_table['cash_value'][ticker].to_dict()
        table[ticker]['cash_flow_value_fx'] =\
            summary_table['cash_value_fx'][ticker].to_dict()
        table[ticker]['trade_fees'] = \
            summary_table['trade_fees'][ticker].to_dict()
        table[ticker]['trade_fees_fx'] = \
            summary_table['trade_fees_fx'][ticker].to_dict()
        table[ticker]['trade_quantity'] = \
            summary_table['trade_quantity'][ticker].to_dict()
        table[ticker]['count'] = summary_table['count'][ticker].to_dict()
        table[ticker]['average_price'] = \
            summary_table['average_price'][ticker].to_dict()
        table[ticker]['average_price_fx'] = \
            summary_table['average_price_fx'][ticker].to_dict()

    return(table, pie_data)


@memoized
def cleancsv(text):  # Function to clean CSV fields - leave only digits and .
    if text is None:
        return (0)
    acceptable = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."]
    str = ""
    for char in text:
        if char in acceptable:
            str = str + char
    str = float(str)
    return(str)


@MWT(timeout=10)
@timing
def generatenav(user, force=False, filter=None):
    logging.info(f"[generatenav] Starting NAV Generator for user {user}")
    # Variables
    # Portfolios smaller than this size do not account for NAV calculations
    # Otherwise, there's an impact of dust left in the portfolio (in USD)
    # This is set in config.ini file
    min_size_for_calc = int(PORTFOLIO_MIN_SIZE_NAV)
    logging.info(f"[generatenav] Force update status is {force}")
    # This process can take some time and it's intensive to run NAV
    # generation every time the NAV is needed. A compromise is to save
    # the last NAV generation locally and only refresh after a period of time.
    # This period of time is setup in config.ini as RENEW_NAV (in minutes).
    # If last file is newer than 60 minutes (default), the local saved file
    # will be used.
    # Unless force is true, then a rebuild is done regardless
    # Local files are  saved under a hash of username.
    if force:
        logging.info("[generatenav] FORCE update is on. Not using local file")
        usernamehash = hashlib.sha256(current_user.username.encode(
            'utf-8')).hexdigest()
        filename = "thewarden/nav_data/"+usernamehash + ".nav"
        logging.info(f"[generatenav] {filename} marked for deletion.")
        # Since this function can be run as a thread, it's safer to delete
        # the current NAV file if it exists. This avoids other tasks reading
        # the local file which is outdated
        try:
            os.remove(filename)
            logging.info("[generatenav] Local NAV file found and deleted")
        except OSError:
            logging.info("[generatenav] Local NAV file was not found" +
                         " for removal - continuing")

    if not force:
        usernamehash = hashlib.sha256(current_user.username.encode(
            'utf-8')).hexdigest()
        filename = "thewarden/nav_data/"+usernamehash + ".nav"
        try:
            # Check if NAV saved file is recent enough to be used
            # Local file has to have a saved time less than RENEW_NAV min old
            # See config.ini to change RENEW_NAV
            modified = datetime.utcfromtimestamp(os.path.getmtime(filename))
            elapsed_seconds = (datetime.utcnow() - modified).total_seconds()
            logging.info(f"Last time file was modified {modified} is " +
                         f" {elapsed_seconds} seconds ago")
            if (elapsed_seconds/60) < int(RENEW_NAV):
                nav_pickle = pd.read_pickle(filename)
                logging.info(f"Success: Open {filename} - no need to rebuild")
                return (nav_pickle)
            else:
                logging.info("File found but too old - rebuilding NAV")

        except FileNotFoundError:
            logging.warn(f"[generatenav] File not found to load NAV" +
                         " - rebuilding")

    # Pandas dataframe with transactions
    df = transactions_fx()

    if filter:
        df = df.query(filter)
    logging.info("[generatenav] Success - read trades from database")
    start_date = df.index.min() - timedelta(days=1)  # start on t-1 of first trade
    end_date = datetime.today()

    # Create a list of all tickers that were traded in this portfolio
    tickers = df.trade_asset_ticker.unique().tolist()

    # Create an empty DF, fill with dates and fill with operation and prices then NAV
    dailynav = pd.DataFrame(columns=['date'])
    # Fill the dates from first trade until today
    dailynav['date'] = pd.date_range(start=start_date, end=end_date)
    dailynav = dailynav.set_index('date')
    # dailynav = dailynav.index.floor('d')
    dailynav['PORT_usd_pos'] = 0
    dailynav['PORT_fx_pos'] = 0
    dailynav['PORT_cash_value'] = 0
    dailynav['PORT_cash_value_fx'] = 0
    # Fill with conversion from USD to current selected FX.
    if current_user.fx() != "USD":
        local_json, _, _ = alphavantage_historical("USD", current_user.fx())
        prices = pd.DataFrame(local_json)
        prices.reset_index(inplace=True)
        # Reassign index to the date column
        prices = prices.set_index(
            list(prices.columns[[0]]))
        prices = prices['4. close']
        # convert string date to datetime
        prices.index = pd.to_datetime(prices.index)
        # Make sure this is a dataframe so it can be merged later
        if type(prices) != type(dailynav):
            prices = prices.to_frame()
        # rename index to date to match dailynav name
        prices.index.rename('date', inplace=True)
        prices.columns = ['fx']
        # Fill dailyNAV with prices for each ticker
        dailynav = pd.merge(dailynav, prices, on='date', how='left')
        dailynav['fx'].fillna(method='ffill', inplace=True)
    else:
        dailynav['fx'] = 1

    # Create a dataframe for each position's prices
    for id in tickers:
        # if id == current_user.fx():
        #     continue
        local_json, _, _ = alphavantage_historical(id)
        try:
            prices = pd.DataFrame(local_json)
            prices.reset_index(inplace=True)
            # Reassign index to the date column
            prices = prices.set_index(
                list(prices.columns[[0]]))
            prices = prices['4a. close (USD)']
            # convert string date to datetime
            prices.index = pd.to_datetime(prices.index)
            # Make sure this is a dataframe so it can be merged later
            if type(prices) != type(dailynav):
                prices = prices.to_frame()
            # rename index to date to match dailynav name
            prices.index.rename('date', inplace=True)
            prices.columns = [id+'_price']

            # Fill dailyNAV with prices for each ticker
            dailynav = pd.merge(dailynav, prices, on='date', how='left')

            # Update today's price with realtime data
            try:
                dailynav[id+"_price"][-1] = (
                    rt_price_grab(id)['USD'])
            except IndexError:
                pass
            except TypeError:
                # If for some reason the last price is an error,
                # use the previous close
                dailynav[id+"_price"][-1] = dailynav[id+"_price"][-2]

            # Replace NaN with prev value, if no prev value then zero

            dailynav[id+'_price'].fillna(method='ffill', inplace=True)
            dailynav[id+'_price'].fillna(0, inplace=True)
            # Convert price to default fx
            dailynav[id+'_fx_price'] = dailynav[id+'_price'].astype(
                    float) * dailynav['fx'].astype(float)

            # Now let's find trades for this ticker and include in dailynav
            tradedf = df[['trade_asset_ticker',
                          'trade_quantity', 'cash_value', 'cash_value_fx']]
            print (tradedf)
                          # Filter trades only for this ticker
            tradedf = tradedf[tradedf['trade_asset_ticker'] == id]
            # consolidate all trades in a single date Input
            tradedf = tradedf.groupby(level=0).sum()

            tradedf.sort_index(ascending=True, inplace=True)
            # include column to cumsum quant
            tradedf['cum_quant'] = tradedf['trade_quantity'].cumsum()
            # merge with dailynav - 1st rename columns to include ticker
            tradedf.index.rename('date', inplace=True)
            # rename columns to include ticker name so it's differentiated
            # when merged
            tradedf.rename(columns={'trade_quantity': id+'_quant',
                                    'cash_value': id+'_cash_value',
                                    'cum_quant': id+'_pos',
                                    'cash_value_fx': id+'_cash_value_fx'},
                           inplace=True)
            # merge
            dailynav = pd.merge(dailynav, tradedf, on='date', how='left')
            # for empty days just trade quantity = 0, same for CV
            dailynav[id+'_quant'].fillna(0, inplace=True)
            dailynav[id+'_cash_value'].fillna(0, inplace=True)
            dailynav[id+'_cash_value_fx'].fillna(0, inplace=True)
            # Now, for positions, fill with previous values, NOT zero,
            # unless there's no previous
            dailynav[id+'_pos'].fillna(method='ffill', inplace=True)
            dailynav[id+'_pos'].fillna(0, inplace=True)
            # Calculate USD and fx position and % of portfolio at date
            dailynav[id+'_usd_pos'] = dailynav[id+'_price'].astype(
                float) * dailynav[id+'_pos'].astype(float)
            # Calculate USD position and % of portfolio at date
            dailynav[id+'_fx_pos'] = dailynav[id+'_fx_price'].astype(
                float) * dailynav[id+'_pos'].astype(float)
            # Before calculating NAV, clean the df for small
            # dust positions. Otherwise, a portfolio close to zero but with
            # 10 sats for example, would still have NAV changes
            dailynav[id+'_usd_pos'].round(2)
            dailynav[id+'_fx_pos'].round(2)
            logging.info(
                f"Success: imported prices from file:{filename}")

        except (FileNotFoundError, KeyError, ValueError) as e:
            logging.error(f"File not Found Error: ID: {id}")
            logging.error(f"{id}: Error: {e}")

    # Another loop to sum the portfolio values - maybe there is a way to
    # include this on the loop above. But this is not a huge time drag unless
    # there are too many tickers in a portfolio
    for id in tickers:
        if id == current_user.fx():
            continue
        # Include totals in new columns
        try:
            dailynav['PORT_usd_pos'] = dailynav['PORT_usd_pos'] +\
                dailynav[id+'_usd_pos']
            dailynav['PORT_fx_pos'] = dailynav['PORT_fx_pos'] +\
                dailynav[id+'_fx_pos']
        except KeyError:
            logging.warning(f"[GENERATENAV] Ticker {id} was not found " +
                            "on NAV Table - continuing but this is not good." +
                            " NAV calculations will be erroneous.")
            continue
        dailynav['PORT_cash_value'] = dailynav['PORT_cash_value'] +\
            dailynav[id+'_cash_value']
        dailynav['PORT_cash_value_fx'] = dailynav['PORT_cash_value_fx'] +\
            dailynav[id+'_cash_value_fx']

    # Now that we have the full portfolio value each day, calculate alloc %
    for id in tickers:
        if id == current_user.fx():
            continue
        try:
            dailynav[id+"_usd_perc"] = dailynav[id+'_usd_pos'] /\
                dailynav['PORT_usd_pos']
            dailynav[id+"_usd_perc"].fillna(0, inplace=True)
            dailynav[id+"_fx_perc"] = dailynav[id+'_fx_pos'] /\
                dailynav['PORT_fx_pos']
            dailynav[id+"_fx_perc"].fillna(0, inplace=True)
        except KeyError:
            logging.warning(f"[GENERATENAV] Ticker {id} was not found " +
                            "on NAV Table - continuing but this is not good." +
                            " NAV calculations will be erroneous.")
            continue

    # Create a new column with the portfolio change only due to market move
    # discounting all cash flows for that day
    dailynav['adj_portfolio'] = dailynav['PORT_usd_pos'] -\
        dailynav['PORT_cash_value']
    dailynav['adj_portfolio_fx'] = dailynav['PORT_fx_pos'] -\
        dailynav['PORT_cash_value_fx']

    # For the period return let's use the Modified Dietz Rate of return method
    # more info here: https://tinyurl.com/y474gy36
    # There is one caveat here. If end value is zero (i.e. portfolio fully
    # redeemed, the formula needs to be adjusted)
    dailynav.loc[dailynav.PORT_usd_pos > min_size_for_calc,
                 'port_dietz_ret'] =\
        ((dailynav['PORT_usd_pos'] -
          dailynav['PORT_usd_pos'].shift(1)) -
         dailynav['PORT_cash_value']) /\
        (dailynav['PORT_usd_pos'].shift(1) +
         abs(dailynav['PORT_cash_value']))

    dailynav.loc[dailynav.PORT_fx_pos > min_size_for_calc,
                 'port_dietz_ret_fx'] =\
        ((dailynav['PORT_fx_pos'] -
          dailynav['PORT_fx_pos'].shift(1)) -
         dailynav['PORT_cash_value_fx']) /\
        (dailynav['PORT_fx_pos'].shift(1) +
         abs(dailynav['PORT_cash_value_fx']))

    # Fill empty and NaN with zero
    dailynav['port_dietz_ret'].fillna(0, inplace=True)
    dailynav['port_dietz_ret_fx'].fillna(0, inplace=True)

    dailynav['adj_port_chg_usd'] = ((dailynav['PORT_usd_pos'] -
                                    dailynav['PORT_usd_pos'].shift(1)) -
                                    dailynav['PORT_cash_value'])
    dailynav['adj_port_chg_fx'] = ((dailynav['PORT_fx_pos'] -
                                    dailynav['PORT_fx_pos'].shift(1)) -
                                    dailynav['PORT_cash_value_fx'])

    # let's fill NaN with zeros
    dailynav['adj_port_chg_usd'].fillna(0, inplace=True)
    dailynav['adj_port_chg_fx'].fillna(0, inplace=True)
    dailynav['port_perc_factor'] = (dailynav['port_dietz_ret']) + 1
    dailynav['port_perc_factor_fx'] = (dailynav['port_dietz_ret_fx']) + 1
    dailynav['NAV'] = dailynav['port_perc_factor'].cumprod()
    dailynav['NAV_fx'] = dailynav['port_perc_factor_fx'].cumprod()
    dailynav['NAV_fx'] = dailynav['NAV_fx'] * 100
    dailynav['PORT_ac_CFs'] = dailynav['PORT_cash_value'].cumsum()
    dailynav['PORT_ac_CFs_fx'] = dailynav['PORT_cash_value_fx'].cumsum()
    logging.info(
        f"[generatenav] Success: NAV Generated for user {user}")

    # Save NAV Locally as Pickle
    usernamehash = hashlib.sha256(current_user.username.encode(
        'utf-8')).hexdigest()
    filename = "thewarden/nav_data/"+usernamehash + ".nav"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    dailynav.to_pickle(filename)
    logging.info(f"[generatenav] NAV saved to {filename}")
    return dailynav


def regenerate_nav():
    # re-generates the NAV on the background - delete First
    # the local NAV file so it's not used.
    usernamehash = hashlib.sha256(
        current_user.username.encode("utf-8")).hexdigest()
    filename = "thewarden/nav_data/" + usernamehash + ".nav"
    logging.info(f"[newtrade] {filename} marked for deletion.")
    # Since this function can be run as a thread,
    # it's safer to delete the current NAV file if it exists.
    # This avoids other tasks reading the local file which
    # is outdated
    try:
        os.remove(filename)
        logging.info("[newtrade] Local NAV file deleted")
    except OSError:
        logging.info("[newtrade] Local NAV file not found" +
                     " for removal - continuing")
    generatenav(current_user.username, True)
    # clear key memoized functions

    logging.info("Change to database - generate NAV")


def alphavantage_historical(id, to_symbol=None):
    # Downloads Historical prices from Alphavantage
    # Can handle both Stock and Crypto tickers - try stock first, then crypto
    # Returns:
    #  - data matrix (prices)
    #  - notification messages: error, stock, crypto
    #  - Metadata:
    #     "Meta Data": {
    #     "1. Information": "Daily Prices and Volumes for Digital Currency",
    #     "2. Digital Currency Code": "BTC",
    #     "3. Digital Currency Name": "Bitcoin",
    #     "4. Market Code": "USD",
    #     "5. Market Name": "United States Dollar",
    #     "6. Last Refreshed": "2019-06-02 (end of day)",
    #     "7. Time Zone": "UTC"
    # },
    # To limit the number of requests to ALPHAVANTAGE, if data is Downloaded
    # successfully, it will be saved locally to be reused during that day

    # Alphavantage Keys can be generated free at
    # https://www.alphavantage.co/support/#api-key

    user_info = User.query.filter_by(username=current_user.username).first()
    api_key = user_info.aa_apikey
    if api_key is None:
        return("API Key is empty", "error", "empty")

    if to_symbol is not None:
        from_symbol = id
        id = id + "_" + to_symbol

    id = id.upper()

    filename = "thewarden/alphavantage_data/" + id + ".aap"
    meta_filename = "thewarden/alphavantage_data/" + id + "_meta.aap"

    try:
        # Check if saved file is recent enough to be used
        # Local file has to have a modified time in today
        today = datetime.now().date()
        filetime = datetime.fromtimestamp(os.path.getctime(filename))

        if filetime.date() == today:
            logging.info("[ALPHAVANTAGE] Local file is fresh. Using it.")
            id_pickle = pd.read_pickle(filename)
            with open(meta_filename, 'rb') as handle:
                meta_pickle = pickle.load(handle)
            logging.info(f"Success: Open {filename} - no need to rebuild")
            return (id_pickle, "downloaded", meta_pickle)
        else:
            logging.info("[ALPHAVANTAGE] File found but too old" +
                            " - downloading a fresh one.")

    except FileNotFoundError:
        logging.info(f"[ALPHAVANTAGE] File not found for {id} - downloading")

    if to_symbol is None:
        baseURL = "https://www.alphavantage.co/query?"
        func = "DIGITAL_CURRENCY_DAILY"
        market = "USD"
        globalURL = baseURL + "function=" + func + "&symbol=" + id +\
            "&market=" + market + "&apikey=" + api_key
        logging.info(f"[ALPHAVANTAGE] {id}: Downloading data")
        logging.info(f"[ALPHAVANTAGE] Fetching URL: {globalURL}")
    else:
        baseURL = "https://www.alphavantage.co/query?"
        func = "FX_DAILY"
        globalURL = baseURL + "function=" + func + "&from_symbol=" + from_symbol +\
            "&to_symbol=" + to_symbol + "&outputsize=full&apikey=" + api_key
        logging.info(f"[ALPHAVANTAGE - FX] {id}: Downloading data")
        logging.info(f"[ALPHAVANTAGE - FX] Fetching URL: {globalURL}")

    try:
        logging.info(f"[ALPHAVANTAGE] Requesting URL: {globalURL}")
        request = tor_request(globalURL)
    except requests.exceptions.ConnectionError:
        logging.error("[ALPHAVANTAGE] Connection ERROR " +
                        "while trying to download prices")
        return("Connection Error", 'error', 'empty')
    data = request.json()
    # if FX request
    try:
        if to_symbol is not None:
            meta_data = (data['Meta Data'])
            logging.info(f"[ALPHAVANTAGE FX] Downloaded historical price for {id}")
            df = pd.DataFrame.from_dict(data[
                'Time Series FX (Daily)'],
                orient="index")
            # Save locally for reuse today
            filename = "thewarden/alphavantage_data/" + id + ".aap"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_pickle(filename)
            meta_filename = "thewarden/alphavantage_data/" + id + "_meta.aap"
            with open(meta_filename, 'wb') as handle:
                pickle.dump(meta_data, handle,
                            protocol=pickle.HIGHEST_PROTOCOL)
            logging.info(f"[ALPHAVANTAGE FX] {filename}: Filed saved locally")
            return (df, 'FX', meta_data)
    except KeyError:
        return("Invalid FX Ticker", "error", "empty")
    # Try first as a crypto request
    try:
        meta_data = (data['Meta Data'])
        logging.info(f"[ALPHAVANTAGE] Downloaded historical price for {id}")
        df = pd.DataFrame.from_dict(data[
            'Time Series (Digital Currency Daily)'],
            orient="index")
        # Save locally for reuse today
        filename = "thewarden/alphavantage_data/" + id + ".aap"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df.to_pickle(filename)
        meta_filename = "thewarden/alphavantage_data/" + id + "_meta.aap"
        with open(meta_filename, 'wb') as handle:
            pickle.dump(meta_data, handle,
                        protocol=pickle.HIGHEST_PROTOCOL)
        logging.info(f"[ALPHAVANTAGE] {filename}: Filed saved locally")
        return (df, 'crypto', meta_data)
    except KeyError:
        logging.info(
            f"[ALPHAVANTAGE] Ticker {id} not found as Crypto. Trying Stock.")
        # Data not found - try as STOCK request
        func = "TIME_SERIES_DAILY_ADJUSTED"
        globalURL = baseURL + "function=" + func + "&symbol=" + id +\
            "&market=" + market + "&outputsize=full&apikey=" +\
            api_key
        try:
            request = tor_request(globalURL)
        except requests.exceptions.ConnectionError:
            logging.error("[ALPHAVANTAGE] Connection ERROR while" +
                            " trying to download prices")
            return("Connection Error", "error", "empty")
        data = request.json()
        try:
            meta_data = (data['Meta Data'])
            logging.info(
                f"[ALPHAVANTAGE] Downloaded historical price for stock {id}")
            df = pd.DataFrame.from_dict(
                data['Time Series (Daily)'],
                orient="index")
            # Save locally for reuse today
            filename = "thewarden/alphavantage_data/" + id + ".aap"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_pickle(filename)
            meta_filename = "thewarden/alphavantage_data/" + id + "_meta.aap"
            with open(meta_filename, 'wb') as handle:
                pickle.dump(meta_data, handle,
                            protocol=pickle.HIGHEST_PROTOCOL)
            logging.info(f"[ALPHAVANTAGE] {filename}: Filed saved locally")
            return (df, "stock", meta_data)

        except KeyError as e:
            logging.warning(
                f"[ALPHAVANTAGE] {id} not found as Stock or Crypto" +
                f" - INVALID TICKER - {e}")
            # Last Try - look at Bitmex for  this ticker
            logging.info("Trying Bitmex as a final alternative for this ticker")
            data = bitmex_gethistory(id)
            try:
                if data == 'error':  # In case a df is returned this raises an error
                    return("Invalid Ticker", "error", "empty")
            except ValueError:
                # Match the AA data and save locally before returning
                data = data.rename(columns={'close': '4a. close (USD)'})
                data['4b. close (USD)'] = data['4a. close (USD)']
                # Remove tzutc() time type from timestamp (otherwise merging would fail)
                data['timestamp'] = pd.to_datetime(data['timestamp'], utc=False)

                # Change timestamp column to index
                data.set_index('timestamp', inplace=True)
                # Convert to UTC and remove localization
                data = data.tz_convert(None)
                meta_data = "Bitmex Metadata not available"

                # Save locally for reuse today
                filename = "thewarden/alphavantage_data/" + id + ".aap"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                data.to_pickle(filename)
                meta_filename = "thewarden/alphavantage_data/" + id + "_meta.aap"
                with open(meta_filename, 'wb') as handle:
                    pickle.dump(meta_data, handle,
                                protocol=pickle.HIGHEST_PROTOCOL)
                logging.info(f"[BITMEX] {filename}: Filed saved locally")
                return (data, "bitmex", meta_data)

    return("Invalid Ticker", "error", "empty")


def bitmex_gethistory(ticker):
    # Gets historical prices from bitmex
    # Saves to folder
    from bitmex import bitmex
    testnet = False
    logging.info(f"[Bitmex] Trying Bitmex for {ticker}")
    bitmex_credentials = load_bitmex_json()

    if ("api_key" in bitmex_credentials) and ("api_secret" in bitmex_credentials):
        try:
            mex = bitmex(test=testnet,
                         api_key=bitmex_credentials['api_key'],
                         api_secret=bitmex_credentials['api_secret'])
            # Need to paginate results here to get all the history
            # Bitmex API end point limits 750 results per call
            start_bin = 0
            resp = (mex.Trade.Trade_getBucketed(
                symbol=ticker, binSize="1d", count=750, start=start_bin).result())[0]
            df = pd.DataFrame(resp)
            last_update = df['timestamp'].iloc[-1]

            # If last_update is older than 3 days ago, keep building.
            while last_update < (datetime.now(timezone.utc) - timedelta(days=3)):
                start_bin += 750
                resp = (mex.Trade.Trade_getBucketed(
                    symbol=ticker, binSize="1d", count=750, start=start_bin).result())[0]
                df = df.append(resp)
                last_update = df['timestamp'].iloc[-1]
                # To avoid an infinite loop, check if start_bin
                # is higher than 10000 and stop (i.e. 30+yrs of data)
                if start_bin > 10000:
                    logging.error("[Bitmex] Something went wrong on price grab loop. Forced quit of loop.")
                    break

            logging.info(f"[Bitmex] Success. Downloaded data for {ticker}")
            return(df)

        except Exception as e:
            logging.error(f"[Bitmex] error: {e}")
            return ("error")

    else:
        logging.warning(f"[Bitmex] No Credentials Found")
        return ('error')


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='cryptoblotterrp@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
                {url_for('users.reset_token', token=token, _external=True)}


                If you did not make this request then simply ignore this email
                 and no changes will be made.
                '''
    mail.send(msg)


@MWT(timeout=20)
def heatmap_generator():
    # If no Transactions for this user, return empty.html
    transactions = Trades.query.filter_by(user_id=current_user.username).order_by(
        Trades.trade_date
    )
    if transactions.count() == 0:
        return None, None, None, None

    # Generate NAV Table first
    data = generatenav(current_user.username)
    data["navpchange"] = (data["NAV"] / data["NAV"].shift(1)) - 1
    returns = data["navpchange"]
    # Run the mrh function to generate heapmap table
    heatmap = mrh.get(returns, eoy=True)

    heatmap_stats = heatmap.copy()
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
    years = (heatmap.index.tolist())
    heatmap_stats["MAX"] = heatmap_stats[heatmap_stats[cols_months] != 0].max(axis=1)
    heatmap_stats["MIN"] = heatmap_stats[heatmap_stats[cols_months] != 0].min(axis=1)
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
    heatmap_stats["MEAN"] = heatmap_stats[heatmap_stats[cols_months] != 0].mean(axis=1)

    return (heatmap, heatmap_stats, years, cols)


@memoized
def price_ondate(ticker, date_input, to_symbol=None):
    # Returns the price of a ticker on a given date
    # if to_symbol is passed, it assumes FX and ticker is from_symbol
    if to_symbol is not None:
        local_json, message, error = alphavantage_historical(ticker, to_symbol)
    else:
        local_json, message, error = alphavantage_historical(ticker)
    if message == 'error':
        return 'error'
    try:
        prices = pd.DataFrame(local_json)
        prices.reset_index(inplace=True)
        # Reassign index to the date column
        prices = prices.set_index(
            list(prices.columns[[0]]))
        if to_symbol is None:
            prices = prices['4a. close (USD)']
        else:
            prices = prices['4. close']
        # convert string date to datetime
        prices.index = pd.to_datetime(prices.index)
        # rename index to date to match dailynav name
        prices.index.rename('date', inplace=True)
        idx = prices[prices.index.get_loc(date_input, method='nearest')]
    except KeyError:
        return ("0")
    return (idx)


@memoized
def fx_list():
    with open('thewarden/static/csv_files/physical_currency_list.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        fiat_dict = {rows[0]: (rows[1]) for rows in reader}
    # Convert dict to list
    fx_list = [(k, k + ' | ' + v) for k, v in fiat_dict.items()]
    fx_list.sort()
    return (fx_list)


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
    with open('thewarden/static/json_files/currency.json') as fx_json:
        fx_list = json.load(fx_json)
    try:
        out = fx_list[fx][output]
    except Exception:
        out = fx

    return (out)


# ------------------------------------
# Helpers for Bitmex start here
# ------------------------------------

def save_bitmex_json(api_key, api_secret):
    # receives api_key and api_secret then saves to a local json for later use
    if (api_key is None) or (api_secret is None):
        return ("missing arguments")
    bitmex_data = {"api_key": api_key, "api_secret": api_secret}
    with open('thewarden/api/bitmex.json', 'w') as fp:
        json.dump(bitmex_data, fp)
        return ("Credentials saved to bitmex.json")


def load_bitmex_json():
    # returns current stored keys if any
    try:
        with open('thewarden/api/bitmex.json', 'r') as fp:
            data = json.load(fp)
            return (data)
    except (FileNotFoundError, KeyError):
        return ({'status': 'error', 'message': 'API credentials not found'})


def bitmex_orders(api_key, api_secret, testnet=True):
    # Returns a json with all Bitmex Order History
    # Takes arguments: ticker, testnet
    # reads api credentials from file
    from bitmex import bitmex
    try:
        mex = bitmex(test=testnet, api_key=api_key, api_secret=api_secret)
    except Exception:
        return ("Connection Error. Check your connection.")
    try:
        resp = mex.Execution.Execution_getTradeHistory(count=500, start=0, reverse=True).result()
        # resp = mex.User.User_getWalletHistory(count=50000).result()
        # resp = mex.User.User_getWalletHistory(currency=ticker, count=5000).result()
    except Exception:
        resp = "Invalid Credential or Connection Error"
    return(resp)

