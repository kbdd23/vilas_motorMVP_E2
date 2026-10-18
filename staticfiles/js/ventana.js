/*
 * Selector de la ventana de trazabilidad, compartido por las bandejas de trabajo
 * (arriendos y horómetros).
 *
 * El filtrado real lo hace el backend: este script solo recuerda la elección y
 * recarga con ?ventana= para que el servidor devuelva la lista ya filtrada.
 * Filtrar ocultando filas en el navegador dejaría mal calculados los conteos y
 * la deduplicación por equipo de la bandeja de arriendos.
 *
 * La recarga usa recargarCon() (parametros.js) para no pisar los otros parámetros
 * de la URL: en horómetros conviven con fuente y nueva.
 *
 * La clave es la misma en ambas páginas porque la ventana es una preferencia de
 * la persona, no de la pantalla.
 */
window.iniciarSelectorDeVentana = function () {
    'use strict';

    var CLAVE = 'vilas_ventana_bandeja';
    var CLAVE_ANTERIOR = 'vilas_ventana_arriendos';
    var selector = document.getElementById('selector-ventana');

    if (!selector) {
        return;
    }

    var valores = Array.prototype.map.call(selector.options, function (opcion) {
        return opcion.value;
    });
    // La clave anterior es la que usaba solo la bandeja de arriendos: se migra
    // para no perder la preferencia ya elegida.
    var guardada = localStorage.getItem(CLAVE) || localStorage.getItem(CLAVE_ANTERIOR);
    var vieneEnLaUrl = window.location.search.indexOf('ventana=') !== -1;

    // Si hay una preferencia guardada y la URL no trae ninguna, se aplica una vez.
    if (!vieneEnLaUrl && guardada && valores.indexOf(guardada) !== -1) {
        localStorage.setItem(CLAVE, guardada);
        recargarCon({ventana: guardada});
        return;
    }

    selector.addEventListener('change', function () {
        localStorage.setItem(CLAVE, selector.value);
        recargarCon({ventana: selector.value});
    });
};
