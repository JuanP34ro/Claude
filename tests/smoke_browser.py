"""Optional browser smoke test. Needs Playwright + Chromium, not app dependencies.
Map responses are intentionally failed: this is NOT a map-coverage verification.
Usage: python tests/smoke_browser.py
"""
from pathlib import Path
import shutil
import struct
import sys
import threading
import zlib
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler
from playwright.sync_api import sync_playwright

def tiny_png(w=640, h=480, rgb=(120, 90, 40)):
    """A flat PNG, used as a catch photo (no real photo is ever stored in the repo)."""
    raw = b''.join(b'\x00' + bytes(rgb) * w for _ in range(h))
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

def wcc_inside(sec, n):
    """Vertex average of a closed WCC 2026 zone, used as a simulated GPS fix inside it."""
    import json
    text = (Path(__file__).resolve().parents[1] / 'wcc2026.js').read_text(encoding='utf-8')
    data = json.loads(text[text.index('{'):text.rindex('}') + 1])
    i = next(k for k, p in enumerate(data['pegs']) if data['secs'][p[0]][0] == sec and p[1] == n)
    zone = data['zones'][i]
    return [sum(c[0] for c in zone) / len(zone), sum(c[1] for c in zone) / len(zone)]

class QuietHandler(Handler):
    def log_message(self, *args):
        pass

def team_check(browser, base):
    """Two phones share positions through the local server (in-memory relay): create, join, see each other, stop."""
    geo = {'boat': {'latitude': 39.0064, 'longitude': -5.4068, 'accuracy': 6}, 'bank': {'latitude': 39.0039, 'longitude': -5.4089, 'accuracy': 5}}
    phones, errors = {}, []
    for who in geo:
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, geolocation=geo[who], permissions=['geolocation'])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: dialog.accept())   # «¿Dejar de compartir?»
        page.route('**/*', lambda route: route.fulfill(status=503, body='offline test') if '/api/wms' in route.request.url
                   else (route.continue_() if route.request.url.startswith(base) else route.abort()))
        page.goto(base, wait_until='domcontentloaded')
        page.wait_for_function('window.OrellanaAtlas')
        page.locator('#tutSkip').click()
        phones[who] = (context, page)
    boat, bank = phones['boat'][1], phones['bank'][1]
    members = 'p => window.OrellanaAtlas.team() && window.OrellanaAtlas.team().members.length === p'
    boat.locator('#fabBtn').click()
    boat.locator('#teamBtn').click()
    boat.locator('#teamName').fill('Barca')
    boat.locator('#teamCreate').click()
    code = boat.locator('#teamCodeOut').inner_text()
    assert len(code) == 9 and code[4] == '-', code
    boat.locator('#teamDialog .close-dialog').first.click()
    bank.locator('#fabBtn').click()
    bank.locator('#teamBtn').click()
    bank.locator('#teamName').fill('Orilla')
    bank.locator('#teamCodeIn').fill(code)
    bank.locator('#teamJoin').click()
    bank.wait_for_function(members, arg=1, timeout=15000)
    assert bank.evaluate('window.OrellanaAtlas.team().members[0].name') == 'Barca'
    boat.wait_for_function(members, arg=1, timeout=15000)
    boat.locator('#teamBadge').click()
    boat.locator('#teamStop').click()
    assert boat.evaluate('window.OrellanaAtlas.team()') is None, 'Sharing did not stop'
    bank.wait_for_function(members, arg=0, timeout=20000)
    assert not errors, errors
    for context, _ in phones.values():
        context.close()
    print('PASS team: two phones share positions through the relay, see each other and stop')

