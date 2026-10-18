/*
 * Celdas plegables de una página.
 *
 * El <details> nativo ya abre y cierra solo, así que acá no se esconde ni se
 * muestra nada: lo único que se agrega es recordar cómo quedó cada celda, porque
 * el despliegue es una preferencia de la persona y no de la pantalla. Nacen
 * cerradas: al entrar se ve el índice, no las tablas completas.
 *
 * La clave se arma con el nombre de la celda (data-plegable), así que sirve para
 * cualquier página que use el mismo patrón.
 */
(function () {
    'use strict';

    var PREFIJO = 'vilas_celda_';

    document.querySelectorAll('[data-plegable]').forEach(function (celda) {
        var clave = PREFIJO + celda.dataset.plegable;

        if (localStorage.getItem(clave) === 'abierta') {
            celda.open = true;
        }

        celda.addEventListener('toggle', function () {
            localStorage.setItem(clave, celda.open ? 'abierta' : 'cerrada');
        });
    });
})();
