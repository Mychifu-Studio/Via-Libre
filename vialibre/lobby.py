from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.showbase.DirectObject import DirectObject
from panda3d.core import BitMask32, CollisionNode, CollisionSphere, Point3, TextNode, Vec3

from vialibre.characters import CHARACTERS, get_character_definition


class LobbyManager(DirectObject):
    START_ZONE_NAME = "lobby_start_zone"
    START_RADIUS = 2.2
    DEFAULT_START_POS = Point3(16, 1.5, 0)
    START_LABEL_GROUPS = (
        ("start", "launch", "lobby", "depart", "demarrer"),
        ("button", "switch", "console"),
        ("portal",),
    )

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.is_active = True
        self.player_inside_start_zone = False
        self.last_status_text = None
        self.last_character_id = None
        self.character_buttons = {}

        self.start_pos = self._find_start_position()
        self._create_ui()
        self._create_start_zone()

        self.accept("e", self.try_start_game)
        self.accept("arrow_left", self.select_previous_character)
        self.accept("arrow_right", self.select_next_character)
        for index, character in enumerate(CHARACTERS, start=1):
            self.accept(str(index), self.select_character, [character.id])
        self.accept(f"player-into-{self.START_ZONE_NAME}", self.on_start_zone_enter)
        self.accept(f"player-out-{self.START_ZONE_NAME}", self.on_start_zone_exit)

    def _find_start_position(self):
        map_collision = getattr(self.game, "map_collision", None)
        if map_collision is not None and hasattr(map_collision, "find_labeled_bounds"):
            for label_group in self.START_LABEL_GROUPS:
                bounds = map_collision.find_labeled_bounds(*label_group)
                if bounds is not None:
                    return Point3(bounds["center"])

        return Point3(self.DEFAULT_START_POS)

    def _prepare_gui_node(self, node, sort):
        node.setBin("fixed", sort)
        node.setDepthWrite(False)
        node.setDepthTest(False)

    def _create_ui(self):
        self.panel = DirectFrame(
            parent=self.game.aspect2d,
            frameColor=(0.018, 0.018, 0.018, 0.78),
            frameSize=(-0.86, 0.86, -0.115, 0.115),
            pos=(0, 0, 0.64),
        )
        self._prepare_gui_node(self.panel, 92)

        self.status_label = DirectLabel(
            parent=self.panel,
            text="",
            scale=0.04,
            pos=(0, 0, 0.025),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=34,
        )
        self._prepare_gui_node(self.status_label, 93)

        self.hint_label = DirectLabel(
            parent=self.panel,
            text="",
            scale=0.032,
            pos=(0, 0, -0.055),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 0.92, 0.58, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=38,
        )
        self._prepare_gui_node(self.hint_label, 93)

        self.character_panel = DirectFrame(
            parent=self.game.aspect2d,
            frameColor=(0.018, 0.018, 0.018, 0.82),
            frameSize=(-0.98, 0.98, -0.15, 0.15),
            pos=(0, 0, -0.78),
        )
        self._prepare_gui_node(self.character_panel, 92)

        self.character_title = DirectLabel(
            parent=self.character_panel,
            text="Choisis ton personnage",
            scale=0.04,
            pos=(0, 0, 0.08),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 0.94, 0.62, 1),
            text_align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.character_title, 93)

        self.character_label = DirectLabel(
            parent=self.character_panel,
            text="",
            scale=0.034,
            pos=(0, 0, -0.108),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.character_label, 93)

        start_x = -0.54
        spacing = 0.36
        for index, character in enumerate(CHARACTERS, start=1):
            button = DirectButton(
                parent=self.character_panel,
                text=f"{index}. {character.display_name}",
                scale=0.043,
                pos=(start_x + (index - 1) * spacing, 0, -0.02),
                pad=(0.28, 0.11),
                frameColor=(0.16, 0.16, 0.16, 0.95),
                text_fg=(1, 1, 1, 1),
                relief=1,
                command=self.select_character,
                extraArgs=[character.id],
            )
            self._prepare_gui_node(button, 94)
            self.character_buttons[character.id] = button

        self._refresh_character_ui()

    def _create_start_zone(self):
        cnode = CollisionNode(self.START_ZONE_NAME)
        cnode.addSolid(CollisionSphere(0, 0, 0, self.START_RADIUS))
        cnode.setIntoCollideMask(BitMask32.bit(1))
        cnode.setFromCollideMask(BitMask32.allOff())

        trigger_root = getattr(self.game, "trigger_collision_root", None)
        parent = trigger_root if trigger_root is not None and not trigger_root.isEmpty() else self.game.render
        self.zone_np = parent.attachNewNode(cnode)
        self.zone_np.setPos(self.start_pos)

        # self.marker = self.game.loader.loadModel("assets/sphere")
        # self.marker.reparentTo(self.game.render)
        # self.marker.setPos(self.start_pos)
        # self.marker.setScale(self.START_RADIUS)
        # self.marker.setTransparency(True)
        # self.marker.setAlphaScale(0.22)
        # self.marker.setColor(0.1, 0.95, 0.45, 1)

        # self.world_label_node = TextNode("lobby_start_label")
        # self.world_label_node.setText(self._start_label_text())
        # self.world_label_node.setTextColor(1, 0.95, 0.65, 1)
        # self.world_label_node.setAlign(TextNode.ACenter)
        # self.world_label_node.setCardColor(0, 0, 0, 0.62)
        # self.world_label_node.setCardAsMargin(0.25, 0.25, 0.12, 0.12)
        # self.world_label_node.setCardDecal(True)

        # self.world_label = self.game.render.attachNewNode(self.world_label_node)
        # self.world_label.setPos(self.start_pos.x, self.start_pos.y, self.start_pos.z + 1.7)
        # self.world_label.setScale(0.32)
        # self.world_label.setBillboardPointEye()
        # self.world_label.setDepthTest(False)
        # self.world_label.setDepthWrite(False)
        # self.world_label.setBin("fixed", 1)

    def _is_local_host(self):
        net_iface = getattr(self.game, "network", None)
        net = getattr(net_iface, "net", None) if net_iface is not None else None
        return net is None or net.is_host

    def _connected_player_count(self):
        net_iface = getattr(self.game, "network", None)
        if net_iface is None:
            return 1
        return 1 + len(getattr(net_iface, "other_players", {}))

    def _level_text(self):
        current_level = getattr(self.game, "current_level", 1)
        max_levels = getattr(self.game, "max_levels", 5)
        return f"Niveau {current_level}/{max_levels}"

    def _start_label_text(self):
        if getattr(self.game, "game_completed", False):
            return "Jeu termine"
        return f"Lancer {self._level_text().lower()}"

    def _selected_character_id(self):
        player = getattr(self.game, "player", None)
        return getattr(player, "selected_character_id", CHARACTERS[0].id)

    def _refresh_character_ui(self):
        selected_id = self._selected_character_id()
        if selected_id == self.last_character_id:
            return

        selected = get_character_definition(selected_id)
        self.character_label["text"] = f"Selection : {selected.display_name}  |  1-4 ou fleches"
        for character in CHARACTERS:
            button = self.character_buttons.get(character.id)
            if button is None:
                continue
            if character.id == selected.id:
                button["frameColor"] = (0.82, 0.55, 0.14, 1)
                button["text_fg"] = (0.08, 0.06, 0.03, 1)
            else:
                button["frameColor"] = (0.16, 0.16, 0.16, 0.95)
                button["text_fg"] = (1, 1, 1, 1)

        self.last_character_id = selected.id

    def select_character(self, character_id):
        if not self.is_active or getattr(self.game, "game_started", False):
            return

        player = getattr(self.game, "player", None)
        if player is None or not hasattr(player, "set_character"):
            return

        selected_id = player.set_character(character_id)
        self.last_character_id = None
        self._refresh_character_ui()

        selected = get_character_definition(selected_id)
        popup_ui = getattr(self.game, "popup_ui", None)
        if popup_ui is not None:
            popup_ui.show_popup(f"Personnage selectionne : {selected.display_name}.", duration=1.6)

    def select_previous_character(self):
        self._select_character_offset(-1)

    def select_next_character(self):
        self._select_character_offset(1)

    def _select_character_offset(self, offset):
        if not self.is_active:
            return

        current_id = self._selected_character_id()
        ids = [character.id for character in CHARACTERS]
        try:
            current_index = ids.index(current_id)
        except ValueError:
            current_index = 0
        self.select_character(ids[(current_index + offset) % len(ids)])

    def on_start_zone_enter(self, entry):
        if not self.is_active:
            return

        self.player_inside_start_zone = True
        if self._is_local_host():
            self.game.popup_ui.show_popup("Appuie sur E pour lancer la partie.", duration=4.0)
        else:
            self.game.popup_ui.show_popup("En attente du host pour lancer la partie.", duration=4.0)

    def on_start_zone_exit(self, entry):
        if not self.is_active:
            return

        self.player_inside_start_zone = False
        self.game.popup_ui.hide_popup()

    def try_start_game(self):
        if not self.is_active or getattr(self.game, "game_started", False):
            return

        if getattr(self.game, "game_completed", False):
            self.game.popup_ui.show_popup("Les 5 niveaux sont termines.")
            return

        if not self._is_local_host():
            self.game.popup_ui.show_popup("Seul le host peut lancer la partie.")
            return

        if not self.player_inside_start_zone and not self._is_player_near_start_zone():
            return

        self.game.start_game()

    def _is_player_near_start_zone(self):
        player = getattr(self.game, "player", None)
        player_np = getattr(player, "player", None)
        if player_np is None:
            return False

        player_pos = player_np.getPos(self.zone_np.getParent())
        offset = player_pos - self.zone_np.getPos()
        flat_offset = Vec3(offset.x, offset.y, 0)
        return flat_offset.lengthSquared() <= self.START_RADIUS * self.START_RADIUS

    def update(self):
        if not self.is_active:
            return

        self._refresh_character_ui()

        players = self._connected_player_count()
        plural = "s" if players > 1 else ""
        level_text = self._level_text()
        if getattr(self.game, "game_completed", False):
            status = f"Lobby - Jeu termine - {players} joueur{plural} connecte{plural}"
            hint = "Les 5 niveaux sont termines."
        elif self._is_local_host():
            status = f"Lobby - {level_text} - {players} joueur{plural} connecte{plural}"
            hint = "Va sur le point de depart et appuie sur E pour lancer."
        else:
            status = f"Lobby - {level_text} - {players} joueur{plural} connecte{plural}"
            hint = "En attente du host."

        # self.world_label_node.setText(self._start_label_text())

        next_text = (status, hint)
        if next_text == self.last_status_text:
            return

        self.status_label["text"] = status
        self.hint_label["text"] = hint
        self.last_status_text = next_text

    def finish(self):
        if not self.is_active:
            return

        self.is_active = False
        self.player_inside_start_zone = False

        self.panel.hide()
        self.character_panel.hide()
        self.zone_np.removeNode()
        # self.marker.removeNode()
        # self.world_label.removeNode()
        self.game.popup_ui.hide_popup()

        self.ignore("e")
        self.ignore("arrow_left")
        self.ignore("arrow_right")
        for index, _character in enumerate(CHARACTERS, start=1):
            self.ignore(str(index))
        self.ignore(f"player-into-{self.START_ZONE_NAME}")
        self.ignore(f"player-out-{self.START_ZONE_NAME}")
