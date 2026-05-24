import os

from direct.gui.DirectGui import DirectFrame, DirectLabel
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.DirectObject import DirectObject
from panda3d.core import BitMask32, CollisionNode, CollisionSphere, Point3, TextNode, TransparencyAttrib


class LobbyManual:
    PAGE_PATHS = (
        "./assets/manual/1.png",
        "./assets/manual/2.png",
        "./assets/manual/3.png",
        "./assets/manual/4.png",
    )

    def __init__(self, game, prepare_gui_node):
        self.game = game
        self.prepare_gui_node = prepare_gui_node
        self.page_index = 0
        self.visible = False
        self.previous_player_pause = None

        self.root = DirectFrame(
            parent=self.game.aspect2d,
            frameColor=(0, 0, 0, 0.9),
            frameSize=(-2.0, 2.0, -1.0, 1.0),
            pos=(0, 0, 0),
        )
        self.prepare_gui_node(self.root, 180)
        self.root.hide()

        self.pages = []
        for path in self.PAGE_PATHS:
            if not os.path.exists(path):
                continue

            image = OnscreenImage(
                parent=self.root,
                image=path,
                pos=(0, 0, 0),
                scale=(self._aspect_ratio(), 1, 1),
            )
            image.setTransparency(TransparencyAttrib.MAlpha)
            self.prepare_gui_node(image, 181)
            image.hide()
            self.pages.append(image)

    def _aspect_ratio(self):
        return max(1.0, self.game.getAspectRatio())

    def _resize_to_window(self):
        aspect = self._aspect_ratio()
        self.root["frameSize"] = (-aspect, aspect, -1, 1)
        for page in self.pages:
            page.setScale(aspect, 1, 1)

    def _set_page(self, index):
        if not self.pages:
            return

        self.page_index = max(0, min(index, len(self.pages) - 1))
        for page_number, page in enumerate(self.pages):
            if page_number == self.page_index:
                page.show()
            else:
                page.hide()

    def show(self):
        if self.visible or not self.pages:
            return

        player = getattr(self.game, "player", None)
        if player is not None:
            self.previous_player_pause = player.is_paused
            player.is_paused = True
            player.movementVector.set(0, 0, 0)
            player.lastMovement.set(0, 0, 0)

        self._resize_to_window()
        self._set_page(self.page_index)
        self.root.show()
        self.visible = True

    def hide(self):
        if not self.visible:
            return

        self.root.hide()
        self.visible = False

        player = getattr(self.game, "player", None)
        if player is not None and self.previous_player_pause is not None:
            player.is_paused = self.previous_player_pause
            if not player.is_paused:
                player.camera.mouse.centerMouse()
        self.previous_player_pause = None

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def next_page(self):
        if self.visible:
            self._set_page(self.page_index + 1)

    def previous_page(self):
        if self.visible:
            self._set_page(self.page_index - 1)

    def destroy(self):
        self.hide()
        for page in self.pages:
            page.destroy()
        self.root.destroy()


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

        self.start_pos = self._find_start_position()
        self._create_ui()
        self.manual = LobbyManual(self.game, self._prepare_gui_node)
        self._create_start_zone()

        self.accept("e", self.try_start_game)
        self.accept("m", self.toggle_manual)
        self.accept("arrow_right", self.next_manual_page)
        self.accept("arrow_down", self.next_manual_page)
        self.accept("arrow_left", self.previous_manual_page)
        self.accept("arrow_up", self.previous_manual_page)
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

        if self.manual.visible:
            return

        if getattr(self.game, "game_completed", False):
            self.game.popup_ui.show_popup("Les 5 niveaux sont termines.")
            return

        if not self._is_local_host():
            self.game.popup_ui.show_popup("Seul le host peut lancer la partie.")
            return

        if not self.player_inside_start_zone:
            return

        self.game.start_game()

    def toggle_manual(self):
        if not self.is_active:
            return

        self.manual.toggle()
        if self.manual.visible:
            self.panel.hide()
        else:
            self.panel.show()

    def next_manual_page(self):
        if self.is_active:
            self.manual.next_page()

    def previous_manual_page(self):
        if self.is_active:
            self.manual.previous_page()

    def update(self):
        if not self.is_active:
            return

        players = self._connected_player_count()
        plural = "s" if players > 1 else ""
        level_text = self._level_text()
        if getattr(self.game, "game_completed", False):
            status = f"Lobby - Jeu termine - {players} joueur{plural} connecte{plural}"
            hint = "Les 5 niveaux sont termines."
        elif self._is_local_host():
            status = f"Lobby - {level_text} - {players} joueur{plural} connecte{plural}"
            hint = "Va sur le point de depart, E pour lancer. M : manuel."
        else:
            status = f"Lobby - {level_text} - {players} joueur{plural} connecte{plural}"
            hint = "En attente du host. M : manuel."

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
        self.manual.destroy()
        self.zone_np.removeNode()
        # self.marker.removeNode()
        # self.world_label.removeNode()
        self.game.popup_ui.hide_popup()

        self.ignore("e")
        self.ignore("m")
        self.ignore("arrow_right")
        self.ignore("arrow_down")
        self.ignore("arrow_left")
        self.ignore("arrow_up")
        self.ignore(f"player-into-{self.START_ZONE_NAME}")
        self.ignore(f"player-out-{self.START_ZONE_NAME}")
