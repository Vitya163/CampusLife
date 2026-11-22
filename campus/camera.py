import os
import threading
import time

os.environ.setdefault('OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS', '0')
os.environ.setdefault('OPENCV_LOG_LEVEL', 'SILENT')

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget
from kivy.utils import platform


class CvCamera(Widget):
    def __init__(self, index=0, **kw):
        super().__init__(**kw)
        try:
            import cv2
            import numpy
        except ImportError:
            raise RuntimeError('не установлены пакеты: pip install opencv-python numpy')
        self.cv2 = cv2
        self.index = index
        self.frame = None
        self.error = ''
        self.cap = None
        self.texture = None
        self._lock = threading.Lock()
        self._new = False
        self._running = True
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(pos=self.pos, size=(0, 0))
        self.bind(pos=self._layout, size=self._layout)
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self._clock = Clock.schedule_interval(self.update, 1 / 30.0)

    def _open(self):
        cv2 = self.cv2
        if platform == 'win':
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]
        for i in dict.fromkeys([self.index, 0, 1, 2]):
            for backend in backends:
                if not self._running:
                    return None
                try:
                    cap = cv2.VideoCapture(i, backend)
                except Exception:
                    continue
                if cap.isOpened():
                    for _ in range(40):
                        if not self._running:
                            cap.release()
                            return None
                        ok, frame = cap.read()
                        if ok and frame is not None and frame.size:
                            return cap
                        time.sleep(0.05)
                cap.release()
        return None

    def _worker(self):
        cap = self._open()
        if cap is None:
            if self._running:
                self.error = ('камера не найдена или занята другой программой '
                              '(закройте Zoom/Teams/«Камеру» и проверьте доступ в '
                              'Параметры Windows → Конфиденциальность → Камера)')
            return
        self.cap = cap
        fails = 0
        while self._running:
            try:
                ok, frame = cap.read()
            except Exception:
                ok, frame = False, None
            if not ok or frame is None or not frame.size:
                fails += 1
                if fails > 100:
                    self.error = 'камера перестала отвечать'
                    break
                time.sleep(0.02)
                continue
            fails = 0
            with self._lock:
                self.frame = frame
                self._new = True
            time.sleep(0.01)
        cap.release()
        self.cap = None

    def _layout(self, *args):
        if self.texture is None:
            return
        tw, th = self.texture.size
        if not tw or not th or not self.width or not self.height:
            return
        k = min(self.width / tw, self.height / th)
        w, h = tw * k, th * k
        self._rect.size = (w, h)
        self._rect.pos = (self.x + (self.width - w) / 2, self.y + (self.height - h) / 2)

    def get_frame(self):
        with self._lock:
            return None if self.frame is None else self.frame.copy()

    def update(self, dt):
        if not self._new:
            return
        with self._lock:
            frame = self.frame
            self._new = False
        if frame is None:
            return
        rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        if self.texture is None or tuple(self.texture.size) != (w, h):
            self.texture = Texture.create(size=(w, h), colorfmt='rgb')
            self.texture.flip_vertical()
            self._rect.texture = self.texture
            self._layout()
        self.texture.blit_buffer(rgb.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        self.canvas.ask_update()

    def release(self):
        self._running = False
        self._clock.cancel()
