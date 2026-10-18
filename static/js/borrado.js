/*
 * Confirmación de borrado en dos pasos, compartida por las páginas que borran.
 *
 * Borrar es irreversible, así que la primera pregunta confirma la intención y la
 * segunda advierte la consecuencia. Los dos <dialog> y el formulario usan ids
 * fijos (dialogo-borrar, dialogo-borrar-confirmar, formulario-borrar,
 * boton-borrar-seguir), así que cualquier página puede colgarlos sin escribir su
 * propio JavaScript.
 */
window.iniciarCierreDeDialogos = function () {
    'use strict';

    document.querySelectorAll('[data-cerrar-dialogo]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            boton.closest('dialog').close();
        });
    });
};

window.iniciarBorradoEnDosPasos = function () {
    'use strict';

    var primero = document.getElementById('dialogo-borrar');
    var segundo = document.getElementById('dialogo-borrar-confirmar');
    var formulario = document.getElementById('formulario-borrar');
    var seguir = document.getElementById('boton-borrar-seguir');

    if (!primero || !segundo || !formulario) {
        return;
    }

    document.querySelectorAll('[data-borrar]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            formulario.action = boton.dataset.borrar;
            primero.showModal();
        });
    });

    if (seguir) {
        seguir.addEventListener('click', function () {
            primero.close();
            segundo.showModal();
        });
    }
};
