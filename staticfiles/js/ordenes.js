/*
 * Comportamiento de la lista de órdenes de trabajo.
 *
 * La confirmación de borrado la aporta borrado.js (compartida). Acá queda lo
 * propio: el alta, que vive en un diálogo. El botón lo abre y el formulario
 * postea a la URL de siempre; si el POST no pasa la validación, el servidor
 * devuelve la lista con el diálogo abierto para que el error quede a la vista.
 */
(function () {
    'use strict';

    function iniciarDialogoDeCrear() {
        var dialogo = document.getElementById('dialogo-crear-orden');

        if (!dialogo) {
            return;
        }

        document.querySelectorAll('[data-abrir-orden]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                dialogo.showModal();
            });
        });

        if (dialogo.dataset.abrirAlCargar === 'si') {
            dialogo.showModal();
        }
    }

    iniciarCierreDeDialogos();
    iniciarDialogoDeCrear();
    iniciarBorradoEnDosPasos();
})();
