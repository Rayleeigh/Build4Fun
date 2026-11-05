"""Observable browser checks against isolated snapshots and controlled API responses."""
import json
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright


def check(url, stage):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(service_workers='block')
            page = context.new_page()
            page.set_default_timeout(1800)
            source = urlsplit(url)
            origin = f'{source.scheme}://{source.netloc}'
            folder = source.path.rsplit('/', 1)[0] + '/'
            state = {'sample': 0, 'failure': None, 'nulls': False, 'calls': {}}

            def route(request):
                parsed = urlsplit(request.request.url)
                if parsed.scheme + '://' + parsed.netloc != origin:
                    request.abort()
                    return
                path = parsed.path.rstrip('/')
                if path.startswith('/api/'):
                    state['calls'][path] = state['calls'].get(path, 0) + 1
                    if state['failure'] == 'network':
                        request.abort()
                        return
                    if state['failure'] == 'http':
                        request.fulfill(status=503, content_type='application/json', body='{"error":"Temporarily unavailable"}')
                        return
                    n = state['sample']
                    data = {
                        '/api/hostname': {'hostname': f'learning-server-{n}'},
                        '/api/username': {'username': f'learner-{n}'},
                        '/api/ip': {'addresses': [f'172.24.0.{10+n}', f'fd00::{10+n}']},
                        '/api/metrics': {
                            'cpu_percent': None if state['nulls'] else 23 + n,
                            'memory_used_bytes': None if state['nulls'] else 1048576 + n,
                            'memory_limit_bytes': None if state['nulls'] else 268435456 + n,
                            'uptime_seconds': 123 + n,
                        },
                    }.get(path)
                    request.fulfill(status=200 if data else 404, content_type='application/json', body=json.dumps(data or {'error': 'Unknown endpoint'}))
                elif parsed.path in [folder + name for name in ('index.html', 'style.css', 'script.js')]:
                    request.continue_()
                else:
                    request.abort()

            context.route('**/*', route)

            def load():
                page.goto(url, wait_until='domcontentloaded', timeout=6000)

            def expect_js(expression):
                page.wait_for_function('() => (' + expression + ')', timeout=2500)

            def run(label, action):
                try:
                    action()
                    results.append({'label': label, 'passed': True, 'message': 'Passed.'})
                except Exception as error:
                    import sys
                    print(f'Check failed: {label}: {error}', file=sys.stderr)
                    results.append({'label': label, 'passed': False, 'message': 'Not yet. ' + label + '. Review this checkpoint and try again.'})

            load()
            if stage == 0:
                run('Add a non-empty h1', lambda: expect_js("!!document.querySelector('h1')?.textContent.trim()"))
                run('Add an introductory paragraph', lambda: expect_js("!!document.querySelector('p')?.textContent.trim()"))
                run('Add section#server-info with a non-empty h2', lambda: expect_js("!!document.querySelector('section#server-info h2')?.textContent.trim()"))
            elif stage == 1:
                run('Give body a non-white, non-transparent background', lambda: expect_js("!['rgba(0, 0, 0, 0)', 'rgb(255, 255, 255)'].includes(getComputedStyle(document.body).backgroundColor)"))
                run('Give #server-info at least 12px padding on every side', lambda: expect_js("['Top','Right','Bottom','Left'].every(s=>parseFloat(getComputedStyle(document.querySelector('#server-info'))['padding'+s])>=12)"))
                run('Give #server-info a visible border at least 1px wide', lambda: expect_js("(() => {const s=getComputedStyle(document.querySelector('#server-info'));return ['Top','Right','Bottom','Left'].every(e=>parseFloat(s['border'+e+'Width'])>=1&&!['none','hidden'].includes(s['border'+e+'Style'])&&s['border'+e+'Color']!=='rgba(0, 0, 0, 0)')})()"))
            elif stage == 2:
                def greeting():
                    before = page.locator('#message').inner_text()
                    page.locator('#greet').click()
                    page.wait_for_function('(before)=>{const e=document.querySelector("#message");return e&&e.innerText.trim()&&e.innerText!==before}', arg=before)
                run('Make #greet change the visible #message text', greeting)
            elif stage == 3:
                def theme():
                    before = page.evaluate('getComputedStyle(document.body).backgroundColor')
                    page.locator('#theme-toggle').click()
                    page.wait_for_function('(before)=>getComputedStyle(document.body).backgroundColor!==before', arg=before)
                    page.locator('#theme-toggle').click()
                    page.wait_for_function('(before)=>getComputedStyle(document.body).backgroundColor===before', arg=before)
                run('Make #theme-toggle change the background and restore it on a second click', theme)
            elif stage == 4:
                def hostname():
                    for sample in (1, 4):
                        state['sample'] = sample
                        load()
                        page.wait_for_function('(value)=>document.querySelector("#hostname")?.innerText.includes(value)', arg=f'learning-server-{sample}')
                    assert state['calls'].get('/api/hostname', 0) >= 2
                run('Display the hostname returned by the API on page load', hostname)
            elif stage == 5:
                endpoints = ('/api/username', '/api/hostname', '/api/ip', '/api/metrics')

                def values(sample):
                    expected = {'username': f'learner-{sample}', 'hostname': f'learning-server-{sample}',
                                'addresses': [f'172.24.0.{10+sample}', f'fd00::{10+sample}'],
                                'cpu': str(23+sample), 'memory': str(1048576+sample),
                                'memory-limit': str(268435456+sample), 'uptime': str(123+sample)}
                    page.wait_for_function('''expected=>Object.entries(expected).every(([id, values])=>{
                        const e=document.getElementById(id);
                        return e&&e.getClientRects().length&&[values].flat().every(v=>e.innerText.includes(v));
                    })''', arg=expected, timeout=3000)

                def all_data():
                    values(0)
                    assert all(state['calls'].get(p, 0) for p in endpoints)
                run('Show username, hostname, both addresses, CPU, memory, memory limit, and uptime from the API', all_data)

                def refresh():
                    state['sample'] = 1
                    before = dict(state['calls'])
                    page.locator('#refresh').click()
                    values(1)
                    assert all(state['calls'].get(p, 0) > before.get(p, 0) for p in endpoints)
                run('Make #refresh fetch and display changed readings from all four endpoints', refresh)

                def automatic():
                    state['sample'] = 2
                    page.wait_for_function('() => document.querySelector("#hostname")?.innerText.includes("learning-server-2")', timeout=6500)
                    values(2)
                run('Automatically update readings at least every 5 seconds', automatic)

                # Delaying route fulfillment in sync Playwright blocks the driver. An init
                # script delays fetch resolution instead, exercising visible pending state.
                context.add_init_script('''const originalFetch = window.fetch;
                    window.fetch = async (...args) => {
                        const response = await originalFetch(...args);
                        await new Promise(resolve => setTimeout(resolve, 650));
                        return response;
                    };''')

                def status(pattern):
                    page.wait_for_function('(pattern)=>{const e=document.querySelector("#status");return e&&e.getClientRects().length&&new RegExp(pattern,"i").test(e.innerText)}', arg=pattern)

                def loading():
                    load()
                    status('loading')
                    values(2)
                    page.wait_for_function('() => !(/loading/i.test(document.querySelector("#status")?.innerText||""))')
                run('Show Loading in #status while fetching, and clear it afterwards', loading)

                def failure(mode):
                    state['failure'] = mode
                    load()
                    status('error|failed')
                    state['failure'] = None
                    page.locator('#refresh').click()
                    values(2)
                    page.wait_for_function('() => !(/error|failed|loading/i.test(document.querySelector("#status")?.innerText||""))')
                run('Report failed HTTP responses in #status and recover on refresh', lambda: failure('http'))
                state['failure'] = None
                run('Report network failures in #status and recover on refresh', lambda: failure('network'))
                state['failure'] = None

                def unavailable():
                    state['nulls'] = True
                    load()
                    page.wait_for_function('() => ["cpu","memory","memory-limit"].every(id=>document.getElementById(id)?.innerText.includes("N/A"))')
                run('Display N/A for unavailable CPU and memory measurements', unavailable)
            return results
        finally:
            browser.close()


if __name__ == '__main__':
    import sys
    print(json.dumps(check(sys.argv[1], int(sys.argv[2]))))
