
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
                    console.log(data)
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