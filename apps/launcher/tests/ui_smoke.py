"""Browser action wiring, source selection, logs and responsive layout; no real apps stopped."""
import copy
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import APPS
from server import handler
from playwright.sync_api import sync_playwright, expect


class Fixture:
    def __init__(self):
        self.calls=[];self.state={'docker':None,'registry':'ghcr.io/rayleeigh/educate4fun','jobs':{},'settings':{},'apps':[{**{k:item[k] for k in ('title','description','accent','port')},'id':app,'status':'stopped'} for app,item in APPS.items()]}
    def snapshot(self):return copy.deepcopy(self.state)
    def launch(self,app,action,source,tag,architecture):
        self.calls.append((app,action,source,tag,architecture))
        job={'running':False,'exit_code':0,'action':action,'source':source,'tag':tag,'log': 'Pulled image.\nReady.\n' if source=='registry' else 'Built image.\nReady.\n'}
        self.state['jobs'][app]=job
        next(a for a in self.state['apps'] if a['id']==app)['status']='running' if action=='start' else 'stopped'
        return job


def main():
    fixture=Fixture();server=ThreadingHTTPServer(('127.0.0.1',0),handler(fixture,0));server.RequestHandlerClass=handler(fixture,server.server_port)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            expect(page.get_by_role('heading',name='What will you discover?')).to_be_visible()
            expect(page.locator('article')).to_have_count(3)
            code=page.locator('.code4fun');expect(code.get_by_role('button',name='Start',exact=True)).to_be_disabled();code.get_by_role('button',name='About CPU architectures').click();expect(page.get_by_role('heading',name='Choose your architecture')).to_be_visible();page.keyboard.press('Escape');code.get_by_label('Architecture',exact=True).select_option('arm64');code.get_by_label('Launch from').select_option('registry');code.get_by_label('Image tag').fill('v1.2.3')
            code.get_by_role('button',name='Start',exact=True).click();expect(page.locator('#logs')).to_be_visible()
            expect(page.locator('#log-output')).to_contain_text('Pulled image.')
            page.get_by_role('button',name='Close activity',exact=True).click();expect(code.get_by_role('link',name='Open app')).to_be_visible()
            assert fixture.calls[-1]==('code4fun','start','registry','v1.2.3','arm64')
            code.get_by_role('button',name='Stop',exact=True).click();expect(page.locator('#logs')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#logs')).not_to_be_visible();expect(code.locator('.status')).to_have_text('Stopped')
            build=page.locator('.build4fun');build.get_by_label('Architecture',exact=True).select_option('amd64');build.get_by_role('button',name='Start',exact=True).click();expect(page.locator('#log-output')).to_contain_text('Built image.')
            assert fixture.calls[-1]==('build4fun','start','local','latest','amd64')
            page.keyboard.press('Escape');page.screenshot(path='/tmp/fourfun-launcher-desktop.png',full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            for card in page.locator('article').all():assert card.bounding_box()['width']>300
            page.screenshot(path='/tmp/fourfun-launcher-mobile.png',full_page=True)
            assert not errors,errors;browser.close()
        print('Launcher source selection, lifecycle actions, logs, desktop and mobile checks passed.')
    finally:server.shutdown();server.server_close()


if __name__=='__main__':main()
