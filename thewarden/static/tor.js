$(document).ready(function () {
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Checking TOR..." +
        "</div>")
    run_ajax();
});



function run_ajax() {
    // Ajax to test TOR

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/testtor",
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request: OK")
            handle_ajax_data(data);
        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while making TOR requests." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });

};

function handle_ajax_data(data) {
    console.log(data)
}
