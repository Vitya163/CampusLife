from kivy.app import App
from kivy.uix.screenmanager import Screen

from campus.config import LEADS, ROW_KEYS
from campus.widgets import Chip


class SettingsScreen(Screen):
    _loading = False

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.lead_chips = []
        for name in LEADS:
            chip = Chip(text=name)
            chip.bind(on_release=lambda w: self.set_lead(w.text))
            self.ids.lead_row.add_widget(chip)
            self.lead_chips.append(chip)

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        s = app.state['settings']
        self._loading = True
        for key in ROW_KEYS:
            self.ids['r_' + key].ids.tg.active = bool(s.get(key))
        self.ids.p_name.text = app.state['profile']['name']
        self.ids.p_cls.text = app.state['profile']['cls']
        self.ids.server.text = s.get('server', '')
        for c in self.lead_chips:
            c.active = LEADS[c.text] == s['lead']
        self._loading = False

    def set_lead(self, name):
        App.get_running_app().set_opt('lead', LEADS[name])
        for c in self.lead_chips:
            c.active = c.text == name

    def save_profile(self):
        if self._loading:
            return
        app = App.get_running_app()
        app.state['profile'] = {'name': self.ids.p_name.text.strip(),
                                'cls': self.ids.p_cls.text.strip()}
        app.save()

    def save_server(self):
        if self._loading:
            return
        App.get_running_app().set_opt('server', self.ids.server.text.strip())

    def test_server(self):
        app = App.get_running_app()
        if not app.server():
            app.toast('Адрес сервера не указан — работаем автономно')
            return
        app.api('/ping', None, lambda res: app.toast('Сервер отвечает'),
                lambda msg: app.toast(msg))
