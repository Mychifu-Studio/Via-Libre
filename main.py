from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, load_prc_file_data, DirectionalLight, CardMaker, PNMImage, Texture, AntialiasAttrib
import random
from direct.gui.DirectGui import DirectFrame, DirectButton

from vialibre.player import Player
from vialibre.multiplayer import MultiplayerManager
from vialibre.ressource_system import ResourceSystem
from vialibre.inventory_ui import InventoryUI
from vialibre.popup_ui import PopupUI
from vialibre.shooting import ShootingSystem
from vialibre.enemies import EnemyManager

# Configuration globale
load_prc_file_data('', 'sync-video f\nshow-frame-rate-meter t\nwin-size 1280 720\nclient-sleep 0.001\nframebuffer-multisample 1\nmultisamples 2\nload-file-type p3assimp')

class EnvironmentManager:
    """SRP: Initialise et gère le décor statique (lumières, terrain)."""
    def __init__(self, render):
        self.render = render
        self.generate_ground()
        self.setup_lights()

    def generate_ground(self):
        size = 256
        img = PNMImage(size, size)
        for x in range(size):
            for y in range(size):
                r = min(max(0.25 + random.uniform(-0.05, 0.05), 0), 1)
                g = min(max(0.70 + random.uniform(-0.1, 0.1), 0), 1)
                b = min(max(0.25 + random.uniform(-0.05, 0.05), 0), 1)
                img.setXel(x, y, r, g, b)

        texture = Texture("groundTexture")
        texture.load(img)
        texture.setWrapU(Texture.WM_repeat)
        texture.setWrapV(Texture.WM_repeat)

        cm = CardMaker("ground")
        cm.setFrame(-50, 50, -50, 50)
        cm.setUvRange((0, 0), (10, 10))

        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)
        ground.setTexture(texture)

    def setup_lights(self):
        dlight = DirectionalLight('dlight')
        dlight.setColor((0.8, 0.8, 0.5, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(0, -60, 0)
        self.render.setLight(dlnp)

class GameMenu:
    """SRP: Gère l'affichage du menu système (Pause/Quitter)."""
    def __init__(self, game):
        self.game = game
        self.is_open = False
        
        self.frame = DirectFrame(frameColor=(0, 0, 0, 0.8), frameSize=(-0.5, 0.5, -0.4, 0.4))
        self.frame.hide()

        self.leave_btn = DirectButton(parent=self.frame, text="Leave", scale=0.1, pad=(0.2, 0.2), command=self.game.exit_game)

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
        self.render.setAntialias(AntialiasAttrib.MMultisample)
        self.disable_mouse()
        
        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)

        self.environment = EnvironmentManager(self.render)

        # Entités & Systèmes
        self.enemies = EnemyManager(self)
        self.player = Player()
        self.shooting = ShootingSystem(game=self, player=self.player)
        self.multiplayer = MultiplayerManager(self, self.player)
        self.enemies.spawn_random_dogs_in_area()

        # UI & Inventaire
        self.inventory = {"ressource": 0}
        self.inventory_ui = InventoryUI(self)
        self.popup_ui = PopupUI(self)
        self.menu = GameMenu(self)

        self.resource_system = ResourceSystem(game=self, inventory_ui=self.inventory_ui, popup_ui=self.popup_ui)
        self.resource_system.setup_player_collider(self.player)
        self.resource_system.generate_random_zones(8)

        # Events
        self.accept("escape", self.menu.toggle)
        self.accept('window-close', self.exit_game)
        
        # Le main est propriétaire de l'inventaire : c'est lui qui écoute l'événement
        self.accept('enemy-hit', self.reward_enemy_hit)

        self.game_started = True
        self.taskMgr.add(self.update, 'update')

    def reward_enemy_hit(self):
        self.inventory["ressource"] = self.inventory.get("ressource", 0) + 1
        self.inventory_ui.update()
        self.popup_ui.show_popup(f"Ennemi touché : ressource +1 ! (Total : {self.inventory['ressource']})")

    def exit_game(self):
        self.taskMgr.remove('update')
        self.multiplayer.exit()
        self.userExit()

    def update(self, task):
        dt = globalClock.getDt() # pyright: ignore
        self.player.update(dt)
        self.multiplayer.update()
        self.resource_system.update()
        self.inventory_ui.update()
        self.enemies.update(dt)
        self.shooting.update()
        return task.cont

if __name__ == "__main__":
    app = MainGame()
    app.run()