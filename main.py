import os

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from panda3d.core import AmbientLight, DirectionalLight, TextNode, WindowProperties, load_prc_file_data, Spotlight, PerspectiveLens
import simplepbr

from vialibre.enemies import EnemyManager
from vialibre.health_ui import PipeHealthUI, PlayerHealthUI
from vialibre.inventory_ui import InventoryUI
from vialibre.lobby import LobbyManager
from vialibre.map_collision import MapCollisionManager
from vialibre.multiplayer import GameNetworkInterface
from vialibre.pipe_base import PipeBase
from vialibre.player import Player
from vialibre.popup_ui import PopupUI
from vialibre.resource_system import ResourceSystem
from vialibre.shooting import ShootingSystem
from vialibre.upgrade_system import UpgradeSystem
from vialibre.vague import VagueManager
from vialibre.soundSystem import SoundEngine


load_prc_file_data(
    "",
    "sync-video f\n"
    "show-frame-rate-meter t\n"
    "win-size 1920 1080\n"
    "client-sleep 0.001\n"
    "framebuffer-multisample 0\n"
    "multisamples 0\n"
    # "load-file-type p3assimp\n" 
)

GAME_SPAWN_POS = (0, 0, 0)
PERFORMANCE_LIGHTING = True


class EnvironmentManager:
    """SRP: Initialise et gere le decor statique (lumieres, terrain)."""

    LOBBY_MAP_CANDIDATES = (
        ("assets/Shop.bam", 0),
        ("assets/Jungle3.bam", -90),
    )
    GAME_MAP = ("assets/Jungle3.bam", -90)
    BARTENDER_CANDIDATES = ("assets/bartender.bam", "assets/bartender.bam")
    QUEST_GUY_CANDIDATES = ("assets/quest_guy.bam", "assets/quest_guy.bam")

    def __init__(self, render):
        self.render = render
        self.jungle = None
        self.map_path = None
        self.lobby_characters = []
        self.load_lobby_map()
        self.setup_lights()

    def load_lobby_map(self):
        self._load_map(*self._resolve_lobby_map_path())
        self._load_lobby_characters()

    def load_game_map(self):
        self._clear_lobby_characters()
        self._load_map(*self.GAME_MAP)

    def _load_map(self, map_path, map_heading):
        if self.jungle is not None and not self.jungle.isEmpty():
            self._remove_loaded_node(self.jungle)

        # size = 256
        # img = PNMImage(size, size)

        # for x in range(size):
        #     for y in range(size):
        #         r = min(max(0.25 + random.uniform(-0.05, 0.05), 0), 1)
        #         g = min(max(0.70 + random.uniform(-0.1, 0.1), 0), 1)
        #         b = min(max(0.25 + random.uniform(-0.05, 0.05), 0), 1)
        #         img.setXel(x, y, r, g, b)

        # texture = Texture("groundTexture")
        # texture.load(img)
        # texture.setWrapU(Texture.WM_repeat)
        # texture.setWrapV(Texture.WM_repeat)

        # cm = CardMaker("ground")
        # cm.setFrame(-50, 50, -50, 50)
        # cm.setUvRange((0, 0), (10, 10))

        # ground = self.render.attachNewNode(cm.generate())
        # ground.setP(-90)
        # ground.setTexture(texture)
        self.map_path = map_path
        self.jungle = loader.loadModel(map_path)
        self.jungle.setPos(0, 0, 0)
        self.jungle.setH(map_heading)
        self.jungle.reparentTo(self.render)

    def _resolve_lobby_map_path(self):
        for path, heading in self.LOBBY_MAP_CANDIDATES:
            if os.path.exists(path):
                return path, heading

        return "assets/Jungle3.bam", -90

    def _resolve_model_path(self, candidates):
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _load_actor_or_model(self, path):
        try:
            return Actor(path)
        except Exception:
            return loader.loadModel(path)

    def _remove_loaded_node(self, node):
        if node is None or node.isEmpty():
            return

        cleanup = getattr(node, "cleanup", None)
        if callable(cleanup):
            cleanup()

        node.removeNode()

    def _load_lobby_character(self, attr_name, candidates, pos, scale, heading=None):
        path = self._resolve_model_path(candidates)
        if path is None:
            setattr(self, attr_name, None)
            return

        character = self._load_actor_or_model(path)
        character.reparentTo(self.render)
        character.setPos(*pos)
        character.setScale(scale)
        if heading is not None:
            character.setH(heading)

        if hasattr(character, "getAnimNames"):
            anims = character.getAnimNames()
            print(f"Animations {attr_name} :", anims)
            if anims:
                character.loop(anims[0])

        setattr(self, attr_name, character)
        self.lobby_characters.append(character)

    def _load_lobby_characters(self):
        self._clear_lobby_characters()
        self._load_lobby_character(
            "bartender",
            self.BARTENDER_CANDIDATES,
            pos=(0, 0.5, 0),
            scale=0.90,
        )
        self._load_lobby_character(
            "quest_guy",
            self.QUEST_GUY_CANDIDATES,
            pos=(16, 1.5, 0.05),
            scale=0.83,
            heading=-90,
        )

    def _clear_lobby_characters(self):
        for character in self.lobby_characters:
            self._remove_loaded_node(character)
        self.lobby_characters = []

    def add_spotlight(self, name, color, pos, target, fov=45, near=1, far=50):
        spot = Spotlight(name)
        spot.setColor(color)

        lens = PerspectiveLens()
        lens.setFov(fov)
        lens.setNearFar(near, far)
        spot.setLens(lens)

        spotNP = self.render.attachNewNode(spot)
        spotNP.setPos(*pos)
        spotNP.lookAt(*target)

        self.render.setLight(spotNP)
        return spotNP

    def setup_lights(self):
        ambientLight = AmbientLight('ambientLight')
        ambientLight.setColor((0.62, 0.62, 0.54, 1))
        ambientLightNP = self.render.attachNewNode(ambientLight)
        self.render.setLight(ambientLightNP)

        if PERFORMANCE_LIGHTING:
            sun = DirectionalLight("sun")
            sun.setColor((0.75, 0.72, 0.62, 1))
            sunNP = self.render.attachNewNode(sun)
            sunNP.setHpr(-35, -60, 0)
            self.render.setLight(sunNP)
            return

        self.spot1 = self.add_spotlight(
            name="feu de camp",
            color=(1.0, 0.2, 0.1, 1),
            pos=(0, -7, 2),
            target=(0, -9, 0),
            fov=140
        )

        self.mid_haut = self.add_spotlight(
            name="mid haut",
            color=(0, 0.2, 1, 1),
            pos=(0, 15, 10),
            target=(0, 15, 0),
            fov=140
        )

        self.mid_right = self.add_spotlight(
            name="mid right",
            color=(0.8, 0.6, 0.2, 1),
            pos=(110, 0, 10),
            target=(110, 0, 0),
            fov=140
        )

        self.spot_minerai_left = self.add_spotlight(
            name="spot_minerai_left",
            color=(0, 0, 0.9, 1),
            pos=(-30, 6, 3),
            target=(-35, 8, 0),
            fov=70
        )
        self.spot_minerai_right = self.add_spotlight(
            name="spot_minerai_right",
            color=(0, 0, 0.9, 1),
            pos=(30, 7, 3),
            target=(35, 10, 0),
            fov=70
        )

        self.spot_caillou_right = self.add_spotlight(
            name="spot_caillou_right",
            color=(0, 0, 0.9, 1),
            pos=(22, 9, 6),
            target=(22, 9, 0),
            fov=140
        )

        self.spot_caillou_left = self.add_spotlight(
            name="spot_caillou_left",
            color=(0, 0, 0.9, 1),
            pos=(-22, 9, 6),
            target=(-22, 9, 0),
            fov=140
        )

        self.spot_caillou_bas_left = self.add_spotlight(
            name="spot_caillou_bas_left",
            color=(0, 0.3, 0.9, 1),
            pos=(-30, -9, 6),
            target=(-30, -9, 0),
            fov=140
        )
        self.spot_caillou_bas_right = self.add_spotlight(
            name="spot_caillou_bas_right",
            color=(0, 0.3, 0.9, 1),
            pos=(30, -9, 6),
            target=(30, -9, 0),
            fov=140
        )

        self.spot_mid = self.add_spotlight(
            name="spot_mid",
            color=(0.9, 0.95, 0.80, 1),
            pos=(0, -9, 14),
            target=(0, -9, 0),
            fov=70
        )

        self.spot_mid_bas = self.add_spotlight(
            name="spot_mid_bas",
            color=(0, 0.3, 0.80, 1),
            pos=(0, -33, 6),
            target=(0, -33, 0),
            fov=100
        )


