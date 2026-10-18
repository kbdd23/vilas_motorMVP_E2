/*
 * Cierre automático de los toasts.
 *
 * El aviso lo escribe el servidor (django.contrib.messages) y viaja con la página,
 * así que sobrevive al redirect del POST que falló. Acá solo se desvanece solo,
 * para no obligar a cerrarlo a mano.
 */
(function () {
    'use strict';

    var contenedor = document.querySelector('.toast-contenedor');

    if (!contenedor) {
        return;
    }

    contenedor.querySelectorAll('.toast').forEach(function (toast) {
        window.setTimeout(function () {
            toast.classList.add('toast-saliendo');
            window.setTimeout(function () {
                toast.remove();
            }, 400);
        }, 6000);
    });
})();
