$(document).ready(function () {
    $("#api_key").click(function () {
        var api_key = $("#api_txt").val()
        $("#api_key").html("testing...")
        test_apikey(api_key);
    });

    $("#dojo").click(function () {
        var dojo_onion = $("#dojo_onion").val()
        var dojo_api = $("#dojo_api").val()
        $.ajax({
            type: "GET",
            dataType: 'json',
            url: "/dojo_autoconfig?onion=" + dojo_onion + "&api_key=" + dojo_api,
            success: function (data) {
                console.log(data)
                if (data == 'Failed. Empty field.') {
                    $("#dojo").html("Missing field. Check and try again.")
                } else {
                    console.log("[DOJO Register] OK");
                    $("#dojo").prop('disabled', true);
                    $("#dojo").html("<span style='color: lightgreen;'>Settings saved!</span>")
                }

            },
            error: function (xhr, status, error) {
                console.log("error on Ajax")
                console.log(status)
                $("#dojo").html("Something went wrong. Retry")
            }
        });


    });

});

function test_apikey(api_key) {
    console.log(api_key);
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/test_aakey?key=" + api_key,
        success: function (data) {
            console.log("[Testing API Key] OK");
            $("#api_status").show("slow");
            if (data.status == 'failed') {
                html_test = "<code><span class='danger'>Failed: " + data.message + "</span></code>"
            } else {
                console.log(data.message)
                if (data.message == "ConnectionError") {
                    html_test = "<code>Fail: Connection Error. Check your connection.</code>"
                    $("#api_key").html("Test Key")
                    $('#api_status').html(html_test);
                }
                if (["Realtime Currency Exchange Rate"] in data.message) {
                    html_test = "<code>Success: Bitcoin price is " +
                        data.message["Realtime Currency Exchange Rate"]["5. Exchange Rate"] +
                        "</code><p style='color: grey;'>Key saved. You can edit it later at the <strong>Manage User Account</strong> tab</p>"
                    $("#api_key").html("<i class='fas fa-check-circle fa-lg' style='color: lightgreen;'></i>")
                    $("#api_key").prop('disabled', true);
                } else {
                    html_test = "<code>Fail: Check your API Key and try again</code>"
                    $("#api_key").html("Test Key")
                }
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

