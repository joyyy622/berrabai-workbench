"""Build only the browser-local public demo. No database, secrets or server code."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'public-demo'
FILES = ('index.html', 'owner.css', 'owner.js', 'catalog-data.js')


def build():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    for name in FILES:
        shutil.copyfile(ROOT / 'dist' / name, OUTPUT / name)
    entry = OUTPUT / 'index.html'
    html = entry.read_text(encoding='utf-8')
    marker = '<script src="catalog-data.js"></script>'
    if marker not in html:
        raise ValueError('Missing public demo entry script')
    html = html.replace(marker, '<script>window.BERRABAI_PUBLIC_DEMO=true;</script>'+marker, 1)
    entry.write_text(html, encoding='utf-8')
    (OUTPUT / '_headers').write_text('''/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com/beacon.min.js; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://cloudflareinsights.com; object-src 'none'; base-uri 'self'; frame-ancestors 'self'
''', encoding='utf-8')
    print('Cloudflare Pages output: public-demo (browser-local data, no backend)')


if __name__ == '__main__':
    build()
