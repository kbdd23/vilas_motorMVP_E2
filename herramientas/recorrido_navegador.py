"""Recorre los casos de prueba manual M1 a M8 en un navegador real (Playwright) y guarda capturas.

Requisitos: servidor en ejecución en 127.0.0.1:8765 con los datos de demostración (seed_demo), un usuario
planificador (planificador@vilasmotor.cl) y Playwright con Chromium instalado. Para que M7 muestre la
diferencia entre ventanas, una solicitud cumplida debe tener fecha_resolucion de hace unos 3 días.
Salida: carpeta shots/ con las capturas y res.json con el resultado de cada caso.
"""
import json, re, datetime
from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8765'; S='shots/'
USER='planificador@vilasmotor.cl'; PW='Demo-Vilas-2026-Clave'
res=[]
PG=[None]
def caso(id_, nombre, fn):
    try:
        det=fn(); res.append({'id':id_,'caso':nombre,'estado':'OK','detalle':det})
    except Exception as e:
        res.append({'id':id_,'caso':nombre,'estado':'FALLA','detalle':str(e)[:300]})
        try: PG[0].screenshot(path=S+'fallo_'+id_+'.png',full_page=True)
        except Exception: pass
    print(res[-1])

def abrir(pg):
    while pg.locator('details.celda-plegable:not([open]) > summary').count():
        pg.locator('details.celda-plegable:not([open]) > summary').first.click()

def login(pg):
    pg.goto(B+'/login/'); pg.fill('input[name=username]',USER); pg.fill('input[name=password]',PW); pg.click('main form button[type=submit]'); pg.wait_for_load_state()