def main():
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{httpd.server_port}'
    try:
        with sync_playwright() as pw:
            options = {'headless': True}
            chromium = shutil.which('chromium')
            if chromium:
                options['executable_path'] = chromium
            browser = pw.chromium.launch(**options)
            for name, width, height, mobile in [('mobile', 430, 932, True), ('desktop', 1280, 800, False)]:
                context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=mobile, has_touch=mobile,
                                              geolocation={'latitude': 39.046, 'longitude': -5.444, 'accuracy': 8}, permissions=['geolocation'])
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                def routing(route):
                    url = route.request.url
                    if '/api/wms?' in url:
                        return route.fulfill(status=503, content_type='application/json', body='{"error":"Deliberate offline test"}')
                    if not url.startswith(base):
                        return route.abort()
                    return route.continue_()
                page.route('**/*', routing)
                page.goto(base, wait_until='domcontentloaded')
                page.wait_for_function("window.OrellanaAtlas && window.OrellanaAtlas.version === '0.6'")
                caps = ('<?xml version="1.0"?><WMS_Capabilities version="1.3.0" xmlns="http://www.opengis.net/wms"><Capability><Layer><CRS>EPSG:3857</CRS>'
                        '<Layer><Name>grupo</Name><Title>G</Title><MaxScaleDenominator>50000</MaxScaleDenominator><Layer><Name>a</Name><Title>A</Title><MaxScaleDenominator>80000</MaxScaleDenominator></Layer><Layer><Name>b</Name><Title>B</Title></Layer></Layer>'
                        '<Layer><Name>libre</Name><Title>L</Title><Layer><Name>c</Name><Title>C</Title><MinScaleDenominator>1000</MinScaleDenominator></Layer><Layer><Name>d</Name><Title>D</Title></Layer></Layer></Layer></Capability></WMS_Capabilities>')
                layers = {l['name']: l for l in page.evaluate('x => window.OrellanaAtlas.parseCapabilities(x).layers', caps)}
                assert layers['a']['maxScale'] == 80000 and layers['b']['maxScale'] == 50000 and layers['grupo']['maxScale'] == 80000, layers
                assert layers['c']['minScale'] == 1000 and layers['libre']['minScale'] is None and layers['libre']['maxScale'] is None, layers
                page.locator('#tutorial').wait_for(state='visible')
                assert page.locator('#tutorial .tut-page.active').count() == 1, 'Tutorial did not open on first run'
                page.locator('#tutNext').click()
                page.wait_for_timeout(900)
                assert page.locator('#tutorial .tut-page.active').count() == 1
                page.locator('#tutSkip').click()
                assert page.evaluate('window.OrellanaAtlas.getState().settings.tutorialSeen'), 'Tutorial not marked as seen'
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow'
                assert page.locator('#roadsBadge').is_hidden(), 'Paths badge shown while the paths layer is off'
                assert page.locator('link[rel="apple-touch-icon"]').get_attribute('href') == 'apple-touch-icon.png'
                page.locator('[data-go="spots"]').click()
                assert page.evaluate('window.OrellanaAtlas.getScreen()') == 'spots', 'Spots tab did not open'
                page.locator('#addPointPanel').click()
                page.locator('#map').click(position={'x': 140, 'y': 370})
                page.locator('#pointDialog').wait_for(state='visible')
                page.locator('#pointName').fill('Prueba automatizada (no dato real)')
                page.locator('#pointForm button[type="submit"]').click()
                assert page.evaluate('window.OrellanaAtlas.getState().features.length') == 1
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('window.OrellanaAtlas')
                assert page.evaluate('window.OrellanaAtlas.getState().features.length') == 1, 'Storage was not restored'
                page.locator('[data-go="map"]').click()
                page.locator('#locateBtn').click()
                page.wait_for_function('window.OrellanaAtlas.getGps() && window.OrellanaAtlas.getGps().follow', timeout=10000)
                assert page.locator('#gpsBadge').is_visible() and 'Parado' in page.locator('#gpsMain').inner_text(), 'GPS badge missing'
                page.locator('#locateBtn').click()
                assert page.evaluate('window.OrellanaAtlas.getGps()') is None, 'GPS did not stop'
                # WCC 2026 (capa temporal del concurso): búsqueda, ficha, «Es mi puesto» y zona desde el GPS.
                page.locator('#layersPill').click()
                page.locator('#wccEnabled').check()
                page.locator('#wccSec').select_option(label='Meus')
                page.locator('#wccNum').fill('8')
                page.locator('#wccFind button[type="submit"]').click()
                page.locator('#wccSheet').wait_for(state='visible')
                assert page.locator('#wccTitle').inner_text() == 'Meus 8', 'WCC peg sheet did not open'
                page.locator('#wccMineBtn').click()
                assert page.evaluate('window.OrellanaAtlas.wcc().mine') == 'MEU-8', 'WCC peg not marked as mine'
                page.locator('#wccClose').click()
                inside = wcc_inside('Meus', 8)
                assert page.evaluate('c => window.OrellanaAtlas.wccZoneAt(c).peg', inside) == 'Meus 8'
                context.set_geolocation({'latitude': inside[1], 'longitude': inside[0], 'accuracy': 6})
                page.locator('#locateBtn').click()
                page.wait_for_function("document.getElementById('gpsWcc').textContent.startsWith('Dentro de tu zona')", timeout=10000)
                page.locator('#locateBtn').click()
                if page.locator('#traceDialog').is_visible():
                    page.keyboard.press('Escape')
                assert page.evaluate('window.OrellanaAtlas.getGps()') is None, 'GPS did not stop after the WCC check'
                # Dónde poner las cañas: a synthetic weather history (wind veering W→NE 4 h ago, a day 9 °C colder than yesterday, overcast, rain, falling pressure)
                page.evaluate('''() => { const H = 36e5, now = Date.now(), start = Math.floor((now - 72 * H) / H) * H, d0 = new Date(now).setHours(0, 0, 0, 0);
                    const w = {fetchedAt: now, place: [-5.41, 39.01], t: [], p: [], temp: [], wind: [], dir: [], gust: [], cloud: [], rain: []};
                    for (let i = 0; i < 7 * 24; i++) { const x = start + i * H, day = Math.floor((x - d0) / 864e5), hr = new Date(x).getHours(), ne = x >= now - 4 * H;
                        w.t.push(x); w.p.push(1015 - 0.5 * i); w.temp.push((day === -1 ? 30 : day === 0 ? 21 : 24) - 6 * Math.min(1, Math.abs(hr - 15) / 9));
                        w.wind.push(ne ? 20 : 15); w.dir.push(ne ? 45 : 270); w.gust.push(ne ? 30 : 22); w.cloud.push(90); w.rain.push(x > now - 2 * H && x <= now ? 2 : 0); }
                    localStorage.setItem('orellana-atlas-weather', JSON.stringify(w)); }''')
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('window.OrellanaAtlas')
                page.locator('[data-go="weather"]').click()
                heads = page.evaluate("[...document.querySelectorAll('#wxRead .wx-line > b')].map(b => b.textContent)")
                assert heads[0] == 'Sin temperatura del agua' and 'El viento ha rolado de O a NE' in heads and any(h.startswith('Viento NE') for h in heads), heads
                assert 'La máxima cae 9 °C respecto a ayer' in heads and 'Cielo cubierto' in heads and any(h.startswith('Lluvia: 4 mm') for h in heads) and any(h.startswith('Presión bajando') for h in heads), heads
                assert page.evaluate("document.querySelectorAll('#wxRead .tag-sci, #wxRead .tag-con').length") >= 6, 'evidence tags missing'
                page.locator('#waterIn').fill('19,5')
                page.locator('#waterForm button[type="submit"]').click()
                assert page.evaluate('window.OrellanaAtlas.getState().water')[0]['c'] == 19.5
                assert page.locator('#wxRead .wx-line > b').first.inner_text().startswith('Agua 19,5 °C'), 'water line not shown'
                page.locator('#waterIn').fill('x')
                page.locator('#waterForm button[type="submit"]').click()
                assert len(page.evaluate('window.OrellanaAtlas.getState().water')) == 1, 'invalid water temperature accepted'
                page.locator('[data-go="diary"]').click()
                page.locator('#addCatch').click()
                page.locator('#catchDialog').wait_for(state='visible')
                for key in ['1', '2', ',', '5']:
                    page.locator(f'#catchKeypad [data-key="{key}"]').click()
                page.locator('#catchSave').click()
                catch = page.evaluate('window.OrellanaAtlas.getState().catches[0]')
                assert catch['weightKg'] == 12.5 and catch['outcome'] == 'catch' and catch['cond'].get('water') == 19.5, catch
                events = page.evaluate('window.OrellanaAtlas.getState().events')
                assert [e['kind'] for e in events][-1:] == ['catch'] and events[-1]['kg'] == 12.5, events
                assert page.locator('#timelineList li').count() >= 1 and page.locator('#exportTimeline').is_visible(), 'Timeline not rendered'
                # WCC 2026 programme: countdown card in Diario, the same model at fixed times, the agenda dialog and a venue on the map
                model = page.evaluate('window.OrellanaAtlas.wccProg()')
                if model:
                    assert page.locator('#wccProg').is_visible() and page.locator('#wccProgMain').inner_text() == model['main'], model
                else:
                    assert page.locator('#wccProg').is_hidden(), 'programme card shown after the contest'
                at = lambda iso: page.evaluate('t => window.OrellanaAtlas.wccProg(Date.parse(t))', iso)
                before, during, after = at('2026-10-19T13:00:00+02:00'), at('2026-10-22T18:48:00+02:00'), at('2026-10-24T09:00:00+02:00')
                assert before['main'] == 'La pesca empieza en 1 h' and before['next']['title'].startswith('Actualización'), before
                assert during['main'] == 'Quedan 1 d 13 h de pesca' and during['next']['title'].startswith('Ceremonia de clausura'), during
                assert after['phase'] == 'after' and after['next']['when'] == 'hoy, 15:00', after
                assert at('2026-10-17T10:00:00+02:00')['cur'] == {'title': 'Inscripción', 'until': '17:00'}
                assert at('2026-10-26T12:00:00+02:00') is None, 'the programme must go quiet after the contest'
                page.locator('#wccProg').evaluate('b => { b.hidden = false; b.click(); }')
                page.locator('#wccProgDialog').wait_for(state='visible')
                assert page.locator('#wccProgList .wcc-ev').count() == 12 and page.locator('#wccProgSource a[href^="https://www.worldcarpclassic.com/"]').count() == 1
                page.locator('#wccProgList [data-wcc-venue="Opening and Closing ceremony"]').first.click()
                page.locator('#wccSheet').wait_for(state='visible')
                assert page.locator('#wccTitle').inner_text() == 'Opening and Closing ceremony' and page.evaluate('window.OrellanaAtlas.getScreen()') == 'map'
                page.locator('#wccClose').click()
                page.locator('[data-go="diary"]').click()
                # a photo on the catch: reduced, stored in IndexedDB, shown in the Diario card
                page.locator('[data-catch-edit]').first.click()
                page.locator('#catchDialog').wait_for(state='visible')
                page.locator('#catchPhotoIn').set_input_files({'name': 'carpa.png', 'mimeType': 'image/png', 'buffer': tiny_png()})
                page.wait_for_function("!document.getElementById('catchPhotoPrev').hidden", timeout=10000)
                page.locator('#catchSave').click()
                page.wait_for_function('window.OrellanaAtlas.photoCount().then(n => n === 1)', timeout=10000)
                page.wait_for_selector('#catchesList img.catch-photo:not([hidden])', timeout=10000)
                page.locator('#openNotebook').click()
                page.locator('#notebook').wait_for(state='visible')
                assert page.locator('#notebook .nb-key').count() >= 5, 'Learning notebook has no keys'
                assert page.evaluate("[...document.querySelectorAll('#notebook .nb-key')].every(k=>k.querySelector('.nb-stamp')&&k.querySelector('.nb-src a[href^=\"https://\"]'))"), 'A notebook key lacks its stamp or sources'
                assert page.evaluate('document.getElementById("nbScroll").scrollWidth <= document.getElementById("nbScroll").clientWidth'), 'Notebook overflows horizontally'
                page.locator('#notebook .nb-close').click()
                page.locator('[data-go="rods"]').click()
                page.locator('#rodsAdd').click()
                page.locator('#rodDialog').wait_for(state='visible')
                assert page.evaluate("document.querySelector('#rodAlarm .active').dataset.alarm") == 'verde', 'First rod alarm is not green'
                page.locator('#rodForm button[type="submit"]').click()
                assert page.evaluate('window.OrellanaAtlas.getState().rods[0].alarm') == 'verde'
                page.locator('#helpBtn').click()
                page.locator('#tutorial').wait_for(state='visible')
                page.locator('#tutSkip').click()
                page.locator('#moreBtn').click()
                page.locator('#sourcesBtn').click()
                page.locator('#helpDialog').wait_for(state='visible')
                page.locator('#helpDialog .primary.close-dialog').click()
                with page.expect_download() as download:
                    page.locator('#backupBtn').click()
                assert download.value.suggested_filename.endswith('.json')
                page.evaluate('navigator.serviceWorker.ready.then(() => true)')
                page.wait_for_timeout(800)
                context.set_offline(True)
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('window.OrellanaAtlas', timeout=10000)
                context.set_offline(False)
                assert not errors, errors
                print(f'PASS {name}: startup, catalogue scale limits, tutorial, no overflow, paths badge off, tabs, point form, save/reload, GPS follow, WCC 2026 peg search, zone from GPS and programme countdown, weather reading and water temperature, quick catch, session timeline, catch photo, learning notebook, rod alarm colour, contextual help, export, offline reopen; maps unavailable by design')
                context.close()
            team_check(browser, base)
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)

if __name__ == '__main__':
    main()
