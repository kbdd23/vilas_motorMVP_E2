/*
 * Comportamiento de la ficha de una orden de trabajo.
 *
 * El cierre vive en un diálogo de la ficha y no en una página aparte. El aviso
 * con el horómetro actual lo escribe el servidor, porque acá hay una sola OT: no
 * hace falta que el botón traiga datos, a diferencia de la bandeja de horómetros.
 * El cierre del diálogo lo aporta borrado.js (compartido). Si el POST no pasa la
 * validación, el servidor devuelve la ficha con el diálogo abierto para que el
 * error quede a la vista.
 */
(function () {
    'use strict';

    function iniciarDialogoDeCierre() {
        var dialogo = document.getElementById('dialogo-cerrar-orden');

        if (!dialogo) {
            return;
        }

        document.querySelectorAll('[data-abrir-cierre]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                dialogo.showModal();
            });
        });

        if (dialogo.dataset.abrirAlCargar === 'si') {
            dialogo.showModal();
        }
    }

    iniciarCierreDeDialogos();
    iniciarDialogoDeCierre();
})();
