document.addEventListener('DOMContentLoaded', function () {
    function setAlignmentAidVisibility() {
        var selected = document.querySelector('input[name="alignment_aid"]:checked');
        var value = selected ? selected.value : 'none';
        document.getElementById('ledge-options').classList.toggle('collapsed', value !== 'ledge');
        document.getElementById('frame-options').classList.toggle('collapsed', value !== 'frame');
    }

    document.querySelectorAll('input[name="alignment_aid"]').forEach(function (radio) {
        radio.addEventListener('change', setAlignmentAidVisibility);
    });

    setAlignmentAidVisibility();

    document.querySelectorAll('.manual-stencil-size').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            document.getElementById('id_outline_file').disabled = this.checked;
        });
    });
});
