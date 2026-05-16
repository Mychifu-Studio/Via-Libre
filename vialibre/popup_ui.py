from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TextNode


class PopupUI:
    """
    Gère :
    - les popups d'information
    - l'affichage de la progression
    """

    def __init__(self, game):
        self.game = game
        self.create_popup_ui()
        self.create_progress_ui()

    def create_popup_ui(self):
        self.popup_bg = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0, 0, 0, 0.65),
            frameSize=(-0.75, 0.75, -0.09, 0.09),
            pos=(0, 0, 0.82)
        )
        self.popup_bg.setBin("fixed", 100)
        self.popup_bg.setDepthWrite(False)
        self.popup_bg.setDepthTest(False)
        self.popup_bg.hide()

        self.popup = OnscreenText(
            parent=base.aspect2d,
            text="",
            pos=(0, 0.80),
            scale=0.06,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            mayChange=True
        )
        self.popup.setBin("fixed", 101)
        self.popup.setDepthWrite(False)
        self.popup.setDepthTest(False)
        self.popup.hide()

    def create_progress_ui(self):
        self.progress_text = OnscreenText(
            parent=base.aspect2d,
            text="",
            pos=(0, 0.70),
            scale=0.05,
            fg=(1, 1, 0.8, 1),
            align=TextNode.ACenter,
            mayChange=True
        )
        self.progress_text.setBin("fixed", 102)
        self.progress_text.setDepthWrite(False)
        self.progress_text.setDepthTest(False)
        self.progress_text.hide()

    def show_popup(self, message):
        self.popup.setText(message)
        self.popup_bg.show()
        self.popup.show()

    def hide_popup(self):
        self.popup.hide()
        self.popup_bg.hide()

    def show_progress(self, message):
        self.progress_text.setText(message)
        self.progress_text.show()

    def hide_progress(self):
        self.progress_text.hide()