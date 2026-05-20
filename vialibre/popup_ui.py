from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TextNode


class PopupUI:
    
    def __init__(self, game):
        self.game = game
        self.popup_timer = 0.0
        self.popup_task_name = "popup_auto_hide_task"
        self.create_popup_ui()
        self.create_progress_ui()
        self.game.taskMgr.add(self.update, self.popup_task_name)

    def _prepare_gui_node(self, node, sort):
        node.setBin("fixed", sort)
        node.setDepthWrite(False)
        node.setDepthTest(False)

    def create_popup_ui(self):
        self.popup_bg = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0.02, 0.02, 0.02, 0.78),
            frameSize=(-0.95, 0.95, -0.075, 0.075),
            pos=(0, 0, -0.82),
        )
        self._prepare_gui_node(self.popup_bg, 100)
        self.popup_bg.hide()

        self.popup = OnscreenText(
            parent=base.aspect2d,
            text="",
            pos=(0, -0.842),
            scale=0.043,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            mayChange=True,
            wordwrap=36,
        )
        self._prepare_gui_node(self.popup, 101)
        self.popup.hide()

    def create_progress_ui(self):
        self.progress_bg = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0.02, 0.02, 0.02, 0.70),
            frameSize=(-0.70, 0.70, -0.06, 0.06),
            pos=(0, 0, -0.67),
        )
        self._prepare_gui_node(self.progress_bg, 98)
        self.progress_bg.hide()

        self.progress_text = OnscreenText(
            parent=base.aspect2d,
            text="",
            pos=(0, -0.69),
            scale=0.04,
            fg=(1, 0.95, 0.65, 1),
            align=TextNode.ACenter,
            mayChange=True,
            wordwrap=28,
        )
        self._prepare_gui_node(self.progress_text, 99)
        self.progress_text.hide()

    def show_popup(self, message, duration=2.0):
        self.popup.setText(message)
        self.popup_bg.show()
        self.popup.show()
        self.popup_timer = duration

    def hide_popup(self):
        self.popup_timer = 0.0
        self.popup.hide()
        self.popup_bg.hide()

    def show_progress(self, message):
        self.progress_text.setText(message)
        self.progress_bg.show()
        self.progress_text.show()

    def hide_progress(self):
        self.progress_text.hide()
        self.progress_bg.hide()

    def update(self, task):
        if self.popup_timer > 0:
            self.popup_timer -= globalClock.getDt()  # pyright: ignore
            if self.popup_timer <= 0:
                self.hide_popup()

        return task.cont