class GameMenu:
    """Menu pause / quitter."""

    def __init__(self, game):
        self.game = game
        self.is_open = False

        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0.02, 0.02, 0.02, 0.88),
            frameSize=(-0.55, 0.55, -0.35, 0.35),
            pos=(0, 0, 0),
        )
        self.frame.setBin("fixed", 150)
        self.frame.setDepthWrite(False)
        self.frame.setDepthTest(False)
        self.frame.hide()

        self.leave_btn = DirectButton(
            parent=self.frame,
            text="Quitter",
            scale=0.075,
            pos=(0, 0, -0.05),
            pad=(0.22, 0.08),
            frameColor=(0.75, 0.12, 0.12, 1),
            text_fg=(1, 1, 1, 1),
            relief=1,
            command=self.game.exit_game,
        )

    def toggle(self):
        self.is_open = not self.is_open

        if self.is_open:
            self.frame.show()
            self.game.player.is_paused = True
        else:
            self.frame.hide()
            if not self.game.is_game_over and not getattr(self.game, "game_completed", False):
                self.game.player.camera.mouse.centerMouse()
                self.game.player.is_paused = False


class GameOverScreen:
    """Ecran de defaite quand le tuyau est detruit."""

    def __init__(self, game):
        self.game = game

        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0, 0, 0, 0.9),
            frameSize=(-1.4, 1.4, -0.8, 0.8),
            pos=(0, 0, 0),
        )
        self.frame.setBin("fixed", 210)
        self.frame.setDepthWrite(False)
        self.frame.setDepthTest(False)
        self.frame.hide()

        self.label = DirectLabel(
            parent=self.frame,
            text="GAME OVER\nLe tuyau est detruit.",
            scale=0.095,
            pos=(0, 0, 0.12),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=18,
        )
        self.label.setBin("fixed", 211)
        self.label.setDepthWrite(False)
        self.label.setDepthTest(False)

        self.leave_btn = DirectButton(
            parent=self.frame,
            text="Quitter",
            scale=0.07,
            pos=(0, 0, -0.24),
            pad=(0.22, 0.08),
            frameColor=(0.75, 0.12, 0.12, 1),
            text_fg=(1, 1, 1, 1),
            relief=1,
            command=self.game.exit_game,
        )
        self.leave_btn.setBin("fixed", 211)
        self.leave_btn.setDepthWrite(False)
        self.leave_btn.setDepthTest(False)

    def show(self):
        self.frame.show()


