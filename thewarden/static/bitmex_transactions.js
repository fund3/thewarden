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


    // When import button is clicked, prepare transactions to send to database
    $("#import_button").click(function () {

        // $('#import_button').attr('disabled', 'disabled');
        $('#import_button').html('Please wait. Importing into Database.');
        console.log("Staring Import Routine...")
        // Loop through the selected transactions
        // Alert if none selected and abort
        var list = {};
        var count = 0;
        $('#transactionstable').find('input[type="checkbox"]:checked').each(function () {
            // Create a dictionary of transaction details to return to model
            var row = {};
            row['trade_inputon'] = new Date();
            row['trade_quantity'] = ($(this).closest('tr').find('td:nth-child(2)').attr('id')) / 100000000;
            if (row['trade_quantity'] < 0) {
                row['trade_operation'] = 'S'
            };
            if (row['trade_quantity'] >= 0) {
                row['trade_operation'] = 'B'
            };
            row['trade_currency'] = 'USD';
            row['trade_fees'] = 0
            row['trade_asset_ticker'] = 'BTC';
            row['trade_price'] = ($(this).closest('tr').find('td:nth-child(3)').find('input:text').val());
            row['trade_date'] = ($(this).closest('tr').find('td:nth-child(1)').attr('id'))
            row['trade_blockchain_id'] = ($(this).closest('tr').find('td:nth-child(4)').attr('id'))
            row['trade_account'] = $('#account').data('account')
            row['trade_notes'] = "Imported with Samourai Dojo"
            // Add this row to our list of rows
            list[count] = row;
            count = count + 1;
        });
        // Now push the list into the database through the API
        list = JSON.stringify(list)

        $.ajax({
            type: "POST",
            contentType: 'application/json',
            dataType: "json",
            url: "/import_transaction",
            data: list,
            success: function (data_back) {
                console.log("[import] Ajax ok");
                console.log(data_back)
                window.location.href = "/bitcoin_monitor";
            }
        });

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
                    "</code><p style='color: grey;'>Key saved. <strong>Page will reload soon</strong></p>"
                $("#api_key").html("<i class='fas fa-check-circle fa-lg' style='color: lightgreen;'></i>")
                $("#api_key").prop('disabled', true);
                // // Wait a few seconds so message can be read by user
                setTimeout(function () {
                    location.reload()
                }, 4000);
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
