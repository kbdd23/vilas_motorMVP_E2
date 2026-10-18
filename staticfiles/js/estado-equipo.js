/*
 * Diálogo de "Cambiar estado" del inventario de equipos.
 *
 * El botón de la fila lleva la URL del equipo y su estado actual en atributos data,
 * así que abrir el diálogo no consulta al servidor: el select llega marcado con el
 * estado de la máquina y el formulario apunta a su URL.
 */
(function () {
    'use strict';

    var dialogo = document.getElementById('dialogo-estado');
    var formulario = document.getElementById('formulario-estado');
    var seleccion = document.getElementById('select-estado');
    var nombre = document.getElementById('estado-equipo');

    if (!dialogo || !formulario || !seleccion) {
        return;
    }

    document.querySelectorAll('[data-cambiar-estado]').forEach(function (boton) {
        boton.addEventListener('click', function () {
            formulario.action = boton.dataset.cambiarEstado;
            nombre.textContent = boton.dataset.equipo;
            seleccion.value = boton.dataset.estado;
            dialogo.showModal();
        });
    });

    iniciarCierreDeDialogos();
})();
