$(document).ready(function () {
    // Initialize tool tips
    $(function () {
        $('[data-toggle="tooltip"]').tooltip()
    })

    // Sum totals
    refresh_tables();

    $(document).on('click', '.check_address', function () {
        var $linkID = $(this).attr('id');
        response = check_address($linkID, this);
    });

    // Select All and Select None
    $('#selectAllButton').on('click', function () {
        $('input[type="checkbox"]').prop('checked', true);
    });

    // Listen for changes in any table to sum rows again
    $(document).on('change', '.monitor_table', function () {
        refresh_tables();
    });


    $('#selectNoneButton').on('click', function () {
        $('input[type="checkbox"]').prop('checked', false);
    });

    // Section (account) click - select section checkbox
    $('.section .section_label input').click(function () {
        $(this).closest('.section').find('input[type="checkbox"]').not(this).prop('checked', this.checked)
    });

    $('#check_selected').on('click', function () {
        // Any address selected?
        var count = $('.address_check:checkbox:checked').length
        if (count == 0) {
            alert("No addresses selected. Try again.");
            return;
        };

        // Open scan console
        $('#scan_section').slideToggle("slow");
        $('#status_bar').html("Initializing...");

        // Disable Buttons and checkboxes
        // $(className).hide();
        $('.checkbox').hide();
        $('.xbuttons').hide();

        // Get variables - look how many are checked from class address_check
        var checked = 0;
        var progress = 100 / count
        $('#status_bar').html("Checking a total of " + count + " addresses...");

        // Loop through list of addresses
        $('.address_check:checkbox:checked').each(function () {
            // Show if address is being checked
            address = ($(this).attr('id'))
            $('#status_bar').html("Checking address: " + address + "...");
            $(this).closest('tr').children('#check').html("Checking...");
            // Store current balance in Satoshis
            balance = $(this).closest('tr').children('#balance').data("balance");
            check_address(address, this, progress)
        });

    });

});

// Sum all balances in table positions into a last row
function refresh_tables() {
    $('.monitor_table').each(function () {
        var TotalValue = 0;
        $(this).find('.balance_sum').each(function () {
            TotalValue += parseFloat($(this).data("balance"));
            console.log("This" + $(this).data("balance"))
        });
        console.log(this);
        console.log(TotalValue);
        $(this).find('.sum_total').html((TotalValue / 100000000).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));
    });
};

function increment_progress(increment) {
    // Update the progress bar
    // First get progress bar value
    pr_now = parseFloat($('.progress-bar').data('prog')) + increment
    $('.progress-bar').data('prog', String(pr_now));
    $('.progress-bar').width(String(pr_now) + '%');
    $('.progress-bar').html(String(pr_now.toFixed(2)) + '%')
    if (pr_now >= 99.9999) {
        $('.progress-bar').html("All Done")
        $('.progress-bar').queue(function () {
            $('.progress-bar').css("background-color", "green");
        });
        $('#scan_title').html("Scan Complete. Check table for status.")
        $('#status_all').hide();
        $('#scan_section_done').slideToggle("slow");
    }
}

function check_address(address, element, progress) {
    $.ajax({
        type: "POST",
        url: "/get_address",
        timeout: 20000,
        data: {
            "address": address
        },
        success: function (data_return) {
            $('#status_bar').html("Received back data for address: " + address + "...");
            increment_progress(progress);

            if (data_return == 'error') {
                $(element).closest('tr').children('#check').html("Error. Try again.");
                $(element).closest('tr').children('#check').addClass('text-danger').removeClass('text-dark');
            }
            if (data_return['success'] != null) {
                console.log("Success - data ok")
                // Hide alert after 4500ms
                if (data_return['change'] == true) {
                    $(element).closest('tr').children('#transactions').addClass("text-danger");
                    $(element).closest('tr').children('#check').addClass('align-middle text-left text-danger')
                    $(element).closest('tr').children('#check').html("Change Detected");
                    $(element).closest('tr').children('#balance').html("<strong class='text-center'>Changed from:<br><span class='text-info'> " +
                        (data_return['address_data']['previous_balance'] / 100000000).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) +
                        "</span><br> to: <br><span class='text-info'>" +
                        (data_return['address_data']['last_balance'] / 100000000).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 })) +
                        "Check recent <a href='/bitcoin_transactions/" + address + "'>transactions</a></strong>."
                    $(element).closest('tr').children('#method').html(data_return['method']);
                } else {
                    $(element).closest('tr').children('#check').addClass('text-success')
                    $(element).closest('tr').children('#check').html("No Changes");
                    $(element).closest('tr').children('#method').html(data_return['method']);

                }
            }

        },
        error: function (xhr, status, error) {
            increment_progress(progress);
            $('#status_bar').html("Address: " + address + " FAILED. Error: " + error);
            console.log("ERROR on AJAX")
            console.log(status);
            console.log(error);
            $(element).closest('tr').children('#check').html("Error: " + error);
            $(element).closest('tr').children('#check').addClass('text-danger').removeClass('text-dark');
        }
    });

}