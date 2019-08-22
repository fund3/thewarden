import json
import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from thewarden.node.utils import (
    dojo_add_hd,
    dojo_auth,
    dojo_status,
    tor_request,
    dojo_get_settings,
    dojo_multiaddr,
    dojo_get_txs,
)
from thewarden import db, test_tor
from thewarden.node.forms import DojoForm, AddressForm, Custody_Account
from thewarden.models import User, BitcoinAddresses, AccountInfo
from thewarden.pricing_engine.pricing import api_keys_class

node = Blueprint("node", __name__)


# Returns a JSON with Test Response on TOR
@node.route("/testtor", methods=["GET"])
@login_required
def testtor():
    return json.dumps(test_tor())


@node.route("/tor_setup", methods=["GET"])
@login_required
def tor_setup():
    tor_enabled = test_tor()
    return render_template("tor.html",
                           title="Tor Config and Check",
                           tor_enabled=tor_enabled)


@node.route("/dojo_setup", methods=["GET", "POST"])
@login_required
def dojo_setup():
    at = dojo_auth()
    try:
        status = dojo_status().json()
    except AttributeError:
        status = dojo_status()

    user_info = User.query.filter_by(username=current_user.username).first()
    form = DojoForm()
    if form.validate_on_submit():
        api_keys_json = api_keys_class.loader()
        api_keys_json['dojo']['onion'] = form.dojo_onion.data
        api_keys_json['dojo']['api_key'] = form.dojo_apikey.data
        api_keys_json['dojo']['token'] = form.dojo_token.data
        api_keys_class.saver(api_keys_json)
        at = dojo_auth()
    elif request.method == "GET":
        at = dojo_auth()
        api_keys_json = api_keys_class.loader()
        form.dojo_onion.data = api_keys_json['dojo']['onion']
        form.dojo_apikey.data = api_keys_json['dojo']['api_key']
        try:
            form.dojo_token.data = at["authorizations"]["access_token"]
        except (KeyError, TypeError):
            form.dojo_token.data = "Error getting token"

    last_block = tor_request("https://api.oxt.me/lastblock")
    if last_block == "ConnectionError":
        last_block = " - "
        progress = "unknown"
    else:
        try:
            if status["blocks"]:
                last_block = last_block.json()
                progress = float(status["blocks"]) / float(
                    last_block["data"][0]["height"])
            else:
                progress = "unknown"
        except (KeyError, TypeError):
            progress = "unknown"

    return render_template(
        "dojo.html",
        title="Dojo Config and Check",
        form=form,
        at=at,
        user_info=user_info,
        status=status,
        last_block=last_block,
        progress=progress,
    )


