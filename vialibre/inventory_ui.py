from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TextNode


class InventoryUI:
    """
    Gère :
    - l'affichage de l'inventaire
    - la mise à jour de la quantité
    """

    def __init__(self, game):
        self.game = game
        self.create_inventory_ui()

    def create_inventory_ui(self):
        parent = base.a2dTopLeft

        self.inventory_bg = DirectFrame(
            parent=parent,
            frameColor=(0, 0, 0, 0.35),
            frameSize=(0.02, 0.62, -0.18, -0.02),
            pos=(0.02, 0, -0.02)
        )
        self.inventory_bg.setBin("fixed", 10)
        self.inventory_bg.setDepthWrite(False)
        self.inventory_bg.setDepthTest(False)

        self.inventory_title = OnscreenText(
            parent=parent,
            text="Inventaire",
            pos=(0.06, -0.08),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )
        self.inventory_title.setBin("fixed", 11)
        self.inventory_title.setDepthWrite(False)
        self.inventory_title.setDepthTest(False)

        self.resource_label = OnscreenText(
            parent=parent,
            text=f"Ressource : {self.game.inventory['ressource']}",
            pos=(0.06, -0.16),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            mayChange=True
        )
        self.resource_label.setBin("fixed", 11)
        self.resource_label.setDepthWrite(False)
        self.resource_label.setDepthTest(False)

    def update(self):
        self.resource_label.setText(
            f"Ressource : {self.game.inventory['ressource']}"
        )