$(document).ready(function () {
    update_test();
    $('.change_monitor').on('change', update_test);

});

function update_test() {
    crypto_ticker = $("#crypto_ticker").val()
    fx_ticker = $("#fx_ticker").val()
    stock_ticker = $("#stock_ticker").val()
    index_ticker = $("#index_ticker").val()
    // Clean all fields
    loading = "<img src='static/images/loading_small.gif' width='30' height='30'></img>"
    $('#aa_crypto_hist').html(loading)
    $('#aa_crypto_rt').html(loading)
    $('#aa_fx_hist').html(loading)
    $('#aa_fx_rt').html(loading)
    $('#aa_stock_hist').html(loading)
    $('#aa_stock_rt').html(loading)
    $('#aa_index_hist').html(loading)
    $('#aa_index_rt').html(loading)
    $('#cc_crypto_hist').html(loading)
    $('#cc_crypto_rt').html(loading)
    $('#cc_fx_hist').html(loading)
    $('#cc_fx_rt').html(loading)
    $('#fp_fx_hist').html(loading)
    $('#fp_fx_rt').html(loading)
    $('#fp_stock_hist').html(loading)
    $('#fp_stock_rt').html(loading)
    $('#fp_index_hist').html(loading)
    $('#fp_index_rt').html(loading)
    $('#bitmex_crypto_hist').html(loading)
    $('#bitmex_fx_hist').html(loading)


    // ALPHAVANTAGE TESTING FIELDS
    test_price(crypto_ticker, 'aa_digital', null, '#aa_crypto_hist')
    test_price(crypto_ticker, 'aa_digital', 'aa_realtime_digital', '#aa_crypto_rt')
    test_price(fx_ticker, 'aa_fx', null, '#aa_fx_hist')
    test_price(fx_ticker, 'aa_fx', 'aa_realtime_digital', '#aa_fx_rt')
    test_price(stock_ticker, 'aa_stock', null, '#aa_stock_hist')
    test_price(stock_ticker, 'aa_stock', 'aa_realtime_stock', '#aa_stock_rt')
    test_price(index_ticker, 'aa_stock', null, '#aa_index_hist')
    test_price(index_ticker, 'aa_stock', 'aa_realtime_stock', '#aa_index_rt')

    // CryptoCompare TESTING FIELDS
    test_price(crypto_ticker, 'cc_digital', null, '#cc_crypto_hist')
    test_price(crypto_ticker, 'cc_digital', 'cc_realtime', '#cc_crypto_rt')
    test_price(fx_ticker, 'cc_fx', null, '#cc_fx_hist')
    test_price(fx_ticker, 'cc_fx', 'cc_realtime', '#cc_fx_rt')

    // Financial Modeling Prep API
    test_price(stock_ticker, 'fmp_stock', null, '#fp_stock_hist')
    test_price(stock_ticker, 'fmp_stock', 'fp_realtime_stock', '#fp_stock_rt')

    // Bimex Testing fields
    // Financial Modeling Prep API
    test_price(crypto_ticker, 'bitmex', null, '#bitmex_crypto_hist')
    test_price(fx_ticker, 'bitmex', null, '#bitmex_fx_hist')

}

function test_price(ticker, provider, rtprovider = null, this_var = null) {
    var url_str = "/test_price?ticker=" + ticker + "&provider=" + provider
    if (rtprovider != null) {
        url_str += "&rtprovider=" + rtprovider
    }
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: url_str,
        success: function (data) {
            console.log(data)
            if ('error' in data) {
                console.log("ERRRROOOOOR")
                html = "<span style='color: orange;'><i class='fas fa-exclamation-triangle fa-2x'></i></br>Error: " + data.error + "</span></br>"

            } else {
                if (rtprovider == null) {
                    html = "<span style='color: green;'><i class='fas fa-check fa-2x'></i></span></br>"
                    html += 'Last Close: $<strong>'
                    html += formatNumber(data.price_data.last_close, 2) + '</strong><br>'
                    html += "<span class='small'>Prices available<br>"
                    html += "from: <strong>" + data.price_data.first_update + '</strong><br>'
                    html += "to: <strong>" + data.price_data.last_update + '</strong><br></span>'

                } else {
                    html = "<span style='color: green;'><i class='fas fa-check fa-2x'></i></span></br>"
                    html += 'Realtime Price: $<strong>'
                    html += formatNumber(data.realtime.price, 2) + '</strong><br>'
                }
            }
            $(this_var).html(html)
        },
        error: function (xhr, status, error) {
            html = "<span style='color: red;'><i class='fas fa-exclamation-triangle fa-2x'></i></span></br>"
            html += error
            $(this_var).html(html)
        }
    });
};


//  HELPER FUNCTION
// Formatter for numbers use
// prepend for currencies, for positive / negative, include prepend = +
// Small_pos signals to hide result - this is due to small positions creating
// unrealistic breakevens (i.e. too small or too large)
function formatNumber(amount, decimalCount = 2, prepend = '', postpend = '', small_pos = 'False', up_down = false) {
    if (((amount == 0) | (amount == null)) | (small_pos == 'True')) {
        return '-'
    }
    try {
        var string = ''
        string += (amount).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: decimalCount, minimumFractionDigits: decimalCount })
        if ((prepend == '+') && (amount > 0)) {
            string = "+" + string
        } else if ((prepend == '+') && (amount <= 0)) {
            string = string
        } else {
            string = prepend + string
        }

        if (up_down == true) {
            if (amount > 0) {
                postpend = postpend + '&nbsp;<img src="static/images/btc_up.png" width="10" height="10"></img>'
            } else if (amount < 0) {
                postpend = postpend + '&nbsp;<img src="static/images/btc_down.png" width="10" height="10"></img>'
            }
        }
        return (string + postpend)
    } catch (e) {
        console.log(e)
    }
};