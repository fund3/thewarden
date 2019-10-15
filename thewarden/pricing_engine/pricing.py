# Class to include several price providers that work together to update a
# list of pricing databases
# The databases are saved in the pickle format as pandas df for later use
# The field dictionary is a list of column names for the provider to
# associate with the standardized field names for the dataframe
# Standardized field names:
# open, high, low, close, volume
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from flask_login import current_user

from thewarden.node.utils import tor_request
from thewarden.users.decorators import MWT, timing

# Generic Requests will try each of these before failing
REALTIME_PROVIDER_PRIORITY = [
    'cc_realtime', 'aa_realtime_digital', 'aa_realtime_stock',
    'fp_realtime_stock'
]
FX_RT_PROVIDER_PRIORITY = ['aa_realtime_digital', 'cc_realtime']
HISTORICAL_PROVIDER_PRIORITY = [
    'cc_digital', 'aa_digital', 'aa_stock', 'cc_fx', 'aa_fx', 'fmp_stock',
    'bitmex'
]
FX_PROVIDER_PRIORITY = ['aa_fx', 'cc_fx']

# How to include new API providers (historical prices):
# Step 1:
#     Edit the PROVIDER_LIST dictionary at the end of the file.
#     See examples there and follow a similar pattern.
#     There are 2 types of providers in that list
#     a. Providers using an html request (like aa_digital)
#     b. Providers using an internal library (like bitmex)
# Step 2:
#     Edit the price parser function to include a new if statement
#     for the new provider. Follow the examples to return a pandas
#     dataframe.
#     Errors can be returned to the self.errors variable
#     on error, return df as None (this will signal an error)
# Notes:
#     Data is saved locally to a pickle file to be used during
#     the same day. File format is <TICKER>_<PROVIDER.NAME>.price
#     see ./pricing_data folder for samples
# Including realtime providers:
# Step 1:
#     follow step 1 above.
# Step 2:
#     edit the realtime function to parse the date correctly and
#     return a price float

# _____________________________________________
# Classes go here
# _____________________________________________


@MWT(timeout=60)
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


class PriceProvider:
    # This class manages a list of all pricing providers
    def __init__(self,
                 name,
                 base_url,
                 ticker_field,
                 field_dict=None,
                 doc_link=None):
        # field dict includes all fields to be passed to the URL
        # for example, for Alphavantage
        # name = 'Alphavantage_digital'
        # base-url = 'https://www.alphavantage.co/query'
        # ticker_field = 'symbol'
        # field_dict = {'function': 'DIGITAL_CURRENCY_DAILY',
        #               'market': 'CNY',
        #               'apikey': 'demo')
        # doc_link = 'https://www.alphavantage.co/documentation/'
        # parse_dict = {'open' : '1a. open (USD)', ...}
        self.name = name.lower()
        self.base_url = base_url
        self.ticker_field = ticker_field
        self.field_dict = field_dict
        self.doc_link = doc_link
        if self.field_dict is not None:
            self.url_args = "&" + urllib.parse.urlencode(field_dict)
        self.errors = []

    @MWT(timeout=5)
    def request_data(self, ticker):
        data = None
        if self.base_url is not None:
            ticker = ticker.upper()
            globalURL = (self.base_url + "?" + self.ticker_field + "=" +
                         ticker + self.url_args)
            # Some APIs use the ticker without a ticker field i.e. xx.xx./AAPL&...
            # in these cases, we pass the ticker field as empty
            if self.ticker_field == '':
                if self.url_args[0] == '&':
                    self.url_args = self.url_args.replace('&', '?', 1)
                globalURL = (self.base_url + "/" + ticker + self.url_args)
            request = tor_request(globalURL)
            try:
                data = request.json()
            except Exception:
                try:  # Try again - some APIs return a json already
                    data = json.loads(request)
                except Exception as e:
                    self.errors.append(e)
        return (data)


