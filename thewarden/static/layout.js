$(document).ready(function () {
    // refresh BTC price every 5 seconds
    window.setInterval(function () {
        BTC_price();
    }, 1000);



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
                html_tor = "<a style='text-decoration : none' href='/tor_setup'>" +
                    "<span class='text-white'>&nbsp;&nbsp;Tor Running" +
                    "</span > <span class=' nav-item' style='color: rgb(139, 195, 113);'>" +
                    "&nbsp;&nbsp;<i class='fas fa-2x fa-user-shield'></i></span> </a > "
            } else {
                html_tor = "<a style='text-decoration : none' href='/tor_setup'>" +
                    "<span class='text-white'>&nbsp;&nbsp;Tor Disabled" +
                    "</span > <span class=' nav-item' style='color: rgb(255, 217, 0);'>" +
                    "&nbsp;&nbsp;<i class='fas fa-2x fa-user-shield'></i></span> </a > "
            }
            $('#tor_span').html(html_tor);
        },
        error: function (xhr, status, error) {
            html_tor = "<a style='text-decoration : none' href='/tor_setup'>" +
                "<span class='text-white'>&nbsp;&nbsp;Tor Unavailable" +
                "</span > <span class=' nav-item' style='color: rgb(179, 179, 179);'>" +
                "&nbsp;&nbsp;<i class='fas fa-2x fa-user-shield'></i></span> </a > "
            $('#tor_span').html(html_tor);
        }
    });


    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/test_dojo",
        success: function (data) {
            console.log("[Check Dojo] ajax request: OK");
            if ('authorizations' in data.dojo_auth) {
                html_dojo = "<a style='text-decoration : none' href='/dojo_setup'>" +
                    "<span class='text-white'>&nbsp;&nbsp;Dojo running" +
                    "</span > <span class=' nav-item' style='color: rgb(139, 195, 113);'>" +
                    "&nbsp;&nbsp;<i class='fas fa-2x fa-user-ninja'></i></span> </a > "
            } else {
                html_dojo = "<a style='text-decoration : none' href='/dojo_setup'>" +
                    "<span class='text-white'>&nbsp;&nbsp;Dojo Disabled" +
                    "</span > <span class=' nav-item' style='color: rgb(255, 217, 0);'>" +
                    "&nbsp;&nbsp;<i class='fas fa-2x fa-user-ninja'></i></span> </a > "
            }
            $('#dojo_span').html(html_dojo);
        },
        error: function (xhr, status, error) {
            html_dojo = "<a style='text-decoration : none' href='/dojo_setup'>" +
                "<span class='text-white'>&nbsp;&nbsp;Dojo Unavailable" +
                "</span > <span class=' nav-item' style='color: rgb(179, 179, 179);'>" +
                "&nbsp;&nbsp;<i class='fas fa-2x fa-user-ninja'></i></span> </a > "
            $('#dojo_span').html(html_dojo);
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
                $('#btc_fx').html(data[data['base']].toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));
                $('#btc_usd').html(data['USD'].toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));

            } else {
                $('#fx_cross').html(data);
            }

        },
        error: function (xhr, status, error) {
            $('#fx_cross').html('error');
        }
    });
};

