"""Builds the installable offline app in app/ from photo-lift.html. Run: python3 build.py"""
import json, hashlib, pathlib
from PIL import Image, ImageDraw

here = pathlib.Path(__file__).resolve().parent
out = here / 'docs'
out.mkdir(exist_ok=True)
body = (here / 'photo-lift.html').read_text()

head = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#eceff2" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111417" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Photo Lift">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}</style>
</head>
<body>
'''
(out / 'index.html').write_text(head + body + '\n</body>\n</html>\n')

def icon(size, pad=0.0):
    s = 1024
    im = Image.new('RGB', (s, s), '#1a1f25')
    d = ImageDraw.Draw(im)
    inset = int(s * pad)
    def P(x, y):
        return (inset + x * (s - 2 * inset), inset + y * (s - 2 * inset))
    # sun
    cx, cy = P(0.64, 0.38); r = 0.15 * (s - 2 * inset)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#f0a042')
    # back and front hills
    d.polygon([P(0, 0.78), P(0.3, 0.46), P(0.55, 0.7), P(0.72, 0.56), P(1, 0.8), P(1, 1), P(0, 1)], fill='#5c6b80')
    d.polygon([P(0, 0.86), P(0.22, 0.68), P(0.48, 0.88), P(0.78, 0.7), P(1, 0.86), P(1, 1), P(0, 1)], fill='#e7eaee')
    return im.resize((size, size), Image.LANCZOS)

icon(180).save(out / 'apple-touch-icon.png')
icon(192).save(out / 'icon-192.png')
icon(512).save(out / 'icon-512.png')
icon(512, pad=0.12).save(out / 'icon-maskable-512.png')

(out / 'manifest.webmanifest').write_text(json.dumps({
    'name': 'Photo Lift',
    'short_name': 'Photo Lift',
    'description': 'Upscale, relight and sharpen photos on your device.',
    'start_url': './',
    'scope': './',
    'display': 'standalone',
    'background_color': '#eceff2',
    'theme_color': '#eceff2',
    'icons': [
        {'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
        {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
        {'src': 'icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
    ],
}, indent=2))

files = ['./', 'index.html', 'manifest.webmanifest', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png']
# Version the cache by content so a new build replaces the old copy on the phone.
digest = hashlib.sha256(b''.join((out / f).read_bytes() for f in files[1:])).hexdigest()[:10]
(out / 'sw.js').write_text(f'''// Keeps Photo Lift on the device so it opens with no connection.
const CACHE = 'photo-lift-{digest}';
const FILES = {json.dumps(files)};

self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
}});
// Serve from the phone first; check online for an update in the background.
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.open(CACHE).then(async c => {{
    const hit = await c.match(e.request, {{ ignoreSearch: true }});
    const net = fetch(e.request).then(r => {{ if (r.ok && new URL(e.request.url).origin === location.origin) c.put(e.request, r.clone()); return r; }}).catch(() => null);
    return hit || (await net) || (e.request.mode === 'navigate' ? c.match('index.html') : Response.error());
  }}));
}});
''')
print('built', digest)