with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':1280,'height':800}); pg=ctx.new_page(); PG[0]=pg

    def m1():
        pg.goto(B+'/login/'); pg.fill('input[name=username]',USER); pg.fill('input[name=password]','mala-clave-123'); pg.click('main form button[type=submit]')
        assert 'incorrectos' in pg.inner_text('body'); pg.screenshot(path=S+'m1_login_error.png')
        login(pg); assert pg.url.endswith('/dashboard/'), pg.url
        pg.screenshot(path=S+'dashboard.png',full_page=True)
        return 'Contraseña incorrecta: mensaje de error. Credenciales válidas: acceso al panel.'
    caso('M1','Inicio de sesión',m1)

    def m2():
        pg.goto(B+'/horometros/'); abrir(pg)
        fila=pg.locator('tr',has_text='RET-118').first
        btn=fila.locator('[data-lectura]'); actual=float(btn.get_attribute('data-actual').replace(',','.'))
        btn.click()
        pg.fill('#formulario-lectura input[name=valor]',str(actual-5)); pg.click('#formulario-lectura button[type=submit]'); pg.wait_for_load_state()
        pg.screenshot(path=S+'m2_lectura_rechazada.png')
        assert pg.locator('tr',has_text='RET-118').locator('.badge-warn').count()>=1, 'la solicitud debía seguir pendiente tras lectura menor'
        rechazo=pg.locator('#dialogo-lectura .errorlist, #dialogo-lectura .form-errors').count()>0 or pg.locator('dialog[open]').count()>0
        assert rechazo, 'no se vio el rechazo'
        # lectura mayor
        pg.fill('#formulario-lectura input[name=valor]',str(actual+10)); pg.click('#formulario-lectura button[type=submit]'); pg.wait_for_load_state()
        fila=pg.locator('tr',has_text='RET-118').first
        assert fila.locator('.badge-ok').count()>=1, 'no quedó cumplida'
        pg.screenshot(path=S+'horometros.png',full_page=True)
        pg.goto(B+'/equipos/'); t=pg.locator('tr',has_text='RET-118').inner_text()
        assert str(int(actual+10)) in t.replace('.',''), t
        return f'Lectura {actual-5} rechazada (solicitud sigue pendiente); lectura {actual+10} cierra la solicitud y actualiza el equipo (horómetro previo {actual}).'
    caso('M2','Lectura de horómetro',m2)

    def m3():
        pg.goto(B+'/arriendos/')
        vig=pg.locator('tr',has=pg.locator('.badge-ok')).first.locator('td').first.inner_text().strip()
        pg.goto(B+'/arriendos/nuevo/')
        opts=[o.inner_text() for o in pg.locator('select[name=equipo] option').all()]
        if any(vig in o for o in opts):
            pg.select_option('select[name=equipo]',label=[o for o in opts if vig in o][0])
            pg.select_option('select[name=cliente]',index=1); pg.fill('input[name=fecha_inicio]',datetime.date.today().isoformat())
            pg.click('main form button[type=submit]'); pg.wait_for_load_state()
            pg.screenshot(path=S+'m3_arriendo_duplicado.png')
            assert pg.locator('.errorlist').count()>0, 'no hubo error'
            return f'Equipo {vig} con arriendo vigente: el formulario muestra error en el campo equipo.'
        pg.screenshot(path=S+'m3_arriendo_duplicado.png')
        return f'El equipo {vig} (arriendo vigente) no aparece entre las opciones del formulario: no se puede duplicar el arriendo.'
    caso('M3','Arriendo duplicado',m3)

    def m4():
        pg.goto(B+'/arriendos/')
        fila=pg.locator('tr',has=pg.locator('.badge-ok')).first; cod=fila.locator('td').first.inner_text().strip()
        fila.locator('a:has-text("Cerrar")').click(); pg.wait_for_load_state()
        pg.fill('input[name=fecha_termino]',datetime.date.today().isoformat()); pg.click('main form button[type=submit]'); pg.wait_for_load_state()
        fila=pg.locator('tr',has_text=cod).first
        assert fila.locator('.badge-neutral').count()>=1, 'no quedó cerrado'
        assert fila.locator('[data-disponible]').count()==1, 'no quedó en bandeja'
        pg.screenshot(path=S+'arriendos_bandeja.png',full_page=True)
        fila.locator('[data-disponible]').click(); pg.click('#formulario-disponible button[type=submit]'); pg.wait_for_load_state()
        fila=pg.locator('tr',has_text=cod)
        assert fila.count()==0 or fila.first.locator('[data-disponible]').count()==0, 'seguía en bandeja'
        return f'Arriendo de {cod} cerrado; permanece en la bandeja hasta marcar disponible; luego sale de la bandeja.'
    caso('M4','Cierre de arriendo',m4)

    def m5():
        pg.goto(B+'/dashboard/'); dash_antes=pg.locator('tr',has_text='V168').first.inner_text()
        pg.goto(B+'/equipos/'); hor_txt=pg.locator('tr',has_text='V168').first.inner_text()
        pg.goto(B+'/ordenes-trabajo/'); antes=pg.locator('tbody tr').count()
        # 1) intento con un servicio de otro tipo de equipo: debe rechazarse
        pg.click('[data-abrir-orden]')
        pg.select_option('dialog select[name=equipo]',label='V168')
        pg.select_option('dialog select[name=servicio_plan]',value='2')
        pg.select_option('dialog select[name=tipo]',index=1)
        pg.fill('dialog input[name=fecha_programada]',datetime.date.today().isoformat())
        pg.click('dialog button:has-text("Sí, crear")'); pg.wait_for_load_state()
        assert pg.locator('.errorlist').count()>0, 'no se rechazó el servicio de otro tipo'
        pg.screenshot(path=S+'m5_servicio_otro_tipo.png')
        # 2) intento correcto
        pg.goto(B+'/ordenes-trabajo/'); antes=pg.locator('tbody tr').count()
        pg.click('[data-abrir-orden]')
        pg.select_option('dialog select[name=equipo]',label='V168')
        pg.select_option('dialog select[name=servicio_plan]',value='6')
        pg.select_option('dialog select[name=tipo]',index=1)
        pg.fill('dialog input[name=fecha_programada]',datetime.date.today().isoformat())
        pg.click('dialog button:has-text("Sí, crear")'); pg.wait_for_load_state(); pg.goto(B+'/ordenes-trabajo/')
        despues=pg.locator('tbody tr').count(); assert despues==antes+1, f'{antes}->{despues}'
        pg.screenshot(path=S+'ordenes.png',full_page=True)
        # la OT nueva es la mas reciente programada hoy: abrir primera fila "Programada" con numero mas alto
        link=pg.locator('tbody tr').first.locator('a').first
        numero=link.inner_text().strip(); link.click(); pg.wait_for_load_state()
        pg.click('button:has-text("Marcar en curso")'); pg.wait_for_load_state()
        pg.goto(B+'/ordenes-trabajo/'); assert 'En curso' in pg.locator('tbody tr').first.inner_text(), 'no quedó en curso'
        pg.locator('tbody tr').first.locator('a').first.click(); pg.wait_for_load_state()
        pg.click('a:has-text("Registrar insumo")'); pg.wait_for_load_state()
        pg.select_option('select[name=insumo]',index=1); pg.fill('input[name=cantidad_usada]','2')
        pg.click('main form button[type=submit]'); pg.wait_for_load_state()
        pg.screenshot(path=S+'detalle_orden.png',full_page=True)
        pg.click('a:has-text("Cerrar OT")'); pg.wait_for_load_state()
        nums=[float(x.replace('.','').replace(',','.')) for x in re.findall(r'\d[\d.]*,\d',hor_txt)]
        cierre=(max(nums) if nums else 0)+25
        pg.fill('input[name=horometro_cierre]',str(cierre)); pg.click('main form button[type=submit]'); pg.wait_for_load_state()
        pg.goto(B+'/ordenes-trabajo/'); fila=pg.locator('tbody tr',has_text=numero).first
        assert 'Cerrada' in fila.inner_text(), 'no quedó cerrada: '+fila.inner_text()
        pg.goto(B+'/dashboard/'); dash_despues=pg.locator('tr',has_text='V168').first.inner_text()
        pg.screenshot(path=S+'dashboard_tras_ot.png',full_page=True)
        assert dash_antes!=dash_despues, 'el panel no cambió: '+' '.join(dash_antes.split())+' || '+' '.join(dash_despues.split())
        return f'{numero}: creada, iniciada, con 1 insumo y cerrada con horómetro {cierre}; el pronóstico de V168 en el panel cambió de «{" ".join(dash_antes.split())}» a «{" ".join(dash_despues.split())}».'
    caso('M5','Ciclo de OT',m5)

    def m6():
        pg.goto(B+'/dashboard/'); pg.click('#theme-toggle'); pg.reload()
        assert pg.evaluate("document.documentElement.getAttribute('data-theme')")=='dark'
        pg.screenshot(path=S+'tema_oscuro.png')
        pg.click('#theme-toggle'); pg.reload()
        assert pg.evaluate("document.documentElement.getAttribute('data-theme')") is None
        pg.goto(B+'/horometros/'); abrir(pg)
        pg.locator('details.celda-plegable > summary').first.click(); pg.reload()
        estado=pg.evaluate("[...document.querySelectorAll('details.celda-plegable')].map(d=>d.open)")
        assert estado[0] is False, estado
        pg.locator('details.celda-plegable > summary').first.click()
        return 'El tema oscuro y la celda plegada se mantienen tras recargar.'
    caso('M6','Tema y preferencias',m6)

    def m7():
        pg.goto(B+'/horometros/'); abrir(pg)
        sel=pg.locator('#selector-ventana'); opts=[o.get_attribute('value') for o in sel.locator('option').all()]
        cuentas={}
        for v in [opts[0],opts[-1]]:
            sel.select_option(v); pg.wait_for_load_state(); pg.wait_for_timeout(500); abrir(pg)
            cuentas[v]=pg.locator('[data-plegable=bandeja] tbody tr').count(); sel=pg.locator('#selector-ventana')
        assert cuentas[opts[0]]<=cuentas[opts[-1]], cuentas
        pg.screenshot(path=S+'m7_ventana.png',full_page=True)
        return f'Filas en la bandeja según ventana: {cuentas}.'
    caso('M7','Ventana de trazabilidad',m7)

    def m8():
        mv=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); q=mv.new_page(); login(q)
        malas=[]
        for path,nom in [('/dashboard/','dashboard'),('/horometros/','horometros'),('/arriendos/','arriendos'),('/ordenes-trabajo/','ordenes'),('/equipos/','equipos'),('/planes/','planes'),('/catalogos/','catalogos')]:
            q.goto(B+path); abrir(q)
            ov=q.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            q.screenshot(path=S+f'movil_{nom}.png',full_page=False)
            if ov>1: malas.append((nom,ov))
        mv.close()
        assert not malas, f'desborde horizontal de página: {malas}'
        return 'En 390 px de ancho ninguna de las 7 pantallas desborda horizontalmente; las tablas se desplazan dentro de su contenedor.'
    caso('M8','Pantalla angosta',m8)

    # capturas de escritorio del resto
    for path,nom in [('/equipos/','equipos'),('/planes/','planes'),('/catalogos/','catalogos'),('/arriendos/','arriendos')]:
        pg.goto(B+path); pg.screenshot(path=S+f'{nom}.png',full_page=True)
    with open('res.json','w') as f: json.dump(res,f,ensure_ascii=False,indent=1)
    b.close()
