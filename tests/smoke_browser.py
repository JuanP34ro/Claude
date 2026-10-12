"""Optional browser smoke test. Needs Playwright + Chromium, not app dependencies.
Map responses are intentionally failed: this is NOT a map-coverage verification.
Usage: python tests/smoke_browser.py
"""
from pathlib import Path
import shutil
import sys
import threading
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Handler
from playwright.sync_api import sync_playwright

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
                page.locator('[data-go="diary"]').click()
                page.locator('#addCatch').click()
                page.locator('#catchDialog').wait_for(state='visible')
                for key in ['1', '2', ',', '5']:
                    page.locator(f'#catchKeypad [data-key="{key}"]').click()
                page.locator('#catchSave').click()
                catch = page.evaluate('window.OrellanaAtlas.getState().catches[0]')
                assert catch['weightKg'] == 12.5 and catch['outcome'] == 'catch', catch
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
                print(f'PASS {name}: startup, catalogue scale limits, tutorial, no overflow, paths badge off, tabs, point form, save/reload, GPS follow, WCC 2026 peg search and zone from GPS, quick catch, learning notebook, rod alarm colour, contextual help, export, offline reopen; maps unavailable by design')
                context.close()
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)

if __name__ == '__main__':
    main()
