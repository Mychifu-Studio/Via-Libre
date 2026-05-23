from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode


class PlayerHealthUI:
    """Affiche la barre de vie du joueur dans l'interface."""

    def __init__(self, game, player):
        self.game = game
        self.player = player

        parent = self.game.a2dTopLeft

        self.root = DirectFrame(
            parent=parent,
            frameColor=(0, 0, 0, 0.45),
            frameSize=(0.02, 0.62, -0.13, -0.02),
            pos=(0.02, 0, -0.27),
        )
        self.root.setBin("fixed", 12)
        self.root.setDepthWrite(False)
        self.root.setDepthTest(False)

        self.label = OnscreenText(
            parent=parent,
            text="Vie joueur",
            pos=(0.06, -0.325),
            scale=0.04,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.label.setBin("fixed", 13)
        self.label.setDepthWrite(False)
        self.label.setDepthTest(False)

        self.bar_bg = DirectFrame(
            parent=parent,
            frameColor=(0.08, 0.08, 0.08, 0.9),
            frameSize=(0.06, 0.58, -0.365, -0.355),
            pos=(0, 0, 0),
        )
        self.bar_bg.setBin("fixed", 13)
        self.bar_bg.setDepthWrite(False)
        self.bar_bg.setDepthTest(False)

        self.bar_fill = DirectFrame(
            parent=parent,
            frameColor=(0.15, 0.85, 0.28, 0.95),
            frameSize=(0.065, 0.575, -0.36, -0.33),
            pos=(0, 0, 0),
        )
        self.bar_fill.setBin("fixed", 14)
        self.bar_fill.setDepthWrite(False)
        self.bar_fill.setDepthTest(False)

        self.update()

    def update(self):
        hp = max(0, self.player.hp)
        max_hp = max(1, self.player.MAX_HP)
        ratio = max(0.0, min(1.0, hp / max_hp))
        fill_right = 0.065 + (0.575 - 0.065) * ratio

        if ratio > 0.55:
            color = (0.15, 0.85, 0.28, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)

        self.label.setText(f"Vie joueur : {hp}/{max_hp}")
        self.bar_fill["frameColor"] = color
        self.bar_fill["frameSize"] = (0.065, fill_right, -0.36, -0.33)

    def set_visible(self, visible):
        action = "show" if visible else "hide"
        for node in (self.root, self.label, self.bar_bg, self.bar_fill):
            getattr(node, action)()


class PipeHealthUI:
    """Affiche la barre de vie du tuyau a defendre."""

    def __init__(self, game, pipe_base):
        self.game = game
        self.pipe_base = pipe_base

        parent = self.game.a2dTopLeft

        self.root = DirectFrame(
            parent=parent,
            frameColor=(0, 0, 0, 0.45),
            frameSize=(0.02, 0.62, -0.13, -0.02),
            pos=(0.02, 0, -0.40),
        )
        self.root.setBin("fixed", 12)
        self.root.setDepthWrite(False)
        self.root.setDepthTest(False)

        self.label = OnscreenText(
            parent=parent,
            text="Vie tuyau",
            pos=(0.06, -0.455),
            scale=0.04,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self.label.setBin("fixed", 13)
        self.label.setDepthWrite(False)
        self.label.setDepthTest(False)

        self.bar_bg = DirectFrame(
            parent=parent,
            frameColor=(0.08, 0.08, 0.08, 0.9),
            frameSize=(0.06, 0.58, -0.495, -0.485),
            pos=(0, 0, 0),
        )
        self.bar_bg.setBin("fixed", 13)
        self.bar_bg.setDepthWrite(False)
        self.bar_bg.setDepthTest(False)

        self.bar_fill = DirectFrame(
            parent=parent,
            frameColor=(0.15, 0.65, 1.0, 0.95),
            frameSize=(0.065, 0.575, -0.49, -0.46),
            pos=(0, 0, 0),
        )
        self.bar_fill.setBin("fixed", 14)
        self.bar_fill.setDepthWrite(False)
        self.bar_fill.setDepthTest(False)

        self.update()

    def update(self):
        hp = max(0, self.pipe_base.hp)
        max_hp = max(1, self.pipe_base.MAX_HP)
        ratio = max(0.0, min(1.0, hp / max_hp))
        fill_right = 0.065 + (0.575 - 0.065) * ratio

        if ratio > 0.55:
            color = (0.15, 0.65, 1.0, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)

        self.label.setText(f"Vie tuyau : {hp}/{max_hp}")
        self.bar_fill["frameColor"] = color
        self.bar_fill["frameSize"] = (0.065, fill_right, -0.49, -0.46)

    def set_visible(self, visible):
        action = "show" if visible else "hide"
        for node in (self.root, self.label, self.bar_bg, self.bar_fill):
            getattr(node, action)()
