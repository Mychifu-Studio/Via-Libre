from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, load_prc_file_data, DirectionalLight, CardMaker, PNMImage, Texture, AntialiasAttrib, AmbientLight, Spotlight, PerspectiveLens
import random
from direct.gui.DirectGui import DirectFrame, DirectButton
import simplepbr

from vialibre.player import Player
from vialibre.multiplayer import MultiplayerManager
from vialibre.resource_system import ResourceSystem
from vialibre.inventory_ui import InventoryUI
from vialibre.popup_ui import PopupUI
from vialibre.shooting import ShootingSystem
from vialibre.enemies import EnemyManager
from vialibre.vague import VagueManager


# Configuration globale
load_prc_file_data(
    '',
    'sync-video f\n'
    'show-frame-rate-meter t\n'
    'win-size 1280 720\n'
    'client-sleep 0.001\n'
    'framebuffer-multisample 1\n'
    'multisamples 2\n'
    'load-file-type p3assimp\n'
    'load-file-type p3dopenstdl'
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
        jungle = loader.loadModel('assets/Jungle3.bam')
        jungle.setPos(0, 0, 0)
        jungle.setH(-90)
        jungle.reparentTo(self.render)

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
    """SRP: Gère l'affichage du menu système (Pause/Quitter)."""
    def __init__(self, game):
        self.game = game
        self.is_open = False

        self.frame = DirectFrame(
            frameColor=(0, 0, 0, 0.8),
            frameSize=(-0.5, 0.5, -0.4, 0.4)
        )
        self.frame.hide()

        self.leave_btn = DirectButton(
            parent=self.frame,
            text="Leave",
            scale=0.1,
            pad=(0.2, 0.2),
            command=self.game.exit_game
        )

    def toggle(self):
        self.is_open = not self.is_open

        if self.is_open:
            self.frame.show()
            self.game.player.is_paused = True
        else:
            self.frame.hide()
            self.game.player.camera.mouse.centerMouse()
            self.game.player.is_paused = False


class MainGame(ShowBase):
    def __init__(self):
        super().__init__(True)
        simplepbr.init()

        self.render.setAntialias(AntialiasAttrib.MMultisample)
        self.disable_mouse()

        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)

        self.environment = EnvironmentManager(self.render)

        # Entités & systèmes
        self.enemies = EnemyManager(self)
        self.player = Player()

        # Dans ta version actuelle de shooting.py, il faut passer self.player,
        # car shooting.py récupère lui-même player.player.
        self.shooting = ShootingSystem(game=self, player=self.player)

        self.multiplayer = MultiplayerManager(self, self.player)

        # UI & inventaire
        self.inventory = {
            "ressource": 0
        }

        self.inventory_ui = InventoryUI(self)
        self.popup_ui = PopupUI(self)
        self.menu = GameMenu(self)

        self.resource_system = ResourceSystem(
            game=self,
            inventory_ui=self.inventory_ui,
            popup_ui=self.popup_ui
        )
        self.resource_system.setup_player_collider(self.player)
        self.resource_system.generate_random_zones(8)

        # Système de vagues
        # Important : on ne fait PLUS self.enemies.spawn_random_dogs_in_area()
        # directement dans main.py. C'est vague.py qui gère les spawns.
        self.vague_manager = VagueManager(self, self.enemies)
        self.vague_manager.start()

        # Events
        self.accept("escape", self.menu.toggle)
        self.accept("window-close", self.exit_game)

        # shooting.py doit envoyer "enemy-hit" quand un projectile tue un ennemi.
        self.accept("enemy-hit", self.reward_enemy_hit)

        self.game_started = True
        self.taskMgr.add(self.update, "update")

    def reward_enemy_hit(self):
        self.inventory["ressource"] = self.inventory.get("ressource", 0) + 1
        self.inventory_ui.update()

        self.popup_ui.show_popup(
            f"Ennemi touché : ressource +1 ! (Total : {self.inventory['ressource']})"
        )

        # C'est cette ligne qui permet à vague.py de compter les kills
        # et de lancer la vague suivante.
        self.vague_manager.enemy_killed()

    def exit_game(self):
        self.taskMgr.remove("update")
        self.enemies.clear()
        self.multiplayer.exit()
        self.userExit()

    def update(self, task):
        dt = globalClock.getDt()  # pyright: ignore

        self.player.update(dt)
        self.multiplayer.update()
        self.resource_system.update()
        self.inventory_ui.update()
        self.enemies.update(dt)
        self.shooting.update()
        self.vague_manager.update(dt)

        return task.cont


if __name__ == "__main__":
    app = MainGame()
    app.run()
