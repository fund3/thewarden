$(document).ready(function () {
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

