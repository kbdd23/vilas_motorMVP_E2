/*
 * Recarga la página cambiando un parámetro de la URL y dejando quietos los demás.
 *
 * Reemplazar el search entero con "?algo=valor" se lleva puestos los otros
 * parámetros. En la página de horómetros conviven tres (ventana, fuente y nueva) y
 * perder cualquiera de ellos cambia lo que el servidor devuelve: sin ventana se
 * vuelve a la preferencia guardada, sin fuente queda vacío el desplegable de
 * equipos, y sin nueva se cierra el diálogo que se estaba llenando.
 */
window.recargarCon = function (parametros) {
    'use strict';

    var url = new URL(window.location.href);

    Object.keys(parametros).forEach(function (nombre) {
        if (parametros[nombre] === null) {
            url.searchParams.delete(nombre);
        } else {
            url.searchParams.set(nombre, parametros[nombre]);
        }
    });

    window.location.href = url.toString();
};
