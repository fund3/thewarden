$(document).ready(function () {

    // Format Red and Green Numbers (negative / positive)
    $("td.redgreen").removeClass('red_negpos');
    $("td.redgreen").addClass('green_negpos');
    $("td.redgreen:contains('-')").removeClass('green_negpos');
    $("td.redgreen:contains('-')").addClass('red_negpos');


    $("#select_all").click(function () {
        $('.import_check').attr('checked', 'checked');
    });

    $("#select_none").click(function () {
        $('.import_check').removeAttr('checked');
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



    // // Looping through Transactions to get prices
    $('.btc_price').each(function (i, obj) {
        var date_grab = ($(this).attr('id'));
        // date is EPOCH - convert to string
        var date = new Date(date_grab * 1000);
        var year = date.getFullYear();
        var month = date.getMonth() + 1;
        var day = date.getDate();
        date_grab = (year + "-" + month + "-" + day);
        var ticker = 'BTC'

        $.ajax({
            type: "GET",
            dataType: 'json',
            url: "/getprice_ondate?ticker=" + ticker + "&date=" + date_grab,
            success: function (data) {
                html_data = "<input type='text' value='" + data.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) +
                    "' class='form-control text-center' aria-label='Small' aria-describedby='inputGroup-sizing-sm' id='" + $(this).attr('id') + "'>"
                $(obj).html(html_data);
            },
            error: function (xhr, status, error) {
                console.log(status);
            }
        });

    });
});