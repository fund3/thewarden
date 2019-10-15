import configparser
import csv
import glob
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from flask import flash, url_for
from flask_login import current_user
from flask_mail import Message

from thewarden import db, mail
from thewarden import mhp as mrh
from thewarden.models import Trades
from thewarden.pricing_engine.pricing import (fx_price_ondate,
                                              multiple_price_grab, price_data,
                                              price_data_fx, price_data_rt,
                                              price_data_rt_full)
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
    RENEW_NAV = 3600
    logging.error("Could not find RENEW_NAV at config.ini. Defaulting to 60.")
try:
    PORTFOLIO_MIN_SIZE_NAV = config['MAIN']['PORTFOLIO_MIN_SIZE_NAV']
except KeyError:
    PORTFOLIO_MIN_SIZE_NAV = 5
    logging.error("Could not find PORTFOLIO_MIN_SIZE_NAV at config.ini." +
                  " Defaulting to 5.")


# The following function is used when deploying the application
# In this case, the path changes and the below makes sure the
# correct path is used.
# Returns the base path of the application that can be later used with:
# file_path = os.path.join(current_path, file_path)
@memoized
def current_path():
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    elif __file__:
        application_path = os.path.dirname(os.path.abspath(__file__))
        application_path = os.path.dirname(application_path)
        application_path = os.path.dirname(application_path)
    # The application_path above would return the location of:
    # /thewarden/thewarden/users
    # which is were the utils.py file for this function is located
    # Make sure we go 2 levels up for the base application folder
    return(application_path)


@MWT(timeout=60)
@timing
def cost_calculation(ticker, html_table=None):
    # This function calculates the cost basis assuming 3 different methods
    # FIFO, LIFO and avg. cost
    # If html_table is set to either FIFO or LIFO, it will return
    # an html table for this ticker

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
    fifo_df['Q'] = fifo_df['Q'].fillna(fifo_df['acum_Q'])
    # if fifo_df['acum_Q'].count() == 1:
    #     fifo_df['Q'] = fifo_df['acum_Q']
    # Adjust Cash Value only to account for needed position
    fifo_df['adjusted_cv'] = fifo_df['cash_value_fx'] * fifo_df['Q'] /\
        fifo_df['trade_quantity']
    cost_matrix['FIFO'] = {}
    cost_matrix['FIFO']['FIFO_cash'] = fifo_df['adjusted_cv'].sum()
    cost_matrix['FIFO']['FIFO_quantity'] = open_position
    cost_matrix['FIFO']['FIFO_count'] = int(fifo_df['trade_operation'].count())
    cost_matrix['FIFO']['FIFO_average_cost'] = fifo_df['adjusted_cv'].sum()\
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
    lifo_df['Q'] = lifo_df['Q'].fillna(lifo_df['acum_Q'])
    # if lifo_df['acum_Q'].count() == 1:
    #     lifo_df['Q'] = lifo_df['acum_Q']
    # Adjust Cash Value only to account for needed position
    lifo_df['adjusted_cv'] = lifo_df['cash_value_fx'] * lifo_df['Q'] /\
        lifo_df['trade_quantity']

    cost_matrix['LIFO'] = {}
    cost_matrix['LIFO']['LIFO_cash'] = lifo_df['adjusted_cv'].sum()
    cost_matrix['LIFO']['LIFO_quantity'] = open_position
    cost_matrix['LIFO']['LIFO_count'] = int(lifo_df['trade_operation'].count())
    cost_matrix['LIFO']['LIFO_average_cost'] = lifo_df['adjusted_cv'].sum() / open_position

    if html_table == "FIFO":
        # Format the df into an HTML table to be served at main page
        html = fifo_df[[
            'trade_operation', 'Q', 'acum_Q',
            'trade_price_fx', 'trade_fees_fx', 'cash_value_fx', 'adjusted_cv',
            'trade_reference_id']]

    if html_table == "LIFO":
        html = lifo_df[[
            'trade_operation', 'Q', 'acum_Q',
            'trade_price_fx', 'trade_fees_fx', 'cash_value_fx', 'adjusted_cv',
            'trade_reference_id']]

    # Now format the HTML properly
    if html_table:
        fx = current_user.fx_rate_data()['symbol']
        # Include a link to edit this transaction
        html["trade_reference_id"] = "<a href='/edittransaction?reference_id=" +\
                                     html['trade_reference_id'] +\
                                     "'><i class='fas fa-edit'></i></a>"

        html.index = pd.to_datetime(html.index).strftime('%Y-%m-%d')
        # Include TOTAL row
        html.loc['TOTAL'] = 0
        # Need to add only some fields - strings can't be added for example
        columns_sum = ['Q', 'trade_fees_fx', 'cash_value_fx',
                       'adjusted_cv']
        for field in columns_sum:
            html.loc['TOTAL', field] = html[field].sum()

        # format numbers
        html['acum_Q'] = abs(html['acum_Q'])
        html['Q'] = abs(html['Q'])
        html['acum_Q'] = html['acum_Q'].map('{:,.4f}'.format)
        html['Q'] = html['Q'].map('{:,.4f}'.format)
        html['trade_price_fx'] = html['trade_price_fx'].map('{:,.2f}'.format)
        html['trade_fees_fx'] = html['trade_fees_fx'].map('{:,.2f}'.format)
        html['cash_value_fx'] = html['cash_value_fx'].map('{:,.2f}'.format)
        html['adjusted_cv'] = html['adjusted_cv'].map('{:,.2f}'.format)
        html.loc['TOTAL', 'trade_operation'] = ''
        html.loc['TOTAL', 'acum_Q'] = ''
        html.loc['TOTAL', 'trade_price_fx'] = ''
        html.loc['TOTAL', 'trade_reference_id'] = ''
        html = html.rename(
            columns={
                'trade_operation': 'B/S',
                'acum_Q': 'Q (acum)',
                'trade_price_fx': 'Price (' + fx + ')',
                'trade_fees_fx': 'Fees (' + fx + ')',
                'cash_value_fx': 'Cash Flow (' + fx + ')',
                'adjusted_cv': 'Adj CF (' + fx + ')',
                'trade_reference_id': ' '
            })

        cost_matrix = html.to_html(
            classes='table table-condensed table-striped small-text text-right',
            escape=False, index_names=False, justify='right')

    return (cost_matrix)


