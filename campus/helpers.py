import base64
import hashlib
import hmac
import json
import os
import time
import zlib
from datetime import date, datetime
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture

from campus.config import CAT_GRAD, DEFAULT_GRAD, MONTHS

try:
    import qrcode
except ImportError:
    qrcode = None


_grad_cache = {}
_qr_cache = {}


def gradient(c1, c2):
    key = (tuple(c1), tuple(c2))
    if key in _grad_cache:
        return _grad_cache[key]
    a = [int(v * 255) for v in c1]
    b = [int(v * 255) for v in c2]
    mid = [(x + y) // 2 for x, y in zip(a, b)]
    data = bytes(mid + b + a + mid)
    tex = Texture.create(size=(2, 2), colorfmt='rgba')
    tex.blit_buffer(data, colorfmt='rgba', bufferfmt='ubyte')
    tex.mag_filter = 'linear'
    tex.min_filter = 'linear'
    _grad_cache[key] = tex
    return tex


def cover_texture(img, cat):
    if img and os.path.exists(img):
        try:
            return CoreImage(img).texture, False
        except Exception:
            pass
    c1, c2 = CAT_GRAD.get(cat, DEFAULT_GRAD)
    return gradient(c1, c2), True


def cat_color(cat):
    return CAT_GRAD.get(cat, DEFAULT_GRAD)[1]


def human_date(d):
    delta = (d - date.today()).days
    if delta == 0:
        return 'Сегодня'
    if delta == 1:
        return 'Завтра'
    return '%d %s' % (d.day, MONTHS[d.month - 1])


def start_dt(ev):
    try:
        return datetime.strptime(ev['date'] + ' ' + ev['time'], '%Y-%m-%d %H:%M')
    except ValueError:
        return datetime.combine(date.fromisoformat(ev['date']), datetime.min.time()).replace(hour=12)


def reg_status(ev):
    now = datetime.now()
    ro = ev.get('reg_open')
    if ro:
        rd = date.fromisoformat(ro)
        if rd > now.date():
            return 'wait', 'откроется %d %s' % (rd.day, MONTHS[rd.month - 1])
    if start_dt(ev) <= now:
        return 'closed', 'закрыт'
    cap = ev.get('capacity', 0)
    if cap and ev['registered'] >= cap:
        return 'full', 'мест нет'
    return 'open', 'открыт'


def fmt_left(td):
    m = int(td.total_seconds() // 60)
    if m >= 60:
        return '%d ч %d мин' % (m // 60, m % 60) if m % 60 else '%d ч' % (m // 60)
    return '%d мин' % max(m, 1)


def ago(ts):
    s = int(time.time() - ts)
    if s < 60:
        return 'только что'
    if s < 3600:
        return '%d мин назад' % (s // 60)
    if s < 86400:
        return '%d ч назад' % (s // 3600)
    d = datetime.fromtimestamp(ts)
    return '%d %s' % (d.day, MONTHS[d.month - 1])


def clean(s):
    return (s or '').replace('|', ' ').strip()


def sign(secret, *parts):
    return hmac.new(secret.encode('utf-8'), '|'.join(parts).encode('utf-8'),
                    hashlib.sha256).hexdigest()[:12]


def event_payload(ev):
    d = dict(i=ev['id'], t=ev['title'], c=ev['category'], d=ev['date'], h=ev['time'],
             p=ev.get('place', ''), x=(ev.get('desc') or '')[:120],
             n=ev.get('capacity', 0), o=ev.get('reg_open', ''))
    raw = zlib.compress(json.dumps(d, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), 9)
    return 'CLE1|' + base64.urlsafe_b64encode(raw).decode('ascii')


def parse_event(text):
    try:
        raw = base64.urlsafe_b64decode(text.split('|', 1)[1].encode('ascii'))
        d = json.loads(zlib.decompress(raw).decode('utf-8'))
        date.fromisoformat(d['d'])
        return d
    except Exception:
        return None


def qr_matrix(data):
    if not data or qrcode is None:
        return None
    if data in _qr_cache:
        return _qr_cache[data]
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=1, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    m = qr.get_matrix()
    _qr_cache[data] = m
    return m


_det = None


def decode_qr(tex):
    global _det
    try:
        import numpy as np
        w, h = tex.size
        arr = np.frombuffer(tex.pixels, dtype=np.uint8)
        if arr.size != w * h * 4:
            return ''
        arr = arr.reshape(h, w, 4)
    except Exception:
        return ''
    for frame in (arr[::-1], arr):
        gray = None
        try:
            import cv2
            if _det is None:
                _det = cv2.QRCodeDetector()
            gray = cv2.cvtColor(np.ascontiguousarray(frame), cv2.COLOR_RGBA2GRAY)
            text = _det.detectAndDecode(gray)[0]
            if text:
                return text
        except Exception:
            pass
        try:
            from pyzbar import pyzbar
            if gray is None:
                gray = np.ascontiguousarray(frame[:, :, :3].mean(axis=2).astype('uint8'))
            res = pyzbar.decode((gray.tobytes(), w, h))
            if res:
                return res[0].data.decode('utf-8', 'ignore')
        except Exception:
            pass
    return ''


def decode_frame(frame):
    global _det
    try:
        import cv2
        if _det is None:
            _det = cv2.QRCodeDetector()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        text = _det.detectAndDecode(gray)[0]
        if text:
            return text
        big = cv2.resize(gray, None, fx=1.5, fy=1.5)
        return _det.detectAndDecode(cv2.equalizeHist(big))[0]
    except Exception:
        return ''
