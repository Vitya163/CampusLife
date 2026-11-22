from kivy.app import App
from kivy.uix.screenmanager import Screen

from campus.helpers import ago
from campus.widgets import EmptyState, NotifItem


class NotifScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh()

    def on_enter(self, *args):
        app = App.get_running_app()
        for n in app.state['notifs']:
            n['read'] = True
        app.update_unread()
        app.save()

    def refresh(self):
        app = App.get_running_app()
        box = self.ids.box
        box.clear_widgets()
        if not app.state['notifs']:
            box.add_widget(EmptyState(
                kind='bell',
                text='Пока уведомлений нет.\nЗдесь появятся новости о наборе\nи скором старте событий'))
        for n in app.state['notifs']:
            box.add_widget(NotifItem(title=n['title'], text=n['text'],
                                     when=ago(n['ts']), unread=not n.get('read')))
