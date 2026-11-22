import threading
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.utils import platform

from campus.camera import CvCamera
from campus.helpers import decode_frame, decode_qr

ERR = (0.88, 0.25, 0.30, 1)
HINT = (0.35, 0.35, 0.46, 1)
OK = (0.10, 0.60, 0.35, 1)


class ScanScreen(Screen):
    cam = None
    _clock = None
    _start_ev = None
    _last = ''
    _lt = 0
    _busy = False
    _waited = 0

    def on_enter(self, *args):
        self.ids.result.text = 'Запускаю камеру…'
        self.ids.result.color = HINT
        self._waited = 0
        self._start_ev = Clock.schedule_once(self.start, 0.3)

    def start(self, dt):
        if self.cam or App.get_running_app().sm.current != 'scan':
            return
        if platform == 'android' and not self.has_permission():
            if self._waited == 0:
                App.get_running_app().ask_perms(['android.permission.CAMERA'])
            self._waited += 1
            if self._waited > 40:
                self.fail('нет доступа к камере. Разрешите её в настройках приложения')
                return
            self._start_ev = Clock.schedule_once(self.start, 0.5)
            return
        try:
            if platform in ('android', 'ios'):
                from kivy.uix.camera import Camera
                self.cam = Camera(index=0, resolution=(640, 480), play=True)
            else:
                self.cam = CvCamera(index=0)
            self.ids.cam_box.add_widget(self.cam)
        except Exception as e:
            self.cam = None
            self.fail(e)
            return
        self.ids.result.text = 'Наведите камеру на QR-код'
        self.ids.result.color = HINT
        self._clock = Clock.schedule_interval(self.scan, 0.3)

    def has_permission(self):
        try:
            from android.permissions import Permission, check_permission
            return bool(check_permission(Permission.CAMERA))
        except Exception:
            return True

    def fail(self, e):
        self.ids.result.text = 'Камера недоступна: %s.\nМожно вставить код вручную.' % e
        self.ids.result.color = ERR

    def on_leave(self, *args):
        self.stop()

    def stop(self):
        if self._start_ev:
            self._start_ev.cancel()
            self._start_ev = None
        if self._clock:
            self._clock.cancel()
            self._clock = None
        if self.cam:
            try:
                if isinstance(self.cam, CvCamera):
                    self.cam.release()
                else:
                    self.cam.play = False
                self.ids.cam_box.remove_widget(self.cam)
            except Exception:
                pass
            self.cam = None

    def scan(self, dt):
        cam = self.cam
        if not cam:
            return
        if isinstance(cam, CvCamera):
            if cam.error:
                self.stop()
                self.fail(cam.error)
                return
            frame = cam.get_frame()
            if frame is None or self._busy:
                return
            self._busy = True
            threading.Thread(target=self.work, args=(decode_frame, frame), daemon=True).start()
        else:
            if cam.texture is None:
                return
            text = decode_qr(cam.texture)
            if text:
                self.handle(text)

    def work(self, fn, data):
        try:
            text = fn(data)
        except Exception:
            text = ''
        self._busy = False
        if text:
            Clock.schedule_once(lambda dt: self.handle(text))

    def handle(self, text):
        now = time.time()
        text = (text or '').strip()
        if not text or (text == self._last and now - self._lt < 3):
            return
        self._last, self._lt = text, now
        App.get_running_app().handle_qr(text, self.show_result)

    def show_result(self, ok, msg, ev):
        app = App.get_running_app()
        self.ids.result.text = msg
        self.ids.result.color = OK if ok else ERR
        if ok and ev:
            app.open_event(ev)
            Clock.schedule_once(lambda dt: app.offer_register(ev), 0.5)
