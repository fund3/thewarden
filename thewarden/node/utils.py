import logging

import pandas as pd
import requests
from flask import Markup, current_app, flash
from flask_login import current_user

from thewarden.models import User
from thewarden.users.decorators import MWT, memoized


@MWT(30)
# Requests within 30sec of each other will return the same result
# This is an optimization variable, too short and the app will run
# slow, too high and the data refresh will suffer.
# Default=20
def tor_request(url, tor_only=False, method="get"):
    # Tor requests takes arguments:
    # url:       url to get or post
    # tor_only:  request will only be executed if tor is available
    # method:    'get or' 'post'
    from thewarden import TOR

    logging.info(f"Starting request for url: {url}")
    tor_check = TOR
    if tor_check["status"] is True:
        try:
            # Activate TOR proxies
            session = requests.session()
            session.proxies = {
                "http": "socks5h://127.0.0.1:9150",
                "https": "socks5h://127.0.0.1:9150",
            }
            if method == "get":
                request = session.get(url, timeout=15)
            if method == "post":
                request = session.post(url, timeout=15)

        except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
        ) as e:
            logging.error(f"Connection Error on tor request: {e}")
            return "ConnectionError"
    else:
        if tor_only:
            return "Tor not available"
        try:
            if method == "get":
                request = requests.get(url, timeout=10)
            if method == "post":
                request = requests.post(url, timeout=10)

        except requests.exceptions.ConnectionError:
            logging.error("Connection Error on tor request")
            return "ConnectionError"

    logging.info("Tor Request: Success")
    return request


@MWT(10)
def dojo_get_settings(force=False):
    # Get and test settings. If not working get a new at
    logging.info("Getting Dojo settings")
    # check if dojo_settings are already stored
    from thewarden.pricing_engine.pricing import api_keys_class
    api_keys_json = api_keys_class.loader()
    onion_address = api_keys_json['dojo']['onion']
    api_key = api_keys_json['dojo']['api_key']
    at = dojo_auth()
    try:
        logging.info("Trying to get token")
        logging.info(f"Received back from auth: {at}")
        token = at["authorizations"]["access_token"]
        api_keys_json['dojo']['token'] = token
        api_keys_class.saver(api_keys_json)
    except (KeyError, TypeError) as e:
        logging.warn(f"Unable to get Dojo Token: {e}")
        logging.warn(f"Received back from auth: {at}, setting token to error.")
        token = "error"
        api_keys_json['dojo']['token'] = token
        api_keys_class.saver(api_keys_json)
        logging.error(f"Error while getting token.")

    logging.info(f"Current token: {token}")

    return (api_keys_json['dojo'])


@memoized
def dojo_auth(force=False):
    # Receives authentication token back from Dojo
    # https://github.com/Samourai-Wallet/samourai-dojo/blob/develop/doc/POST_auth_login.md
    # POST /v2/auth/login

    # On Success, returns:                  On Invalid token:
    # {                                     {'status': 'error',
    #   "authorizations": {                 'error': 'Invalid JSON Web Token'}
    #     "access_token": <token>,
    #     "refresh_token": <token>
    #   }
    # }

    # On API Key error, returns:            On Connection error, returns:
    # {                                     {
    #   "status": "error",                      "status": "error",
    #   "error": "Invalid API key"              "error": "Connection Error"
    # }                                     }
    # SET Default timeout to get a token. Too low timeouts could be a problem

    TIME_OUT = 20
    logging.info("Starting DOJO Auth")
    # Check if variables are saved
    from thewarden.pricing_engine.pricing import api_keys_class
    api_keys_json = api_keys_class.loader()
    onion_address = api_keys_json['dojo']['onion']
    APIKey = api_keys_json['dojo']['api_key']
    token = api_keys_json['dojo']['token']
    if (onion_address is None) or (APIKey is None):
        logging.info("DOJO Auth: No Onion Address or API Key")
        auth_response = {"status": "error", "error": "missing config"}
        try:
            api_keys_json['dojo']['token'] = 'error'
        except TypeError:
            logging.info("Dojo_AUTH: Dojo Settings not found at database")
        return auth_response

    # Try to get the token
    url = "http://" + onion_address + "/v2/auth/login"
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    post_fields = {"apikey": APIKey}
    try:
        logging.info("DOJO AUTH: Trying to get authorization")
        auth_response = session.post(url, post_fields, timeout=TIME_OUT).json()
        token = auth_response['authorizations']['access_token']
    except (requests.exceptions.ConnectionError,
            requests.exceptions.InvalidURL, KeyError,
            requests.exceptions.ReadTimeout, requests.exceptions.InvalidSchema,
            UnicodeError, requests.exceptions.InvalidSchema) as e:
        logging.info(f"DOJO AUTH: Error: {e}")
        auth_response = {"status": "error", "error": f"Error: {e}"}
        token = 'error'
    # Store for this session in Global Variable
    api_keys_json['dojo']['token'] = token
    api_keys_class.saver(api_keys_json)
    logging.info(f"DOJO Settings updated")
    return (auth_response)


@MWT(20)
def dojo_get_address(addr, at):
    # Request details about a collection of HD accounts and/or loose addresses and/or public keys.
    # Takes arguments:
    #   addr:   address or list of addresses
    #   at:     authentication token

    onion_address = dojo_get_settings()["onion"]

    url = "http://" + onion_address + "/v2/address/" + addr + "/info?at=" + at

    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        auth_response = session.get(url)
    except requests.exceptions.ConnectionError:
        auth_response = {"status": "error", "error": "Connection Error"}
    return auth_response


