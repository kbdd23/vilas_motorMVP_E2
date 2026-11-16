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
    var CENTRO_INICIAL = [-20.2280, -70.1150];
    var ZOOM_INICIAL = 12;

    var contenedor = document.getElementById('mapa-flota');
    if (!contenedor) {
        return;
    }

    var aviso = document.getElementById('mapa-flota-aviso');
    var endpoint = contenedor.getAttribute('data-endpoint');

    var drawer = document.getElementById('drawer-equipo');
    var drawerFondo = document.getElementById('drawer-equipo-fondo');
    var drawerCerrar = document.getElementById('drawer-equipo-cerrar');
    var drawerEnlace = document.getElementById('drawer-equipo-enlace');
    var hayDrawer = Boolean(drawer && drawerFondo && drawerCerrar);

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
        var cantidad = grupo.getChildCount();
        var tamano = cantidad < 10 ? 30 : (cantidad < 100 ? 36 : 44);
        return L.divIcon({
            className: 'marcador-grupo',
            html: '<span style="width:' + tamano + 'px;height:' + tamano + 'px">' + cantidad + '</span>',
            iconSize: [tamano, tamano],
            iconAnchor: [tamano / 2, tamano / 2]
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
            iconSize: [14, 14],
            iconAnchor: [7, 7],
            popupAnchor: [0, -7]
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

    function formatearSenal(iso) {
        if (!iso) {
            return 'Sin reportar';
        }
        var fecha = new Date(iso);
        if (isNaN(fecha.getTime())) {
            return 'Sin reportar';
        }
        return fecha.toLocaleString('es-CL', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function escribir(id, texto) {
        var elemento = document.getElementById(id);
        if (elemento) {
            elemento.textContent = texto;
        }
    }

    function abrirDrawer(posicion) {
        escribir('drawer-equipo-codigo', posicion.codigo);
        escribir('drawer-equipo-detalle', posicion.detalle || 'Sin detalle registrado');
        escribir('drawer-equipo-patente', posicion.patente || '—');
        escribir('drawer-equipo-horometro', posicion.horometro || '—');
        escribir('drawer-equipo-senal', formatearSenal(posicion.senal));

        var estado = document.getElementById('drawer-equipo-estado');
        if (estado) {
            estado.textContent = posicion.estado_etiqueta;
            estado.setAttribute('data-tono', tonoDelEstado(posicion.estado));
        }
        if (drawerEnlace) {
            drawerEnlace.setAttribute('href', posicion.url);
        }

        drawer.hidden = false;
        drawerFondo.hidden = false;
        drawerCerrar.focus();
    }

    function cerrarDrawer() {
        drawer.hidden = true;
        drawerFondo.hidden = true;
    }

    if (hayDrawer) {
        drawerCerrar.addEventListener('click', cerrarDrawer);
        drawerFondo.addEventListener('click', cerrarDrawer);
        document.addEventListener('keydown', function (evento) {
            if (evento.key === 'Escape' && !drawer.hidden) {
                cerrarDrawer();
            }
        });
    }

    function dibujar(datos) {
        marcadores.clearLayers();

        datos.posiciones.forEach(function (posicion) {
            var marcador = L.marker([posicion.lat, posicion.lng], {
                icon: iconoEquipo(posicion),
                title: posicion.codigo
            });

            if (hayDrawer) {
                marcador.on('click', function () {
                    abrirDrawer(posicion);
                });
            } else {
                marcador.bindPopup(contenidoPopup(posicion));
            }

            marcador.addTo(marcadores);
        });

        if (datos.posiciones.length) {
            var esquinas = datos.posiciones.map(function (posicion) {
                return [posicion.lat, posicion.lng];
            });
            mapa.fitBounds(L.latLngBounds(esquinas), {
                padding: [28, 28],
                maxZoom: 14
            });
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