def to_epoch(in_date):
    return str(int((in_date - datetime(1970, 1, 1)).total_seconds()))


def find_fx(row, fx=None):
    # row.name is the date being passed
    # row['trade_currency'] is the base fx (the one where the trade was included)
    # Create an instance of PriceData:
    price = fx_price_ondate(current_user.fx(), row['trade_currency'], row.name)
    return price


@timing
@MWT(timeout=30)
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
    df['trade_price_fx'] = df['trade_price'].astype(float) / df['fx'].astype(float)
    return (df)


@memoized
def is_currency(id):
    # Return true if id is in list of currencies
    found = ([item for item in fx_list() if item[0] == id])
    if found != []:
        return True
    return False


@MWT(timeout=2)
def list_tickers():
    df = pd.read_sql_table('trades', db.engine)
    df = df[(df.user_id == current_user.username)]
    # remove the currencies from tickers
    df['is_currency'] = df['trade_asset_ticker'].apply(is_currency)
    df = df[df['is_currency'] == False]
    return (df.trade_asset_ticker.unique().tolist())


# ---------------- PANDAS HELPER FUNCTION --------------------------
# This is a function to concatenate a function returning multiple columns into
# a dataframe.
def apply_and_concat(dataframe, field, func, column_names):
    return pd.concat((
        dataframe,
        dataframe[field].apply(
            lambda cell: pd.Series(func(cell), index=column_names))), axis=1)


# ---------------- PANDAS HELPER FUNCTION --------------------------
# Pandas helper function to unpack a dictionary stored within a
# single pandas column cells.
def df_unpack(df, column, fillna=None):
    ret = None
    if fillna is None:
        ret = pd.concat([df, pd.DataFrame(
            (d for idx, d in df[column].iteritems()))], axis=1)
        del ret[column]
    else:
        ret = pd.concat([df, pd.DataFrame(
            (d for idx, d in df[column].iteritems())).fillna(fillna)], axis=1)
        del ret[column]
    return ret