# PriceData Class Information
# Example on how to create a ticker class (PriceData)
# provider = PROVIDER_LIST['cc_digital']
# btc = PriceData("BTC", provider)
# btc.errors:       Any error messages
# btc.provider:     Provider being used for requests
# btc.filename:     Local filename where historical prices are saved
# Other info:
# btc.ticker, btc.last_update, btc.first_update, btc.last_close
# btc.update_history(force=False)
# btc.df_fx(currency, fx_provider): returns a df with
#                                   prices and fx conversions
# btc.price_ondate(date)
# btc.price_parser(): do not use directly. This is used to parse
#                     the requested data from the API provider
# btc.realtime(provider): returns realtime price (float)
class PriceData():
    # All methods related to a ticker
    def __init__(self, ticker, provider):
        # providers is a list of pricing providers
        # ex: ['alphavantage', 'Yahoo']
        self.ticker = ticker.upper()
        self.provider = provider
        self.filename = ("thewarden/pricing_engine/pricing_data/" +
                         self.ticker + "_" + provider.name + ".price")
        self.filename = os.path.join(current_path(), self.filename)
        self.errors = []
        # makesure file path exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        # Try to read from file and check how recent it is
        try:
            today = datetime.now().date()
            filetime = datetime.fromtimestamp(os.path.getctime(self.filename))
            if filetime.date() == today:
                self.df = pd.read_pickle(self.filename)
            else:
                self.df = self.update_history()
        except FileNotFoundError:
            self.df = self.update_history()

        try:
            self.last_update = self.df.index.max()
            self.first_update = self.df.index.min()
            self.last_close = self.df.head(1).close[0]
        except AttributeError as e:
            self.errors.append(e)
            self.last_update = self.first_update = self.last_close = None

    @timing
    @MWT(timeout=30)
    def update_history(self, force=False):
        # Check first if file exists and if fresh
        # The line below skips history for providers that have realtime in name
        if 'realtime' in self.provider.name:
            return None
        if not force:
            try:
                # Check if saved file is recent enough to be used
                # Local file has to have a modified time in today
                today = datetime.now().date()
                filetime = datetime.fromtimestamp(
                    os.path.getctime(self.filename))
                if filetime.date() == today:
                    price_pickle = pd.read_pickle(self.filename)
                    return (price_pickle)
            except FileNotFoundError:
                pass
        # File not found ot not new. Need to update the matrix
        # Cycle through the provider list until there's satisfactory data
        price_request = self.provider.request_data(self.ticker)
        # Parse and save
        df = self.price_parser(price_request, self.provider)
        if df is None:
            self.errors.append(
                f"Empty df for {self.ticker} using {self.provider.name}")
            return (None)
        df.sort_index(ascending=False, inplace=True)
        df.index = pd.to_datetime(df.index)
        df.to_pickle(self.filename)
        # Refresh the class - reinitialize
        return (df)

    @MWT(timeout=10)
    def df_fx(self, currency, fx_provider):
        try:
            # First get the df from this currency
            if currency != 'USD':
                fx = PriceData(currency, fx_provider)
                fx.df = fx.df.rename(columns={'close': 'fx_close'})
                fx.df["fx_close"] = pd.to_numeric(fx.df.fx_close,
                                                  errors='coerce')
                # Merge the two dfs:
                merge_df = pd.merge(self.df, fx.df, on='date', how='inner')
                merge_df['close'] = merge_df['close'].astype(float)
                merge_df['close_converted'] = merge_df['close'] * merge_df[
                    'fx_close']
                return (merge_df)
            else:  # If currency is USD no conversion is needed - prices are all in USD
                self.df['fx_close'] = 1
                self.df['close_converted'] = self.df['close'].astype(float)
                return (self.df)
        except Exception as e:
            self.errors.append(e)
            return (None)

    @MWT(timeout=120)
    def price_ondate(self, date_input):
        try:
            dt = pd.to_datetime(date_input)
            idx = self.df.iloc[self.df.index.get_loc(dt, method='nearest')]
            return (idx)
        except Exception as e:
            self.errors.append(
                f"Error getting price on date {date_input} for {self.ticker}. Error {e}"
            )
            return (None)

    def price_parser(self, data, provider):
        # Parse the pricing of a specific API provider so it is in a
        # standard pandas df format that can be used and merged.
        # WHEN ADDING NEW APIs, this is the main function that needs to be
        # updated since each API has a different price format
        # Standard format is:
        # date (index), close, open, high, low, volume
        # Provider: alphavantagedigital
        if provider.name == 'alphavantagedigital':
            try:
                df = pd.DataFrame.from_dict(
                    data['Time Series (Digital Currency Daily)'],
                    orient="index")
                df = df.rename(
                    columns={
                        '4a. close (USD)': 'close',
                        '1a. open (USD)': 'open',
                        '2a. high (USD)': 'high',
                        '3a. low (USD)': 'low',
                        '5. volume': 'volume'
                    })
                df_save = df[['close', 'open', 'high', 'low', 'volume']]
                df.index.names = ['date']
            except Exception as e:
                self.errors.append(e)
                df_save = None
            return (df_save)

        # Provider: alphavantagestocks
        if provider.name == 'alphavantagestock':
            try:
                df = pd.DataFrame.from_dict(data['Time Series (Daily)'],
                                            orient="index")
                df = df.rename(
                    columns={
                        '4. close': 'close',
                        '1. open': 'open',
                        '2. high': 'high',
                        '3. low': 'low',
                        '5. volume': 'volume'
                    })
                df_save = df[['close', 'open', 'high', 'low', 'volume']]
                df.index.names = ['date']
            except Exception as e:
                self.errors.append(e)
                df_save = None
            return (df_save)

        # Provider: fmpstocks
        if provider.name == 'financialmodelingprep':
            try:
                df = pd.DataFrame.from_records(data['historical'])
                df = df.rename(
                    columns={
                        'close': 'close',
                        'open': 'open',
                        'high': 'high',
                        'low': 'low',
                        'volume': 'volume'
                    })
                df.set_index('date', inplace=True)
                df_save = df[['close', 'open', 'high', 'low', 'volume']]
            except Exception as e:
                self.errors.append(e)
                df_save = None
            return (df_save)

        # Provider:
        if provider.name == 'alphavantagefx':
            try:
                df = pd.DataFrame.from_dict(data['Time Series FX (Daily)'],
                                            orient="index")
                df = df.rename(
                    columns={
                        '4. close': 'close',
                        '1. open': 'open',
                        '2. high': 'high',
                        '3. low': 'low'
                    })
                df_save = df[['close', 'open', 'high', 'low']]
                df.index.names = ['date']
            except Exception as e:
                self.errors.append(e)
                df_save = None
            return (df_save)

        # CryptoCompare Digital and FX use the same parser
        if provider.name == 'ccdigital' or provider.name == 'ccfx':
            try:
                df = pd.DataFrame.from_dict(data['Data'])
                df = df.rename(columns={'time': 'date'})
                df['date'] = pd.to_datetime(df['date'], unit='s')
                df.set_index('date', inplace=True)
                df_save = df[['close', 'open', 'high', 'low']]
            except Exception as e:
                self.errors.append(e)
                df_save = None
            return (df_save)

        if provider.name == 'bitmex':
            try:
                df = bitmex_gethistory(self.ticker, provider)
                if isinstance(df, str):
                    if df.find('error') != -1:
                        self.errors.append(df)
                        df = None
                        return (df)
                df = df.rename(columns={'timestamp': 'date'})
                df.set_index('date', inplace=True)
                df_save = df[[
                    'close', 'open', 'high', 'low', 'volume', 'vwap'
                ]]
                return (df_save)
            except Exception as e:
                self.errors.append(e)
                df = None
            return (df)
        # If no name is found, return None
        return None

    def realtime(self, rt_provider):
        # This is the parser for realtime prices.
        # Data should be parsed so only the price is returned
        price_request = rt_provider.request_data(self.ticker)
        price = None
        if rt_provider.name == 'ccrealtime':
            try:
                price = (price_request['USD'])
            except Exception as e:
                self.errors.append(e)

        if rt_provider.name == 'aarealtime':
            try:
                price = (price_request['Realtime Currency Exchange Rate']
                         ['5. Exchange Rate'])
            except Exception as e:
                self.errors.append(e)

        if rt_provider.name == 'aarealtimestock':
            try:
                price = (price_request['Global Quote']['05. price'])
            except Exception as e:
                self.errors.append(e)

        if rt_provider.name == 'ccrealtimefull':
            try:
                price = (price_request['RAW'][self.ticker]['USD'])
            except Exception as e:
                self.errors.append(e)

        if rt_provider.name == 'fprealtimestock':
            try:
                price = (price_request['price'])
            except Exception as e:
                self.errors.append(e)

        return price