@MWT(20)
def dojo_multiaddr(addr, type, at):
    # Request details about a collection of HD accounts and/or loose addresses and/or public keys.
    # Takes arguments:
    #   addr    address or list of addresses
    #   type    [active, new, bip49, bip84, pubkey] - more details below
    #           https://github.com/Samourai-Wallet/samourai-dojo/blob/develop/doc/GET_multiaddr.md
    #           IMPORTANT: to include new addresses for tracking, the type ACTIVE needs to be passed
    #           This will force a rescan of that address.
    #   at      authentication token
    logging.info("Starting MultiAddr")
    onion_address = dojo_get_settings()["onion"]
    if type.lower() == "bip44":
        type = "bip84"
    if onion_address is None:
        flash(
            Markup(
                "No Onion Address found for Dojo. <a class='alert-link' href='/account'>Go to settings to set one up.</a> "
            ),
            "warning",
        )
        auth_response = {"status": "error", "error": "No Onion Address set"}
        return auth_response
    url = "http://" + onion_address + "/v2/multiaddr"
    url = url + "?" + type + "=" + addr + "&at=" + at
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        logging.info("Sending GET request [Tor]")
        auth_response = session.get(url)
        logging.info("GET request success")
    except requests.exceptions.ConnectionError:
        logging.warn("Connection Error")
        auth_response = {"status": "error", "error": "Connection Error"}
    return auth_response


@memoized
def dojo_add_hd(xpub, type, at):
    # Notify the server of the new HD account for tracking.
    # https://github.com/Samourai-Wallet/samourai-dojo/blob/master/doc/POST_xpub.md
    onion_address = dojo_get_settings()["onion"]
    url = "http://" + onion_address + "/v2/xpub"
    post_fields = {"xpub": xpub, "type": type, "at": at, "force": "true"}
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        auth_response = session.post(url, post_fields)
    except requests.exceptions.ConnectionError:
        auth_response = {"status": "error", "error": "Connection Error"}
    return auth_response


@MWT(20)
def dojo_get_hd(xpub, at):
    # Request details about an HD account. If account does not exist, it must be created.
    # https://github.com/Samourai-Wallet/samourai-dojo/blob/master/doc/GET_xpub.md
    onion_address = dojo_get_settings()["onion"]
    url = "http://" + onion_address + "/v2/xpub/"
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        url = url + xpub + "?at=" + at
        auth_response = session.get(url)
    except requests.exceptions.ConnectionError:
        auth_response = {"status": "error", "error": "Connection Error"}
    return auth_response


@MWT(20)
def dojo_get_txs(addr, at):
    # Request transactions of an active address and return a dataframe + metadata
    onion_address = dojo_get_settings()["onion"]
    url = "http://" + onion_address + "/v2/txs?active="
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        url = url + addr + "&count=500&at=" + at
        auth_response = session.get(url)
        auth_response = auth_response.json()
        meta = {}
        meta["n_tx"] = auth_response["n_tx"]
        meta["address"] = addr
        txs = auth_response["txs"]
        # Create dataframe
        df_dict = pd.DataFrame.from_dict(txs)
        # Now construct the tx table in a pandas df
        tmp_list = []
        for __, row in df_dict.iterrows():
            tmp_list.append(
                [row["time"], row["result"], row["hash"], row["block_height"]])

        df = pd.DataFrame(tmp_list,
                          columns=["time", "result", "hash", "block"])
        if not df.empty:
            meta["transactions"] = df.to_dict()
            meta["balance"] = df["result"].sum().astype(float)
        else:
            meta["transactions"] = ""
            meta["balance"] = ""
        meta["raw"] = txs
        return meta

    except requests.exceptions.ConnectionError:
        auth_response = {"status": "error", "error": "Connection Error"}
        return auth_response

    except KeyError:
        if "error" in auth_response:
            # If Token error, force a new token
            if auth_response["error"] == "Invalid JSON Web Token":
                at = dojo_auth(True)
        return auth_response


@MWT(20)
def oxt_get_address(addr):
    # Requests via TOR address details from OXT
    url = "https://api.oxt.me/addresses/"
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        url = url + addr
        auth_response = session.get(url).json()
    except requests.exceptions.ConnectionError:
        auth_response = {"status": "error", "error": "Connection Error"}
    return auth_response


@MWT(10)
def dojo_status(token_test=None):
    logging.info("Getting Current Dojo Status")
    settings = dojo_get_settings()
    onion_address = settings["onion"]
    if not onion_address:
        auth_response = {"status": "error", "error": "Missing Onion Address"}
        return auth_response
    # If a token is passed for testing, use that token
    if not token_test:
        token = settings["token"]
    else:
        token = token_test

    url = "http://" + onion_address + "/v2/status?at=" + token
    session = requests.session()
    session.proxies = {
        "http": "socks5h://127.0.0.1:9150",
        "https": "socks5h://127.0.0.1:9150",
    }
    try:
        auth_response = session.get(url)
    except (
            requests.exceptions.ConnectionError,
            requests.exceptions.InvalidURL,
            requests.exceptions.ReadTimeout,
            UnicodeError,
    ) as e:
        auth_response = {"status": "error", "error": e}
    logging.info(f"Dojo Status responded: {auth_response}")
    return auth_response
