import numpy as np
import logging
from flask import render_template, Blueprint
from flask_login import current_user, login_required
from thewarden.models import Trades, User
from datetime import datetime
from thewarden.users.utils import (
    generatenav, generate_pos_table, heatmap_generator)

portfolio = Blueprint("portfolio", __name__)


@portfolio.before_request
def before_request():
    # Before any request at main, check if API Keys are set
    # But only if user is logged in.
    if current_user.is_authenticated:
        user_info = User.query.filter_by(username=current_user.username).first()
        if user_info.aa_apikey is None:
            logging.error("NO AA API KEY FOUND!")
            return render_template("welcome.html", title="Welcome")
        transactions = Trades.query.filter_by(user_id=current_user.username)
        if transactions.count() == 0:
            return render_template("empty.html")


@portfolio.route("/portfolio")
@login_required
# Home Page - details of the portfolio
def portfolio_main():
    user = current_user.username
    transactions = Trades.query.filter_by(user_id=current_user.username)
    if transactions.count() == 0:
        return render_template("empty.html")
    portfolio_data, pie_data = generate_pos_table(user, "USD", False)
    if portfolio_data == "empty":
        return render_template("empty.html")
    if portfolio_data == "ConnectionError":
        return render_template("offline.html", title="Connection Error")
    return render_template(
        "portfolio.html",
        title="Portfolio View",
        portfolio_data=portfolio_data,
        pie_data=pie_data,
    )


@portfolio.route("/navchart")
# Page with a single historical chart of NAV
# Include portfolio value as well as CF_sumcum()
@login_required
def navchart():
    data = generatenav(current_user.username)
    navchart = data[["NAV"]].copy()
    # dates need to be in Epoch time for Highcharts
    navchart.index = (navchart.index - datetime(1970, 1, 1)).total_seconds()
    navchart.index = navchart.index * 1000
    navchart.index = navchart.index.astype(np.int64)
    navchart = navchart.to_dict()
    navchart = navchart["NAV"]

    port_value_chart = data[["PORT_cash_value", "PORT_usd_pos", "PORT_ac_CFs"]].copy()
    port_value_chart["ac_pnl"] = (
        port_value_chart["PORT_usd_pos"] - port_value_chart["PORT_ac_CFs"]
    )
    # dates need to be in Epoch time for Highcharts
    port_value_chart.index = (
        port_value_chart.index - datetime(1970, 1, 1)
    ).total_seconds()
    port_value_chart.index = port_value_chart.index * 1000
    port_value_chart.index = port_value_chart.index.astype(np.int64)
    port_value_chart = port_value_chart.to_dict()

    return render_template(
        "navchart.html",
        title="NAV Historical Chart",
        navchart=navchart,
        port_value_chart=port_value_chart,
    )


@portfolio.route("/heatmap")
@login_required
# Returns a monthly heatmap of returns and statistics
def heatmap():
    heatmap_gen, heatmap_stats, years, cols = heatmap_generator()

    if not years:
        return render_template("empty.html")

    return render_template(
        "heatmap.html",
        title="Monthly Returns HeatMap",
        heatmap=heatmap_gen,
        heatmap_stats=heatmap_stats,
        years=years,
        cols=cols,
    )


@portfolio.route("/volchart", methods=["GET", "POST"])
@login_required
# Only returns the html - request for data is done through jQuery AJAX
def volchart():
    return render_template("volchart.html", title="Historical Volatility Chart")


@portfolio.route("/portfolio_compare", methods=["GET"])
@login_required
def portfolio_compare():
    return render_template("portfolio_compare.html", title="Portfolio Comparison")


@portfolio.route("/activity_summary", methods=["GET"])
@login_required
def activity_summary():
    user = current_user.username
    transactions = Trades.query.filter_by(user_id=current_user.username)
    if transactions.count() == 0:
        return render_template("empty.html")
    portfolio_data, pie_data = generate_pos_table(user, "USD", False)
    if portfolio_data == "ConnectionError":
        return render_template("offline.html", title="Connection Error")
    return render_template(
        "activity_summary.html",
        title="Activity Summary",
        portfolio_data=portfolio_data,
        pie_data=pie_data,
    )


@portfolio.route("/allocation_history", methods=["GET"])
@login_required
def allocation_history():
    return render_template(
        "allocation_history.html", title="Portfolio Historical Allocation"
    )


@portfolio.route("/scatter", methods=["GET"])
@login_required
def scatter():
    return render_template("scatter.html", title="Scatter Plot of Returns")


@portfolio.route("/stack_analysis", methods=["GET"])
@login_required
def stack_analysis():
    return render_template("stack_analysis.html", title="Stack & Cost Analysis")


@portfolio.route("/drawdown", methods=["GET"])
@login_required
def drawdown():
    return render_template("drawdown.html", title="Drawdown Analysis")
