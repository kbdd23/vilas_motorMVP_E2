/*
 * Comportamiento de la bandeja de horómetros.
 *
 * La ventana de trazabilidad la maneja ventana.js y la confirmación de borrado
 * borrado.js, ambos compartidos. Acá queda lo propio del módulo: el diálogo que
 * registra la lectura, que se resuelve en la misma bandeja en vez de llevar a una
 * página aparte. El botón de la fila trae los datos del encabezado, así que
 * abrirlo no le pide nada al servidor.
 */
(function () {
    'use strict';

    function iniciarDialogoDeLectura() {
        var dialogo = document.getElementById('dialogo-lectura');
        var formulario = document.getElementById('formulario-lectura');
        var contexto = document.getElementById('lectura-contexto');

        if (!dialogo || !formulario || !contexto) {
            return;
        }

        function encabezado(boton) {
            var texto = 'Horómetro del equipo ' + boton.dataset.equipo +
                ' pedido por vía ' + boton.dataset.fuente;
            if (boton.dataset.cliente) {
                texto += ', a ' + boton.dataset.cliente;
            }
            return texto + '. Horómetro actual: ' + boton.dataset.actual +
                '. La lectura no puede ser menor.';
        }

        document.querySelectorAll('[data-lectura]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                formulario.action = boton.dataset.lectura;
                contexto.textContent = encabezado(boton);
                formulario.reset();
                dialogo.showModal();
            });
        });

        // Cuando el servidor reenvía la bandeja con el diálogo abierto es porque el
        // POST no pasó la validación: se abre solo para que el error quede a la vista.
        if (dialogo.dataset.abrirAlCargar === 'si') {
            dialogo.showModal();
        }
    }

    iniciarSelectorDeVentana();
    iniciarCierreDeDialogos();
    iniciarDialogoDeLectura();
    iniciarBorradoEnDosPasos();
})();
