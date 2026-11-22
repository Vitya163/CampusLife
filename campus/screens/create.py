import uuid
from datetime import date, datetime
from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from campus.config import CATEGORIES
from campus.helpers import human_date, start_dt
from campus.widgets import Chip


class CreateScreen(Screen):
    cat = StringProperty('Спорт')

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.chips = []
        for name in CATEGORIES:
            chip = Chip(text=name, active=(name == self.cat))
            chip.bind(on_release=lambda w: self.pick(w.text))
            self.ids.cat_row.add_widget(chip)
            self.chips.append(chip)

    def pick(self, name):
        self.cat = name
        for c in self.chips:
            c.active = c.text == name

    def save(self):
        app = App.get_running_app()
        ids = self.ids
        title = ids.title.text.strip()
        if not title:
            ids.msg.text = 'Введите название'
            return
        dt = ids.dt.text.strip()
        tm = ids.tm.text.strip() or '12:00'
        try:
            date.fromisoformat(dt)
            datetime.strptime(tm, '%H:%M')
        except ValueError:
            ids.msg.text = 'Дата — ГГГГ-ММ-ДД, время — ЧЧ:ММ'
            return
        ro = ids.ro.text.strip() or date.today().isoformat()
        try:
            date.fromisoformat(ro)
        except ValueError:
            ids.msg.text = 'Начало набора — в формате ГГГГ-ММ-ДД'
            return
        ev = dict(id='ev-' + uuid.uuid4().hex[:10], title=title, desc=ids.desc.text.strip(),
                  category=self.cat, date=dt, time=tm, place=ids.place.text.strip(),
                  registered=0, capacity=int(ids.cap.text or 0), reg_open=ro,
                  image='', mine=True)
        if start_dt(ev) <= datetime.now():
            ids.msg.text = 'Это время уже прошло'
            return
        app.state['events'].append(ev)
        app.state['sent'].append('open:' + ev['id'])
        app.save()
        for key in ('title', 'desc', 'place', 'dt', 'tm', 'cap', 'ro', 'msg'):
            ids[key].text = ''
        self.pick('Спорт')
        if app.notify('new:' + ev['id'], 'Новое мероприятие', '«%s» — %s, %s' % (
                title, human_date(date.fromisoformat(dt)), tm), 'new'):
            app.show_toast('Новое мероприятие', '«%s» опубликовано' % title)
        app.go('feed', 'right')