@MWT(timeout=2)
def positions():
    # Method to create a user's position table
    # Returns a df with the following information
    # Ticker, name, quantity, small_pos
    # THIS SHOULD CONTAIN THE STATIC FIELDS ONLY - no web requests
    # It should be a light method to load quickly on the main page.
    # Anything with web requests should be done on a separate function

    # Get all transactions & group by ticker name and operation
    df = transactions_fx()
    summary_table = df.groupby(['trade_asset_ticker', 'trade_operation'])[
                                ["trade_quantity",
                                 "cash_value_fx",
                                 "trade_fees_fx"]].sum()
    # Now let's create our main dataframe with information for each ticker
    list_of_tickers = list_tickers()
    main_df = pd.DataFrame({'trade_asset_ticker': list_of_tickers})
    # Fill with positions, cash_values and fees
    df_tmp = df.groupby(['trade_asset_ticker'])[
                        ["trade_quantity",
                         "cash_value_fx",
                         "trade_fees_fx"]].sum()
    main_df = pd.merge(main_df, df_tmp, on='trade_asset_ticker')
    # Fill in with same information but only for buys, sells, deposits and withdraws
    # main_df = pd.merge(main_df, summary_table, on='trade_asset_ticker')
    summary_table = summary_table.unstack(level='trade_operation').fillna(0)
    main_df = pd.merge(main_df, summary_table, on='trade_asset_ticker')
    # Include FIFO and LIFO calculations for each ticker
    main_df['cost_frame'] = main_df['trade_asset_ticker'].apply(cost_calculation)
    # Unpack this into multiple columns now
    main_df = df_unpack(main_df, 'cost_frame', 0)
    main_df = df_unpack(main_df, 'FIFO', 0)
    main_df = df_unpack(main_df, 'LIFO', 0)
    main_df['is_currency'] = main_df['trade_asset_ticker'].apply(is_currency)
    return main_df


def single_price(ticker):
    return (price_data_rt(ticker), datetime.now())


