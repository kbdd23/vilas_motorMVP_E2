/*
 * Mapa de flota en vivo del dashboard.
 *
 * Leaflet dibuja el mapa y este archivo solo se encarga de pedirle las
 * posiciones al endpoint, pintar un marcador por equipo y refrescar cada tanto.
 * Si el CDN de Leaflet no carga, el panel lo dice en vez de quedar en blanco.
 */
(function () {
    'use strict';

    var INTERVALO_ACTUALIZACION = 30000;
    var CENTRO_INICIAL = [-20.2300, -70.1000];
    var ZOOM_INICIAL = 10;

    var contenedor = document.getElementById('mapa-flota');
    if (!contenedor) {
        return;
    }

    var aviso = document.getElementById('mapa-flota-aviso');
    var endpoint = contenedor.getAttribute('data-endpoint');

    function mostrarAviso(texto) {
        if (!aviso) {
            return;
        }
        aviso.textContent = texto;
        aviso.hidden = false;
    }

    function ocultarAviso() {
        if (aviso) {
            aviso.hidden = true;
        }
    }

    if (typeof L === 'undefined') {
        mostrarAviso('No se pudo cargar el mapa: la librería no respondió.');
        return;
    }

    function escaparHtml(texto) {
        var caja = document.createElement('div');
        caja.textContent = texto == null ? '' : texto;
        return caja.innerHTML;
    }

    function tonoDelEstado(estado) {
        if (estado === 'DISPONIBLE') {
            return 'verde';
        }
        if (estado === 'EN_FAENA') {
            return 'azul';
        }
        if (estado === 'EN_MANTENIMIENTO') {
            return 'ambar';
        }
        return 'gris';
    }

    var mapa = L.map(contenedor, {
        center: CENTRO_INICIAL,
        zoom: ZOOM_INICIAL,
        scrollWheelZoom: false
    });

    var teselasArcGis = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        { maxZoom: 19, attribution: 'Mapa &copy; Esri, HERE, Garmin, OpenStreetMap' }
    );

    var teselasOsm = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; colaboradores de OpenStreetMap'
    });

    // Esri es gratuito y no pide clave; si igual falla, se cae a OpenStreetMap.
    var erroresDeTesela = 0;
    teselasArcGis.on('tileerror', function () {
        erroresDeTesela += 1;
        if (erroresDeTesela === 3 && !mapa.hasLayer(teselasOsm)) {
            mapa.removeLayer(teselasArcGis);
            teselasOsm.addTo(mapa);
        }
    });
    teselasArcGis.addTo(mapa);

    function iconoGrupo(grupo) {
        return L.divIcon({
            className: 'marcador-grupo',
            html: '<span>' + grupo.getChildCount() + '</span>',
            iconSize: [34, 34],
            iconAnchor: [17, 17]
        });
    }

    var marcadores = (typeof L.markerClusterGroup === 'function')
        ? L.markerClusterGroup({
            showCoverageOnHover: false,
            maxClusterRadius: 45,
            iconCreateFunction: iconoGrupo
        })
        : L.layerGroup();
    mapa.addLayer(marcadores);

    function iconoEquipo(posicion) {
        return L.divIcon({
            className: 'marcador-equipo',
            html: '<span class="marcador-punto" data-tono="' + tonoDelEstado(posicion.estado) + '"></span>',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
            popupAnchor: [0, -8]
        });
    }

    function contenidoPopup(posicion) {
        var detalle = posicion.detalle
            ? '<span>' + escaparHtml(posicion.detalle) + '</span>'
            : '';
        return '<strong class="mapa-popup-codigo">' + escaparHtml(posicion.codigo) + '</strong>' +
            detalle +
            '<em class="mapa-popup-estado" data-tono="' + tonoDelEstado(posicion.estado) + '">' +
            escaparHtml(posicion.estado_etiqueta) + '</em>' +
            '<a href="' + escaparHtml(posicion.url) + '">Abrir ficha →</a>';
    }

    function dibujar(datos) {
        marcadores.clearLayers();

        datos.posiciones.forEach(function (posicion) {
            L.marker([posicion.lat, posicion.lng], {
                icon: iconoEquipo(posicion),
                title: posicion.codigo
            })
                .bindPopup(contenidoPopup(posicion))
                .addTo(marcadores);
        });

        if (datos.posiciones.length) {
            var esquinas = datos.posiciones.map(function (posicion) {
                return [posicion.lat, posicion.lng];
            });
            mapa.fitBounds(L.latLngBounds(esquinas).pad(0.15), { maxZoom: 13 });
        }

        if (!datos.posiciones.length) {
            mostrarAviso('Ningún equipo ha reportado posición todavía.');
        } else if (datos.sin_ubicacion > 0) {
            mostrarAviso(datos.sin_ubicacion + ' equipos aún no reportan posición.');
        } else {
            ocultarAviso();
        }
    }

    function actualizar() {
        fetch(endpoint, { headers: { 'X-Requested-With': 'fetch' } })
            .then(function (respuesta) {
                if (!respuesta.ok) {
                    throw new Error('Respuesta ' + respuesta.status);
                }
                return respuesta.json();
            })
            .then(dibujar)
            .catch(function () {
                mostrarAviso('No se pudieron cargar las posiciones de la flota.');
            });
    }

    actualizar();
    window.setInterval(function () {
        if (!document.hidden) {
            actualizar();
        }
    }, INTERVALO_ACTUALIZACION);
}());
