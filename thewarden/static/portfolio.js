
$(document).ready(function () {
    console.log("-------------");
    console.log("00000080   01 04 45 54 68 65 20 54  69 6D 65 73 20 30 33 2F   ..EThe Times 03/");
    console.log("00000090   4A 61 6E 2F 32 30 30 39  20 43 68 61 6E 63 65 6C   Jan/2009 Chancel");
    console.log("000000A0   6C 6F 72 20 6F 6E 20 62  72 69 6E 6B 20 6F 66 20   lor on brink of ");
    console.log("000000B0   73 65 63 6F 6E 64 20 62  61 69 6C 6F 75 74 20 66   second bailout f");
    console.log("000000C0   6F 72 20 62 61 6E 6B 73  FF FF FF FF 01 00 F2 05   or banksÿÿÿÿ..ò.");
    console.log("--------------");

    // Format Red and Green Numbers (negative / positive)
    red_green()

    // Show / hide small and closed positions on button click
    $('.lifo_costtable').toggle();

    $('#myonoffswitch').on('click', function () {
        $('.small_pos').toggle(100);
    });

    $('#myfifolifoswitch').on('click', function () {
        $('.fifo_costtable').toggle();
        $('.lifo_costtable').toggle();
        $('#acc_method').html(function (i, text) {
            return text === 'Method: LIFO (Last-in First-Out)' ? 'Method: FIFO (First-in First-Out)' : 'Method: LIFO (Last-in First-Out)';
        });

    });

    // Function to get the max value in an Array
    Array.max = function (array) {
        return Math.max.apply(Math, array);
    };

    // Function to get the min value in an Array
    Array.min = function (array) {
        return Math.min.apply(Math, array);
    };

    $('#button_nochange').on('click', checkBitcoinBalance())

    // set run_once to true so some functions at ajax are only executed once
    run_once = true;
    realtime_table();
    getblockheight();
    getBitcoinAddresses();
    checkDojo();

    // Popover management
    // Default popover enabler from Bootstrap
    $('[data-toggle="popover"]').popover()
    // The below lines are needed to include a table inside a popover
    // Taken from here:
    // https://stackoverflow.com/questions/55362609/bootstrap-4-3-1-popover-does-not-display-table-inside-popover-content
    $.fn.popover.Constructor.Default.whiteList.table = [];
    $.fn.popover.Constructor.Default.whiteList.tr = [];
    $.fn.popover.Constructor.Default.whiteList.td = [];
    $.fn.popover.Constructor.Default.whiteList.div = [];
    $.fn.popover.Constructor.Default.whiteList.tbody = [];
    $.fn.popover.Constructor.Default.whiteList.thead = [];
    // If clicked outside of popover, it closes
    $('.popover-dismiss').popover({
        trigger: 'focus'
    })
    // Start this function whenever a popup opens
    $('[data-toggle="popover"]').on('shown.bs.popover', onPopoverHtmlLoad)

    $('.FIFOLIFOmodal').click(function () {
        $('#FIFOLIFOModal').modal('show');
        this_var = $(this)
        updateModal(this_var);
    });

    // Main function to update the Modal with some cost calculations
    function updateModal(this_var) {
        ticker = (this_var.data('ticker'));
        accounting = (this_var.data('accounting'));
        console.log('/accounting_json?ticker=' + ticker + '&method=' + accounting)
        $.ajax({
            type: 'GET',
            url: '/accounting_json?ticker=' + ticker + '&method=' + accounting,
            dataType: 'html',
            success: function (data) {
                console.log(data)
                // Parse data

                $('#accounting_table').html('<br> ' + data + '<br>');
            },
            error: console.log("AJAX Error")
        });

    }


    function onPopoverHtmlLoad() {
        ticker = $(this).data('ticker')
        this_var = $(this)
        accounting = $(this).data('accounting')
        // Get the cost table for this ticker
        $.ajax({
            type: 'GET',
            url: '/positions_json',
            dataType: 'json',
            success: function (data) {
                // Parse data
                var fx = data.user.symbol
                var pop_html = `
                <div class="row">
                    <div class='col-sm-6'>
                        <table class="table table-condensed table-striped popover_table">
                            <tbody>
                                <tr>
                                    <td>
                                        Operation
                                    </td>
                                    <td class="text-right">
                                        Quantity
                                    </td>
                                    <td class="text-right">
                                    ` + data.user.name_plural + `
                                    </td>
                                </tr>
                            <tr>
                                <td>
                                    Buys
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].trade_quantity_B, 4) + `
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].cash_value_fx_B, 0, fx) + `
                                    </td>
                            </tr>

                            <tr>
                                <td>
                                    Sells
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].trade_quantity_S, 4) + `
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].cash_value_fx_S, 0, fx) + `
                                    </td>
                            </tr>

                            <tr>
                                <td>
                                    Deposits
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].trade_quantity_D, 4) + `
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].cash_value_fx_D, 0, fx) + `
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    Withdraws
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].trade_quantity_W, 4) + `
                                    </td>
                                <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].cash_value_fx_W, 0, fx) + `
                                    </td>
                            </tr>
                            <tr class="thead-dark">
                            <td>
                                Total
                                </td>
                            <td class="text-right"> <span class="numberCircle">&nbsp1&nbsp</span>
                                ` + formatNumber(data.positions[ticker][accounting + '_quantity'], 4) + `
                                </td>
                            <td class="text-right"> <span class="numberCircle">&nbsp2&nbsp</span>
                                ` + formatNumber(data.positions[ticker].cash_value_fx, 0, fx) + `

                                </td>
                            </tr>

                            </tbody>
                        </table >

                        <table class="table table-condensed table-striped popover_table">
                            <tbody>

                                <tr>
                                    <td>
                                    ` + accounting + ` Average Cost
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker][accounting + '_average_cost'], 2, fx) + `
                                    <span class="numberCircle">&nbsp9&nbsp</span>
                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Unrealized PnL = ( <span class="numberCircle">&nbsp3&nbsp</span> - <span class="numberCircle">&nbsp9&nbsp</span> ) X <span class="numberCircle">&nbsp1&nbsp</span>
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker][accounting + '_unreal'], 0, fx) + `
                                    <span class="numberCircle">&nbsp10&nbsp</span>
                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Unrealized Break Even = <span class="numberCircle">&nbsp3&nbsp</span> - ( <span class="numberCircle">&nbsp10&nbsp</span> &#xF7 <span class="numberCircle">&nbsp1&nbsp</span> )
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker][accounting + '_unrealized_be'], 2, fx) + `

                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Realized PnL = ( <span class="numberCircle">&nbsp7&nbsp</span> - <span class="numberCircle">&nbsp10&nbsp</span> )
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker][accounting + '_real'], 0, fx) + `

                                    </td>
                                </tr>


                            </tbody>
                        </table>


                    </div>

                    <div class="col-sm-6">
                        <table class="table table-condensed table-striped popover_table">
                            <tbody>

                                <tr>
                                    <td>
                                    Open Position
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker][accounting + '_quantity'], 4) + `
                                    <span class="numberCircle">&nbsp1&nbsp</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                     Price
                                    </td>
                                    <td class="text-right">
                                        ` + formatNumber(data.positions[ticker].price, 2, fx) + `
                                        <span class="numberCircle">&nbsp3&nbsp</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                    Current Market Value = <span class="numberCircle">&nbsp1&nbsp</span> X <span class="numberCircle">&nbsp3&nbsp</span>
                                    </td>
                                    <td class="text-right">
                                        ` + formatNumber(data.positions[ticker].position_fx, 0, fx) + `
                                        <span class="numberCircle">&nbsp4&nbsp</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td>
                                    Total Cash Flow
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].cash_value_fx, 0, fx) + `
                                    <span class="numberCircle">&nbsp2&nbsp</span>
                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Gross PnL = <span class="numberCircle">&nbsp4&nbsp</span> - <span class="numberCircle">&nbsp2&nbsp</span>
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].pnl_gross, 0, fx) + `
                                    <span class="numberCircle">&nbsp5&nbsp</span>
                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Fees
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].trade_fees_fx * -1, 0, fx) + `
                                    <span class="numberCircle">&nbsp6&nbsp</span>
                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Net PnL = <span class="numberCircle">&nbsp5&nbsp</span> + <span class="numberCircle">&nbsp6&nbsp</span>
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].pnl_net, 0, fx) + `
                                    <span class="numberCircle">&nbsp7&nbsp</span>
                                    </td>
                                </tr>

                                <tr>
                                    <td>
                                    Break Even price = <span class="numberCircle">&nbsp2&nbsp</span> &#xF7 <span class="numberCircle">&nbsp1&nbsp</span>
                                    </td>
                                    <td class="text-right">
                                    ` + formatNumber(data.positions[ticker].breakeven, 2, fx) + `
                                    <span class="numberCircle">&nbsp8&nbsp</span>
                                    </td>
                                </tr>


                            </tbody>
                        </table>
                    </div>

                </div>

                    `

                this_var.attr('data-content', pop_html).data('bs.popover').setContent()
                $('[data-toggle="popover"]').popover({

                    html: true
                })

            },
        })



    }


    // Refresh pricings
    window.setInterval(function () {
        realtime_table();
    }, 5000);

    window.setInterval(function () {
        getblockheight();
    }, 120000);



    // Grab Portfolio NAV Statistics from JSON and return to table
    $.ajax({
        type: 'GET',
        url: '/portstats',
        dataType: 'json',
        success: function (data) {
            $('#end_nav').html(data.end_nav.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));
            var max_nav_txt = data.max_nav.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "<span class='small'> on "
            max_nav_txt = max_nav_txt + data.max_nav_date + "</span>"
            $('#max_nav').html(max_nav_txt);
            var min_nav_txt = data.min_nav.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "<span class='small'> on "
            min_nav_txt = min_nav_txt + data.min_port_date + "</span>"
            $('#min_nav').html(min_nav_txt);

            var max_pv_txt = data.max_portvalue.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) + "<span class='small'> on "
            max_pv_txt = max_pv_txt + data.max_port_date + "</span>"
            $('#max_portvalue').html(max_pv_txt);
            $('#return_1d').html((data.return_1d * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#return_1wk').html((data.return_1wk * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#return_30d').html((data.return_30d * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#return_90d').html((data.return_90d * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#return_ATH').html((data.return_ATH * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#return_SI').html((data.return_SI * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            var stats_dates_txt = data.start_date + " to " + data.end_date
            $('#stats_dates_txt').html(stats_dates_txt);

            // Data for the Current Week section
            weekly_html = "<table class='table-responsive' style='border-collapse: separate; border-spacing: 5px;'><tr></tr></table>"
            $('#weekly_map').html(weekly_html);

            for (i = 1; i <= 7; i++) {

                if (data['daily'][i]['port_chg'] >= 0) {
                    add_class = 'green';
                } else {
                    add_class = 'red';
                }
                $('#weekly_map tr').append("<td style='height:120px; border: 2px solid #bebebe; border-radius: 10px; border-spacing: 5px;'><p style='font-size: 14px'>" +
                    data['daily'][i]['date'] + "</p>" +
                    "<p class='heatmap changebox' data-html='true' data-toggle='tooltip' data-placement='top'>" +
                    formatNumber(data['daily'][i]['perc_chg'] * 100, 2, '', '%', 'False', true) + "</p><strong style='font-size: 16px'> " +
                    formatNumber(data['daily'][i]['port'], 0, data['fx']) + "</strong></br><span style='font-size: 14px; color: " + add_class + "'> " +
                    formatNumber(data['daily'][i]['port_chg'], 0, data['fx'], '', 'False', true) + "</span></td>")

            };


            heat_color('.heatmap');
            red_green();
        }
    });


    // Get NAV Data for chart
    $.ajax({
        type: 'GET',
        url: '/navchartdatajson',
        dataType: 'json',
        success: function (data) {
            navChart(data);
        }
    });


});

//  HELPER FUNCTION
// Runs the class to change pos numbers to green and neg to red
function red_green() {
    // re-apply redgreen filter (otherwise it's all assumed positive since fields were empty before ajax)
    $(".redgreen").removeClass('red_negpos');
    $(".redgreen").addClass('green_negpos');
    $(".redgreen:contains('-')").removeClass('green_negpos');
    $(".redgreen:contains('-')").addClass('red_negpos');
    // Hide NaN
    $(".redgreen:contains('NaN%')").addClass('text-white');
}

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
                postpend = postpend + '&nbsp;<i class="fas fa-angle-up"></i>'
            } else if (amount < 0) {
                postpend = postpend + '&nbsp;<i class="fas fa-angle-down"></i>'
            }
        }
        return (string + postpend)
    } catch (e) {
        console.log(e)
    }
};

// Updates the realtime table of prices and positions
function realtime_table() {
    // Grab Portfolio NAV Statistics from JSON and return to table
    $.ajax({
        type: 'GET',
        url: '/positions_json',
        dataType: 'json',
        success: function (data) {
            // Now assign the values from the JSON to the table
            // variable fx will contain the user's currency symbol
            var fx = data.user.symbol
            // Parse the json
            $('#pvalue').html(formatNumber(data.positions.Total.position_fx, 0, fx)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            $('#end_portvalue').html(formatNumber(data.positions.Total.position_fx, 0)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });

            posbtc = data.positions.Total.position_fx / data.btc
            $('#pvaluebtc').html(formatNumber(posbtc, 2, "&#8383 ")).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
            $('#chg1').html(formatNumber(data.positions.Total.change_fx, 0, fx)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
            pct_chg = (data.positions.Total.change_fx / data.positions.Total.position_fx) * 100
            $('#chg2').html(formatNumber(pct_chg, 2, '+', '%', 'False', true)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
            $('#lstupd').html(data.positions.Total.last_up_source).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            // Update BTC price on layout
            $('#latest_btc_price').html(formatNumber(data.btc, 2, fx)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;

            // Totals for FIFO and LIFO tables
            $('#F_total').html(formatNumber(data.positions.Total.position_fx, 0, fx, ''));
            $('#F_real').html(formatNumber(data.positions.Total.FIFO_real, 0, fx, ''));
            $('#F_unreal').html(formatNumber(data.positions.Total.FIFO_unreal, 0, fx, ''));
            $('#F_pnl').html(formatNumber(data.positions.Total.pnl_net, 0, fx, ''));
            $('#F_fees').html(formatNumber(data.positions.Total.trade_fees_fx, 0, fx, ''));
            $('#L_total').html(formatNumber(data.positions.Total.position_fx, 0, fx, ''));
            $('#L_real').html(formatNumber(data.positions.Total.LIFO_real, 0, fx, ''));
            $('#L_unreal').html(formatNumber(data.positions.Total.LIFO_unreal, 0, fx, ''));
            $('#L_pnl').html(formatNumber(data.positions.Total.pnl_net, 0, fx, ''));
            $('#L_fees').html(formatNumber(data.positions.Total.trade_fees_fx, 0, fx, ''));


            // Loop through tickers to fill the tables
            $.each(data.positions, function (key, value) {
                // Portfolio Snapshot
                if (value.price != 0) {
                    $('#' + key + '_price').html(formatNumber(value.price, 2, fx, '')).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
                    $('#' + key + '_24hchg').html(formatNumber(value['24h_change'], 2, '+', '%', 'False', true)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
                    $('#' + key + '_position').html(formatNumber(value.position_fx, 0, fx, ''));
                    $('#' + key + '_allocation').html(formatNumber(value.allocation * 100, 2, '', '%'));

                    // FIFO Table values
                    $('#' + key + '_F_position').html(formatNumber(value.position_fx, 0, fx, ''));
                    $('#' + key + '_fifo_real').html(formatNumber(value.FIFO_real, 0, fx, ''));
                    $('#' + key + '_fifo_unreal').html(formatNumber(value.FIFO_unreal, 0, fx, ''));
                    $('#' + key + '_fifo_unreal_be').html(formatNumber(value.FIFO_unrealized_be, 2, fx, '', value.small_pos));
                    $('#' + key + '_F_trade_fees_fx').html(formatNumber(value.trade_fees_fx, 0, fx, ''));
                    $('#' + key + '_F_pnl_net').html(formatNumber(value.pnl_net, 0, fx, ''));
                    $('#' + key + '_F_breakeven').html(formatNumber(value.breakeven, 2, fx, '', value.small_pos));

                    // LIFO Table values
                    $('#' + key + '_L_position').html(formatNumber(value.position_fx, 0, fx, ''));
                    $('#' + key + '_lifo_real').html(formatNumber(value.LIFO_real, 0, fx, ''));
                    $('#' + key + '_lifo_unreal').html(formatNumber(value.LIFO_unreal, 0, fx, ''));
                    $('#' + key + '_lifo_unreal_be').html(formatNumber(value.LIFO_unrealized_be, 2, fx, '', value.small_pos));
                    $('#' + key + '_L_trade_fees_fx').html(formatNumber(value.trade_fees_fx, 0, fx, ''));
                    $('#' + key + '_L_pnl_net').html(formatNumber(value.pnl_net, 0, fx, ''));
                    $('#' + key + '_L_breakeven').html(formatNumber(value.breakeven, 2, fx, '', value.small_pos));

                    // Market Data values
                    $('#' + key + '_mkt_price').html(formatNumber(value.price, 2, fx, '')).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
                    $('#' + key + '_24h_change').html(formatNumber(value['24h_change'], 2, '+', '%', 'False', true)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
                    var price_range = formatNumber(value['24h_low'], 2, fx, '') + ' - ' + formatNumber(value['24h_high'], 2, fx, '')
                    $('#' + key + '_24h_range').html(price_range);
                    $('#' + key + '_volume').html(value.volume);
                    if (value.notes != null) {
                        $('#' + key + '_volume').html(value.notes);
                    }
                    $('#' + key + '_mktcap').html(value.mktcap);
                    $('#' + key + '_source').html(value.source);
                    update = new Date(value.last_update)
                    if (update.getHours() == 0 && update.getMinutes() == 0 && update.getSeconds() == 0) {
                        update = (update.getMonth() + 1) + '-' + update.getDate() + '-' + update.getFullYear()
                    } else {
                        if (isNaN(update.getHours())) {

                        } else {
                            update = update.getHours() + ':' + update.getMinutes() + ':' + update.getSeconds()
                        }
                    }
                    if (update == 'Invalid Date') {
                        update = '-'
                    }
                    $('#' + key + '_lastupdate').html(update);
                }
                // Add small position class to hide/show small positions
                if (value.small_pos == "True") {
                    $('#ticker' + key).addClass('small_pos')
                    $('#tickerfifo_' + key).addClass('small_pos')
                    $('#tickerlifo_' + key).addClass('small_pos')
                    $('#tickerdata_' + key).addClass('small_pos')
                    // Hide the calculators for small positions
                    $('#' + key + '_be_calculator_FIFO').html(" ")
                    $('#' + key + '_be_calculator_LIFO').html(" ")
                    $('#' + key + '_pnl_calculator_FIFO').html(" ")
                    $('#' + key + '_pnl_calculator_LIFO').html(" ")
                }

            })

            // Functions that should only be run once during the page refresh
            if (run_once == true) {
                $('.small_pos').toggle(100);
            }

            createcharts(data.piechart); //Load pie chart
            red_green();
            run_once = false
        }
    });


};

function getBitcoinAddresses() {
    $.ajax({
        type: 'GET',
        url: '/frontpage_btc',
        dataType: 'json',
        timeout: 5000,
        success: function (data) {
            if (data.count == 0) {
                $('#bitcoin_addresses_section').hide()
            } else {
                $('#total_addresses').html(data.count);
                $('#bitcoin_balance').html("&#8383 " + data.balance.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 4, minimumFractionDigits: 4 }));
                $('#bitcoin_last_check').html(data.last_update);
            }
        },
        error: function () {
            $('#total_addresses').html("---");
            console.log("Error: failed to get Bitcoin Addresses data")
        }
    });
}

function checkBitcoinBalance() {
    $.ajax({
        type: "POST",
        contentType: 'application/json',
        dataType: "json",
        url: "/frontpage_btc",
        success: function (data_back) {
            console.log("Done checking all balances with the Dojo");
            console.log(data_back.changes)
            console.log(data_back.changes.length)
            if (data_back.errors == true) {
                $('#bitcoin_check').html("<a id='change' class='btn btn-sm btn-outline-secondary btn-block' href='/bitcoin_monitor' role='button'><i class='fas fa-exclamation-triangle'></i>&nbsp; Error checking balances</a>");
            } else {
                if (data_back.changes.length > 0) {
                    $('#bitcoin_check').html("<a id='change' class='btn btn-sm btn-warning btn-block' href='/bitcoin_monitor' role='button'><i class='fas fa-exclamation-triangle'></i>&nbsp; Changes detected since last check. New balance: " + data_back.total_balance + "</a>");
                } else {
                    $('#bitcoin_check').html("<a id='button_nochange' class='btn btn-sm btn-outline-success btn-block' href='/bitcoin_monitor' role='button'>No activity since last check &nbsp;<i class='fas fa-check'></i></a>");
                }
            }
            console.log(data_back)
        }
    })
}

function getblockheight() {
    // GET latest Bitcoin Block Height
    $.ajax({
        type: 'GET',
        url: 'https://blockstream.info/api/blocks/tip/height',
        dataType: 'json',
        timeout: 5000,
        success: function (data) {
            $('#latest_btc_block').html(data.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }));
        },
        error: function () {
            $('#latest_btc_block').html("------");
            console.log("Error: failed to download block count from BlockStream.info")
        }
    });
};

// Pie Chart - allocation
function createcharts(piechart) {

    var myChart = Highcharts.chart('piechart', {
        credits: {
            text: "",
            href: ""
        },
        legend: {
            enabled: false
        },
        chart: {
            plotBackgroundColor: null,

            backgroundColor: "#FAFAFA",
            type: 'pie'
        },
        title: {
            text: "Portfolio Allocation",
            style: {
                "fontSize": "12px"
            },
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.0f}%</b>'
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    enabled: true
                },
                showInLegend: true
            }
        },

        series: [{
            name: 'Allocation',
            animation: false,
            colorByPoint: true,
            data: piechart,
            size: '90%',
            innerSize: '60%',
            dataLabels: {
                enabled: true,
                align: 'center',
                allowOverlap: false,
                format: '{point.name} {point.y:.0f}%',
                connectorPadding: 1,
                distance: 10,
                softConnector: true,
                crookDistance: '10%'
            },
        }]
    });

    myChart.reflow();

};


// NAV CHART
function navChart(data) {
    var myChart = Highcharts.stockChart('navchart', {
        credits: {
            text: "<a href='/navchart'>Click here for detailed view<i class='fas fa-external-link-alt'></i></a>",
            style: {
                fontSize: '13px',
                color: '#363636'
            },
            position: {
                align: 'right',
                y: 0
            },
            href: "/navchart"
        },
        navigator: {
            enabled: false
        },
        rangeSelector: {
            selected: 1
        },
        chart: {
            zoomType: 'xy',
            backgroundColor: "#FAFAFA",
        },
        title: {
            text: 'Portfolio NAV over time'
        },
        subtitle: {
            text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
        },
        xAxis: {
            type: 'datetime'
        },
        yAxis: {
            title: {
                text: 'NAV'
            },
            startOnTick: false,
            endOnTick: false
        },
        legend: {
            enabled: false
        },
        plotOptions: {
            area: {
                fillColor: {
                    linearGradient: {
                        x1: 0,
                        y1: 0,
                        x2: 0,
                        y2: 1
                    },
                    stops: [
                        [0, Highcharts.getOptions().colors[0]],
                        [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                    ]
                },
                marker: {
                    radius: 2
                },
                lineWidth: 1,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                },
                threshold: null
            }
        },

        series: [{
            type: 'line',
            name: 'NAV',
            // The line below maps the dictionary coming from Python into
            // the data needed for highcharts. It's weird but the *1 is
            // needed, otherwise the date does not show on chart.
            data: Object.keys(data).map((key) => [((key * 1)), data[key]]),
            turboThreshold: 0,
            tooltip: {
                pointFormat: "NAV (first trade=100): {point.y:,.0f}"
            }
        }]
    });

};



function checkDojo() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/test_dojo",
        success: function (data) {
            html_dojo = "-"
            if ('authorizations' in data.dojo_auth) {
                html_dojo = "<a style='text-decoration: none' href='/dojo_setup'>" +
                    "<span class='text-success'> " +
                    "&nbsp;&nbsp;&nbsp;&nbsp;Dojo running </span></a>"

            } else {
                html_dojo = "<a style='text-decoration: none' href='/dojo_setup'>" +
                    "<span class='text-warning'>" +
                    "&nbsp;&nbsp;&nbsp;&nbsp;Node Unavailable </span> </a>"
            }
            $('#node_status').html(html_dojo);
        },
        error: function (xhr, status, error) {
            html_dojo = "<a style='text-decoration: none' href='/dojo_setup'>" +
                "<span class='text-warning'>" +
                "&nbsp;&nbsp;&nbsp;&nbsp;Node Unavailable  </span></a>"
        }
    });
}



function heat_color(object) {
    // Get all data values from our table cells making sure to ignore the first column of text
    // Use the parseInt function to convert the text string to a number
    var counts_positive = $(object).map(function () {
        if (parseFloat($(this).text()) > 0) {
            return parseFloat($(this).text());
        };
    }).get();

    var counts_negative = $(object).map(function () {
        if (parseFloat($(this).text()) < 0) {
            return parseFloat($(this).text());
        };
    }).get();

    console.log(counts_positive)
    console.log(counts_negative)

    // run max value function and store in variable
    var max = Array.max(counts_positive);
    var min = Array.min(counts_negative) * (-1);

    n = 100; // Declare the number of groups

    // Define the ending colour, which is white
    xr = 230; // Red value
    xg = 233; // Green value
    xb = 237; // Blue value

    // Define the starting colour for positives
    yr = 97; // Red value 243
    yg = 184; // Green value 32
    yb = 115; // Blue value 117

    // Define the starting colour for negatives
    nr = 226; // Red value 243
    ng = 156; // Green value 32
    nb = 131; // Blue value 117

    // Loop through each data point and calculate its % value
    $(object).each(function () {
        if (parseFloat($(this).text()) > 0) {
            var val = parseFloat($(this).text());
            var pos = parseFloat((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (yr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (yg - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (yb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).css({ backgroundColor: clr });
        }
        else {
            var val = parseFloat($(this).text()) * (-1);
            var pos = parseFloat((Math.round((val / min) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (nr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (ng - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (nb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).css({ backgroundColor: clr });
        }
    });
}