import json
import os
import subprocess
import time
import uuid
from datetime import date, datetime, timedelta
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.properties import ColorProperty, NumericProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.utils import platform

from campus.config import DEFAULT_SETTINGS, seed_events
from campus.helpers import (clean, fmt_left, gradient, human_date,
    parse_event, reg_status, sign, start_dt)
from campus.screens.create import CreateScreen
from campus.screens.detail import DetailScreen
from campus.screens.feed import FeedScreen
from campus.screens.notifs import NotifScreen
from campus.screens.qr import QRScreen
from campus.screens.scan import ScanScreen
from campus.screens.settings import SettingsScreen
from campus.widgets import Panel, RBtn, Toast, Txt


KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kv')
KV_FILES = ['theme', 'feed', 'detail', 'create', 'settings', 'notifs', 'scan', 'qr']
SCREENS = (FeedScreen, DetailScreen, CreateScreen, SettingsScreen, NotifScreen, ScanScreen, QRScreen)


def load_kv():
    for name in KV_FILES:
        Builder.load_file(os.path.join(KV_DIR, name + '.kv'))


class CampusApp(App):
    title = 'CampusLife'
    accent = ColorProperty((0.36, 0.30, 0.95, 1))
    grad_header = ObjectProperty(None)
    unread = NumericProperty(0)

    def build(self):
        self.path = os.path.join(self.user_data_dir, 'state2.json')
        self.state = self.load()
        self.grad_header = gradient((0.43, 0.36, 0.98, 1), (0.72, 0.32, 0.88, 1))
        load_kv()
        self.sm = ScreenManager(transition=SlideTransition(duration=0.22))
        for cls in SCREENS:
            self.sm.add_widget(cls())
        self.update_unread()
        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_once(self.check_notifications, 1.5)
        Clock.schedule_interval(self.check_notifications, 30)
        Clock.schedule_once(self.sync_counts, 2)
        Clock.schedule_interval(self.sync_counts, 60)
        return self.sm


    def load(self):
        state = {'events': seed_events(), 'regs': {}, 'favs': [], 'reminders': {},
                 'profile': {'name': '', 'cls': ''}, 'settings': dict(DEFAULT_SETTINGS),
                 'notifs': [], 'sent': [], 'checkins': []}
        try:
            with open(self.path, encoding='utf-8') as f:
                loaded = json.load(f)
            for k, v in loaded.items():
                if k in ('settings', 'profile') and isinstance(v, dict):
                    state[k].update(v)
                else:
                    state[k] = v
        except (OSError, ValueError):
            pass
        return state

    def save(self):
        del self.state['sent'][:-600]
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False)
        except OSError:
            pass

    def set_opt(self, key, val):
        s = self.state['settings']
        if s.get(key) == val:
            return
        s[key] = val
        self.save()
        if key == 'n_system' and val:
            self.ask_perms(['android.permission.POST_NOTIFICATIONS'])
        if key == 'server':
            Clock.schedule_once(self.sync_counts, 0.5)

    def find_event(self, uid):
        for ev in self.state['events']:
            if ev['id'] == uid:
                return ev
        return None


    def go(self, name, direction='left'):
        self.sm.transition.direction = direction
        self.sm.current = name

    def on_key(self, window, key, *args):
        if key == 27 and self.sm.current != 'feed':
            self.go('feed', 'right')
            return True
        return False

    def open_event(self, ev):
        self.sm.get_screen('detail').show(ev)
        self.go('detail', 'left')

    def open_qr(self, ev):
        self.sm.get_screen('qr').show(ev, 'event')
        self.go('qr', 'left')

    def toggle_fav(self, ev_id):
        favs = self.state['favs']
        if ev_id in favs:
            favs.remove(ev_id)
        else:
            favs.append(ev_id)
        self.save()

    def ask_perms(self, perms):
        if platform != 'android':
            return
        try:
            from android.permissions import request_permissions
            request_permissions(perms)
        except Exception:
            pass


    def show_toast(self, title, text, duration=3.8, top=True):
        h = dp(80) if title else dp(54)
        t = Toast(title=title, text=text, size_hint=(None, None),
                  size=(Window.width - dp(24), h))
        t.x = dp(12)
        end_y = Window.height - h - dp(36) if top else dp(104)
        t.y = Window.height if top else end_y - dp(20)
        t.opacity = 0
        Window.add_widget(t)
        Animation(y=end_y, opacity=1, duration=0.25).start(t)

        def hide(dt):
            anim = Animation(opacity=0, duration=0.25)
            anim.bind(on_complete=lambda *a: Window.remove_widget(t) if t.parent else None)
            anim.start(t)
        Clock.schedule_once(hide, duration)

    def toast(self, text, duration=3.2):
        self.show_toast('', text, duration, top=False)

    def ask(self, title, text, yes_text, on_yes):
        view = ModalView(size_hint=(0.88, None), height=dp(200), background='',
                         background_color=(0, 0, 0, 0), overlay_color=(0, 0, 0, 0.45))
        box = Panel(orientation='vertical', padding=dp(20), spacing=dp(10))
        box.add_widget(Txt(text=title, bold=True, font_size='20sp', size_hint_y=None, height=dp(30)))
        box.add_widget(Txt(text=text, font_size='15sp', color=(0.35, 0.35, 0.46, 1)))
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        no = RBtn(text='Отмена', bg=(0.93, 0.93, 0.96, 1), color=(0.38, 0.38, 0.48, 1))
        yes = RBtn(text=yes_text)
        no.bind(on_release=lambda *a: view.dismiss())
        yes.bind(on_release=lambda *a: (view.dismiss(), on_yes()))
        row.add_widget(no)
        row.add_widget(yes)
        box.add_widget(row)
        view.add_widget(box)
        view.open()


    def update_unread(self):
        self.unread = sum(1 for n in self.state['notifs'] if not n.get('read'))

    def notify(self, key, title, text, kind):
        if key in self.state['sent']:
            return False
        self.state['sent'].append(key)
        s = self.state['settings']
        if not s['n_enabled'] or not s.get('n_' + kind, True):
            self.save()
            return False
        self.state['notifs'].insert(0, dict(title=title, text=text, ts=time.time(),
                                            read=False, kind=kind))
        del self.state['notifs'][100:]
        self.update_unread()
        self.save()
        return True

    def system_notify(self, title, text):
        if not self.state['settings']['n_system']:
            return
        try:
            from plyer import notification
            notification.notify(title=title, message=text, app_name='CampusLife', timeout=8)
        except Exception:
            pass

    def test_notify(self):
        key = 'test:%f' % time.time()
        self.notify(key, 'Тестовое уведомление',
                    'Так выглядят уведомления о наборе и скором старте событий', 'test')
        self.show_toast('Тестовое уведомление', 'Так выглядят уведомления о наборе и старте')
        self.system_notify('CampusLife', 'Тестовое уведомление')

    def clear_notifs(self):
        self.state['notifs'] = []
        self.update_unread()
        self.save()
        self.sm.get_screen('notifs').refresh()

    def check_notifications(self, *args):
        now = datetime.now()
        today = now.date()
        s = self.state['settings']
        lead = timedelta(hours=s['lead'])
        fresh = []

        def push(key, title, text, kind):
            if self.notify(key, title, text, kind):
                fresh.append((title, text))

        for ev in list(self.state['events']):
            st = start_dt(ev)
            left = st - now
            eid = ev['id']
            mine = eid in self.state['regs'] or eid in self.state['favs']
            name = '«%s»' % ev['title']
            ro = ev.get('reg_open')
            if ro and left > timedelta(0):
                since = (today - date.fromisoformat(ro)).days
                if 0 <= since <= 2:
                    push('open:' + eid, 'Начался набор', '%s — открыта запись' % name, 'reg_open')
            if timedelta(0) < left <= lead and (s['soon_all'] or mine):
                push('soon:%s:%d' % (eid, s['lead']), 'Скоро начнётся',
                     '%s — старт через %s' % (name, fmt_left(left)), 'soon')
            if timedelta(minutes=-15) <= left <= timedelta(0) and mine:
                push('go:' + eid, 'Началось!', '%s уже начинается' % name, 'soon')
            days = self.state['reminders'].get(eid, 0)
            ld = (st.date() - today).days
            if mine and days and 0 <= ld <= days and left > timedelta(0):
                when = 'сегодня в %s' % ev['time'] if ld == 0 else 'через %d дн., %s' % (ld, ev['time'])
                push('rem:%s:%d' % (eid, ld), 'Напоминание', '%s — %s' % (name, when), 'remind')
        if fresh:
            if len(fresh) == 1:
                title, text = fresh[0]
            else:
                title, text = 'Новые уведомления', 'Новых: %d. Откройте колокольчик' % len(fresh)
            self.show_toast(title, text)
            self.system_notify(title, text)


    def server(self):
        return self.state['settings'].get('server', '').strip().rstrip('/')

    def api(self, path, body, ok, fail):
        url = self.server() + path

        def on_ok(req, res):
            ok(res if isinstance(res, dict) else {})

        def on_fail(req, res):
            msg = res.get('error') if isinstance(res, dict) else None
            fail(msg or 'Ошибка сервера')

        def on_err(req, err):
            fail('Нет связи с сервером')

        kw = dict(on_success=on_ok, on_failure=on_fail, on_error=on_err, timeout=8)
        if body is not None:
            kw.update(req_body=json.dumps(body, ensure_ascii=False),
                      req_headers={'Content-Type': 'application/json'})
        UrlRequest(url, **kw)

    def sync_counts(self, *args):
        if not self.server():
            return

        def ok(res):
            for ev in self.state['events']:
                if ev['id'] in res:
                    ev['registered'] = res[ev['id']]
            self.save()
        self.api('/counts', None, ok, lambda msg: None)


    def register(self, ev, done=None):
        p = self.state['profile']
        if not p['name'].strip():
            self.toast('Сначала укажите имя в настройках')
            self.go('settings')
            return
        if ev['id'] in self.state['regs']:
            self.toast('Вы уже записаны')
            return
        code, txt = reg_status(ev)
        if code != 'open':
            self.toast('Запись недоступна: набор %s' % txt)
            return
        reg = dict(rid=uuid.uuid4().hex[:12], name=p['name'], cls=p['cls'], ts=time.time())

        def commit(count=None):
            self.state['regs'][ev['id']] = reg
            ev['registered'] = count if count is not None else ev['registered'] + 1
            self.save()
            if done:
                done()
            self.toast('Вы записаны! Билет с QR — на кнопке «QR»')

        if self.server():
            self.api('/register', dict(uid=ev['id'], rid=reg['rid'], name=reg['name'],
                                       cls=reg['cls'], capacity=ev.get('capacity', 0)),
                     lambda res: commit(res.get('count')), lambda msg: self.toast(msg))
        else:
            commit()

    def cancel_registration(self, ev, done=None):
        reg = self.state['regs'].get(ev['id'])
        if not reg:
            return

        def commit(count=None):
            self.state['regs'].pop(ev['id'], None)
            ev['registered'] = count if count is not None else max(0, ev['registered'] - 1)
            self.save()
            if done:
                done()
            self.toast('Запись отменена')

        if self.server():
            self.api('/cancel', dict(uid=ev['id'], rid=reg['rid']),
                     lambda res: commit(res.get('count')), lambda msg: self.toast(msg))
        else:
            commit()

    def offer_register(self, ev):
        if ev['id'] in self.state['regs']:
            self.toast('Вы уже записаны на это событие')
            return
        self.ask('Записаться?', '«%s»\n%s, %s' % (
            ev['title'], human_date(date.fromisoformat(ev['date'])), ev['time']),
            'Записаться', lambda: self.register(ev, self.sm.get_screen('detail').update_buttons))


    def ticket_payload(self, ev, reg):
        parts = [reg['rid'], ev['id'], clean(reg['name']), clean(reg['cls'])]
        return 'CLT1|' + '|'.join(parts) + '|' + sign(self.state['settings']['secret'], *parts)

    def handle_qr(self, text, cb):
        if text.startswith('CLE1|'):
            d = parse_event(text)
            if not d:
                return cb(False, 'Не удалось прочитать QR мероприятия', None)
            ev = self.find_event(d['i'])
            if ev is None:
                ev = dict(id=d['i'], title=d['t'], category=d.get('c', 'Конкурсы'), date=d['d'],
                          time=d.get('h', '12:00'), place=d.get('p', ''), desc=d.get('x', ''),
                          capacity=d.get('n', 0), reg_open=d.get('o', ''), registered=0,
                          image='', mine=False)
                self.state['events'].append(ev)
                self.save()
                self.sync_counts()
            return cb(True, 'Мероприятие: ' + ev['title'], ev)
        if text.startswith('CLT1|'):
            return self.check_in(text, cb)
        cb(False, 'Это не QR-код CampusLife', None)

    def check_in(self, text, cb):
        p = text.split('|')
        if len(p) != 6:
            return cb(False, 'Повреждённый билет', None)
        _, rid, uid, name, cls, sig = p
        s = self.state['settings']
        if sign(s['secret'], rid, uid, name, cls) != sig:
            return cb(False, 'Билет поддельный или из другой системы', None)
        ev = self.find_event(uid)
        if ev is None:
            return cb(False, 'Это событие неизвестно устройству. Сначала отсканируйте его QR', None)
        if not (ev.get('mine') or s['organizer']):
            return cb(False, 'Билеты проверяет организатор: включите режим в настройках', None)
        who = name + (', ' + cls if cls else '')
        if self.server():
            def ok(res):
                if res.get('already'):
                    cb(False, 'Уже отмечен: ' + who, None)
                else:
                    cb(True, 'Допущен: ' + who, None)
            return self.api('/checkin', dict(uid=uid, rid=rid), ok, lambda msg: cb(False, msg, None))
        if rid in self.state['checkins']:
            return cb(False, 'Уже проходил: ' + who, None)
        self.state['checkins'].append(rid)
        self.save()
        cb(True, 'Допущен: ' + who, None)


    def out_dir(self):
        try:
            if platform == 'android':
                from android.storage import primary_external_storage_path
                p = os.path.join(primary_external_storage_path(), 'Download')
            else:
                p = os.path.join(os.path.expanduser('~'), 'CampusLife_QR')
            os.makedirs(p, exist_ok=True)
            return p
        except Exception:
            return self.user_data_dir

    def print_file(self, path):
        try:
            if platform == 'win':
                os.startfile(path, 'print')
                return True
            if platform in ('linux', 'macosx'):
                subprocess.Popen(['lp', path])
                return True
        except Exception:
            pass
        return False
