$(document).ready(function(){
    $('.settings-form').submit(save_clicked);
});

function save_clicked(event) {
    event.preventDefault();
    var form = $('.settings-form')
    var formData = new FormData(form[0]);

    //alert( "Enable" + id );
    $.ajax({
        type: "POST",
        url: form.attr('action'),
        data: formData,
        async: false,
        cache: false,
        contentType: false,
        processData: false,
        success: function (data) {
            if (data === "ok") {
                location.href = "/admin";
            } else {
                alert(data);
            }
        }
    });
}
