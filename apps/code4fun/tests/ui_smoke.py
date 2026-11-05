"""Isolated real-browser and HTTP checks; never opens the user's workspace."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace'))
from server import Store, make_handler
from checks import check
from playwright.sync_api import sync_playwright

spec = importlib.util.spec_from_file_location('prepared_api', ROOT / 'api' / 'server.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def start(handler):
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    with tempfile.TemporaryDirectory() as directory:
        store = Store(directory)
        api_server = start(api.handler(api.Measurements()))
        api_url = f'http://127.0.0.1:{api_server.server_port}'
        preview = start(make_handler(store, True, api_url=api_url))
        server = start(make_handler(store, preview_port=preview.server_port))
        server.preview_internal_port = preview.server_port
        origin = f'http://127.0.0.1:{server.server_port}'
        preview_origin = f'http://127.0.0.1:{preview.server_port}'
        try:
            # Contract, same-origin proxy, and management boundary checks.
            for endpoint in ('info', 'username/', 'hostname/', 'ip', 'metrics', 'metrics/'):
                with urlopen(preview_origin + '/api/' + endpoint) as response:
                    assert response.headers['Cache-Control'] == 'no-store'
                    assert isinstance(json.load(response), dict)
            try:
                urlopen(Request(origin + '/code4fun/api/save', data=b'{}', headers={'Origin': preview_origin, 'Content-Type': 'application/json'}))
                raise AssertionError('Cross-origin management write was accepted')
            except HTTPError as error:
                assert error.code == 403
            try:
                urlopen(preview_origin + '/code4fun/api/project')
                raise AssertionError('Management state exposed on preview origin')
            except HTTPError as error:
                assert error.code == 404

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={'width': 1512, 'height': 1100})
                page.goto(origin)
                page.wait_for_function('() => document.querySelector("#save-status").textContent==="All changes saved"')
                page.locator('#code').fill('<h1>My dashboard</h1><p>My introduction.</p><section id="server-info"><h2>Server</h2></section>')
                page.get_by_role('button', name='Run preview', exact=False).click()
                page.frame_locator('#preview').get_by_role('heading', name='My dashboard').wait_for()
                page.get_by_role('button', name='Check my work').click()
                page.get_by_text('Checkpoint passed! Your progress is saved.', exact=True).wait_for(timeout=30000)
                assert '1 / 6' in page.locator('#progress-count').inner_text()
                page.get_by_role('button', name='Next stage').click()
                assert 'My dashboard' in page.locator('#code').input_value()
                page.get_by_role('button', name='Save project', exact=True).click()
                page.get_by_text('Project saved.', exact=True).wait_for()
                page.reload()
                page.wait_for_function('() => document.querySelector("#stage-number").textContent==="2 / 6"')
                assert 'My dashboard' in page.locator('#code').input_value()
                page.locator('#code').fill('<h1>A recovered draft</h1>')
                page.reload()
                page.get_by_role('button', name='Recover draft').click()
                assert 'A recovered draft' in page.locator('#code').input_value()
                page.get_by_role('button', name='Save project', exact=True).click()
                page.get_by_text('Project saved.', exact=True).wait_for()
                page.get_by_role('tab', name='style.css', exact=True).click()
                page.locator('#code').fill('body { background: #d8f1e5; }')
                page.get_by_role('button', name='Run preview', exact=False).click()
                page.frame_locator('#preview').get_by_role('heading', name='A recovered draft').wait_for()
                page.screenshot(path='/tmp/code4fun-desktop.png', full_page=True)
                frame = page.frame_locator('#preview').locator('body')
                assert frame.evaluate("() => {try {parent.document.body; return false;} catch (_) {return true;}}")
                assert frame.evaluate("async (element, origin) => {try {await fetch(origin+'/code4fun/api/project'); return false;} catch (_) {return true;}}", origin)
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path='/tmp/code4fun-mobile.png', full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                # An old browser draft must not silently overwrite a newer save.
                saved = store.read()
                newer_files = {**saved['files'], 'index.html': '<h1>A newer save</h1>'}
                store.save({**saved, 'files': newer_files})
                page.reload()
                page.get_by_role('button', name='Recover draft').click()
                page.get_by_role('button', name='Save project', exact=True).click()
                page.get_by_text('A newer save exists.', exact=False).wait_for()
                assert store.read()['files']['index.html'] == '<h1>A newer save</h1>'
                page.reload()
                page.get_by_role('button', name='Discard draft').click()
                page.on('dialog', lambda dialog: dialog.accept())
                page.get_by_role('button', name='Reset entire project').click()
                page.get_by_text('Project reset to its starting point.', exact=True).wait_for()
                assert store.read()['files'] == store.starter()
                assert not store.read()['completed']
                browser.close()

            # Real behavior checks accept a complete solution and reject empty work.
            files = {name: (ROOT / 'tests' / 'fixtures' / name).read_text() for name in store.starter()}
            token = store.snapshot(files)
            url = preview_origin + f'/preview/{token}/index.html'
            for stage in range(6):
                results = check(url, stage)
                assert results and all(item['passed'] for item in results), (stage, results)
            token = store.snapshot(store.starter())
            url = preview_origin + f'/preview/{token}/index.html'
            for stage in (0, 4):
                assert not all(item['passed'] for item in check(url, stage))
            # Hardcoded API sample values must fail when the mocked response changes.
            hardcoded = {**files, 'script.js': "document.querySelector('#hostname').textContent='learning-server-1';"}
            token = store.snapshot(hardcoded)
            assert not all(item['passed'] for item in check(preview_origin + f'/preview/{token}/index.html', 4))
            print('Code4Fun HTTP, workspace browser, six passing stages, and negative checks passed.')
        finally:
            for instance in (server, preview, api_server):
                instance.shutdown()
                instance.server_close()


if __name__ == '__main__':
    main()
