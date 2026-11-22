import math
from kivy.animation import Animation
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ColorProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from campus.helpers import qr_matrix


class Txt(Label):
    pass


class Sec(Txt):
    pass


class RBtn(Button):
    bg = ColorProperty((0.36, 0.30, 0.95, 1))
    radius = ListProperty([dp(16)])


class Chip(RBtn):
    active = BooleanProperty(False)


class Panel(BoxLayout):
    pass


class Card(ButtonBehavior, Panel):
    pass


class InfoTile(Panel):
    caption = StringProperty('')
    value = StringProperty('')


class Pill(Label):
    bg = ColorProperty((1, 1, 1, 0.9))


class Badge(BoxLayout):
    day = StringProperty('')
    month = StringProperty('')


class Banner(BoxLayout):
    tex = ObjectProperty(None, allownone=True)
    deco = BooleanProperty(True)
    radii = ListProperty([0, 0, 0, 0])


class NavBar(BoxLayout):
    pass


class NavTab(ButtonBehavior, BoxLayout):
    kind = StringProperty('feed')
    text = StringProperty('')
    active = BooleanProperty(False)


class BackBtn(ButtonBehavior, BoxLayout):
    pass


class HeadBtn(ButtonBehavior, Widget):
    kind = StringProperty('bell')
    badge = NumericProperty(0)


class StyledInput(TextInput):
    pass


class Toggle(ButtonBehavior, Widget):
    active = BooleanProperty(False)
    k = NumericProperty(0)

    def on_active(self, *args):
        Animation(k=1 if self.active else 0, duration=0.15).start(self)

    def on_release(self):
        self.active = not self.active


class SettingRow(BoxLayout):
    text = StringProperty('')
    key = StringProperty('')


class NotifItem(Panel):
    title = StringProperty('')
    text = StringProperty('')
    when = StringProperty('')
    unread = BooleanProperty(False)


class Toast(Panel):
    title = StringProperty('')
    text = StringProperty('')


class QRWidget(Widget):
    data = StringProperty('')

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, data=self.redraw)
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        m = qr_matrix(self.data)
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size)
            if m is None:
                return
            q = 4
            n = len(m) + 2 * q
            buf = bytearray()
            for y in range(n - 1, -1, -1):
                for x in range(n):
                    yy, xx = y - q, x - q
                    dark = 0 <= yy < len(m) and 0 <= xx < len(m) and m[yy][xx]
                    buf += b'\x00\x00\x00\xff' if dark else b'\xff\xff\xff\xff'
            tex = Texture.create(size=(n, n), colorfmt='rgba')
            tex.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
            tex.mag_filter = 'nearest'
            tex.min_filter = 'nearest'
            side = min(self.width, self.height)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, size=(side, side),
                      pos=(self.center_x - side / 2.0, self.center_y - side / 2.0))


class Icon(Widget):
    kind = StringProperty('feed')
    col = ColorProperty((0.5, 0.5, 0.6, 1))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, kind=self.draw, col=self.draw)
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        s = min(self.width, self.height)
        if s <= 1:
            return
        cx, cy = self.center_x, self.center_y
        r = s / 2.0
        lw = max(dp(1.5), s * 0.085)
        k = self.kind
        with self.canvas:
            Color(*self.col)
            if k == 'feed':
                q = r * 0.85
                g = r * 0.12
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        x = cx + g if sx > 0 else cx - g - q
                        y = cy + g if sy > 0 else cy - g - q
                        RoundedRectangle(pos=(x, y), size=(q, q), radius=[q * 0.28])
            elif k == 'star':
                pts = []
                for i in range(10):
                    ang = math.pi / 2 + i * math.pi / 5
                    rad = r if i % 2 == 0 else r * 0.45
                    pts += [cx + rad * math.cos(ang), cy + rad * math.sin(ang) - r * 0.05]
                Line(points=pts, close=True, width=lw, joint='round')
            elif k == 'check':
                Line(rounded_rectangle=(cx - r * 0.88, cy - r * 0.88, r * 1.76, r * 1.76, r * 0.32),
                     width=lw)
                Line(points=[cx - r * 0.42, cy, cx - r * 0.1, cy - r * 0.34, cx + r * 0.46, cy + r * 0.36],
                     width=lw, cap='round', joint='round')
            elif k == 'add':
                Line(circle=(cx, cy, r * 0.88), width=lw)
                Line(points=[cx - r * 0.42, cy, cx + r * 0.42, cy], width=lw, cap='round')
                Line(points=[cx, cy - r * 0.42, cx, cy + r * 0.42], width=lw, cap='round')
            elif k == 'back':
                Line(points=[cx + r * 0.3, cy + r * 0.75, cx - r * 0.45, cy, cx + r * 0.3, cy - r * 0.75],
                     width=lw * 1.25, cap='round', joint='round')
            elif k == 'search':
                Line(circle=(cx - r * 0.12, cy + r * 0.12, r * 0.62), width=lw)
                Line(points=[cx + r * 0.34, cy - r * 0.34, cx + r * 0.85, cy - r * 0.85],
                     width=lw * 1.25, cap='round')
            elif k == 'gear':
                Line(circle=(cx, cy, r * 0.58), width=lw)
                Line(circle=(cx, cy, r * 0.22), width=lw)
                for i in range(8):
                    a = i * math.pi / 4
                    Line(points=[cx + r * 0.62 * math.cos(a), cy + r * 0.62 * math.sin(a),
                                 cx + r * 0.9 * math.cos(a), cy + r * 0.9 * math.sin(a)],
                         width=lw * 1.2, cap='round')
            elif k == 'bell':
                Line(circle=(cx, cy + r * 0.1, r * 0.5, 270, 450), width=lw)
                Line(points=[cx - r * 0.5, cy + r * 0.1, cx - r * 0.72, cy - r * 0.5,
                             cx + r * 0.72, cy - r * 0.5, cx + r * 0.5, cy + r * 0.1],
                     width=lw, cap='round', joint='round')
                Line(circle=(cx, cy - r * 0.72, r * 0.16), width=lw)
            elif k == 'scan':
                a, b = r * 0.88, r * 0.38
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        Line(points=[cx + sx * a, cy + sy * b, cx + sx * a, cy + sy * a,
                                     cx + sx * b, cy + sy * a],
                             width=lw, cap='round', joint='round')
                Line(points=[cx - r * 0.45, cy, cx + r * 0.45, cy], width=lw, cap='round')


class EmptyState(BoxLayout):
    kind = StringProperty('bell')
    text = StringProperty('')
