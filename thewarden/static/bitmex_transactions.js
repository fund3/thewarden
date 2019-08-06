$(document).ready(function () {

    $("#select_all").click(function () {
        $('.import_check').attr('checked', 'checked');
    });

    $("#select_none").click(function () {
        $('.import_check').removeAttr('checked');
    });


    $("#api_key").click(function () {
        var api_key = $("#api_txt").val()
        var api_secret = $("#api_secret").val()
        $("#api_key").html("Testing...")
        test_apikey(api_key, api_secret);
    });
});

function test_apikey(api_key, api_secret) {
    console.log(api_key + "--0---" + api_secret);
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/test_bitmex?api_key=" + api_key + "&api_secret=" + api_secret,
        success: function (data) {
            console.log("[Testing API Key] OK");
            $("#api_status").show("slow");
            if (data.status == 'error') {
                html_test = "<code><span class='danger'>Failed: " + data.message + "</span></code>"
                $("#api_key").html("Test Key")
            } else {
                html_test = "<code>Success. Credentials match username: " + data.message['username'] +
                    "</code><p style='color: grey;'>Key saved.</p>"
                $("#api_key").html("<i class='fas fa-check-circle fa-lg' style='color: lightgreen;'></i>")
                $("#api_key").prop('disabled', true);
            }
            $('#api_status').html(html_test);
        },
        error: function (xhr, status, error) {
            console.log("error on Ajax")
            $("#api_status").show();
            console.log(status)
            html_test = "<code>Something went wrong. Error: " + status + ". Try again.</code>"
            $('#api_status').html(html_test);
            $("#api_key").html("Test Key")
        }
    });
};