@MWT(timeout=2)
def positions_dynamic():
    # This method is the realtime updater for the front page. It gets the
    # position information from positions above and returns a dataframe
    # with all the realtime pricing and positions data - this method
    # should be called from an AJAX request at the front page in order
    # to reduce loading time.
    df = positions()
    # Drop all currencies from table
    df = df[df['is_currency'] == False]
    # check if trade_asset_ticker is set as index. If so, move to column
    # This happens on some memoized functions - need to understand why
    # The below is a temporary fix
    df = df.reset_index()
    if df is None:
        return None, None
    tickers_string = ",".join(list_tickers())
    # Let's try to get as many prices as possible into the df with a
    # single request - first get all the prices in current currency and USD
    multi_price = multiple_price_grab(tickers_string, 'USD,' + current_user.fx())
    # PARSER Function to fing the ticker price inside the matrix. First part
    # looks into the cryptocompare matrix. In the exception, if price is not
    # found, it sends a request to other providers

    def find_data(ticker):
        notes = None
        try:
            # Parse the cryptocompare data
            price = multi_price["RAW"][ticker][current_user.fx()]["PRICE"]
            price = float(price)
            high = float(multi_price["RAW"][ticker][
                current_user.fx()]["HIGHDAY"])
            low = float(multi_price["RAW"][ticker][
                current_user.fx()]["LOWDAY"])
            chg = multi_price["RAW"][ticker][current_user.fx()]["CHANGEPCT24HOUR"]
            mktcap = multi_price["DISPLAY"][ticker][current_user.fx()]["MKTCAP"]
            volume = multi_price["DISPLAY"][ticker][current_user.fx()]["VOLUME24HOURTO"]
            last_up_source = multi_price["RAW"][ticker][current_user.fx()]["LASTUPDATE"]
            source = multi_price["DISPLAY"][ticker][current_user.fx()]["LASTMARKET"]
            last_update = datetime.now()
        except (KeyError, TypeError):
            # Couldn't find price with CryptoCompare. Let's try a different source
            # and populate data in the same format [aa = alphavantage]
            try:
                single_price = price_data_rt_full(ticker, 'aa')
                if single_price is None:
                    raise KeyError
                price = single_price[0]
                high = single_price[2]
                low = single_price[3]
                (_, last_update, _, _,
                    chg, mktcap, last_up_source,
                    volume, source, notes) = single_price
            except Exception:
                # Let's try a final time using Financial Modeling Prep API
                try:
                    single_price = price_data_rt_full(ticker, 'fp')
                    if single_price is None:
                        raise KeyError
                    price = single_price[0]
                    high = single_price[2]
                    low = single_price[3]
                    (_, last_update, _, _,
                        chg, mktcap, last_up_source,
                        volume, source, notes) = single_price
                except Exception:
                    try:
                        # Finally, if realtime price is unavailable, find the latest
                        # saved value in historical prices
                        # Create a price class
                        price_class = price_data(ticker)
                        if price_class is None:
                            raise KeyError
                        price = float(price_class.df['close'].iloc[0]) * current_user.fx_rate_USD()
                        high = float(price_class.df['high'].iloc[0]) * current_user.fx_rate_USD()
                        low = float(price_class.df['low'].iloc[0]) * current_user.fx_rate_USD()
                        volume = current_user.fx() + "  " + "{0:,.0f}".format(float(price_class.df[
                            'volume'].iloc[0]) * current_user.fx_rate_USD())
                        mktcap = chg = 0
                        source = last_up_source = 'Historical Data'
                        last_update = price_class.df.index[0]
                    except Exception as e:
                        price = high = low = chg = mktcap = last_up_source = last_update = volume = 0
                        source = '-'
                        logging.error(f"There was an error getting the price for {ticker}." +
                                      f"Error: {e}")
        return price, last_update, high, low, chg, mktcap, last_up_source, volume, source, notes
    df = apply_and_concat(df, 'trade_asset_ticker',
                          find_data, ['price', 'last_update', '24h_high', '24h_low',
                                      '24h_change', 'mktcap', 'last_up_source',
                                      'volume', 'source', 'notes'])
    # Now create additional columns with calculations
    df['position_fx'] = df['price'] * df['trade_quantity']
    df['allocation'] = df['position_fx'] / df['position_fx'].sum()
    df['change_fx'] = df['position_fx'] * df['24h_change'] / 100
    # Pnl and Cost calculations
    df['breakeven'] = df['cash_value_fx'] / df['trade_quantity']
    df['pnl_gross'] = df['position_fx'] - df['cash_value_fx']
    df['pnl_net'] = df['pnl_gross'] - df['trade_fees_fx']
    # FIFO and LIFO PnL calculations
    df['LIFO_unreal'] = (df['price'] - df['LIFO_average_cost']) * \
                         df['trade_quantity']
    df['FIFO_unreal'] = (df['price'] - df['FIFO_average_cost']) * \
                         df['trade_quantity']
    df['LIFO_real'] = df['pnl_net'] - df['LIFO_unreal']
    df['FIFO_real'] = df['pnl_net'] - df['FIFO_unreal']
    df['LIFO_unrealized_be'] = df['price'] - \
                              (df['LIFO_unreal'] / df['trade_quantity'])
    df['FIFO_unrealized_be'] = df['price'] - \
                              (df['FIFO_unreal'] / df['trade_quantity'])
    # Allocations below 0.01% are marked as small
    # this is used to hide small and closed positions at html
    df.loc[df.allocation <= 0.0001, 'small_pos'] = 'True'
    df.loc[df.allocation >= 0.0001, 'small_pos'] = 'False'

    # Prepare for delivery. Change index, add total
    df.set_index('trade_asset_ticker', inplace=True)
    df.loc['Total'] = 0
    # Column names can't be tuples - otherwise json generates an error
    df.rename(columns={
        ('trade_quantity', 'B'): 'trade_quantity_B',
        ('trade_quantity', 'S'): 'trade_quantity_S',
        ('trade_quantity', 'D'): 'trade_quantity_D',
        ('trade_quantity', 'W'): 'trade_quantity_W',
        ('cash_value_fx', 'B'): 'cash_value_fx_B',
        ('cash_value_fx', 'S'): 'cash_value_fx_S',
        ('cash_value_fx', 'D'): 'cash_value_fx_D',
        ('cash_value_fx', 'W'): 'cash_value_fx_W',
        ('trade_fees_fx', 'B'): 'trade_fees_fx_B',
        ('trade_fees_fx', 'S'): 'trade_fees_fx_S',
        ('trade_fees_fx', 'D'): 'trade_fees_fx_D',
        ('trade_fees_fx', 'W'): 'trade_fees_fx_W'
    }, inplace=True)

    # Need to add only some fields - strings can't be added for example
    columns_sum = ['cash_value_fx', 'trade_fees_fx', 'position_fx',
                   'allocation', 'change_fx', 'pnl_gross', 'pnl_net',
                   'LIFO_unreal', 'FIFO_unreal', 'LIFO_real', 'FIFO_real']
    for field in columns_sum:
        df.loc['Total', field] = df[field].sum()
    # Set the portfolio last update to be equal to the latest update in df
    df.loc['Total', 'last_up_source'] = (datetime.now()).strftime('%d-%b-%Y %H:%M:%S')
    df['last_update'] = df['last_update'].astype(str)
    # Create a pie chart data in HighCharts format excluding small pos
    pie_data = []
    for ticker in list_tickers():
        if df.loc[ticker, 'small_pos'] == 'False':
            tmp_dict = {}
            tmp_dict['y'] = round(df.loc[ticker, 'allocation'] * 100, 2)
            tmp_dict['name'] = ticker
            pie_data.append(tmp_dict)
    return(df, pie_data)


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


