from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TextNode


class InventoryUI:
    def __init__(self, game):
        self.game = game
        self.create_inventory_ui()

    def _prepare_gui_node(self, node, sort=20):
        node.setBin("fixed", sort)
        node.setDepthWrite(False)
        node.setDepthTest(False)

    def create_inventory_ui(self):
        parent = base.a2dTopLeft

        self.inventory_bg = DirectFrame(
            parent=parent,
            frameColor=(0.02, 0.02, 0.02, 0.72),
            frameSize=(0.00, 0.86, -0.24, 0.00),
            pos=(0.03, 0, -0.03),
        )
        self._prepare_gui_node(self.inventory_bg, 20)

        self.inventory_title = OnscreenText(
            parent=parent,
            text="INVENTAIRE",
            pos=(0.07, -0.075),
            scale=0.04,
            fg=(1, 0.95, 0.70, 1),
            align=TextNode.ALeft,
        )
        self._prepare_gui_node(self.inventory_title, 21)

        self.resource_label = OnscreenText(
            parent=parent,
            text="",
            pos=(0.07, -0.135),
            scale=0.043,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self._prepare_gui_node(self.resource_label, 21)

        self.help_label = OnscreenText(
            parent=parent,
            text="C : construire   E : recolter   U : ameliorer",
            pos=(0.07, -0.195),
            scale=0.032,
            fg=(0.82, 0.82, 0.82, 1),
            align=TextNode.ALeft,
        )
        self._prepare_gui_node(self.help_label, 21)

        self.update()

    def update(self):
        amount = self.game.inventory.get("ressource", 0)
        self.resource_label.setText(f"Ressources : {amount}")

    def set_visible(self, visible):
        action = "show" if visible else "hide"
        for node in (
            self.inventory_bg,
            self.inventory_title,
            self.resource_label,
            self.help_label,
        ):
            getattr(node, action)()