@node.route("/bitcoin_address", methods=["GET", "POST"])
@login_required
# Takes argument id to edit an address
def bitcoin_address():
    form = AddressForm()
    title = form_title = "Bitcoin Address"
    # address_list = BitcoinAddresses.query.filter_by(user_id=current_user.username)
    if form.validate_on_submit():
        id = request.args.get("id")
        if id:
            bitcoin_address = BitcoinAddresses.query.filter_by(
                user_id=current_user.username).filter_by(
                    address_id=id).first()
            if bitcoin_address is None:
                flash("Address id not found", "danger")
                return redirect(url_for("node.bitcoin_monitor"))

            bitcoin_address.user_id = current_user.username
            bitcoin_address.address_hash = form.address.data
            bitcoin_address.check_method = form.check_method.data
            bitcoin_address.account_id = form.account.data
            bitcoin_address.auto_check = form.auto_check.data
            bitcoin_address.imported_from_hdaddress = form.hd_parent.data
            bitcoin_address.notes = form.notes.data
            db.session.commit()
            # Make sure address is registered with Dojo
            at = dojo_get_settings()["token"]
            reg = dojo_multiaddr(bitcoin_address.address_hash, "active", at)
            if "error" in reg:
                flash(
                    f"Something went wrong when registering this address to your Dojo. \
                    It was added to the database but you may want to check your connection. Error: {reg}",
                    "danger",
                )
                return redirect(url_for("node.bitcoin_monitor"))

            flash("Address edited", "success")
            return redirect(url_for("node.bitcoin_monitor"))

        bitcoin_address = BitcoinAddresses(
            user_id=current_user.username,
            address_hash=form.address.data,
            check_method=form.check_method.data,
            account_id=form.account.data,
            auto_check=form.auto_check.data,
            imported_from_hdaddress=form.hd_parent.data,
            notes=form.notes.data,
        )

        try:
            db.session.add(bitcoin_address)
            db.session.commit()
        except Exception as e:
            flash(
                f"Address not included in database. Something went wrong. Try again. | Error Message: {e}",
                "danger",
            )
        try:
            # Import this address into the Dojo database
            at = dojo_get_settings()["token"]
            # Register this new address
            # dojo_multiaddr(bitcoin_address.address_hash, "new", at)
            dojo_multiaddr(bitcoin_address.address_hash, "active", at)
            flash(f"Address included.", "success")
        except Exception as err:
            flash(
                "Address included in database but something went wrong while trying "
                +
                f"to register this address at the Dojo. Check if your Dojo is connected | Error {err}",
                "warning",
            )

        return redirect(url_for("node.bitcoin_monitor"))

    elif request.method == "GET":
        title = form_title = "Register New Bitcoin Address"
        form.auto_check.data = True
        id = request.args.get("id")
        if id:
            title = form_title = "Edit Bitcoin Address"
            bitcoinaddress = (BitcoinAddresses.query.filter_by(
                user_id=current_user.username).filter_by(
                    address_id=id).first())
            if bitcoinaddress is None:
                flash("Address id not found", "danger")
                return redirect(url_for("node.bitcoin_monitor"))
            form.address.data = bitcoinaddress.address_hash
            form.check_method.data = bitcoinaddress.check_method
            form.account.data = bitcoinaddress.account_id
            form.hd_parent.data = bitcoinaddress.imported_from_hdaddress
            form.notes.data = bitcoinaddress.notes

    return render_template("new_address.html",
                           form=form,
                           form_title=form_title,
                           title=title)


@node.route("/bitcoin_addresses", methods=["GET", "POST"])
@login_required
def bitcoin_addresses():
    addresses = BitcoinAddresses.query.filter_by(user_id=current_user.username)
    if addresses.count() == 0:
        return render_template("bitcoin_empty.html", dojo=dojo_get_settings())

    return render_template("bitcoin_addresses.html",
                           title="Transaction History",
                           addresses=addresses)


@node.route("/bitcoin_monitor", methods=["GET", "POST"])
@login_required
def bitcoin_monitor():
    # Create a list of all addresses both in accounts and in bitcoin addresses
    account_list = []
    for account in BitcoinAddresses.query.filter_by(
            user_id=current_user.username).distinct(
                BitcoinAddresses.account_id):
        account_list.append(account.account_id)
    for account in AccountInfo.query.filter_by(
            user_id=current_user.username).distinct(AccountInfo.account_id):
        account_list.append(account.account_longname)
    # Remove duplicates
    account_list = list(set(account_list))
    # Now find each account_id for account_list items (for a link to edit)
    acc_dict = {}
    for ac_name in account_list:
        try:
            ac_id = (AccountInfo.query.filter_by(
                user_id=current_user.username).filter_by(
                    account_longname=ac_name).first().account_id)
        except AttributeError:
            ac_id = 0
        acc_dict[ac_name] = ac_id

    addresses = BitcoinAddresses.query.filter_by(user_id=current_user.username)
    accounts = AccountInfo.query.filter_by(user_id=current_user.username)
    # accounts_addresses = BitcoinAddresses.query().filter_by(user_id=current_user.username)
    total_accounts = AccountInfo.query.filter_by(
        user_id=current_user.username).count()
    accounts_none = (
        (AccountInfo.query.filter_by(user_id=current_user.username).filter_by(
            account_blockchain_id=None).count()) +
        AccountInfo.query.filter_by(user_id=current_user.username).filter_by(
            account_blockchain_id='').count())

    if addresses.count() == 0:
        if (total_accounts - accounts_none) != 0:
            return render_template(
                "bitcoin_monitor.html",
                title="Bitcoin Warden",
                addresses=addresses,
                accounts=account_list,
                acc_dict=acc_dict,
                account_info=accounts,
            )
        return render_template("bitcoin_empty.html",
                               title="Addresses Not Found",
                               dojo=dojo_get_settings())

    return render_template(
        "bitcoin_monitor.html",
        title="Bitcoin Warden",
        addresses=addresses,
        accounts=account_list,
        acc_dict=acc_dict,
        account_info=accounts,
    )


