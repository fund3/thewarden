# Class to include several price providers that work together to update a single
# list of pricing databases
# The databases are saved in the pickle format as pandas df for later use
# The field dictionary is a list of column names for the provider to
# associate with the standardized field names for the dataframe
# Standardized field names:
# open, high, low, close, volume
import os
import sys
import json
import urllib.parse
import pandas as pd
from datetime import datetime, timedelta, timezone
from flask_login import current_user
from thewarden.node.utils import tor_request
from thewarden.users.decorators import timing, memoized

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


@timing
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
        if self.field_dict is not None:
            self.url_args = "&" + urllib.parse.urlencode(field_dict)
        self.errors = []

    @memoized
    def request_data(self, ticker):
        data = None
        if self.base_url is not None:
            ticker = ticker.upper()
            globalURL = (self.base_url + "?" + self.ticker_field + "=" +
                         ticker + self.url_args)
            request = tor_request(globalURL)
            try:
                data = request.json()
            except Exception:
                try:  # Try again - some APIs return a json already
                    data = json.loads(request)
                except Exception as e:
                    self.errors.append(e)
        return (data)


@timing
class PriceData():
    # All methods related to a ticker
    def __init__(self, ticker, provider):
        # providers is a list of pricing providers
        # ex: ['alphavantage', 'Yahoo']
        self.ticker = ticker.upper()
        self.provider = provider
        self.filename = ("thewarden/pricing_engine/pricing_data/" +
                         self.ticker + "_" + provider.name + ".price")
        self.errors = []
        # makesure file path exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        # Try to read from file
        try:
            self.df = pd.read_pickle(self.filename)
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
    def update_history(self, force=False):
        # Check first if file exists and if fresh
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

    @timing
    def df_fx(self, currency, fx_provider):
        try:
            # First get the df from this currency
            if currency != 'USD':
                fx = PriceData(currency, fx_provider)
                fx.df = fx.df.rename(columns={'close': 'fx_close'})
                fx.df["fx_close"] = pd.to_numeric(fx.df.fx_close, errors='coerce')
                # Merge the two dfs:
                merge_df = pd.merge(self.df, fx.df, on='date', how='inner')
                merge_df['close'] = merge_df['close'].astype(float)
                merge_df['close_converted'] = merge_df['close'] * merge_df['fx_close']
                return (merge_df)
            else:  # If currency is USD no conversion is needed - prices are all in USD
                self.df['fx_close'] = 1
                self.df['close_converted'] = self.df['close'].astype(float)
                return (self.df)
        except Exception as e:
            self.errors.append(e)
            return (None)

    @timing
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

    @timing
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

        # Provider: alphavantagestocks
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

    @timing
    def realtime(self, rt_provider):
        price_request = rt_provider.request_data(self.ticker)
        price = None

        if rt_provider.name == 'ccrealtime':
            try:
                price = (price_request['USD'])
            except Exception as e:
                self.errors.append(e)

        if rt_provider.name == 'aarealtime':
            try:
                price = (price_request[
                    'Realtime Currency Exchange Rate'][
                    '5. Exchange Rate'])
            except Exception as e:
                self.errors.append(e)

        return price


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
            mex = bitmex(test=bitmex_credentials.testnet,
                         api_key=bitmex_credentials['api_key'],
                         api_secret=bitmex_credentials['api_secret'])
            # Need to paginate results here to get all the history
            # Bitmex API end point limits 750 results per call
            start_bin = 0
            resp = (mex.Trade.Trade_getBucketed(symbol=ticker,
                                                binSize="1d",
                                                count=750,
                                                start=start_bin).result())[0]
            df = pd.DataFrame(resp)
            last_update = df['timestamp'].iloc[-1]

            # If last_update is older than 3 days ago, keep building.
            while last_update < (datetime.now(timezone.utc) -
                                 timedelta(days=3)):
                start_bin += 750
                resp = (mex.Trade.Trade_getBucketed(
                    symbol=ticker, binSize="1d", count=750,
                    start=start_bin).result())[0]
                df = df.append(resp)
                last_update = df['timestamp'].iloc[-1]
                # To avoid an infinite loop, check if start_bin
                # is higher than 10000 and stop (i.e. 30+yrs of data)
                if start_bin > 10000:
                    break
            return (df)
        except Exception as e:
            return ("error: {e}")
    else:
        return ('error: no credentials found for Bitmex')


# MOVE THIS TO JSON
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
                      'apikey': 'XPTOcddc123'
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'aa_stock':
    PriceProvider(name='alphavantagestock',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='symbol',
                  field_dict={
                      'function': 'TIME_SERIES_DAILY',
                      'outputsize': 'full',
                      'apikey': 'XPTOcddc123'
                  },
                  doc_link='https://www.alphavantage.co/documentation/'),
    'aa_fx':
    PriceProvider(name='alphavantagefx',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='to_symbol',
                  field_dict={
                      'function': 'FX_DAILY',
                      'outputsize': 'full',
                      'from_symbol': 'USD',
                      'apikey': 'XPTOcddc123'
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
        doc_link=
        'https://min-api.cryptocompare.com/documentation?key=Historical&cat=dataHistoday'
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
        doc_link=
        'https://min-api.cryptocompare.com/documentation?key=Historical&cat=dataHistoday'
    ),

    'bitmex':
    PriceProvider(name='bitmex',
                  base_url=None,
                  ticker_field=None,
                  field_dict={
                      'api_key': 'your_key_here',
                      'api_secret': 'your_secret_here',
                      'testnet': False
                  },
                  doc_link='https://www.bitmex.com/api/explorer/'),
    'cc_realtime':
    PriceProvider(name='ccrealtime',
                  base_url='https://min-api.cryptocompare.com/data/price',
                  ticker_field='fsym',
                  field_dict={'tsyms': 'USD'},
                  doc_link=None),
    'aa_realtime':
    PriceProvider(name='aarealtime',
                  base_url='https://www.alphavantage.co/query',
                  ticker_field='from_currency',
                  field_dict={'function' : 'CURRENCY_EXCHANGE_RATE',
                              'to_currency': 'USD',
                              'apikey': 'xpto1234567890'},
                  doc_link='https://www.alphavantage.co/documentation/')
}

# Generic Requests will try each of these before failing
HISTORICAL_PROVIDER_PRIORITY = [
    'cc_digital', 'aa_digital', 'aa_stock', 'cc_fx', 'aa_fx',  'bitmex']
REALTIME_PROVIDER_PRIORITY = ['cc_realtime', 'aa_realtime']
FX_PROVIDER_PRIORITY = ['cc_fx', 'aa_fx']


# Todo: Include benchmarking method maybe to show how slow or quick each are
# Include a daily maintenance to download all historical prices
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