@MWT(timeout=1)
@timing
def generatenav(user, force=False, filter=None):
    logging.info(f"[generatenav] Starting NAV Generator for user {user}")
    # Portfolios smaller than this size do not account for NAV calculations
    # Otherwise, there's an impact of dust left in the portfolio (in USD)
    # This is set in config.ini file
    min_size_for_calc = int(PORTFOLIO_MIN_SIZE_NAV)
    logging.info(f"[generatenav] Force update status is {force}")
    save_nav = True
    # This process can take some time and it's intensive to run NAV
    # generation every time the NAV is needed. A compromise is to save
    # the last NAV generation locally and only refresh after a period of time.
    # This period of time is setup in config.ini as RENEW_NAV (in minutes).
    # If last file is newer than 60 minutes (default), the local saved file
    # will be used.
    # Unless force is true, then a rebuild is done regardless
    # Local files are  saved under a hash of username.
    if force:
        usernamehash = hashlib.sha256(current_user.username.encode(
            'utf-8')).hexdigest()
        filename = "thewarden/nav_data/" + usernamehash + current_user.fx() +  ".nav"
        filename = os.path.join(current_path(), filename)
        # Since this function can be run as a thread, it's safer to delete
        # the current NAV file if it exists. This avoids other tasks reading
        # the local file which is outdated
        try:
            os.remove(filename)
        except OSError:
            logging.info("[generatenav] Local NAV file was not found" +
                         " for removal - continuing")

    if not force:
        usernamehash = hashlib.sha256(current_user.username.encode(
            'utf-8')).hexdigest()
        filename = "thewarden/nav_data/" + usernamehash + current_user.fx() + ".nav"
        filename = os.path.join(current_path(), filename)
        try:
            # Check if NAV saved file is recent enough to be used
            # Local file has to have a saved time less than RENEW_NAV min old
            # See config.ini to change RENEW_NAV
            modified = datetime.utcfromtimestamp(os.path.getmtime(filename))
            elapsed_seconds = (datetime.utcnow() - modified).total_seconds()
            logging.info(f"Last time file was modified {modified} is " +
                         f" {elapsed_seconds} seconds ago")
            if (elapsed_seconds / 60) < int(RENEW_NAV):
                nav_pickle = pd.read_pickle(filename)
                return (nav_pickle)
            else:
                logging.info("File found but too old - rebuilding NAV")

        except FileNotFoundError:
            logging.info(f"[generatenav] File not found to load NAV" +
                         " - rebuilding")

    # Pandas dataframe with transactions
    df = transactions_fx()
    # if a filter argument was passed, execute it
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
    # Create empty fields
    dailynav['PORT_usd_pos'] = 0
    dailynav['PORT_fx_pos'] = 0
    dailynav['PORT_cash_value'] = 0
    dailynav['PORT_cash_value_fx'] = 0

    # Create a dataframe for each position's prices
    for id in tickers:
        if is_currency(id):
            continue
        try:
            # Create a new PriceData class for this ticker
            prices = price_data_fx(id)
            if prices is None:
                logging.error(f"Could not get a price for {id}")
                save_nav = False
                raise ValueError

            prices = prices.rename(columns={'close_converted': id + '_price'})
            prices = prices[id + '_price']
            # Fill dailyNAV with prices for each ticker
            dailynav = pd.merge(dailynav, prices, on='date', how='left')

            # Replace NaN with prev value, if no prev value then zero
            dailynav[id + '_price'].fillna(method='ffill', inplace=True)
            dailynav[id + '_price'].fillna(0, inplace=True)

            # Now let's find trades for this ticker and include in dailynav
            tradedf = df[['trade_asset_ticker',
                          'trade_quantity', 'cash_value_fx']]
            # Filter trades only for this ticker
            tradedf = tradedf[tradedf['trade_asset_ticker'] == id]
            # consolidate all trades in a single date Input
            tradedf = tradedf.groupby(level=0).sum()
            tradedf.sort_index(ascending=True, inplace=True)
            # include column to cumsum quant
            tradedf['cum_quant'] = tradedf['trade_quantity'].cumsum()
            # merge with dailynav - 1st rename columns to match
            tradedf.index.rename('date', inplace=True)
            # rename columns to include ticker name so it's differentiated
            # when merged with other ids
            tradedf.rename(columns={'trade_quantity': id + '_quant',
                                    'cum_quant': id + '_pos',
                                    'cash_value_fx': id + '_cash_value_fx'},
                           inplace=True)
            # merge
            dailynav = pd.merge(dailynav, tradedf, on='date', how='left')
            # for empty days just trade quantity = 0, same for CV
            dailynav[id + '_quant'].fillna(0, inplace=True)
            dailynav[id + '_cash_value_fx'].fillna(0, inplace=True)
            # Now, for positions, fill with previous values, NOT zero,
            # unless there's no previous
            dailynav[id + '_pos'].fillna(method='ffill', inplace=True)
            dailynav[id + '_pos'].fillna(0, inplace=True)
            # Calculate USD and fx position and % of portfolio at date
            # Calculate USD position and % of portfolio at date
            dailynav[id + '_fx_pos'] = dailynav[id + '_price'].astype(
                float) * dailynav[id + '_pos'].astype(float)
            # Before calculating NAV, clean the df for small
            # dust positions. Otherwise, a portfolio close to zero but with
            # 10 sats for example, would still have NAV changes
            dailynav[id + '_fx_pos'].round(2)
            logging.info(
                f"Success: imported prices for id:{id}")
        except (FileNotFoundError, KeyError, ValueError) as e:
            logging.error(f"{id}: Error: {e}")
    # Another loop to sum the portfolio values - maybe there is a way to
    # include this on the loop above. But this is not a huge time drag unless
    # there are too many tickers in a portfolio
    for id in tickers:
        if is_currency(id):
            continue
        # Include totals in new columns
        try:
            dailynav['PORT_fx_pos'] = dailynav['PORT_fx_pos'] +\
                dailynav[id + '_fx_pos']
        except KeyError as e:
            logging.error(f"[GENERATENAV] Ticker {id} was not found " +
                           "on NAV Table - continuing but this is not good." +
                           " NAV calculations will be erroneous.")
            save_nav = False
            flash(f"Ticker {id} was not found on NAV table. " +
                   f"NAV calculations will be off. Error: {e}", "danger")
            continue
        dailynav['PORT_cash_value_fx'] = dailynav['PORT_cash_value_fx'] +\
            dailynav[id + '_cash_value_fx']

    # Now that we have the full portfolio value each day, calculate alloc %
    for id in tickers:
        if is_currency(id):
            continue
        try:
            dailynav[id + "_fx_perc"] = dailynav[id + '_fx_pos'] /\
                dailynav['PORT_fx_pos']
            dailynav[id + "_fx_perc"].fillna(0, inplace=True)
        except KeyError:
            continue

    # Create a new column with the portfolio change only due to market move
    # discounting all cash flows for that day
    dailynav['adj_portfolio_fx'] = dailynav['PORT_fx_pos'] -\
        dailynav['PORT_cash_value_fx']

    # For the period return let's use the Modified Dietz Rate of return method
    # more info here: https://tinyurl.com/y474gy36
    # There is one caveat here. If end value is zero (i.e. portfolio fully
    # redeemed, the formula needs to be adjusted)
    dailynav.loc[dailynav.PORT_fx_pos > min_size_for_calc,
                 'port_dietz_ret_fx'] =\
        ((dailynav['PORT_fx_pos'] -
          dailynav['PORT_fx_pos'].shift(1)) -
         dailynav['PORT_cash_value_fx']) /\
        (dailynav['PORT_fx_pos'].shift(1) +
         abs(dailynav['PORT_cash_value_fx']))

    # Fill empty and NaN with zero
    dailynav['port_dietz_ret_fx'].fillna(0, inplace=True)
    dailynav['adj_port_chg_fx'] = ((dailynav['PORT_fx_pos'] -
                                    dailynav['PORT_fx_pos'].shift(1)) -
                                    dailynav['PORT_cash_value_fx'])

    # let's fill NaN with zeros
    dailynav['adj_port_chg_fx'].fillna(0, inplace=True)
    # Calculate the metrics
    dailynav['port_perc_factor_fx'] = (dailynav['port_dietz_ret_fx']) + 1
    dailynav['NAV_fx'] = dailynav['port_perc_factor_fx'].cumprod()
    dailynav['NAV_fx'] = dailynav['NAV_fx'] * 100
    dailynav['PORT_ac_CFs_fx'] = dailynav['PORT_cash_value_fx'].cumsum()
    logging.info(
        f"[generatenav] Success: NAV Generated for user {user}")

    # Save NAV Locally as Pickle
    if save_nav:
        usernamehash = hashlib.sha256(current_user.username.encode(
            'utf-8')).hexdigest()
        filename = "thewarden/nav_data/" + usernamehash + current_user.fx() + ".nav"
        filename = os.path.join(current_path(), filename)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        dailynav.to_pickle(filename)
        logging.info(f"[generatenav] NAV saved to {filename}")

    return dailynav


