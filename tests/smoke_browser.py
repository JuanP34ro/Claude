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
                context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=mobile, has_touch=mobile)
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
                page.wait_for_function("window.OrellanaAtlas && window.OrellanaAtlas.version === '0.4'")
                page.locator('#tutorial').wait_for(state='visible')
                assert page.locator('#tutorial .tut-page.active').count() == 1, 'Tutorial did not open on first run'
                page.locator('#tutNext').click()
                page.wait_for_timeout(900)
                assert page.locator('#tutorial .tut-page.active').count() == 1
                page.locator('#tutSkip').click()
                assert page.evaluate('window.OrellanaAtlas.getState().settings.tutorialSeen'), 'Tutorial not marked as seen'
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow'
                assert page.locator('link[rel="apple-touch-icon"]').get_attribute('href') == 'apple-touch-icon.png'
                if mobile:
                    page.locator('#openSidebar').click()
                page.locator('[data-tab="points"]').click()
                page.locator('#addPointPanel').click()
                page.locator('#map').click(position={'x': 140, 'y': 370})
                page.locator('#pointDialog').wait_for(state='visible')
                page.locator('#pointName').fill('Prueba automatizada (no dato real)')
                page.locator('#pointForm button[type="submit"]').click()
                assert page.evaluate('window.OrellanaAtlas.getState().features.length') == 1
                page.reload(wait_until='domcontentloaded')
                page.wait_for_function('window.OrellanaAtlas')
                assert page.evaluate('window.OrellanaAtlas.getState().features.length') == 1, 'Storage was not restored'
                page.locator('#helpBtn').click()
                page.locator('#helpDialog').wait_for(state='visible')
                page.locator('#helpDialog .primary.close-dialog').click()
                if mobile:
                    page.locator('#openSidebar').click()
                page.locator('[data-tab="settings"]').click()
                with page.expect_download() as download:
                    page.locator('#backupBtn').click()
                assert download.value.suggested_filename.endswith('.json')
                assert not errors, errors
                print(f'PASS {name}: startup, tutorial, no overflow, point form, save/reload, help, export; maps unavailable by design')
                context.close()
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)

if __name__ == '__main__':
    main()
