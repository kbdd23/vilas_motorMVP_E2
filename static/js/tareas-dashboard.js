/*
 * Filtro de la tabla de "Próximas tareas" del dashboard.
 *
 * Las cuatro filas de la tabla son fijas (una por tipo de pendiente), así que
 * filtrar es mostrar u ocultar cada una según la pestaña activa. No hay
 * peticiones al servidor: los contadores ya vienen calculados en la página.
 */
(function () {
    'use strict';

    var botones = document.querySelectorAll('[data-filtro-tarea]');
    var filas = document.querySelectorAll('[data-categoria]');

    if (!botones.length || !filas.length) {
        return;
    }

    function aplicar(filtro) {
        filas.forEach(function (fila) {
            var categoria = fila.getAttribute('data-categoria');
            fila.hidden = filtro !== 'todas' && categoria !== filtro;
        });
    }

    botones.forEach(function (boton) {
        boton.addEventListener('click', function () {
            botones.forEach(function (otro) {
                otro.classList.remove('active');
                otro.setAttribute('aria-selected', 'false');
            });
            boton.classList.add('active');
            boton.setAttribute('aria-selected', 'true');
            aplicar(boton.getAttribute('data-filtro-tarea'));
        });
    });
}());
