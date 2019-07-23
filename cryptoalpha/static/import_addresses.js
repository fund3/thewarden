$(document).ready(function () {
    // Initialize tool tips
    $(function () {
        $('[data-toggle="tooltip"]').tooltip()
    })


    // Autocomplete for account input text
    $(function () {
        $("#tradeaccount").autocomplete({
            source: function (request, response) {
                $.ajax({
                    url: "/aclst?",
                    dataType: "json",
                    data: {
                        term: request.term
                    },
                    success: function (data) {
                        response($.map(data, function (item) {
                            return {
                                label: item,
                                value: item
                            }
                        }));
                    }
                });
            },
            minLength: 0
        });
    });

    // IMPORT BUTTON CLICKED
    $('#import').on('click', function () {
        // Any address selected?

        var addresses = $('#tickers').val()
        var account = $('#tradeaccount').val()
        addresses_list = addresses.split(',');
        count = addresses_list.length;
        if (count == 0) {
            alert("No addresses in the list. Try again.");
            return;
        };
        if (account == "") {
            alert("Trade Account is required");
            return;
        }

        // Open scan console
        $('#scan_section').slideToggle("slow");
        // $('#table_section').slideToggle("slow");
        $('#status_bar').html("Please hold. This may take many minutes. Scanning the blockchain for addresses and transactions.<br>Do not leave this page. Just wait.");
        // Disable Buttons and checkboxes
        $('#ticker_list').hide();
        $('#import').hide();

        // Get variables - look how many are checked from class address_check
        var checked = 0;
        // createTable(addresses, progress, account);
        // Table is created, now start the ajax requests for info
        // first check address and balances, then get transactions + BTC prices on transaction date
        // Checking addresses for balance and transactions

        list = JSON.stringify({
            "address_list": addresses,
            "account": account
        })
        check_addresses(list)
    });
});

function check_addresses(addresses) {
    console.log("Sending request... data:")
    console.log(addresses)
    $.ajax({
        type: "POST",
        url: "/addresses_importer",
        timeout: 200000,
        dataType: "json",
        data: addresses,
        success: function (data_return) {
            console.log(data_return)
            $('#status_bar').html("Received response from Dojo");
            if (data_return.dojo.status == 'error') {
                $('#status_bar').html("DOJO Request error: " + data_return.status);
            } else {
                process_data(data_return);
            }
        },
        error: function (xhr, status, error) {
            $('#status_bar').html("Could not get transactions. Error: " + error);
            console.log("ERROR on AJAX")
            console.log(status);
            console.log(error);
        }
    });
}

function process_data(data) {

    // Create table - summary Data for addresses
    $('#table_section').slideToggle("slow");
    var type = "Public Key"
    $.each(data.dojo.addresses, function (key, value) {
        type = "Public Key"
        // check if starts with HD address ['xpub', 'ypub', 'zpub']
        if (value.address.startsWith("xpub") || value.address.startsWith("ypub") || value.address.startsWith("zpub")) {
            type = "HD Address";
        };
        if (value.address.length > 15) {
            var address_trim = value.address.slice(0, 5) + "..." + value.address.slice(-5);
        } else {
            var address_trim = value.address;
        }

        var icon = ""
        var class_icon = ""

        message = data['status'][value.address]['message']
        if (message == "Found and Imported") {
            icon = "<i class='fas fa-check'></i>"
            class_icon = "text-success"
        } else if (message == "Not found") {
            icon = "<i class='fas fa-times'></i>"
            class_icon = "text-danger"
        } else {
            icon = "<i class='fas fa-exclamation-circle'></i>"
            class_icon = "text-warning"
        };

        var body_html = "<tr id=" + value.address + ">" +
            "<td class='align-middle text-left'>" +
            address_trim + "</td><td class='align-middle text-center'>" +
            type + "</td><td class='align-middle text-center'>" +
            data.main_account + "</td><td class='align-middle text-right'>" +
            (value.final_balance / 100000000).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 4, minimumFractionDigits: 4 }) +
            "</td><td class='align-middle text-center'>" +
            value.n_tx.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 }) +
            "</td><td class='align-middle text-center " + class_icon + "' data-toggle='tooltip'" +
            "title='" + message + "' data-placement='top'>" + icon +
            "</td></tr>";

        var html_table = $('#table_body').html() + body_html;
        $('#table_body').html(html_table);
    });

    var empty_list = true;
    html_table = "";
    // Create table for not found addresses, if any
    $.each(data.status, function (key, value) {
        if (value == 'Not found') {
            empty_list = false;
            html_table += "<tr><td class='text-left'>" + key + '</td></tr>';
        };
    });
    if (empty_list == false) {
        $('#not_found').slideToggle("slow");
        $('#not_found_body').html(html_table);
    };

};





