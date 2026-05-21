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
            pos=(0.02, 0, -0.23),
        )
        self.root.setBin("fixed", 12)
        self.root.setDepthWrite(False)
        self.root.setDepthTest(False)

        self.label = OnscreenText(
            parent=parent,
            text="Vie joueur",
            pos=(0.06, -0.285),
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
            frameSize=(0.06, 0.58, -0.365, -0.325),
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
