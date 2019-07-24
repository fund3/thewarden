
$(document).ready(function () {
    console.log("Wherever the real power in a Government lies, there is the danger of oppression. In our Governments, the real power lies in the majority of the Community, and the invasion of private rights is chiefly to be apprehended, not from the acts of Government contrary to the sense of its constituents, but from acts in which the Government is the mere instrument of the major number of the constituents. - James Madison")

    // Test Tor
    $.ajax({
        type: 'GET',
        url: '/test_tor',
        dataType: 'json',
        success: function (data) {
            if (data.status == true) {
                $('#tor_txt').html("<span style='color: green;'>Success</span>: Tor Enabled" +
                    "<div class='float-right text-success' role='status'>" +
                    "<i class='fas fa-check fa-2x'></i></div>");
            }
        },
        error: function (xhr, status, error) {
            $('tor_txt').html("<span style='color: red;'>Failed</span>: Tor not available. Check the instructions on how to download and install Tor." +
                "<div class='float-right text-danger' role='status'>" +
                "<i class='fas fa-times-circle fa-2x'></i></div>");
            console.log(status);
        }
    });

    // Test OXT with a random address from block 100,000
    // In the future - implement a randomization pick of an
    // address. But since the test here is mostly for connectivity
    // and not accuracy of data, this is sufficient for now.
    test_addr = '1JxDJCyWNakZ5kECKdCU9Zka6mh34mZ7B2'
    $.ajax({
        type: 'GET',
        url: '/oxt_get_address?addr=' + test_addr,
        dataType: 'json',
        success: function (data) {

            if ('data' in data) {
                $('#oxt_txt').html("<span style='color: green;'>Success</span>: Got a response from OXT using Tor" +
                    "<div class='float-right text-success' role='status'>" +
                    "<i class='fas fa-check fa-2x'></i></div>");
            } else {
                $('#oxt_txt').html("<span style='color: red;'>Failed</span>: Got an empty response from OXT" +
                    "<div class='float-right text-danger' role='status'>" +
                    "<i class='fas fa-times-circle fa-2x'></i></div>");
            }

            if ((data.data[0] != null) && (data.data[0]['value'] == test_addr)) {
                $('#oxta_txt').html("<span style='color: green;'>Success</span>: Sample address returned ok" +
                    "<div class='float-right text-success' role='status'>" +
                    "<i class='fas fa-check fa-2x'></i></div>");
            } else {
                $('#oxta_txt').html("<span style='color: red;'>Failed</span>: Got an empty response from OXT" +
                    "<div class='float-right text-danger' role='status'>" +
                    "<i class='fas fa-times-circle fa-2x'></i></div>");
            }
        },
        error: function (xhr, status, error) {
            $('oxt_txt').html("<span style='color: red;'>Failed</span>: Either Tor is not enabled or OXT is not getting Tor requests.")
            console.log(status);
        }
    });

    // Test Dojo
    $.ajax({
        type: 'GET',
        url: '/test_dojo',
        dataType: 'json',
        success: function (data) {

            if (data['onion_address'] != "empty") {
                $('#dojo_txt').html("<span style='color: green;'>Success</span>: Dojo Onion Address Found" +
                    "<div class='float-right text-success' role='status'>" +
                    "<i class='fas fa-check fa-2x'></i></div>");
            } else {
                $('#dojo_txt').html("<span style='color: red;'>Failed</span>: No onion address found. " +
                    "Click <a href='/dojo_setup'>here to check settings</a>" +
                    "<div class='float-right text-danger' role='status'>" +
                    "<i class='fas fa-times-circle fa-2x'></i></div>");
            }

            if ('authorizations' in data.dojo_auth) {
                $('#dojoa_txt').html("<span style='color: green;'>Success</span>: Authentication succesful" +
                    "<div class='float-right text-success' role='status'>" +
                    "<i class='fas fa-check fa-2x'></i></div>");
            } else {
                $('#dojoa_txt').html("<span style='color: red;'>Failed</span>: Authentication failed. Make sure Dojo is running and click " +
                    "<a href='/dojo_setup'>here to check settings</a>" +
                    "<div class='float-right text-danger' role='status'>" +
                    "<i class='fas fa-times-circle fa-2x'></i></div>");
            }

        },
        error: function (xhr, status, error) {
            $('dojo_txt').html("<span style='color: red;'>Failed</span>: No Dojo connection found. " +
                "Make sure Dojo is running and click " +
                "<a href='/dojo_setup'>here to check settings</a>" +
                "<div class='float-right text-danger' role='status'>" +
                "<i class='fas fa-times-circle fa-2x'></i></div>");
            console.log(status);
        }
    });


});


