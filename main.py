from kivy.core.window import Window
from kivy.utils import platform

Window.clearcolor = (0.95, 0.95, 0.98, 1)
if platform not in ('android', 'ios'):
    Window.size = (400, 780)
else:
    Window.softinput_mode = 'below_target'

from campus.app import CampusApp

if __name__ == '__main__':
    CampusApp().run()