@node.route("/bitcoin_transactions/<address>", methods=["GET", "POST"])
@login_required
def bitcoin_transactions(address):
    logging.info(f"Started Bitcoin Transaction method for {address}")
    meta = {}
    transactions = {}
    # Check if HD Address
    hd_address_list = ("xpub", "ypub", "zpub")
    if address.lower().startswith(hd_address_list):
        hd_address = True
        # Get address data from DB
        bitcoin_address = (AccountInfo.query.filter_by(
            user_id=current_user.username).filter_by(
                account_blockchain_id=address).first())
    else:
        hd_address = False
        # Get address data from DB
        # Check first if this address is in database
        bitcoin_address = (BitcoinAddresses.query.filter_by(
            user_id=current_user.username).filter_by(
                address_hash=address).first())
    transactions["error"] = ""
    meta["hd"] = hd_address
    meta["success"] = False
    meta["n_txs"] = 0
    if bitcoin_address:
        logging.info("Address Found in Database")
        meta["found"] = True  # Found in database
        meta["account"] = bitcoin_address.account_id
        # Let's check if there's a balance in this address
        at = dojo_get_settings()["token"]  # Get Dojo Authent Token
        try:
            derivation = "pubkey"
            if hd_address:
                derivation = bitcoin_address.xpub_derivation
                if not derivation:
                    derivation = "pubkey"
            balance = dojo_multiaddr(address, derivation, at).json()
        except AttributeError:
            logging.warn("Did not receive a json back from multi_add")

            # balance = dojo_multiaddr(address, derivation, at)
        # Check if there's a balance in this address
        # {'wallet': {'final_balance': 0}, 'info':
        # {'latest_block': {'height': 586366, 'hash': '00000000000000000015ea0990b12ea4c04161203a305a0ceb5c67a678468f20',
        # 'time': 1563702071}}, 'addresses': [], 'txs': []}
        try:
            if balance["wallet"]["final_balance"] >= 0:
                meta["balance"] = balance["wallet"]["final_balance"]
                meta["success"] = True
        except (KeyError, UnboundLocalError):
            transactions[
                "error"] += "Could not retrieve a balance for this address. Check the address."
            logging.warn("No balance found on this address")
        except TypeError:
            try:
                balance = balance.json()
                transactions["error"] += balance["error"]
            except TypeError:
                transactions[
                    "error"] += "An unknown error occured. Check connection settings and address info."
        # Check if there are transactions in this address
        try:
            # the [0] here is needed since we're using multiaddr but only returning the 1st (and only) address
            if balance["addresses"][0]["n_tx"] > 0:
                meta["n_txs"] = balance["addresses"][0]["n_tx"]
        except (KeyError, IndexError):
            logging.info("No txs found for this address")
            transactions["error"] += "Could not retrieve any transactions."
            meta["n_txs"] = 0

        # Transactions, at this stage, can only be imported using Dojo
        if "n_txs" in meta:
            meta["check_method"] = "Dojo"
            transactions = dojo_get_txs(address, at)
            if ("balance" in meta) and (meta["balance"] >= 0):
                meta["success"] = True
                logging.info("Success: Address data gathered")

    # OK, this address is not in Database, so do nothing
    else:
        logging.warn(
            "Address not found in database - returning an error message")
        meta["found"] = False
        transactions[
            "error"] = "This address was not found in your list of addresses. Please include."

    return render_template(
        "bitcoin_transactions.html",
        title="Address Transactions",
        meta=meta,
        address=address,
        transactions=transactions,
    )


