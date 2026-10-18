/*
 * Comportamiento del listado de arriendos.
 *
 * 1. Preferencia de ventana: la comparte con la bandeja de horómetros y vive en
 *    ventana.js, porque la ventana es una preferencia de la persona y no de la
 *    pantalla.
 * 2. Confirmación del regreso: el botón de marcar disponible abre un diálogo
 *    antes de enviar, para no cambiar el estado de una máquina por accidente.
 */
(function () {
    'use strict';

    function iniciarConfirmacionDeRegreso() {
        var dialogo = document.getElementById('dialogo-disponible');
        var formulario = document.getElementById('formulario-disponible');
        var botonNo = document.getElementById('boton-no');

        if (!dialogo || !formulario) {
            return;
        }

        document.querySelectorAll('[data-disponible]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                formulario.action = boton.dataset.disponible;
                dialogo.showModal();
            });
        });

        if (botonNo) {
            botonNo.addEventListener('click', function () {
                dialogo.close();
            });
        }
    }

    iniciarSelectorDeVentana();
    iniciarConfirmacionDeRegreso();
})();
