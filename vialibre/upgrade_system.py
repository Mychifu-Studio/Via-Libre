from direct.gui.DirectGui import DirectButton, DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import BitMask32, CollisionNode, CollisionSphere, TextNode


class UpgradeSystem:
    UPGRADE_ORDER = ("health", "damage", "harvest")
    UPGRADE_DEFS = {
        "health": {
            "title": "PV max",
            "tag": "SURVIE",
            "symbol": "PV",
            "effect": "+2 PV max",
            "color": (0.22, 0.78, 0.38, 1),
            "base_cost": 3,
            "cost_step": 3,
            "max_level": 5,
        },
        "damage": {
            "title": "Degats",
            "tag": "COMBAT",
            "symbol": "DMG",
            "effect": "+1 degat par tir",
            "color": (0.92, 0.35, 0.25, 1),
            "base_cost": 5,
            "cost_step": 3,
            "max_level": 3,
        },
        "harvest": {
            "title": "Recolte",
            "tag": "OUTIL",
            "symbol": "REC",
            "effect": "-15% temps de recolte",
            "color": (0.42, 0.62, 0.95, 1),
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
        self.rows = {}

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
            frameColor=(0.015, 0.016, 0.018, 0.94),
            frameSize=(-0.64, 0.64, -0.48, 0.48),
            pos=(0, 0, 0),
        )
        self.frame.setBin("fixed", 140)
        self.frame.setDepthWrite(False)
        self.frame.setDepthTest(False)

        self.header_bg = DirectFrame(
            parent=self.frame,
            frameColor=(0.10, 0.08, 0.055, 0.98),
            frameSize=(-0.64, 0.64, 0.255, 0.48),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(self.header_bg, 141)

        self.header_line = DirectFrame(
            parent=self.frame,
            frameColor=(1.0, 0.67, 0.25, 1),
            frameSize=(-0.64, 0.64, 0.245, 0.255),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(self.header_line, 142)

        self.title = OnscreenText(
            parent=self.frame,
            text="FEU DE CAMP",
            pos=(-0.53, 0.395),
            scale=0.052,
            fg=(1, 0.90, 0.58, 1),
            align=TextNode.ALeft,
        )
        self._prepare_gui_node(self.title, 143)

        self.subtitle = OnscreenText(
            parent=self.frame,
            text="Ameliorations disponibles",
            pos=(-0.53, 0.325),
            scale=0.032,
            fg=(0.88, 0.83, 0.72, 1),
            align=TextNode.ALeft,
        )
        self._prepare_gui_node(self.subtitle, 143)

        self.resource_badge = DirectFrame(
            parent=self.frame,
            frameColor=(0.18, 0.16, 0.10, 1),
            frameSize=(-0.20, 0.20, -0.052, 0.052),
            pos=(0.31, 0, 0.36),
        )
        self._prepare_gui_node(self.resource_badge, 143)

        self.resource_label = OnscreenText(
            parent=self.frame,
            text="",
            pos=(0.31, 0.342),
            scale=0.034,
            fg=(1, 0.94, 0.72, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._prepare_gui_node(self.resource_label, 144)

        self.close_button = DirectButton(
            parent=self.frame,
            text="X",
            pos=(0.57, 0, 0.395),
            scale=0.05,
            frameSize=(-0.72, 0.72, -0.60, 0.60),
            frameColor=(0.34, 0.11, 0.09, 1),
            text_fg=(1, 0.92, 0.88, 1),
            relief=1,
            command=self.close_panel,
        )
        self.close_button.setBin("fixed", 144)
        self.close_button.setDepthWrite(False)
        self.close_button.setDepthTest(False)

        for index, key in enumerate(self.UPGRADE_ORDER, start=1):
            self._create_upgrade_row(index, key, 0.17 - (index - 1) * 0.20)

        self.footer_text = OnscreenText(
            parent=self.frame,
            text="1 / 2 / 3 pour acheter - U pour fermer",
            pos=(0, -0.41),
            scale=0.027,
            fg=(0.72, 0.72, 0.72, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.footer_text, 143)

        self.update_ui()
        self.frame.hide()

    def _prepare_gui_node(self, node, sort):
        node.setBin("fixed", sort)
        node.setDepthWrite(False)
        node.setDepthTest(False)

    def _create_upgrade_row(self, index, key, y):
        data = self.UPGRADE_DEFS[key]
        accent_color = data["color"]

        button = DirectButton(
            parent=self.frame,
            text="",
            pos=(0, 0, y),
            frameSize=(-0.56, 0.56, -0.075, 0.075),
            frameColor=(0.105, 0.108, 0.115, 1),
            relief=1,
            command=self.try_upgrade,
            extraArgs=[key],
        )
        button.setBin("fixed", 142)
        button.setDepthWrite(False)
        button.setDepthTest(False)
        self.buttons[key] = button

        accent = DirectFrame(
            parent=button,
            frameColor=accent_color,
            frameSize=(-0.56, -0.535, -0.075, 0.075),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(accent, 143)

        badge = DirectFrame(
            parent=button,
            frameColor=(accent_color[0] * 0.22, accent_color[1] * 0.22, accent_color[2] * 0.22, 1),
            frameSize=(-0.515, -0.405, -0.046, 0.046),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(badge, 143)

        symbol = OnscreenText(
            parent=button,
            text=data["symbol"],
            pos=(-0.46, -0.017),
            scale=0.032,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(symbol, 144)

        shortcut = OnscreenText(
            parent=button,
            text=str(index),
            pos=(-0.535, 0.046),
            scale=0.024,
            fg=(0.06, 0.055, 0.045, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(shortcut, 144)

        tag = OnscreenText(
            parent=button,
            text=data["tag"],
            pos=(-0.36, 0.033),
            scale=0.021,
            fg=accent_color,
            align=TextNode.ALeft,
        )
        self._prepare_gui_node(tag, 144)

        title = OnscreenText(
            parent=button,
            text=data["title"],
            pos=(-0.36, -0.006),
            scale=0.034,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft,
        )
        self._prepare_gui_node(title, 144)

        effect = OnscreenText(
            parent=button,
            text=data["effect"],
            pos=(-0.36, -0.047),
            scale=0.024,
            fg=(0.78, 0.80, 0.84, 1),
            align=TextNode.ALeft,
            wordwrap=18,
        )
        self._prepare_gui_node(effect, 144)

        value = OnscreenText(
            parent=button,
            text="",
            pos=(-0.05, 0.03),
            scale=0.027,
            fg=(0.92, 0.92, 0.92, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self._prepare_gui_node(value, 144)

        level_label = OnscreenText(
            parent=button,
            text="",
            pos=(-0.05, -0.045),
            scale=0.023,
            fg=(0.70, 0.72, 0.76, 1),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self._prepare_gui_node(level_label, 144)

        pips = []
        for pip_index in range(data["max_level"]):
            pip = DirectFrame(
                parent=button,
                frameColor=(0.06, 0.065, 0.075, 1),
                frameSize=(-0.012, 0.012, -0.013, 0.013),
                pos=(0.085 + pip_index * 0.034, 0, -0.037),
            )
            self._prepare_gui_node(pip, 144)
            pips.append(pip)

        cost_bg = DirectFrame(
            parent=button,
            frameColor=(0.16, 0.14, 0.10, 1),
            frameSize=(0.34, 0.525, -0.044, 0.044),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(cost_bg, 143)

        cost = OnscreenText(
            parent=button,
            text="",
            pos=(0.432, -0.014),
            scale=0.026,
            fg=(1, 0.94, 0.72, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )
        self._prepare_gui_node(cost, 144)

        self.rows[key] = {
            "button": button,
            "cost_bg": cost_bg,
            "cost": cost,
            "value": value,
            "level_label": level_label,
            "pips": pips,
        }

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

        net_iface = getattr(self.game, "network", None)
        is_client = (
            net_iface is not None
            and getattr(net_iface, "net", None) is not None
            and not net_iface.net.is_host
        )
        if is_client:
            net_iface.net.send_msg("upgrade_request", {"key": key})
            self.popup_ui.show_popup("Achat demande...")
            return

        self.game.inventory["ressource"] = resources - cost
        self.levels[key] += 1
        self._apply_upgrade(key)
        self.inventory_ui.update()
        self.update_ui()

        title = self.UPGRADE_DEFS[key]["title"]
        level = self.levels[key]
        self.popup_ui.show_popup(f"{title} ameliore au niveau {level} !")
        if net_iface is not None and getattr(net_iface, "net", None) is not None and net_iface.net.is_host:
            net_iface._broadcast_snapshot(force=True)

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
        self.resource_label.setText(f"{resources} res.")

        for key in self.UPGRADE_ORDER:
            data = self.UPGRADE_DEFS[key]
            row = self.rows[key]
            level = self.levels[key]
            max_level = data["max_level"]
            accent_color = data["color"]

            if self._is_maxed(key):
                cost_text = "MAX"
                row_color = (0.075, 0.15, 0.095, 1)
                cost_color = (0.09, 0.24, 0.12, 1)
            else:
                cost = self._cost_for(key)
                cost_text = f"{cost} res."
                if resources >= cost:
                    row_color = (0.105, 0.108, 0.115, 1)
                    cost_color = (0.18, 0.16, 0.10, 1)
                else:
                    row_color = (0.145, 0.085, 0.080, 1)
                    cost_color = (0.27, 0.10, 0.08, 1)

            row["button"]["frameColor"] = row_color
            row["cost_bg"]["frameColor"] = cost_color
            row["cost"].setText(cost_text)
            row["value"].setText(self._current_value_text(key))
            row["level_label"].setText(f"niveau {level}/{max_level}")

            for pip_index, pip in enumerate(row["pips"]):
                if pip_index < level:
                    pip["frameColor"] = accent_color
                else:
                    pip["frameColor"] = (0.055, 0.060, 0.070, 1)

    def _current_value_text(self, key):
        if key == "health":
            return f"{self.game.player.MAX_HP} PV"
        if key == "damage":
            return f"{self.game.player.damage} dmg"
        if key == "harvest":
            multiplier = getattr(self.game.player, "harvest_time_multiplier", 1.0)
            faster_percent = int(round((1.0 - multiplier) * 100))
            return f"{faster_percent}% rapide"
        return "-"

    def update(self):
        if self.is_open:
            self.update_ui()
