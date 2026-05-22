from direct.gui.DirectGui import DirectButton, DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import BitMask32, CollisionNode, CollisionSphere, TextNode


class UpgradeSystem:
    UPGRADE_ORDER = ("health", "damage", "harvest")
    UPGRADE_DEFS = {
        "health": {
            "title": "PV max",
            "effect": "+2 PV max",
            "base_cost": 3,
            "cost_step": 3,
            "max_level": 5,
        },
        "damage": {
            "title": "Degats",
            "effect": "+1 degat par tir",
            "base_cost": 5,
            "cost_step": 3,
            "max_level": 3,
        },
        "harvest": {
            "title": "Recolte",
            "effect": "-15% temps de recolte",
            "base_cost": 4,
            "cost_step": 3,
            "max_level": 4,
        },
    }

    def __init__(self, game, inventory_ui, popup_ui):
        self.game = game
        self.inventory_ui = inventory_ui
        self.popup_ui = popup_ui

        self.levels = {key: 0 for key in self.UPGRADE_ORDER}
        self.campfire_zones = []
        self.active_zone_names = set()
        self.is_open = False
        self.buttons = {}

        self._ensure_collision_system()
        self._create_ui()
        self._bind_inputs()

    def _ensure_collision_system(self):
        if not hasattr(self.game, "cTrav"):
            from panda3d.core import CollisionTraverser
            self.game.cTrav = CollisionTraverser()

        if not hasattr(self.game, "coll_handler"):
            from panda3d.core import CollisionHandlerEvent
            self.game.coll_handler = CollisionHandlerEvent()
            self.game.coll_handler.addInPattern("%fn-into-%in")
            self.game.coll_handler.addOutPattern("%fn-out-%in")

    def _bind_inputs(self):
        self.game.accept("u", self.toggle_panel)
        self.game.accept("1", self.try_upgrade, ["health"])
        self.game.accept("2", self.try_upgrade, ["damage"])
        self.game.accept("3", self.try_upgrade, ["harvest"])

    def _create_ui(self):
        self.frame = DirectFrame(
            parent=self.game.aspect2d,
            frameColor=(0.02, 0.02, 0.02, 0.9),
            frameSize=(-0.68, 0.68, -0.46, 0.46),
            pos=(0, 0, 0),
        )
        self.frame.setBin("fixed", 140)
        self.frame.setDepthWrite(False)
        self.frame.setDepthTest(False)

        self.title = OnscreenText(
            parent=self.frame,
            text="AMELIORATIONS DU FEU",
            pos=(0, 0.35),
            scale=0.052,
            fg=(1, 0.92, 0.58, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.title, 141)

        self.subtitle = OnscreenText(
            parent=self.frame,
            text="Achete avec tes ressources : 1 / 2 / 3",
            pos=(0, 0.275),
            scale=0.035,
            fg=(0.86, 0.86, 0.86, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.subtitle, 141)

        for index, key in enumerate(self.UPGRADE_ORDER, start=1):
            y = 0.24 - index * 0.18
            button = DirectButton(
                parent=self.frame,
                text="",
                pos=(0, 0, y),
                scale=0.043,
                frameSize=(-13.2, 13.2, -1.35, 1.35),
                frameColor=(0.16, 0.16, 0.16, 1),
                text_fg=(1, 1, 1, 1),
                text_align=TextNode.ALeft,
                text_pos=(-12.4, -0.35),
                relief=1,
                command=self.try_upgrade,
                extraArgs=[key],
            )
            button.setBin("fixed", 142)
            button.setDepthWrite(False)
            button.setDepthTest(False)
            self.buttons[key] = button

        self.close_button = DirectButton(
            parent=self.frame,
            text="Fermer [U]",
            pos=(0, 0, -0.405),
            scale=0.042,
            frameSize=(-3.2, 3.2, -0.75, 0.75),
            frameColor=(0.35, 0.12, 0.10, 1),
            text_fg=(1, 1, 1, 1),
            relief=1,
            command=self.close_panel,
        )
        self.close_button.setBin("fixed", 142)
        self.close_button.setDepthWrite(False)
        self.close_button.setDepthTest(False)

        self.update_ui()
        self.frame.hide()

    def _prepare_gui_node(self, node, sort):
        node.setBin("fixed", sort)
        node.setDepthWrite(False)
        node.setDepthTest(False)

    def generate_campfire_zones(self):
        map_collision = getattr(self.game, "map_collision", None)
        if map_collision is None or not hasattr(map_collision, "get_campfire_zone_definitions"):
            return

        zones = map_collision.get_campfire_zone_definitions()
        if not zones:
            print("Aucun feu de camp trouve pour les ameliorations.")
            return

        for index, zone in enumerate(zones):
            self.create_campfire_zone((zone.x, zone.y, 0), zone.radius, index)

    def create_campfire_zone(self, pos, radius, zone_id):
        zone_name = f"upgrade_zone_{zone_id}"

        cnode = CollisionNode(zone_name)
        cnode.addSolid(CollisionSphere(0, 0, 0, radius))
        cnode.setIntoCollideMask(BitMask32.bit(1))
        cnode.setFromCollideMask(BitMask32.allOff())

        zone_np = self.game.render.attachNewNode(cnode)
        zone_np.setPos(*pos)
        self.campfire_zones.append(zone_np)

        self.game.accept(f"player-into-{zone_name}", self.on_campfire_enter)
        self.game.accept(f"player-out-{zone_name}", self.on_campfire_exit)

    def on_campfire_enter(self, entry):
        if not getattr(self.game, "game_started", False):
            return

        zone_name = entry.getIntoNodePath().getName()
        self.active_zone_names.add(zone_name)
        self.popup_ui.show_popup("Feu de camp : U pour ameliorer tes stats.", duration=4.0)

    def on_campfire_exit(self, entry):
        zone_name = entry.getIntoNodePath().getName()
        self.active_zone_names.discard(zone_name)
        if not self.active_zone_names:
            self.close_panel()
            self.popup_ui.hide_popup()

    def toggle_panel(self):
        if self.is_open:
            self.close_panel()
            return

        if not self.active_zone_names:
            self.popup_ui.show_popup("Approche-toi du feu de camp pour ameliorer tes stats.")
            return

        self.open_panel()

    def open_panel(self):
        self.is_open = True
        self.update_ui()
        self.frame.show()
        self.game.player.is_paused = True
        self.game.player.camera.mouse.showCursor()

    def close_panel(self):
        if not self.is_open:
            return

        self.is_open = False
        self.frame.hide()
        menu = getattr(self.game, "menu", None)
        if not getattr(menu, "is_open", False):
            self.game.player.is_paused = False
            self.game.player.camera.mouse.centerMouse()

    def _cost_for(self, key):
        data = self.UPGRADE_DEFS[key]
        return data["base_cost"] + self.levels[key] * data["cost_step"]

    def _is_maxed(self, key):
        return self.levels[key] >= self.UPGRADE_DEFS[key]["max_level"]

    def try_upgrade(self, key):
        if not self.active_zone_names:
            self.popup_ui.show_popup("Il faut etre pres du feu de camp.")
            return

        if self._is_maxed(key):
            self.popup_ui.show_popup("Cette amelioration est deja au niveau max.")
            self.update_ui()
            return

        cost = self._cost_for(key)
        resources = self.game.inventory.get("ressource", 0)
        if resources < cost:
            missing = cost - resources
            self.popup_ui.show_popup(f"Ressources insuffisantes : il en manque {missing}.")
            self.update_ui()
            return

        self.game.inventory["ressource"] = resources - cost
        self.levels[key] += 1
        self._apply_upgrade(key)
        self.inventory_ui.update()
        self.update_ui()

        title = self.UPGRADE_DEFS[key]["title"]
        level = self.levels[key]
        self.popup_ui.show_popup(f"{title} ameliore au niveau {level} !")

    def _apply_upgrade(self, key):
        if key == "health":
            self.game.player.upgrade_max_hp(2)
        elif key == "damage":
            self.game.player.upgrade_damage(1)
        elif key == "harvest":
            self.game.player.upgrade_harvest_speed(0.15)
            if hasattr(self.game, "resource_system"):
                self.game.resource_system.refresh_current_harvest_time()

    def update_ui(self):
        resources = self.game.inventory.get("ressource", 0)
        self.subtitle.setText(f"Ressources : {resources}   |   1 / 2 / 3 pour acheter")

        for index, key in enumerate(self.UPGRADE_ORDER, start=1):
            data = self.UPGRADE_DEFS[key]
            level = self.levels[key]
            max_level = data["max_level"]
            if self._is_maxed(key):
                cost_text = "MAX"
                color = (0.12, 0.25, 0.14, 1)
            else:
                cost = self._cost_for(key)
                cost_text = f"{cost} ressources"
                color = (0.18, 0.18, 0.18, 1) if resources >= cost else (0.25, 0.12, 0.10, 1)

            current_text = self._current_value_text(key)
            self.buttons[key]["text"] = (
                f"{index}. {data['title']}  niv. {level}/{max_level}  cout : {cost_text}\n"
                f"{data['effect']}  |  actuel : {current_text}"
            )
            self.buttons[key]["frameColor"] = color

    def _current_value_text(self, key):
        if key == "health":
            return f"{self.game.player.MAX_HP} PV"
        if key == "damage":
            return f"{self.game.player.damage} degat(s)"
        if key == "harvest":
            multiplier = getattr(self.game.player, "harvest_time_multiplier", 1.0)
            faster_percent = int(round((1.0 - multiplier) * 100))
            return f"{faster_percent}% plus rapide"
        return "-"

    def update(self):
        if self.is_open:
            self.update_ui()
