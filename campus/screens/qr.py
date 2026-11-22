import os
from datetime import date
from kivy.app import App
from kivy.uix.screenmanager import Screen

from campus.config import MONTHS
from campus.helpers import event_payload


class QRScreen(Screen):
    ev = None
    kind = 'event'

    def show(self, ev, kind='event'):
        app = App.get_running_app()
        ids = self.ids
        self.ev = ev
        reg = app.state['regs'].get(ev['id'])
        if kind == 'ticket' and not reg:
            kind = 'event'
        self.kind = kind
        ids.b_event.bg = app.accent if kind == 'event' else (0.90, 0.89, 1, 1)
        ids.b_event.color = (1, 1, 1, 1) if kind == 'event' else app.accent
        ids.b_ticket.bg = app.accent if kind == 'ticket' else (0.90, 0.89, 1, 1)
        ids.b_ticket.color = (1, 1, 1, 1) if kind == 'ticket' else app.accent
        ids.b_ticket.opacity = 1 if reg else 0.4
        d = date.fromisoformat(ev['date'])
        when = '%d %s, %s' % (d.day, MONTHS[d.month - 1], ev['time'])
        if kind == 'event':
            ids.head.text = 'QR мероприятия'
            ids.p_title.text = ev['title']
            ids.p_sub.text = when + ('\n' + ev['place'] if ev.get('place') else '')
            ids.p_foot.text = 'Отсканируйте в CampusLife, чтобы записаться'
            ids.qr.data = event_payload(ev)
        else:
            ids.head.text = 'Мой билет'
            ids.p_title.text = 'Билет: ' + ev['title']
            who = reg['name'] + (', ' + reg['cls'] if reg['cls'] else '')
            ids.p_sub.text = who + '\n' + when
            ids.p_foot.text = 'Покажите организатору на входе'
            ids.qr.data = app.ticket_payload(ev, reg)

    def export(self, do_print):
        app = App.get_running_app()
        app.ask_perms(['android.permission.WRITE_EXTERNAL_STORAGE'])
        path = os.path.join(app.out_dir(), 'campuslife_%s_%s.png' % (self.kind, self.ev['id']))
        try:
            self.ids.poster.export_to_png(path)
        except Exception as e:
            app.toast('Не удалось сохранить: %s' % e)
            return
        if do_print and app.print_file(path):
            app.toast('Отправлено на печать')
        else:
            app.toast('Сохранено: %s' % path, 5)
