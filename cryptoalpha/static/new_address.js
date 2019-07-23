$(document).ready(function () {
    console.log("Ready")

    $('#submit_button').click(function () {
        $('#alerts').html("<div class='alert alert-info alert-dismissible fade show' role='alert'>Please wait... Importing Address. This may take a few minutes. Do not leave this page. Just wait." +
            "</div>" +
            "<div class='alert alert-info alert-dismissible fade show' role='alert'> <Strong>Scanning the blockchain for address and transactions... Go grab a coffee. For XPUBs and other HD addresses this can take 5 minutes or longer.</stong></div>");
        var $this = $(this);
        $('#submit_button').hide()
        $('#submit_button').attr('value', 'Please wait. Including transaction...');
    });


    $("#tradeaccount").autocomplete({
        source: function (request, response) {
            $.ajax({
                url: "/aclst",
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