class HostCodeUI:
    """Affiche le code de salon pour le host."""

    def __init__(self, game):
        self.game = game
        self.frame = None

        net_iface = getattr(self.game, "network", None)
        net = getattr(net_iface, "net", None) if net_iface is not None else None
        if net is None or not net.is_host:
            return

        if net.game_code:
            text = f"CODE : {net.game_code}"
        else:
            text = f"HOST LOCAL : {net.local_ip}"

        self.frame = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0.018, 0.018, 0.018, 0.78),
            frameSize=(-0.36, 0.36, -0.055, 0.055),
            pos=(0, 0, 0.94),
        )
        self.frame.setBin("fixed", 96)
        self.frame.setDepthWrite(False)
        self.frame.setDepthTest(False)

        self.label = DirectLabel(
            parent=self.frame,
            text=text,
            scale=0.038,
            pos=(0, 0, -0.014),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 0.94, 0.62, 1),
            text_align=TextNode.ACenter,
        )
        self.label.setBin("fixed", 97)
        self.label.setDepthWrite(False)
        self.label.setDepthTest(False)


class MainGame(ShowBase):
    def __init__(self):
        super().__init__(True)
        self.set_fullscreen()
        simplepbr.init(
            msaa_samples=0,
            enable_shadows=False,
            max_lights=2,
            use_emission_maps=False,
            use_hardware_skinning=True,
        )

        self.disable_mouse()
        
        self.initialize()



    def initialize(self):
        props = WindowProperties()
        props.setCursorHidden(True)
        if hasattr(self.win, "requestProperties"):
            self.win.requestProperties(props)

        self.environment = EnvironmentManager(self.render)
        self.map_collision = MapCollisionManager(self.render, self.environment.jungle)

        self.game_started = False
        self.is_game_over = False
        self.game_completed = False
        self.max_levels = 5
        self.current_level = 1
        self.pipe_base = PipeBase(self, self.map_collision)
        self.enemies = EnemyManager(self)
        self.player = Player(map_collision=self.map_collision)
        self.shooting = ShootingSystem(game=self, player=self.player)
        self.network = GameNetworkInterface(self)
        self.host_code_ui = HostCodeUI(self)
        self.sound = SoundEngine(self)

        self.inventory = {"ressource": 0}
        self.inventory_ui = InventoryUI(self)
        self.player_health_ui = PlayerHealthUI(self, self.player)
        self.pipe_health_ui = PipeHealthUI(self, self.pipe_base)
        self.popup_ui = PopupUI(self)
        self.menu = GameMenu(self)
        self.game_over_screen = GameOverScreen(self)

        self.resource_system = ResourceSystem(
            game=self,
            inventory_ui=self.inventory_ui,
            popup_ui=self.popup_ui,
        )
        self.resource_system.setup_player_collider(self.player)

        self.upgrade_system = UpgradeSystem(
            game=self,
            inventory_ui=self.inventory_ui,
            popup_ui=self.popup_ui,
        )

        self.vague_manager = VagueManager(self, self.enemies)
        self.lobby = LobbyManager(self)
        self.set_game_hud_visible(False)

        self.accept("escape", self.menu.toggle)
        self.accept("window-close", self.exit_game)
        self.accept("enemy-killed", self.handle_enemy_killed)
        self.accept("player-take-damage", self.player.take_damage)
        self.accept("pipe-destroyed", self.trigger_game_over)

        self.taskMgr.add(self.update, "update")

    def start_game(self, from_network=False, level_number=None):
        if self.game_started or self.game_completed:
            return

        if level_number is not None:
            self.set_current_level(level_number)

        self.is_game_over = False
        self.game_started = True
        if hasattr(self, "lobby"):
            self.lobby.finish()

        self.prepare_game_level()
        self.set_game_hud_visible(True)
        self.vague_manager.set_level(self.current_level)
        self.vague_manager.start()
        if not from_network and hasattr(self, "network"):
            self.network.broadcast_game_start()

        self.popup_ui.show_popup(
            f"Niveau {self.current_level}/{self.max_levels} commence !",
            duration=2.5,
        )
        # self.sound.loop("kawaii")

    def set_current_level(self, level_number):
        self.current_level = max(1, min(int(level_number), self.max_levels))
        if hasattr(self, "vague_manager"):
            self.vague_manager.set_level(self.current_level)

    def set_game_hud_visible(self, visible):
        self.inventory_ui.set_visible(visible)
        self.player_health_ui.set_visible(visible)
        self.pipe_health_ui.set_visible(visible)

    def prepare_game_level(self):
        self.clear_level_objects()
        self.environment.load_game_map()
        self.map_collision = MapCollisionManager(self.render, self.environment.jungle)

        self.player.map_collision = self.map_collision
        self.player.player.setPos(*GAME_SPAWN_POS)
        self.player.movementVector.set(0, 0, 0)
        self.player.lastMovement.set(0, 0, 0)
        self.player.is_paused = False
        self.player.camera.mouse.centerMouse()

        self.pipe_base = PipeBase(self, self.map_collision)
        self.pipe_health_ui.pipe_base = self.pipe_base
        self.pipe_health_ui.update()

        self.resource_system.generate_diamond_ore_zones()
        self.upgrade_system.generate_campfire_zones()

        net_iface = getattr(self, "network", None)
        for model in getattr(net_iface, "other_players", {}).values():
            model.setPos(*GAME_SPAWN_POS)

    def clear_level_objects(self):
        self.enemies.clear()
        if hasattr(self, "shooting"):
            self.shooting.clear()
        if hasattr(self, "resource_system"):
            self.resource_system.clear_resource_zones()
        if hasattr(self, "upgrade_system"):
            self.upgrade_system.clear_campfire_zones()
        build_manager = getattr(getattr(self, "player", None), "build_manager", None)
        if build_manager is not None and hasattr(build_manager, "clear_structures"):
            build_manager.clear_structures()

    def _load_lobby_for_next_level(self, popup_text=None):
        self.clear_level_objects()
        self.game_started = False
        self.set_game_hud_visible(False)
        self.vague_manager.wave_panel.hide()
        self.vague_manager.final_screen.hide()

        old_lobby = getattr(self, "lobby", None)
        if old_lobby is not None and getattr(old_lobby, "is_active", False):
            old_lobby.finish()

        self.environment.load_lobby_map()
        self.map_collision = MapCollisionManager(self.render, self.environment.jungle)
        self.player.map_collision = self.map_collision
        self.lobby = LobbyManager(self)
        self.player.player.setPos(self.lobby.start_pos)
        self.player.movementVector.set(0, 0, 0)
        self.player.lastMovement.set(0, 0, 0)
        self.player.is_paused = False
        self.player.camera.mouse.centerMouse()

        net_iface = getattr(self, "network", None)
        for model in getattr(net_iface, "other_players", {}).values():
            model.setPos(self.lobby.start_pos)

        if popup_text:
            self.popup_ui.show_popup(popup_text, duration=3.0)

    def complete_current_level(self):
        if self.game_completed:
            return

        completed_level = self.current_level
        if completed_level >= self.max_levels:
            self.vague_manager.finish_game()
            return

        self.set_current_level(completed_level + 1)
        self._load_lobby_for_next_level(
            f"Niveau {completed_level}/{self.max_levels} termine ! "
            f"Lance le niveau {self.current_level} depuis le lobby."
        )

        self._broadcast_network_snapshot()

    def return_to_lobby_from_network(self, level_number=None):
        if self.game_completed:
            return

        if level_number is not None:
            self.set_current_level(level_number)
        self._load_lobby_for_next_level()

    def mark_game_completed(self):
        if self.game_completed:
            return

        self.game_completed = True
        self.game_started = False
        self.clear_level_objects()
        self.set_game_hud_visible(False)
        self.player.is_paused = True
        self.player.camera.mouse.showCursor()

        self._broadcast_network_snapshot()

    def handle_enemy_killed(self):
        self.vague_manager.enemy_killed()
        self._broadcast_network_snapshot()

    def reward_enemy_hit(self):
        self.handle_enemy_killed()

    def damage_pipe(self, amount=1):
        if self.is_game_over:
            return

        self.pipe_base.take_damage(amount)
        self.pipe_health_ui.update()
        self._broadcast_network_snapshot()

    def trigger_game_over(self):
        if self.is_game_over:
            return

        self.is_game_over = True
        self.player.is_paused = True
        self.player.camera.mouse.showCursor()
        self.enemies.clear()
        self.vague_manager.game_over()
        self.game_over_screen.show()

    def exit_game(self):
        self.taskMgr.remove("update")
        self.enemies.clear()
        if hasattr(self, "network"):
            self.network.exit()
        self.userExit()
        
    def _broadcast_network_snapshot(self):
        net_iface = getattr(self, "network", None)
        net = getattr(net_iface, "net", None) if net_iface is not None else None
        if net is not None and net.is_host:
            net_iface._broadcast_snapshot(force=True)

    def set_fullscreen(self):
        w = self.pipe.getDisplayWidth()
        h = self.pipe.getDisplayHeight()
        props = WindowProperties()
        props.setFullscreen(True)
        props.setSize(w, h)
        self.win.requestProperties(props)

        load_prc_file_data("", "fullscreen true")

    def setFullscren(self):
        self.set_fullscreen()

    def update(self, task):
        dt = globalClock.getDt()  # pyright: ignore

        if self.is_game_over:
            self.player.update(dt)
            self.network.update()
            self.player_health_ui.update()
            self.pipe_health_ui.update()
            return task.cont

        self.player.update(dt)
        self.network.update()
        self.resource_system.update()

        if not self.game_started:
            if hasattr(self, "lobby"):
                self.lobby.update()
            return task.cont

        self.inventory_ui.update()
        self.player_health_ui.update()
        self.pipe_health_ui.update()

        self.upgrade_system.update()
        self.enemies.update(dt)
        self.shooting.update()
        self.vague_manager.update(dt)

        return task.cont


if __name__ == "__main__":
    app = MainGame()
    app.run()