@timing
@MWT(timeout=10)
class ApiKeys():
    # returns current stored keys in the api_keys.conf file
    # makesure file path exists
    def __init__(self):
        self.filename = 'thewarden/pricing_engine/api_keys.conf'
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        self.filename = os.path.join(current_path(), self.filename)

    def loader(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as fp:
                    data = json.load(fp)
                    return (data)
            except (FileNotFoundError, KeyError):
                pass
        else:
            # File not found, let's construct a new one
            empty_api = {
                "alphavantage": {"api_key": "AA_TEMP_APIKEY"},
                "bitmex": {"api_key": None, "api_secret": None},
                "dojo": {"onion": None, "api_key": None, "token": "error"}
            }
            return (empty_api)

    def saver(self, api_dict):
        try:
            with open(self.filename, 'w') as fp:
                json.dump(api_dict, fp)
        except Exception:
            pass


# Class instance with api keys loader and saver
api_keys_class = ApiKeys()
api_keys = api_keys_class.loader()

# _____________________________________________
#            Helper functions go here
# _____________________________________________


# Bitmex Helper Function (uses bitmex library instead of requests)
# Returns a df with history
def bitmex_gethistory(ticker, provider):
    # Gets historical prices from bitmex
    # Saves to folder
    from bitmex import bitmex
    bitmex_credentials = provider.field_dict
    if ("api_key" in bitmex_credentials) and (
            "api_secret" in bitmex_credentials):
        try:
            mex = bitmex(api_key=bitmex_credentials['api_key'],
                         api_secret=bitmex_credentials['api_secret'],
                         test=bitmex_credentials['testnet'])
            # Need to paginate results here to get all the history
            # Bitmex API end point limits 750 results per call
            start_bin = 0
            resp = (mex.Trade.Trade_getBucketed(symbol=ticker,
                                                binSize="1d",
                                                count=500,
                                                start=start_bin).result())[0]
            df = pd.DataFrame(resp)
            last_update = df['timestamp'].iloc[-1]

            # If last_update is older than 3 days ago, keep building.
            while last_update < (datetime.now(timezone.utc) -
                                 timedelta(days=3)):
                start_bin += 500
                resp = (mex.Trade.Trade_getBucketed(
                    symbol=ticker, binSize="1d", count=500,
                    start=start_bin).result())[0]
                df = df.append(resp)
                last_update = df['timestamp'].iloc[-1]
                # To avoid an infinite loop, check if start_bin
                # is higher than 10000 and stop (i.e. 30+yrs of data)
                if start_bin > 10000:
                    break
            return (df)
        except Exception as e:
            return (f"error: {e}")
    else:
        return ('error: no credentials found for Bitmex')


# Loop through all providers to get the first non-empty df
def price_data(ticker):
    for provider in HISTORICAL_PROVIDER_PRIORITY:
        price_data = PriceData(ticker, PROVIDER_LIST[provider])
        if price_data.df is not None:
            break
    return (price_data)


# Returns price data in current user's currency
def price_data_fx(ticker):
    for provider in HISTORICAL_PROVIDER_PRIORITY:
        price_data = PriceData(ticker, PROVIDER_LIST[provider])
        if price_data.df is not None:
            break
    # Loop through FX providers until a df is filled
    for provider in FX_PROVIDER_PRIORITY:
        prices = price_data.df_fx(current_user.fx(), PROVIDER_LIST[provider])
        if prices is not None:
            break
    return (prices)


# Returns realtime price for a ticker using the provider list
# Price is returned in USD
def price_data_rt(ticker, priority_list=REALTIME_PROVIDER_PRIORITY):
    if ticker == 'USD':
        return None
    for provider in priority_list:
        price_data = PriceData(ticker, PROVIDER_LIST[provider])
        if price_data.realtime(PROVIDER_LIST[provider]) is not None:
            break
    return (price_data.realtime(PROVIDER_LIST[provider]))


@MWT(timeout=60)
def GBTC_premium(price):
    # Calculates the current GBTC premium in percentage points
    # to BTC (see https://grayscale.co/bitcoin-trust/)
    SHARES = 0.00097630
    fairvalue = price_data_rt("BTC") * SHARES
    premium = (price / fairvalue) - 1
    return fairvalue, premium


# Returns full realtime price for a ticker using the provider list
# Price is returned in USD
def price_grabber_rt_full(ticker, priority_list=['cc', 'aa', 'fp']):
    for provider in priority_list:
        price_data = price_data_rt_full(ticker, provider)
        if price_data is not None:
            return {'provider': provider,
                    'data': price_data}
    return None


@MWT(timeout=10)
def price_data_rt_full(ticker, provider):
    # Function to get a complete data set for realtime prices
    # Loop through the providers to get the following info:
    # price, chg, high, low, volume, mkt cap, last_update, source
    # For some specific assets, a field 'note' can be passed and
    # will replace volume and market cap at the main page
    # ex: GBTC premium can be calculated here
    # returns a list with the format:
    # price, last_update, high, low, chg, mktcap,
    # last_up_source, volume, source, notes
    # All data returned in USD
    # -----------------------------------------------------------
    # This function is used to grab a single price that was missing from
    # the multiprice request. Since this is a bit more time intensive, it's
    # separated so it can be memoized for a period of time (this price will
    # not refresh as frequently)
    # default: timeout=30

    if provider == 'cc':
        multi_price = multiple_price_grab(ticker, 'USD,' + current_user.fx())
        try:
            # Parse the cryptocompare data
            price = multi_price["RAW"][ticker][current_user.fx()]["PRICE"]
            price = float(price * current_user.fx_rate_USD())
            high = float(
                multi_price["RAW"][ticker][current_user.fx()]["HIGHDAY"] *
                current_user.fx_rate_USD())
            low = float(
                multi_price["RAW"][ticker][current_user.fx()]["LOWDAY"] *
                current_user.fx_rate_USD())
            chg = multi_price["RAW"][ticker][
                current_user.fx()]["CHANGEPCT24HOUR"]
            mktcap = multi_price["DISPLAY"][ticker][
                current_user.fx()]["MKTCAP"]
            volume = multi_price["DISPLAY"][ticker][
                current_user.fx()]["VOLUME24HOURTO"]
            last_up_source = multi_price["RAW"][ticker][
                current_user.fx()]["LASTUPDATE"]
            source = multi_price["DISPLAY"][ticker][
                current_user.fx()]["LASTMARKET"]
            last_update = datetime.now()
            notes = None
            return (price, last_update, high, low, chg, mktcap, last_up_source,
                    volume, source, notes)
        except Exception:
            return (None)
    if provider == 'aa':
        try:
            globalURL = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&apikey='
            globalURL += api_keys['alphavantage'][
                'api_key'] + '&symbol=' + ticker
            data = tor_request(globalURL).json()
            price = float(data['Global Quote']
                          ['05. price']) * current_user.fx_rate_USD()
            high = float(
                data['Global Quote']['03. high']) * current_user.fx_rate_USD()
            low = float(
                data['Global Quote']['04. low']) * current_user.fx_rate_USD()
            chg = data['Global Quote']['10. change percent'].replace('%', '')
            try:
                chg = float(chg)
            except Exception:
                chg = chg
            mktcap = '-'
            volume = '-'
            last_up_source = '-'
            last_update = '-'
            source = 'Alphavantage'
            notes = None

            # Start Notes methods for specific assets. For example, for
            # GBTC we report the premium to BTC
            if ticker == 'GBTC':
                fairvalue, premium = GBTC_premium(
                    float(data['Global Quote']['05. price']))
                fairvalue = "{0:,.2f}".format(fairvalue)
                premium = "{0:,.2f}".format(premium * 100)
                notes = f"Fair Value: {fairvalue}<br>Premium: {premium}%"
            return (price, last_update, high, low, chg, mktcap, last_up_source,
                    volume, source, notes)
        except Exception:
            return None

    if provider == 'fp':
        try:
            globalURL = 'https://financialmodelingprep.com/api/v3/stock/real-time-price/'
            globalURL += ticker
            data = tor_request(globalURL).json()
            price = float(data['price']) * current_user.fx_rate_USD()
            high = '-'
            low = '-'
            chg = 0
            mktcap = '-'
            volume = '-'
            last_up_source = '-'
            last_update = '-'
            source = 'FP Modeling API'
            notes = None
            return (price, last_update, high, low, chg, mktcap, last_up_source,
                    volume, source, notes)
        except Exception:
            return None


# Gets Currency data for current user
# Setting a timeout to 10 as fx rates don't change so often
@timing
def fx_rate():
    from thewarden.users.utils import fxsymbol
    # This grabs the realtime current currency conversion against USD
    print(price_data_rt(current_user.fx(), FX_RT_PROVIDER_PRIORITY))
    try:
        # get fx rate
        rate = {}
        rate['base'] = current_user.fx()
        rate['symbol'] = fxsymbol(current_user.fx())
        rate['name'] = fxsymbol(current_user.fx(), 'name')
        rate['name_plural'] = fxsymbol(current_user.fx(), 'name_plural')
        rate['cross'] = "USD" + " / " + current_user.fx()
        try:
            rate['fx_rate'] = 1 / (float(
                price_data_rt(current_user.fx(), FX_RT_PROVIDER_PRIORITY)))
        except Exception:
            rate['fx_rate'] = 1
    except Exception as e:
        rate = {}
        rate['error'] = (f"Error: {e}")
        rate['fx_rate'] = 1
    return (rate)


@MWT(timeout=30)
@timing
# For Tables that need multiple prices at the same time, it's quicker to get
# a single price request
# This will attempt to get all prices from cryptocompare api and return a single df
# If a price for a security is not found, other rt providers will be used.
def multiple_price_grab(tickers, fx):
    # tickers should be in comma sep string format like "BTC,ETH,LTC"
    baseURL = \
        "https://min-api.cryptocompare.com/data/pricemultifull?fsyms="\
        + tickers + "&tsyms=" + fx
    try:
        request = tor_request(baseURL)
    except requests.exceptions.ConnectionError:
        return ("ConnectionError")
    try:
        data = request.json()
    except AttributeError:
        data = "ConnectionError"
    return (data)


@MWT(timeout=20)
def get_price_ondate(ticker, date):
    try:
        price_class = price_data(ticker)
        price_ondate = price_class.price_ondate(date)
        return (price_ondate)
    except Exception:
        return (0)


@MWT(timeout=20)
def fx_price_ondate(base, cross, date):
    # Gets price conversion on date between 2 currencies
    # on a specific date
    try:
        provider = PROVIDER_LIST['cc_fx']
        if base == 'USD':
            price_base = 1
        else:
            base_class = PriceData(base, provider)
            price_base = base_class.price_ondate(date).close
        if cross == 'USD':
            price_cross = 1
        else:
            cross_class = PriceData(cross, provider)
            price_cross = cross_class.price_ondate(date).close
        conversion = float(price_cross) / float(price_base)
        return (conversion)
    except Exception:
        return (1)


# _____________________________________________
# Variables go here
# _____________________________________________
# List of API providers
# name: should be unique and contain only lowecase letters
PROVIDER_LIST = {
    'aa_digital':
    PriceProvider(name='alphavantagedigital',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='symbol',
                  field_dict={
                      'function': 'DIGITAL_CURRENCY_DAILY',
                      'market': 'USD',
                      'apikey': api_keys['alphavantage']['api_key']
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'aa_stock':
    PriceProvider(name='alphavantagestock',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='symbol',
                  field_dict={
                      'function': 'TIME_SERIES_DAILY',
                      'outputsize': 'full',
                      'apikey': api_keys['alphavantage']['api_key']
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'fmp_stock':
    PriceProvider(
        name='financialmodelingprep',
        base_url='https://financialmodelingprep.com/api/v3/historical-price-full',
        ticker_field='',
        field_dict={
            'from': '2001-01-01',
            'to:': '2099-12-31'
        },
        doc_link='https://financialmodelingprep.com/developer/docs/#Stock-Price'
    ),
    'aa_fx':
    PriceProvider(name='alphavantagefx',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='to_symbol',
                  field_dict={
                      'function': 'FX_DAILY',
                      'outputsize': 'full',
                      'from_symbol': 'USD',
                      'apikey': api_keys['alphavantage']['api_key']
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'cc_digital':
    PriceProvider(
        name='ccdigital',
        base_url='https://min-api.cryptocompare.com/data/histoday',
        ticker_field='fsym',
        field_dict={
            'tsym': 'USD',
            'allData': 'true'
        },
        doc_link='https://min-api.cryptocompare.com/documentation?key=Historical&cat=dataHistoday'
    ),
    'cc_fx':
    PriceProvider(
        name='ccfx',
        base_url='https://min-api.cryptocompare.com/data/histoday',
        ticker_field='tsym',
        field_dict={
            'fsym': 'USD',
            'allData': 'true'
        },
        doc_link='https://min-api.cryptocompare.com/documentation?key=Historical&cat=dataHistoday'
    ),
    'bitmex':
    PriceProvider(name='bitmex',
                  base_url=None,
                  ticker_field=None,
                  field_dict={
                      'api_key': api_keys['bitmex']['api_key'],
                      'api_secret': api_keys['bitmex']['api_secret'],
                      'testnet': False
                  },
                  doc_link='https://www.bitmex.com/api/explorer/'),
    'cc_realtime':
    PriceProvider(name='ccrealtime',
                  base_url='https://min-api.cryptocompare.com/data/price',
                  ticker_field='fsym',
                  field_dict={'tsyms': 'USD'},
                  doc_link=None),
    'cc_realtime_full':
    PriceProvider(
        name='ccrealtimefull',
        base_url='https://min-api.cryptocompare.com/data/pricemultifull',
        ticker_field='fsyms',
        field_dict={'tsyms': 'USD'},
        doc_link='https://min-api.cryptocompare.com/documentation?key=Price&cat=multipleSymbolsFullPriceEndpoint'
    ),
    'aa_realtime_digital':
    PriceProvider(name='aarealtime',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='from_currency',
                  field_dict={
                      'function': 'CURRENCY_EXCHANGE_RATE',
                      'to_currency': 'USD',
                      'apikey': api_keys['alphavantage']['api_key']
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'aa_realtime_stock':
    PriceProvider(name='aarealtimestock',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='symbol',
                  field_dict={
                      'function': 'GLOBAL_QUOTE',
                      'apikey': api_keys['alphavantage']['api_key']
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'fp_realtime_stock':
    PriceProvider(
        name='fprealtimestock',
        base_url='https://financialmodelingprep.com/api/v3/stock/real-time-price',
        ticker_field='',
        field_dict='',
        doc_link='https://financialmodelingprep.com/developer/docs/#Stock-Price'
    ),
}


# -------------------------------------
# Search Engine
# -------------------------------------
# This is the main method for the search box
# Should return html ready data to be displayed at the front page
def search_engine(field):
    # Try first with Ticker as a price lookup
    results = price_grabber_rt_full(field)
    if results is not None:
        return results
    return None