def clear_memory():
    for name in dir():
        if not name.startswith('_'):
            del globals()[name]

    for name in dir():
        if not name.startswith('_'):
            del locals()[name]


@timing
def regenerate_nav():
    # re-generates the NAV on the background - delete First
    # the local NAV file so it's not used.
    # Check if there any trades in the database. If not, skip.
    try:
        if not current_user.is_authenticated:
            return
        print("Regenerating NAV. Please wait...")
        # Delete all pricing history
        filename = os.path.join(current_path(), 'thewarden/pricing_engine/pricing_data/*.*')
        aa_files = glob.glob(filename)
        [os.remove(x) for x in aa_files]
        filename = os.path.join(current_path(), 'thewarden/nav_data/*.*')
        nav_files = glob.glob(filename)
        [os.remove(x) for x in nav_files]
        # Clear memory, cache
        clear_memory()
        MWT()._caches = {}
        MWT()._timeouts = {}
        generatenav(current_user.username, force=True)
        logging.info("Change to database - generated new NAV")
    except Exception as e:
        print("Error regenerating NAV")
        print(e)
        return


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


@MWT(timeout=1)
def heatmap_generator():
    # If no Transactions for this user, return empty.html
    transactions = Trades.query.filter_by(user_id=current_user.username).order_by(
        Trades.trade_date
    )
    if transactions.count() == 0:
        return None, None, None, None

    # Generate NAV Table first
    data = generatenav(current_user.username)
    data["navpchange"] = (data["NAV_fx"] / data["NAV_fx"].shift(1)) - 1
    returns = data["navpchange"]
    # Run the mrh function to generate heapmap table
    heatmap = mrh.get(returns, eoy=True)

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
def fx_list():
    filename = os.path.join(current_path(),
        'thewarden/static/csv_files/physical_currency_list.csv')
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        fiat_dict = {rows[0]: (rows[1]) for rows in reader}
    # Convert dict to list
    fx_list = [(k, k + ' | ' + v) for k, v in fiat_dict.items()]
    fx_list.sort()
    return (fx_list)


@memoized
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
    filename = os.path.join(
        current_path(),
        'thewarden/static/json_files/currency.json')
    with open(filename) as fx_json:
        fx_list = json.load(fx_json)
    try:
        out = fx_list[fx][output]
    except Exception:
        out = fx
    return (out)


# ------------------------------------
# Helpers for Bitmex start here
# ------------------------------------

def bitmex_gethistory(ticker):
    # Gets historical prices from bitmex
    # Saves to folder
    from bitmex import bitmex
    testnet = False
    logging.info(f"[Bitmex] Trying Bitmex for {ticker}")
    from thewarden.pricing_engine.pricing import api_keys_class
    api_keys_json = api_keys_class.loader()
    bitmex_credentials = api_keys_json['bitmex']

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
    except Exception:
        resp = "Invalid Credential or Connection Error"
    return(resp)


def time_ago(time=False):
    if type(time) is str:
        try:
            time = int(time)
        except TypeError:
            return ""
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    else:
        return ("")
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

    if day_diff == 0:
        if second_diff < 10:
            return "Just Now"
        if second_diff < 60:
            return str(int(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(int(day_diff)) + " days ago"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months ago"
    return str(int(day_diff / 365)) + " years ago"


