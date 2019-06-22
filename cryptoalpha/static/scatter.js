$(document).ready(function () {

    // Data to pre-fill start and end dates
    var now = new Date();
    var oneYrAgo = new Date();
    oneYrAgo.setYear(now.getFullYear() - 1);

    document.getElementById('start_date').valueAsDate = oneYrAgo;
    document.getElementById('end_date').valueAsDate = new Date();
    $('.change_monitor').on('change', change_refresh);
    run_ajax();
});

function change_refresh() {

    // Send a notice - Refreshing data
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Refreshing data." +
        "</div>")
    setTimeout(function () { run_ajax(); }, 1000)
};

function run_ajax() {
    // Ajax to get the json:
    // portfolio_compare_json?tickers=BTC,ETH,AAPL&start=%272019-05-10%27&end=%272019-05-20%27
    tickers = $('#tickers').val()
    start_date = $('#start_date').val()
    end_date = $('#end_date').val()
    market = $("#market_benchmark").find("option").filter(":selected").text();
    // Update the dropdown menu (market_benchmark)
    var x = $('#tickers').val();
    var options = x.split(",");
    var select = document.getElementById('market_benchmark');
    $("#market_benchmark").empty()
    for (var i = 0; i < options.length; i++) {
        select.options[i] = new Option(options[i], i);  //new Option("Text", "Value")
    }


    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/scatter_json?market=" + market + "&tickers=" + tickers + "&start=" + start_date + "&end=" + end_date,
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request: OK")
            handle_ajax_data(data);
        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });
};

function handle_ajax_data(data) {
    // Var to return message alerts for ticker errors


    // Now, generate the table with meta data for each ticker

    // First the Portfolio Data
    // var html_table = "  <tr class='table-success'> \
    //                     <td class='text-left'> NAV</td>\
    //                     <td class='text-center redgreen'>" + (data.table.NAV.return * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
    //                     <td class='text-center'> - </td>\
    //                     <td class='text-center'>" + (data.table.NAV.ann_std_dev * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
    //                     <td class='text-center redgreen'>" + (data.table.NAV.return / data.table.NAV.ann_std_dev).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
    //                     <td class='text-center redgreen'>" + (data.table.NAV.avg_return * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
    //                     <td class='text-right'>" + (data.table.NAV.start).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
    //                     <td class='text-right'>" + (data.table.NAV.end).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
    //                 </tr>";


    // $.each(data.messages, function (key_x, value) {
    //     console.log(key_x);
    //     if (value == "ok") {
    //         html_table = html_table +
    //             "  <tr> \
    //                     <td class='text-left'>"+ key_x + "</td>\
    //                     <td class='text-center redgreen'>" + (data.table[key_x]['return'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
    //                     <td class='text-center redgreen'>" + (data.table[key_x]['comp2nav'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %</td>\
    //                     <td class='text-center'>" + (data.table[key_x]['ann_std_dev'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
    //                     <td class='text-center redgreen'>" + (data.table[key_x]['return'] / data.table[key_x]['ann_std_dev']).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
    //                     <td class='text-center redgreen'>" + (data.table[key_x]['avg_return'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
    //                     <td class='text-right'>" + (data.table[key_x]['start']).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
    //                     <td class='text-right'>" + (data.table[key_x]['end']).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
    //                 </tr>";
    //     };
    // });

    // $('#table_body').html(html_table);
    // Format Red and Green Numbers (negative / positive)
    // $("td.redgreen").removeClass('red_negpos');
    // $("td.redgreen").addClass('green_negpos');
    // $("td.redgreen:contains('-')").removeClass('green_negpos');
    // $("td.redgreen:contains('-')").addClass('red_negpos');

    // Get data from metadata
    meta_data_all = ((data.meta_data));
    $('#table_start').html(data.table.meta.start_date);
    $('#table_end').html(data.table.meta.end_date);
    $('#table_days').html(data.table.meta.number_of_days + " (" + data.table.meta.count_of_points + ")");

    // // Create Correlation Table
    $('#corr_table').html(data.corr_html);

    // Format colors depending on value
    // Define the ending colour, which is white
    xr = 255; // Red value
    xg = 255; // Green value
    xb = 255; // Blue value

    // Define the starting colour for positives
    yr = 157; // Red value 243
    yg = 188; // Green value 32
    yb = 156; // Blue value 117

    n = 100; // Declare the number of groups

    $('#corr_table').each(function () {
        $(this).find('th').each(function () {
            $(this).css('background-color', '#c5c7c9');
        })
        $(this).find('td').each(function () {
            var val = parseFloat($(this).text(), 10);
            var pos = parseInt((Math.round((val / 1) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (yr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (yg - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (yb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).css({ backgroundColor: clr });

        })
    })

    // Create Chart
    createChart(data.chart_data);

};

//  CHART
function createChart(data) {
    var myChart = Highcharts.chart('compchart', {
        chart: {
            type: 'scatter',
            zoomType: 'xy',
            backgroundColor: "#FAFAFA"
        },
        credits: {
            enabled: false
        },
        title: {
            text: 'Scatter Plot of Daily Returns'
        },
        xAxis: {
            title: {
                enabled: true,
                text: 'Market Return'
            },
            startOnTick: true,
            endOnTick: true,
            showLastLabel: true
        },
        yAxis: {
            title: {
                text: 'Ticker Return'
            }
        },
        plotOptions: {
            scatter: {
                marker: {
                    radius: 5,
                    states: {
                        hover: {
                            enabled: true,
                            lineColor: 'rgb(100,100,100)'
                        }
                    }
                },
                states: {
                    hover: {
                        marker: {
                            enabled: false
                        }
                    }
                },
                tooltip: {
                    headerFormat: '<b>{series.name}</b><br>',
                    pointFormat: '{point.x}, {point.y}'
                }
            }
        },
        series: data
    });

};
