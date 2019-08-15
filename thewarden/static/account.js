$(document).ready(function () {
    $(function () {
        $("#account_form").submit(function () {
            $("#submit").attr("disabled", true);
            $('#submit').prop('value', 'Recalculating. If base currency was changed this can take some time.');
        });
    });
});


$(function () {
    $('#DELETE').change(function () {
        if ($('#DELETE').val() == "DELETE") {
            $('#DELETEBUTTON').prop('disabled', false);
        }
    });
});


$(function () {
    $("#basefx").autocomplete({
        source: function (request, response) {
            $.ajax({
                url: "/fx_lst?",
                dataType: "json",
                data: {
                    term: request.term
                },

                success: function (data) {
                    response($.map(data, function (item) {
                        return {
                            label: (item),
                            value: (item)
                        }
                    }));
                }

            });
        },
        minLength: 1
    });
});