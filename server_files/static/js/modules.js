$(document).ready(function(){
    $('.modules-table__field_btn[data-type=enable]').click(enable_clicked);
    $('.modules-table__field_btn[data-type=approve]').click(approve_clicked);
    $('.modules-table__field_btn[data-type=disable]').click(disable_clicked);
    $('.upload-form').submit(upload_clicked);
});

function enable_clicked(event) {
    event.preventDefault();

    var id = $(this).data('moduleId');
    //alert( "Enable" + id );
    $.ajax({
        type: "POST",
        url: "/admin/enable",
        data: {
            module_id: id
        },
        dataType: "text",
        success: function (data) {
            if (data === "ok") {
                location.reload();
            } else {
                alert(data);
            }
        }
    });
}

function disable_clicked(event) {
    event.preventDefault();

    var id = $(this).data('moduleId');
    //alert( "Enable" + id );
    $.ajax({
        type: "POST",
        url: "/admin/disable",
        data: {
            module_id: id
        },
        dataType: "text",
        success: function (data) {
            if (data === "ok") {
                location.reload();
            } else {
                alert(data);
            }
        }
    });
}

function approve_clicked(event) {
    event.preventDefault();

    var id = $(this).data('moduleId');
    //alert( "Enable" + id );
    $.ajax({
        type: "POST",
        url: "/admin/approve",
        data: {
            module_id: id
        },
        dataType: "text",
        success: function (data) {
            if (data === "ok") {
                location.reload();
            } else {
                alert(data);
            }
        }
    });
}

function upload_clicked(event) {
    event.preventDefault();
    var formData = new FormData($('.upload-form')[0]);

    //alert( "Enable" + id );
    $.ajax({
        type: "POST",
        url: "/admin/upload",
        data: formData,
        async: false,
        cache: false,
        contentType: false,
        processData: false,
        success: function (data) {
            if (data === "ok") {
                location.reload();
            } else {
                alert(data);
            }
        }
    });
}