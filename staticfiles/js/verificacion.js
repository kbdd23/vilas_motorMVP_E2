/*
 * Casillas del código de verificación.
 *
 * Solo gestiona el foco: al escribir un dígito salta a la siguiente casilla, al
 * borrar vuelve atrás y al pegar un código completo lo reparte. La validación del
 * código es del servidor.
 */
(function () {
    'use strict';

    var formulario = document.querySelector('[data-codigo-form]');
    if (!formulario) {
        return;
    }

    var casillas = Array.prototype.slice.call(formulario.querySelectorAll('.codigo-casillas input'));
    if (!casillas.length) {
        return;
    }

    function enfocar(posicion) {
        var destino = casillas[posicion];
        if (destino) {
            destino.focus();
            destino.select();
        }
    }

    function repartir(texto) {
        var digitos = (texto || '').replace(/\D/g, '').split('');
        if (!digitos.length) {
            return;
        }
        casillas.forEach(function (casilla, indice) {
            casilla.value = digitos[indice] || '';
        });
        enfocar(Math.min(digitos.length, casillas.length - 1));
    }

    casillas.forEach(function (casilla, indice) {
        casilla.addEventListener('input', function () {
            var valor = casilla.value.replace(/\D/g, '');
            if (valor.length > 1) {
                repartir(valor);
                return;
            }
            casilla.value = valor;
            if (valor && indice < casillas.length - 1) {
                enfocar(indice + 1);
            }
        });

        casilla.addEventListener('keydown', function (evento) {
            if (evento.key === 'Backspace' && !casilla.value && indice > 0) {
                evento.preventDefault();
                casillas[indice - 1].value = '';
                enfocar(indice - 1);
            } else if (evento.key === 'ArrowLeft' && indice > 0) {
                evento.preventDefault();
                enfocar(indice - 1);
            } else if (evento.key === 'ArrowRight' && indice < casillas.length - 1) {
                evento.preventDefault();
                enfocar(indice + 1);
            }
        });

        casilla.addEventListener('paste', function (evento) {
            var pegado = (evento.clipboardData || window.clipboardData).getData('text');
            if (pegado) {
                evento.preventDefault();
                repartir(pegado);
            }
        });
    });

    formulario.addEventListener('submit', function () {
        casillas.forEach(function (casilla) {
            casilla.value = casilla.value.replace(/\D/g, '');
        });
    });

    casillas[0].focus();
}());
