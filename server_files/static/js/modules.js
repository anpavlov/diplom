$(document).ready(function(){
    $('.modules-table__field_btn[data-type=approve]').click(approve_clicked);
    $('.modules-table__field_btn[data-type=info]').click(info_clicked);
    $('.modules-table__field_btn[data-type=delete]').click(delete_clicked);
});

function approve_clicked(event) {
    event.preventDefault();

    var id = $(this).data('moduleId');
    alert( "Approve" + id );
}

function info_clicked(event) {
    //event.preventDefault();

    var id = $(this).data('moduleId');
    alert( "Info" + id );
}

function delete_clicked(event) {
    if (!confirm('???')) {
        event.preventDefault();
    }
}