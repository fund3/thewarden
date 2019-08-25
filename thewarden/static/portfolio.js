
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

    // set run_once to true so some functions at ajax are only executed once
    run_once = true;
    realtime_table();
    getblockheight();

    // Popover management
    $(function () {
        $('[data-toggle="popover"]').popover()
    })
    $('.popover-dismiss').popover({
        trigger: 'focus'
    })


    // Refresh pricings
    window.setInterval(function () {
        realtime_table();
    }, 2000);

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
            $('#end_portvalue_usd').html("$ " + data.end_portvalue_usd.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }));
            $('#end_portvalue').html(data.end_portvalue.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }));
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
    $("td.redgreen").removeClass('red_negpos');
    $("td.redgreen").addClass('green_negpos');
    $("td.redgreen:contains('-')").removeClass('green_negpos');
    $("td.redgreen:contains('-')").addClass('red_negpos');
    // Hide NaN
    $("td.redgreen:contains('NaN%')").addClass('text-white');
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
            posbtc = data.positions.Total.position_fx / data.btc
            $('#pvaluebtc').html(formatNumber(posbtc, 2, "&#8383 ")).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
            $('#chg1').html(formatNumber(data.positions.Total.change_fx, 0, fx)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
            pct_chg = (data.positions.Total.change_fx / data.positions.Total.position_fx) * 100
            $('#chg2').html(formatNumber(pct_chg, 2, '+', '%', 'False', true)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;
            $('#lstupd').html(data.positions.Total.last_up_source).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });
            // Update BTC price on layout
            $('#latest_btc_price').html(formatNumber(data.btc * data.user.fx_rate, 2, fx)).fadeTo(100, 0.3, function () { $(this).fadeTo(500, 1.0); });;

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
                    update = update.toLocaleTimeString()
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
            selected: 5
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
