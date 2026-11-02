#!/usr/bin/env python3
from __future__ import annotations
import argparse,html,json,mimetypes,re
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
VERSION='5.27.0'
PAGES=['index', 'overview', 'architecture', 'installation', 'configuration', 'tui-reference', 'feature-ai', 'jira-siem', 'privacy-ai', 'autofp', 'notifications-viewers', 'operations', 'update-backup-rollback', 'runbooks', 'troubleshooting', 'security', 'validation', 'known-issues', 'version-history']
def inline(s):
 s=html.escape(s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s);s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s);return s
def render(text):
 out=[];heads=[];code=False;items=[]
 def flush():
  nonlocal items
  if items:out.append('<ul>'+''.join(items)+'</ul>');items=[]
 for raw in text.splitlines():
  if raw.startswith('```'):flush();out.append('</code></pre>' if code else '<pre><code>');code=not code;continue
  if code:out.append(html.escape(raw));continue
  if raw.startswith('- '):items.append('<li>'+inline(raw[2:])+'</li>');continue
  flush()
  if raw.startswith('# '):out.append('<h1>'+inline(raw[2:])+'</h1>')
  elif raw.startswith('## '):
   title=raw[3:];anchor=re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-');heads.append((anchor,title));out.append('<h2 id="'+anchor+'">'+inline(title)+'</h2>')
  elif raw.startswith('### '):out.append('<h3>'+inline(raw[4:])+'</h3>')
  elif raw.startswith('> '):out.append('<div class="callout">'+inline(raw[2:])+'</div>')
  elif raw.strip():out.append('<p>'+inline(raw)+'</p>')
 flush();return '\n'.join(out),heads
def make_page(root,lang,slug):
 p=root/'current'/'docs'/lang/(slug+'.md')
 if not p.is_file():p=root/'docs'/lang/(slug+'.md')
 body,heads=render(p.read_text(encoding='utf-8'));other='en' if lang=='id' else 'id'
 nav=''.join('<a class="'+('active' if x==slug else '')+'" href="/'+lang+'/'+x+'">'+x.replace('-',' ').title()+'</a>' for x in PAGES)
 toc=''.join('<a href="#'+a+'">'+html.escape(t)+'</a>' for a,t in heads)
 return ('<!doctype html><html lang="'+lang+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SOC Automation Docs</title><link rel="stylesheet" href="/assets/docs.css"></head><body><header><span class="brand">SOC Automation</span><span class="badge">Docs '+VERSION+'</span><div class="search"><input id="q" placeholder="Search documentation..."><div id="results" class="results"></div></div></header><div class="layout"><nav class="sidebar"><div class="lang"><a href="/'+lang+'/'+slug+'">'+lang.upper()+'</a><a href="/'+other+'/'+slug+'">'+other.upper()+'</a></div>'+nav+'</nav><main>'+body+'<footer>Documentation '+VERSION+' | Indonesian default | English parity | Runtime baseline 5.26.1 | TUI 1.26.1 | Reviewed 2026-08-20</footer></main><aside class="toc"><b>On this page</b>'+toc+'</aside></div><script src="/assets/docs.js"></script></body></html>').encode()
class H(BaseHTTPRequestHandler):
 root=Path.home()/'SOC-Automation'
 def end_headers(self):self.send_header('Cache-Control','no-store');self.send_header('X-Frame-Options','DENY');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'");super().end_headers()
 def do_POST(self):self.send_error(405,'Read-only documentation viewer')
 do_PUT=do_POST;do_PATCH=do_POST;do_DELETE=do_POST
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/':self.send_response(302);self.send_header('Location','/id/index');self.end_headers();return
  if path.startswith('/assets/'):
   name=path.rsplit('/',1)[-1]
   if name not in {'docs.css','docs.js','search-index.json'}:return self.send_error(404)
   p=self.root/'current'/'docs_static'/name
   if not p.is_file():p=self.root/'docs_static'/name
   try:b=p.read_bytes()
   except OSError:return self.send_error(404)
   self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  m=re.fullmatch(r'/(id|en)/([a-z0-9-]+)',path)
  if not m or m.group(2) not in PAGES:return self.send_error(404)
  try:b=make_page(self.root,*m.groups())
  except OSError:return self.send_error(404)
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='~/SOC-Automation');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8766);a=p.parse_args()
 if a.host!='127.0.0.1':raise SystemExit('Documentation Viewer wajib bind ke 127.0.0.1')
 H.root=Path(a.root).expanduser().resolve();s=ThreadingHTTPServer((a.host,a.port),H)
 try:s.serve_forever()
 except KeyboardInterrupt:pass
 finally:s.server_close()
if __name__=='__main__':main()
