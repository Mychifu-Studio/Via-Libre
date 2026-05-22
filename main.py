from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, AntialiasAttrib, TextNode, WindowProperties, load_prc_file_data, Spotlight, PerspectiveLens
import simplepbr

from vialibre.enemies import EnemyManager
from vialibre.health_ui import PipeHealthUI, PlayerHealthUI
from vialibre.inventory_ui import InventoryUI
from vialibre.map_collision import MapCollisionManager
from vialibre.multiplayer import GameNetworkInterface
from vialibre.pipe_base import PipeBase
from vialibre.player import Player
from vialibre.popup_ui import PopupUI
from vialibre.resource_system import ResourceSystem
from vialibre.shooting import ShootingSystem
from vialibre.upgrade_system import UpgradeSystem
from vialibre.vague import VagueManager


load_prc_file_data(
    "",
    "sync-video f\n"
    "show-frame-rate-meter t\n"
    "win-size 1280 720\n"
    "client-sleep 0.001\n"
    "framebuffer-multisample 1\n"
    "multisamples 2\n"
    "load-file-type p3assimp"
)


class EnvironmentManager:
    """SRP: Initialise et gère le décor statique (lumières, terrain)."""
    def __init__(self, render):
        self.render = render
        self.generate_ground()
        self.setup_lights()

    def generate_ground(self):
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
        self.jungle = loader.loadModel('assets/Jungle3.bam')
        self.jungle.setPos(0, 0, 0)
        self.jungle.setH(-90)
        self.jungle.reparentTo(self.render)

    def add_spotlight(self, name, color, pos, target, fov=45, near=1, far=50):
        spot = Spotlight(name)
        spot.setColor(color)

        lens = PerspectiveLens()
        lens.setFov(fov)
        lens.setNearFar(near, far)
        spot.setLens(lens)

        spotNP = render.attachNewNode(spot)
        spotNP.setPos(*pos)
        spotNP.lookAt(*target)

        render.setLight(spotNP)
        return spotNP

    def setup_lights(self):
        ambientLight = AmbientLight('ambientLight')
        ambientLight.setColor((0.40, 0.40, 0.32, 1))
        ambientLightNP = render.attachNewNode(ambientLight)
        render.setLight(ambientLightNP)

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
        # #DOORS
        # self.door1 = self.add_spotlight(
        #     name="door1",
        #     color=(1, 0, 0, 1),
        #     pos=(-38, -9, 3),
        #     target=(-38, -9, 0),
        #     fov=90
        # )
        # self.door2= self.add_spotlight(
        #     name="door2",
        #     color=(1, 0, 0, 1),
        #     pos=(38, -9, 3),
        #     target=(38, -9, 0),
        #     fov=90
        # )

        # self.door3 = self.add_spotlight(
        #     name="door3",
        #     color=(1, 0, 0, 1),
        #     pos=(-22.8, 17, 3),
        #     target=(-22.8, 17, 0),
        #     fov=90
        # )
        # self.door4= self.add_spotlight(
        #     name="door4",
        #     color=(1, 0, 0, 1),
        #     pos=(21.2, 17, 3),
        #     target=(21.2, 17, 0),
        #     fov=90
        # )

        # self.door5 = self.add_spotlight(
        #     name="door5",
        #     color=(1, 0, 0, 1),
        #     pos=(6, 23.8, 3),
        #     target=(6, 23.8, 0),
        #     fov=90
        # )

        self.spot_minerai_left = self.add_spotlight(
            name="spot_minerai_left",
            color=(0, 0, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
            pos=(-30, 6, 3),
            target=(-35, 8, 0),
            fov=70
        )
        self.spot_minerai_right = self.add_spotlight(
            name="spot_minerai_right",
            color=(0, 0, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
            pos=(30, 7, 3),
            target=(35, 10, 0),
            fov=70
        )


        self.spot_caillou_right = self.add_spotlight(
            name="spot_caillou_right",
            color=(0, 0, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
            pos=(22, 9, 6),
            target=(22, 9, 0),
            fov=140
        )

        self.spot_caillou_left = self.add_spotlight(
            name="spot_caillou_left",
            color=(0, 0, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
            pos=(-22, 9, 6),
            target=(-22, 9, 0),
            fov=140
        )



        self.spot_caillou_bas_left = self.add_spotlight(
            name="spot_caillou_bas_left",
            color=(0, 0.3, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
            pos=(-30, -9, 6),
            target=(-30, -9, 0),
            fov=140
        )
        self.spot_caillou_bas_right = self.add_spotlight(
            name="spot_caillou_right",
            color=(0, 0.3, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
            pos=(30, -9, 6),
            target=(30, -9, 0),
            fov=140
        )

        self.spot_caillou_bas_right = self.add_spotlight(
            name="spot_caillou_right",
            color=(0, 0.3, 0.9, 1), #color=(0.7, 0.6, 0.9, 1),
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
            if not self.game.is_game_over:
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


class MainGame(ShowBase):
    def __init__(self):
        super().__init__(True)
        simplepbr.init()

        self.render.setAntialias(AntialiasAttrib.MMultisample)
        self.disable_mouse()

        props = WindowProperties()
        props.setCursorHidden(True)
        if hasattr(self.win, "requestProperties"):
            self.win.requestProperties(props)

        self.environment = EnvironmentManager(self.render)
        self.map_collision = MapCollisionManager(self.render, self.environment.jungle)

        self.is_game_over = False
        self.pipe_base = PipeBase(self, self.map_collision)
        self.enemies = EnemyManager(self)
        self.player = Player(map_collision=self.map_collision)
        self.shooting = ShootingSystem(game=self, player=self.player)
        self.network = GameNetworkInterface(self)

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
        self.resource_system.generate_diamond_ore_zones()

        self.upgrade_system = UpgradeSystem(
            game=self,
            inventory_ui=self.inventory_ui,
            popup_ui=self.popup_ui,
        )
        self.upgrade_system.generate_campfire_zones()

        self.vague_manager = VagueManager(self, self.enemies)
        self.vague_manager.start()

        self.accept("escape", self.menu.toggle)
        self.accept("window-close", self.exit_game)
        self.accept("enemy-hit", self.reward_enemy_hit)
        self.accept("player-take-damage", self.player.take_damage)
        self.accept("pipe-destroyed", self.trigger_game_over)

        self.game_started = True
        self.taskMgr.add(self.update, "update")

    def reward_enemy_hit(self):
        self.inventory["ressource"] = self.inventory.get("ressource", 0) + 1
        self.inventory_ui.update()
        self.popup_ui.show_popup(
            f"Ennemi touche : ressource +1 ! (Total : {self.inventory['ressource']})"
        )
        self.vague_manager.enemy_killed()
        if getattr(self.network, "net", None) is not None and self.network.net.is_host:
            self.network._broadcast_snapshot(force=True)

    def damage_pipe(self, amount=1):
        if self.is_game_over:
            return

        self.pipe_base.take_damage(amount)
        self.pipe_health_ui.update()
        if getattr(self.network, "net", None) is not None and self.network.net.is_host:
            self.network._broadcast_snapshot(force=True)

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
        self.network.exit()
        self.userExit()

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
        self.upgrade_system.update()
        self.inventory_ui.update()
        self.enemies.update(dt)
        self.player_health_ui.update()
        self.pipe_health_ui.update()
        self.shooting.update()
        self.vague_manager.update(dt)

        return task.cont


if __name__ == "__main__":
    app = MainGame()
    app.run()