@node.route("/custody_account", methods=["GET", "POST"])
@login_required
# Takes argument id to edit an account
def custody_account():
    form = Custody_Account()
    title = form_title = "Custody Account"
    if form.validate_on_submit():
        id = request.args.get("id")
        account_name = request.args.get("name")
        if id:
            account = (AccountInfo.query.filter_by(
                user_id=current_user.username).filter_by(
                    account_id=id).first())
        if account_name:
            account = (AccountInfo.query.filter_by(
                user_id=current_user.username).filter_by(
                    account_longname=account_name).first())

        if id or account_name:
            if account is None:
                account = AccountInfo()
            account.user_id = current_user.username
            account.account_blockchain_id = form.account_blockchain_id.data
            account.account_longname = form.account_longname.data
            account.check_method = form.check_method.data
            account.auto_check = form.auto_check.data
            account.notes = form.notes.data
            db.session.commit()
            # Make sure address is registered with Dojo
            at = dojo_get_settings()["token"]
            reg = dojo_add_hd(account.account_blockchain_id, "restore", at)
            if "error" in reg:
                flash(
                    f"Something went wrong when registering this address to your Dojo. \
                    It was added to the database but you may want to check your connection. Error: {reg}",
                    "danger",
                )
                return redirect(url_for("node.bitcoin_monitor"))

            flash("Account edited", "success")
            return redirect(url_for("node.bitcoin_monitor"))

        account = AccountInfo(
            user_id=current_user.username,
            account_longname=form.account_longname.data,
            check_method=form.check_method.data,
            auto_check=form.auto_check.data,
            account_blockchain_id=form.account_blockchain_id.data,
            notes=form.notes.data,
        )

        try:
            db.session.add(account)
            db.session.commit()
            # Import this address into the Dojo database
            at = dojo_get_settings()["token"]
            # Register this new address
            reg = dojo_add_hd(account.account_blockchain_id, "restore", at)
            if "error" in reg:
                flash(
                    f"Something went wrong when registering this address to your Dojo. \
                    It was added to the database but you may want to check your connection. Error: {reg}",
                    "danger",
                )
                return redirect(url_for("node.bitcoin_monitor"))
            flash(f"Address included.", "success")
        except Exception as e:
            flash(
                f"Account not included. Something went wrong. Try again. | Error Message: {e}",
                "danger",
            )

        return redirect(url_for("node.bitcoin_monitor"))

    elif request.method == "GET":
        title = form_title = "New Custody Account"
        form.auto_check.data = True
        id = request.args.get("id")
        account = None
        account_name = request.args.get("name")
        if id:
            account = (AccountInfo.query.filter_by(
                user_id=current_user.username).filter_by(
                    account_id=id).first())
        if account_name:
            account = (AccountInfo.query.filter_by(
                user_id=current_user.username).filter_by(
                    account_longname=account_name).first())
        if not account:
            title = form_title = "Include Custody Account Info"
            form.account_longname.data = account_name
        if account is not None:
            title = form_title = "Edit Custody Account Info"
            form.account_longname.data = account.account_longname
            form.check_method.data = account.check_method
            form.auto_check.data = account.auto_check
            form.account_blockchain_id.data = account.account_blockchain_id
            form.notes.data = account.notes

    return render_template("custody_account.html",
                           form=form,
                           form_title=form_title,
                           title=title)


@node.route("/delete_baccount/<id>", methods=["GET", "POST"])
@login_required
def delete_baccount(id):
    # type = account or address
    account = None
    type = request.args.get("type")
    if type == "account":
        account = AccountInfo.query.filter_by(
            user_id=current_user.username).filter_by(account_id=id)
    if type == "address":
        account = BitcoinAddresses.query.filter_by(
            user_id=current_user.username).filter_by(address_id=id)

    if (account is None) or (account.count() == 0):
        flash(f"{type.capitalize()} id: {id} not found. Nothing done.",
              "warning")
        return redirect(url_for("node.bitcoin_monitor"))
    if account.first().user_id != current_user.username:
        abort(403)

    account.delete()
    db.session.commit()
    flash(f"{type.capitalize()} deleted", "danger")
    return redirect(url_for("node.bitcoin_monitor"))


@node.route("/import_addresses/", methods=["GET", "POST"])
@login_required
def import_addresses():
    return render_template("import_addresses.html",
                           title="Import Bitcoin Addresses")
