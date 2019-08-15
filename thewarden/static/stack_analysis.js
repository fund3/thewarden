$(document).ready(function () {

    // Data to pre-fill start and end dates
    var now = new Date();
    var tenYrAgo = new Date();
    tenYrAgo.setYear(now.getFullYear() - 10);
    document.getElementById('start_date').valueAsDate = tenYrAgo;
    document.getElementById('end_date').valueAsDate = new Date();
    $('.change_monitor').on('change', change_refresh);

    // Pre-fill drop-down with all traded tickers
    get_Tickers_Ajax();

    run_ajax();

});

// Get the list of tickers and place in drop down menu
function get_Tickers_Ajax() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/portfolio_tickers_json",
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request [tickers]: OK")
            // remove USD

            if (data.indexOf('USD') != -1) {
                data.splice(data.indexOf('USD'), 1);
            }

            btc_pos = data.indexOf('BTC')

            // fill data in dropdown
            var options = data;
            var select = document.getElementById('ticker');

            $("#ticker").empty()
            for (var i = 0; i < options.length; i++) {
                select.options[i] = new Option(options[i], i);  //new Option("Text", "Value")
            }
            $('#ticker>option:eq(' + btc_pos + ')').attr('selected', true);
            ticker = $("#ticker").find("option").filter(":selected").text();


        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while getting tickers" +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });

}

function change_refresh() {

    // Send a notice - Refreshing data
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Refreshing data." +
        "</div>")
    setTimeout(function () { run_ajax(); }, 1000)
};

function run_ajax() {
    // Ajax to get the json:

    start_date = $('#start_date').val()
    end_date = $('#end_date').val()
    ticker = $("#ticker").find("option").filter(":selected").text();

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/transactionsandcost_json?ticker=" + ticker + "&start=" + start_date + "&end=" + end_date,
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request: OK")
            console.log(data)
            handle_ajax_data(data, ticker, data['fx']);

        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });
};

function handle_ajax_data(data, ticker, fx) {
    var parsed_data = (jQuery.parseJSON(data.data));
    // Create Chart
    createChart(parsed_data, ticker, fx);

};

//  CHART
function createChart(data, ticker, fx) {


    var myChart = Highcharts.stockChart('compchart', {
        credits: {
            text: "Stacking Analysis"
        },
        chart: {
            zoomType: 'x',
            backgroundColor: "#FAFAFA",
        },
        rangeSelector: {
            selected: 2
        },
        title: {
            text: 'Average Cost over time'
        },
        subtitle: {
            text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
        },
        xAxis: [
            {
                type: 'datetime',
                id: 'x1'
            },
            {
                type: 'datetime',
                id: 'x2'
            },
        ],
        yAxis: [
            {
                title: {
                    text: 'Cost vs. Price'
                },
                height: '35%',
                lineWidth: 2,
                opposite: true,
                startOnTick: false,
                endOnTick: false
            },
            {
                title: {
                    text: 'Cost over Price'
                },
                lineWidth: 4,
                top: '35%',
                height: '15%',
                offset: 0,
                startOnTick: false,
                endOnTick: false
            },
            {
                title: {
                    text: 'Position'
                },
                lineWidth: 4,
                top: '50%',
                height: '25%',
                offset: 0,
                startOnTick: false,
                endOnTick: false
            }, {
                title: {
                    text: 'Transactions'
                },
                lineWidth: 2,
                top: '75%',
                height: '10%',
                offset: 0,
                opposite: true,
                startOnTick: false,
                endOnTick: false
            }, {
                title: {
                    text: 'Cost Impact'
                },
                lineWidth: 2,
                top: '85%',
                height: '15%',
                offset: 0,
                opposite: true,
                startOnTick: false,
                endOnTick: false
            }
        ],
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


        series: [
            {
                type: 'line',
                dataGrouping: {
                    enabled: false
                },
                name: ticker + ' Price',
                yAxis: 0,
                // The line below maps the dictionary coming from Python into
                // the data needed for highcharts. It's weird but the *1 is
                // needed, otherwise the date does not show on chart.
                data: Object.keys(data[ticker]).map((key) => [((key * 1)), data[ticker][key]]),
                turboThreshold: 0,
                tooltip: {
                    pointFormat: ticker + " Price: " + fx + "{point.y:,.0f}"
                },
            },
            {
                type: 'line',
                name: 'Average Cost',
                dataGrouping: {
                    enabled: false
                },
                yAxis: 0,
                // The line below maps the dictionary coming from Python into
                // the data needed for highcharts. It's weird but the *1 is
                // needed, otherwise the date does not show on chart.
                data: Object.keys(data['avg_cost']).map((key) => [((key * 1)), data['avg_cost'][key]]),
                turboThreshold: 0,
                tooltip: {
                    pointFormat: "Average Cost: " + fx + "{point.y:,.0f}"
                },
            },
            {
                type: 'line',
                dataGrouping: {
                    enabled: false
                },
                name: ticker + ' Position',
                color: '#8CADE1', // Cost basis line is orange and thicker
                lineWidth: 2,
                yAxis: 2,
                // The line below maps the dictionary coming from Python into
                // the data needed for highcharts. It's weird but the *1 is
                // needed, otherwise the date does not show on chart.
                data: Object.keys(data['q_cum_sum']).map((key) => [((key * 1)), data['q_cum_sum'][key]]),
                turboThreshold: 0,
                tooltip: {
                    pointFormat: ticker + " position: {point.y:,.2f}"
                },
            },
            {
                type: 'column',
                name: 'Transactions',
                dataGrouping: {
                    enabled: false
                },
                yAxis: 3,
                // The line below maps the dictionary coming from Python into
                // the data needed for highcharts. It's weird but the *1 is
                // needed, otherwise the date does not show on chart.
                data: Object.keys(data["trade_quantity_sum"]).map((key) => [((key * 1)), data["trade_quantity_sum"][key]]),
                turboThreshold: 0,
                pointWidth: 10,
                tooltip: {
                    pointFormat: "Quantity Transacted: {point.y:,.2f}"
                },
            },
            {
                type: 'column',
                name: 'Cost over Price',
                dataGrouping: {
                    enabled: false
                },
                yAxis: 1,
                // The line below maps the dictionary coming from Python into
                // the data needed for highcharts. It's weird but the *1 is
                // needed, otherwise the date does not show on chart.
                data: Object.keys(data["price_over_cost_usd"]).map((key) => [((key * 1)), data["price_over_cost_usd"][key]]),
                turboThreshold: 0,
                tooltip: {
                    pointFormat: "Cost over Price: " + fx + " {point.y:,.2f}"
                },
            },
            {
                type: 'column',
                name: 'Impact of this transaction on Cost',
                dataGrouping: {
                    enabled: false
                },
                yAxis: 4,
                // The line below maps the dictionary coming from Python into
                // the data needed for highcharts. It's weird but the *1 is
                // needed, otherwise the date does not show on chart.
                data: Object.keys(data["impact_on_cost_usd"]).map((key) => [((key * 1)), data["impact_on_cost_usd"][key]]),
                turboThreshold: 0,
                pointWidth: 10,
                tooltip: {
                    pointFormat: "This transaction changed cost by " + fx + "{point.y:,.2f}"
                },
            }
        ]
    });


};
