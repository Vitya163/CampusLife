from datetime import date, timedelta
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ColorProperty, ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen

from campus.config import CATEGORIES, MONTHS_SHORT, WHEN
from campus.helpers import cat_color, cover_texture, human_date, reg_status
from campus.widgets import Card, Chip, Txt


class EventCard(Card):
    ev = ObjectProperty(None)
    category = StringProperty('')
    cat_color = ColorProperty((0.4, 0.4, 0.6, 1))
    cover_tex = ObjectProperty(None, allownone=True)
    deco = BooleanProperty(True)
    day = StringProperty('')
    month = StringProperty('')
    title_text = StringProperty('')
    meta = StringProperty('')
    count_text = StringProperty('')
    fav = BooleanProperty(False)

    def fill(self, ev):
        app = App.get_running_app()
        d = date.fromisoformat(ev['date'])
        self.ev = ev
        self.category = ev['category']
        self.cat_color = cat_color(ev['category'])
        self.cover_tex, self.deco = cover_texture(ev.get('image'), ev['category'])
        self.day = str(d.day)
        self.month = MONTHS_SHORT[d.month - 1]
        self.title_text = ev['title']
        parts = [human_date(d), ev['time']]
        if ev.get('place'):
            parts.append(ev['place'])
        self.meta = '  ·  '.join(parts)
        cap = ev.get('capacity', 0)
        cnt = '%d/%d' % (ev['registered'], cap) if cap else str(ev['registered'])
        code, txt = reg_status(ev)
        if ev['id'] in app.state['regs']:
            self.count_text = 'Вы записаны · %s' % cnt
        elif code == 'open':
            self.count_text = 'Записались: %s' % cnt
        else:
            self.count_text = 'Набор: %s' % txt
        self.fav = ev['id'] in app.state['favs']

    def toggle_fav(self):
        app = App.get_running_app()
        app.toggle_fav(self.ev['id'])
        self.fav = self.ev['id'] in app.state['favs']
        feed = app.sm.get_screen('feed')
        if feed.mode == 'fav':
            feed.refresh()


class FeedScreen(Screen):
    mode = StringProperty('all')
    cat = StringProperty('Все')
    when = StringProperty('Любая дата')
    _seen = False

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.cat_chips = []
        for name in ['Все'] + CATEGORIES:
            chip = Chip(text=name, active=(name == 'Все'))
            chip.bind(on_release=lambda w: self.set_cat(w.text))
            self.ids.cat_row.add_widget(chip)
            self.cat_chips.append(chip)
        self.when_chips = []
        for name in WHEN:
            chip = Chip(text=name, active=(name == WHEN[0]))
            chip.bind(on_release=lambda w: self.set_when(w.text))
            self.ids.when_row.add_widget(chip)
            self.when_chips.append(chip)

    def on_pre_enter(self, *args):
        self.refresh(animate=not self._seen)
        self._seen = True

    def set_cat(self, name):
        self.cat = name
        for c in self.cat_chips:
            c.active = c.text == name
        self.refresh(animate=True)

    def set_when(self, name):
        self.when = name
        for c in self.when_chips:
            c.active = c.text == name
        self.refresh(animate=True)

    def set_mode(self, mode):
        self.mode = mode
        ids = self.ids
        ids.tab_all.active = mode == 'all'
        ids.tab_fav.active = mode == 'fav'
        ids.tab_my.active = mode == 'my'
        self.refresh(animate=True)

    def refresh(self, *args, animate=False):
        ids = self.ids
        app = App.get_running_app()
        if 'box' not in ids or not hasattr(app, 'state'):
            return
        q = ids.search.text.strip().lower()
        today = date.today()
        box = ids.box
        box.clear_widgets()
        titles = {'all': 'Ближайшие события', 'fav': 'Избранное', 'my': 'Мои записи'}
        box.add_widget(Txt(text=titles[self.mode], bold=True, font_size='20sp',
                           size_hint_y=None, height=dp(32)))
        cards = []
        events = sorted(app.state['events'], key=lambda e: (e['date'], e['time']))
        for ev in events:
            if self.mode == 'fav' and ev['id'] not in app.state['favs']:
                continue
            if self.mode == 'my' and ev['id'] not in app.state['regs']:
                continue
            if q and q not in ev['title'].lower():
                continue
            if self.cat != 'Все' and ev['category'] != self.cat:
                continue
            d = date.fromisoformat(ev['date'])
            if self.when == 'Сегодня' and d != today:
                continue
            if self.when == 'Эта неделя' and not (today <= d <= today + timedelta(days=7)):
                continue
            if self.when == 'Этот месяц' and not (today <= d <= today + timedelta(days=30)):
                continue
            card = EventCard()
            card.fill(ev)
            box.add_widget(card)
            cards.append(card)
        if not cards:
            empty = {'all': 'Ничего не найдено.\nПопробуйте изменить поиск или фильтры',
                     'fav': 'Здесь появятся события,\nкоторые вы добавите в избранное',
                     'my': 'Вы пока никуда не записались'}[self.mode]
            box.add_widget(Txt(text=empty, halign='center', color=(0.55, 0.55, 0.66, 1),
                               size_hint_y=None, height=dp(140)))
        if animate:
            for i, card in enumerate(cards):
                card.opacity = 0
                Clock.schedule_once(
                    lambda dt, c=card: Animation(opacity=1, duration=0.3).start(c),
                    0.05 * min(i, 6))
        ids.subtitle.text = 'Событий: %d  ·  Ваши записи: %d' % (
            len(app.state['events']), len(app.state['regs']))
