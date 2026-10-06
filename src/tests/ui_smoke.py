"""Real-browser regression checks. Uses an isolated temporary workspace.

Run: PLAYWRIGHT_BROWSERS_PATH=.venv/browsers .venv/bin/python src/tests/ui_smoke.py
"""
import argparse
import os
from http.server import HTTPServer
from pathlib import Path
import shutil
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT.parent / '.venv/browsers'))
sys.path.insert(0, str(ROOT / 'application'))
from core import registry
from server import make_handler
from storage import Workspace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', default='/tmp/build4fun-ui')
    args = parser.parse_args()
    artifacts = Path(args.artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Workspace(temporary)
        shutil.copy(ROOT / 'tests/fixtures/homelab/project.yaml', Path(temporary) / 'project.yaml')
        workspace.write('nginx/nginx.conf', 'invalid directive deliberately left untouched\n', create=True)
        workspace.write('nginx/index.html', '<h1>Hello</h1>\n', create=True)
        server = HTTPServer(('127.0.0.1', 0), make_handler(workspace, registry(ROOT / 'templates')))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        errors = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={'width': 1440, 'height': 1050}, device_scale_factor=1)
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.get_by_role('heading', name='Build environment')).to_be_visible()
                expect(page.locator('.service-card')).to_have_count(0)
                expect(page.get_by_role('heading', name='No services yet')).to_be_visible()
                expect(page.locator('#detail-pane')).not_to_contain_text('nginx:latest')
                page.get_by_role('button', name='Open saved project', exact=True).click()
                expect(page.locator('.service-card')).to_have_count(1)
                expect(page.locator('#content input')).to_have_count(0)
                page.screenshot(path=str(artifacts / 'builder.png'), full_page=True, animations="disabled")
                expect(page.locator('#sidebar-content').get_by_role('button', name='nginx.conf', exact=True)).to_be_visible()
                expect(page.locator('#workspace-navigation').get_by_role('button')).to_have_count(2)
                expect(page.locator('#detail-pane')).to_be_visible()
                page.get_by_role('button', name='Hide YAML', exact=True).click()
                expect(page.locator('#detail-pane')).to_be_hidden()
                page.get_by_role('button', name='Show YAML', exact=True).click()
                expect(page.locator('#detail-pane')).to_be_visible()
                explorer = page.locator('#navigation').bounding_box()
                builder = page.locator('#content').bounding_box()
                preview = page.locator('#detail-pane').bounding_box()
                assert explorer['x'] < builder['x'] < preview['x']
                assert builder['width'] > preview['width']
                expect(page.locator('.code-body')).to_contain_text('nginx:latest')
                page.get_by_role('button', name='Inspect Image', exact=True).click()
                expect(page.locator('.code-line.highlight')).to_have_count(1)
                page.screenshot(path=str(artifacts / 'split.png'), full_page=True, animations="disabled")
                page.locator('.code-line').filter(has_text='nginx:latest').click()
                expect(page.get_by_role('button', name='Inspect Image', exact=True).locator('..')).to_have_class('config-row is-selected')

                # Editing is contextual; invalid ports are reported beside the input.
                page.get_by_role('button', name='Expand Ports', exact=True).click()
                page.get_by_role('button', name='Edit Port mapping', exact=True).click()
                port = page.get_by_label('Host port', exact=True)
                expect(port).to_be_focused()
                port.fill('99999')
                page.get_by_label('Container port', exact=True).focus()
                expect(page.get_by_text('Host port must be between 1 and 65535.', exact=True)).to_be_visible()
                port.fill('8081')
                page.get_by_label('Protocol', exact=True).select_option('')
                expect(page.locator('#detail-pane .code-body')).to_contain_text('\"8081:80\"')
                expect(page.locator('#detail-pane .code-body')).to_contain_text('8081')
                page.get_by_role('button', name='Validate', exact=True).click()
                expect(page.locator('#validation-status')).to_have_text('✓ Configuration checked')
                page.screenshot(path=str(artifacts / 'inspector.png'), full_page=True, animations="disabled")
                page.get_by_role('button', name='Close inspector', exact=True).click()

                # Project networks configure IPAM; shared networks are external only.
                page.get_by_role('button', name='Add resource', exact=True).click()
                expect(page.get_by_role('menuitem', name='External network', exact=True)).to_be_visible()
                expect(page.get_by_role('menuitem', name='Project network', exact=True)).to_have_count(0)
                page.keyboard.press('Escape')
                page.get_by_role('button', name='Edit Project network', exact=True).click()
                page.get_by_label('IPv4 subnet (optional)', exact=True).fill('172.25.0.0/24')
                page.get_by_label('IPv4 gateway (optional)', exact=True).fill('172.25.0.1')
                page.get_by_role('button', name='Close inspector', exact=True).click()
                page.get_by_role('button', name='Expand Network configuration', exact=True).click()
                page.get_by_role('button', name='Edit Network attachment', exact=True).click()
                address = page.get_by_label('Static IPv4 address (optional)', exact=True)
                expect(address).to_have_value('')
                address.fill('172.25.0.10')
                expect(page.locator('#detail-pane .code-body')).to_contain_text('ipv4_address: 172.25.0.10')
                page.get_by_role('button', name='Validate', exact=True).click()
                expect(page.locator('#validation-status')).to_have_text('✓ Configuration checked')
                expect(page.locator('#detail-pane .code-body')).to_contain_text('ipv4_address: 172.25.0.10')
                expect(page.locator('#detail-pane .code-body')).to_contain_text('subnet: 172.25.0.0/24')
                page.get_by_role('button', name='Close inspector', exact=True).click()

                # Keyboard-operated contextual add menu and service creation.
                page.get_by_role('button', name='Add service', exact=True).click()
                dialog = page.locator('#form-dialog')
                info = dialog.get_by_role('button', name='About Service name', exact=True)
                info.hover()
                expect(dialog.get_by_role('tooltip')).to_contain_text('demo-web-1')
                info.focus()
                page.keyboard.press('Escape')
                expect(dialog.get_by_role('tooltip')).to_have_count(0)
                expect(dialog).to_be_visible()
                info.click()
                expect(dialog.get_by_role('tooltip')).to_contain_text('demo-web-1')
                page.keyboard.press('Escape')
                dialog.get_by_label('Service name', exact=True).fill('redis')
                dialog.get_by_label('Image reference', exact=True).fill('redis:alpine')
                dialog.get_by_role('button', name='Create service', exact=True).click()
                expect(page.locator('.service-card')).to_have_count(2)
                redis = page.locator('.service-card').filter(has=page.get_by_role('button', name='redis Service', exact=True))
                redis.get_by_role('button', name='Add configuration', exact=True).click()
                page.get_by_role('searchbox', name='Find a block').fill('Environment')
                page.keyboard.press('ArrowDown')
                page.keyboard.press('Enter')
                expect(dialog).to_be_visible()
                dialog.get_by_label('Variable name', exact=True).fill('EXAMPLE')
                dialog.get_by_label('Value', exact=True).fill('literal: $VALUE')
                dialog.get_by_role('button', name='Add block', exact=True).click()
                expect(redis).to_contain_text('EXAMPLE = literal: $VALUE')

                # Drag an existing group to another service, then undo the move.
                nginx = page.locator('.service-card').filter(has=page.get_by_role('button', name='nginx Service', exact=True))
                nginx.get_by_role('button', name='Inspect Ports', exact=True).drag_to(redis.locator('.service-header'))
                expect(redis.get_by_role('button', name='Inspect Ports', exact=True)).to_be_visible()
                expect(nginx.get_by_role('button', name='Inspect Ports', exact=True)).to_have_count(0)
                page.get_by_role('button', name='Undo last project change', exact=True).click()
                expect(nginx.get_by_role('button', name='Inspect Ports', exact=True)).to_be_visible()

                # Delete and undo preserve an entire subtree.
                page.get_by_role('button', name='Actions for redis', exact=True).click()
                page.get_by_role('menuitem', name='Delete block', exact=True).click()
                expect(page.locator('.service-card')).to_have_count(1)
                page.get_by_role('button', name='Undo last project change', exact=True).click()
                expect(page.locator('.service-card')).to_have_count(2)

                # File drafts survive navigation, and invalid service contents are accepted.
                page.locator('#sidebar-content').get_by_role('button', name='nginx.conf', exact=True).click()
                expect(page.locator('#detail-pane')).to_be_visible()
                editor = page.get_by_role('textbox', name='Edit nginx/nginx.conf', exact=True)
                editor.fill('not valid nginx syntax\nkeep this unchanged\n')
                page.locator('#sidebar-content').get_by_role('button', name='index.html', exact=True).click()
                page.locator('#sidebar-content').get_by_role('button', name='nginx.conf', exact=True).click()
                expect(editor).to_have_value('not valid nginx syntax\nkeep this unchanged\n')
                page.get_by_role('button', name='Save all', exact=True).click()
                expect(page.locator('#save-status')).to_have_text('All changes saved')
                assert workspace.read('nginx/nginx.conf') == 'not valid nginx syntax\nkeep this unchanged\n'
                page.reload()
                expect(page.locator('.service-card')).to_have_count(0)
                page.get_by_role('button', name='Open saved project', exact=True).click()
                expect(page.locator('.service-card')).to_have_count(2)

                # File creation uses a dialog and preserves arbitrary file contents.
                page.locator('#workspace-navigation').get_by_role('button', name='Files').click()
                page.get_by_role('button', name='New file', exact=True).click()
                dialog.get_by_label('Project path', exact=True).fill('config/example.conf')
                dialog.get_by_role('button', name='Create', exact=True).click()
                expect(page.get_by_role('textbox', name='Edit config/example.conf')).to_be_visible()
                page.locator('#workspace-navigation').get_by_role('button', name='Build', exact=True).click()

                # Explorer deletion: keyboard, cancellation, overflow, and recursive folders.
                explorer = page.locator('#sidebar-content')
                explorer.get_by_role('button', name='example.conf', exact=True).click()
                page.get_by_role('textbox', name='Edit config/example.conf').fill('unsaved draft')
                row = explorer.get_by_role('button', name='example.conf', exact=True)
                row.focus()
                page.keyboard.press('Delete')
                expect(dialog).to_contain_text('1 file has unsaved changes')
                dialog.get_by_role('button', name='Cancel', exact=True).click()
                assert workspace.path('config/example.conf').exists()
                row.hover()
                explorer.get_by_role('button', name='File actions for config/example.conf', exact=True).click()
                page.get_by_role('menuitem', name='Delete', exact=True).click()
                dialog.get_by_role('button', name='Delete permanently', exact=True).click()
                expect(explorer.get_by_role('button', name='example.conf', exact=True)).to_have_count(0)
                expect(page.get_by_role('textbox', name='Edit config/example.conf')).to_have_count(0)
                assert not workspace.path('config/example.conf').exists()
                explorer.get_by_role('button', name='nginx.conf', exact=True).click()
                page.get_by_role('textbox', name='Edit nginx/nginx.conf').fill('another unsaved draft')
                explorer.get_by_role('button', name='nginx', exact=True).click(button='right')
                page.get_by_role('menuitem', name='Delete', exact=True).click()
                expect(dialog).to_contain_text('and all of its contents')
                expect(dialog).to_contain_text('1 file has unsaved changes')
                dialog.get_by_role('button', name='Delete permanently', exact=True).click()
                expect(explorer.get_by_role('button', name='nginx', exact=True)).to_have_count(0)
                page.keyboard.press('ControlOrMeta+s')
                expect(page.locator('#save-status')).to_have_text('All changes saved')
                assert not workspace.path('nginx').exists()
                page.reload()
                expect(page.locator('.service-card')).to_have_count(0)
                page.get_by_role('button', name='Open saved project', exact=True).click()
                expect(page.locator('.service-card')).to_have_count(2)
                expect(explorer.get_by_role('button', name='nginx', exact=True)).to_have_count(0)

                # Responsive layout and dark appearance.
                page.emulate_media(color_scheme='dark')
                page.screenshot(path=str(artifacts / 'dark.png'), full_page=True, animations="disabled")
                page.set_viewport_size({'width': 390, 'height': 844})
                expect(page.get_by_role('heading', name='Build environment')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.get_by_role('button', name='Toggle navigation', exact=True).click()
                expect(page.locator('#navigation')).to_be_visible()
                page.locator('#workspace-navigation').get_by_role('button', name='Build', exact=True).click()
                page.get_by_role('button', name='YAML', exact=True).click()
                expect(page.locator('#workspace-navigation').get_by_role('button', name='Build', exact=True, include_hidden=True)).to_have_attribute('aria-current', 'page')
                expect(page.locator('.code-body')).to_contain_text('redis:alpine')
                page.screenshot(path=str(artifacts / 'mobile.png'), full_page=True, animations="disabled")
                # Blank projects stay blank; no example or prefab is inserted.
                response = page.request.post(f'http://127.0.0.1:{server.server_port}/api/project', data={'project': {'id': 'root', 'type': 'harness', 'version': 1, 'values': {}, 'children': []}})
                assert response.ok
                page.set_viewport_size({'width': 1440, 'height': 1050})
                page.emulate_media(color_scheme='light')
                page.reload()
                expect(page.get_by_role('heading', name='No services yet')).to_be_visible()
                page.screenshot(path=str(artifacts / 'empty.png'), full_page=True, animations='disabled')
                page.get_by_role('button', name='Set project name', exact=True).click()
                dialog.get_by_label('Name', exact=True).fill('learning')
                dialog.get_by_role('button', name='Add block', exact=True).click()
                page.get_by_role('button', name='Add service', exact=True).click()
                expect(dialog.get_by_label('Service name', exact=True)).to_have_value('')
                expect(dialog.get_by_label('Image reference', exact=True)).to_have_value('')
                dialog.get_by_label('Service name', exact=True).fill('worker')
                dialog.get_by_label('Image reference', exact=True).fill('busybox:latest')
                dialog.get_by_role('button', name='Create service', exact=True).click()
                page.get_by_role('button', name='Validate', exact=True).click()
                expect(page.locator('#validation-status')).to_have_text('✓ Configuration checked')
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
        print(f'Browser checks passed. Screenshots: {artifacts}')


if __name__ == '__main__':
    main()
