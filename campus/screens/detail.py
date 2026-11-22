from datetime import date
from kivy.app import App
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.screenmanager import Screen

from campus.config import MONTHS, REMINDERS, WEEK
from campus.helpers import cat_color, cover_texture, reg_status
from campus.widgets import Chip


class DetailScreen(Screen):
    ev = None
    hero_tex = ObjectProperty(None, allownone=True)
    hero_deco = BooleanProperty(True)

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.rem_chips = []
        for name in REMINDERS:
            chip = Chip(text=name)
            chip.bind(on_release=lambda w: self.on_rem(w.text))
            self.ids.rem_row.add_widget(chip)
            self.rem_chips.append(chip)

    def show(self, ev):
        app = App.get_running_app()
        ids = self.ids
        self.ev = ev
        d = date.fromisoformat(ev['date'])
        self.hero_tex, self.hero_deco = cover_texture(ev.get('image'), ev['category'])
        ids.cat_pill.text = ev['category']
        ids.cat_pill.color = cat_color(ev['category'])
        ids.title.text = ev['title']
        ids.t_date.value = '%s, %d %s' % (WEEK[d.weekday()], d.day, MONTHS[d.month - 1])
        ids.t_time.value = ev['time']
        ids.t_place.value = ev['place'] or 'Уточняется'
        ids.info.text = ev['desc'] or 'Описание пока не добавлено.'
        days = app.state['reminders'].get(ev['id'], 0)
        for chip in self.rem_chips:
            chip.active = REMINDERS[chip.text] == days
        ids.scroll.scroll_y = 1
        self.update_buttons()

    def update_buttons(self, *args):
        app = App.get_running_app()
        ev = self.ev
        ids = self.ids
        signed = ev['id'] in app.state['regs']
        code, txt = reg_status(ev)
        if signed:
            ids.signup.text = 'Отменить запись'
            ids.signup.bg = (0.99, 0.89, 0.89, 1)
            ids.signup.color = (0.85, 0.22, 0.28, 1)
        elif code == 'open':
            ids.signup.text = 'Записаться'
            ids.signup.bg = app.accent
            ids.signup.color = (1, 1, 1, 1)
        else:
            ids.signup.text = {'wait': 'Набор не открыт', 'closed': 'Набор закрыт',
                               'full': 'Мест нет'}[code]
            ids.signup.bg = (0.90, 0.90, 0.94, 1)
            ids.signup.color = (0.50, 0.50, 0.60, 1)
        if ev['id'] in app.state['favs']:
            ids.fav.text = 'В избранном'
            ids.fav.bg = (0.90, 0.89, 1, 1)
            ids.fav.color = app.accent
        else:
            ids.fav.text = 'В избранное'
            ids.fav.bg = (0.93, 0.93, 0.96, 1)
            ids.fav.color = (0.38, 0.38, 0.48, 1)
        cap = ev.get('capacity', 0)
        ids.t_count.value = ('%d из %d' % (ev['registered'], cap)) if cap else '%d чел.' % ev['registered']
        ids.t_reg.value = txt[:1].upper() + txt[1:]

    def toggle_signup(self):
        app = App.get_running_app()
        if self.ev['id'] in app.state['regs']:
            app.cancel_registration(self.ev, self.update_buttons)
        else:
            app.register(self.ev, self.update_buttons)

    def toggle_fav(self):
        App.get_running_app().toggle_fav(self.ev['id'])
        self.update_buttons()

    def on_rem(self, name):
        if not self.ev:
            return
        app = App.get_running_app()
        app.state['reminders'][self.ev['id']] = REMINDERS.get(name, 0)
        app.save()
        for chip in self.rem_chips:
            chip.active = chip.text == name
