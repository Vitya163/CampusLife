import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8000
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'regs.json')
lock = threading.Lock()

try:
    with open(DB_FILE, encoding='utf-8') as f:
        db = json.load(f)
except (OSError, ValueError):
    db = {}


def save():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        with lock:
            if url.path == '/ping':
                return self._send(200, {'ok': True})
            if url.path == '/counts':
                return self._send(200, {uid: len(r) for uid, r in db.items()})
            if url.path == '/list':
                uid = parse_qs(url.query).get('uid', [''])[0]
                return self._send(200, {'regs': list(db.get(uid, {}).values())})
        self._send(404, {'error': 'Не найдено'})

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            b = json.loads(self.rfile.read(n).decode('utf-8'))
            uid, rid = str(b['uid']), str(b['rid'])
        except Exception:
            return self._send(400, {'error': 'Неверный запрос'})
        path = urlparse(self.path).path
        with lock:
            regs = db.setdefault(uid, {})
            if path == '/register':
                if rid in regs:
                    return self._send(200, {'ok': True, 'count': len(regs)})
                name = str(b.get('name', '')).strip()
                cls = str(b.get('cls', '')).strip()
                if not name:
                    return self._send(400, {'error': 'Не указано имя'})
                if any(r['name'].lower() == name.lower() and r['cls'].lower() == cls.lower()
                       for r in regs.values()):
                    return self._send(409, {'error': 'Такой участник уже записан'})
                cap = int(b.get('capacity') or 0)
                if cap and len(regs) >= cap:
                    return self._send(409, {'error': 'Мест не осталось'})
                regs[rid] = dict(rid=rid, name=name, cls=cls, ts=time.time(), checked=None)
                save()
                return self._send(200, {'ok': True, 'count': len(regs)})
            if path == '/cancel':
                regs.pop(rid, None)
                save()
                return self._send(200, {'ok': True, 'count': len(regs)})
            if path == '/checkin':
                r = regs.get(rid)
                if not r:
                    return self._send(404, {'error': 'Билет не найден: запись не оформлена'})
                already = bool(r['checked'])
                if not already:
                    r['checked'] = time.time()
                    save()
                return self._send(200, {'ok': True, 'already': already,
                                        'name': r['name'], 'cls': r['cls']})
        self._send(404, {'error': 'Не найдено'})

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print('CampusLife server: http://0.0.0.0:%d' % PORT)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
