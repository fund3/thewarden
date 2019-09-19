$(document).ready(function () {
    // refresh BTC price every 30 seconds
    BTC_price();
    window.setInterval(function () {
        BTC_price();
    }, 30000);

    $(function () {
        $('[data-toggle="tooltip"]').tooltip()
    })

    $(function () {
        $("#searchbox").autocomplete({
            source: function (request, response) {
                $.ajax({
                    url: "/search?" + $('#searchbox').val(),
                    dataType: "json",
                    data: {
                        term: request.term
                    },

                    success: function (data) {
                        response($.map(data, function (item) {
                            return {
                                label: (item),
                                value: (item)
                            }
                        }));
                    }

                });
            },
            minLength: 1
        });
    });


    $("#menu-toggle").click(function (e) {
        e.preventDefault();
        $("#wrapper").toggleClass("toggled");
        $("#btn_tgl").toggleClass("down");
    });

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/test_tor",
        success: function (data) {
            console.log("[Check Tor] ajax request: OK");
            if (data.status) {
                html_tor = "<i class='fas fa-lg fa-user-shield'></i>&nbsp;&nbsp;&nbsp;&nbsp;Tor running"
            } else {
                html_tor = "<i class='fas fa-lg fa-user-shield text-warning'></i>&nbsp;&nbsp;&nbsp;&nbsp;Tor Disabled"
            }
            $('#tor_span').html(html_tor);
        },
        error: function (xhr, status, error) {
            html_tor = "<i class='fas fa-lg fa-user-shield text-warning'></i>&nbsp;&nbsp;&nbsp;&nbsp;Tor Disabled"
            $('#tor_span').html(html_tor);
        }
    });



});



function BTC_price() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/realtime_user",
        success: function (data) {
            if ('cross' in data) {
                $('#fx_cross').html(data['cross']);
                $('#fx_rate').html(data['fx_rate'].toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));
                $('#btc_fx').html(data['btc_fx'].toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));
                $('#btc_usd').html(data['btc_usd'].toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));
            } else {
                $('#fx_cross').html(data);
            }

        },
        error: function (xhr, status, error) {
            console.log("Error on fx request")
        }
    });
};

function search_engine(field) {
    console.log(field)
}
