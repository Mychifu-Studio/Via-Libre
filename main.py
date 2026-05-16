from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, load_prc_file_data, DirectionalLight
from panda3d.core import CardMaker, PNMImage, Texture, AntialiasAttrib
import random

from direct.gui.DirectGui import DirectFrame, DirectButton

from vialibre.player import Player
from vialibre.multiplayer import MultiplayerManager
from vialibre.ressource_system import ResourceSystem
from vialibre.inventory_ui import InventoryUI
from vialibre.popup_ui import PopupUI


load_prc_file_data('', 'sync-video f\nshow-frame-rate-meter t')
load_prc_file_data('', 'win-size 1280 720')
load_prc_file_data('', 'client-sleep 0.001')
load_prc_file_data('', 'framebuffer-multisample 1\nmultisamples 2')
load_prc_file_data("", "load-file-type p3assimp")


class Test(ShowBase):
    def __init__(self, fStartDirect=True, windowType=None):
        super().__init__(fStartDirect, windowType)

        self.render.setAntialias(AntialiasAttrib.MMultisample)
        self.disable_mouse()

        self.player = Player()

        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)

        self.accept("escape", self.menu)

        self.generateGround()
        self.smooth_dt = None
        self.setupLights()

        ### NETWORK ###
        self.multiplayer = MultiplayerManager(self, self.player)
        ###############

        ### MENU ###
        self.escMenuFrame = DirectFrame(
            frameColor=(0, 0, 0, 0.8),
            frameSize=(-0.5, 0.5, -0.4, 0.4),
            pos=(0, 0, 0)
        )
        self.escMenuFrame.hide()

        self.leaveBtn = DirectButton(
            parent=self.escMenuFrame,
            text="Leave",
            scale=0.1,
            pos=(0, 0, 0),
            pad=(0.2, 0.2),
            command=self.exit
        )

        self.is_esc = False
        ##############

        self.win.setCloseRequestEvent('window-close')
        self.accept('window-close', self.exit)

        self.inventory = {
            "ressource": 0
        }

        self.inventory_ui = InventoryUI(self)
        self.popup_ui = PopupUI(self)

        self.resource_system = ResourceSystem(
            game=self,
            inventory_ui=self.inventory_ui,
            popup_ui=self.popup_ui
        )
        self.resource_system.setup_player_collider(self.player)

        self.game_started = True
        self.resource_system.generate_random_zones(8)

        self.taskMgr.add(self.update, 'update')

    def update(self, task):
        dt = globalClock.getDt()  # pyright: ignore[reportUndefinedVariable]

        self.player.update(dt)
        self.multiplayer.update()
        self.resource_system.update()

        return task.cont

    def menu(self):
        self.is_esc = not self.is_esc
        if self.is_esc:
            self.escMenuFrame.show()
            self.player.is_paused = True
        else:
            self.escMenuFrame.hide()
            self.player.camera.mouse.centerMouse()
            self.player.is_paused = False

    def exit(self):
        self.taskMgr.remove('update')
        self.multiplayer.exit()
        self.userExit()

    def generateGround(self):
        size = 256
        img = PNMImage(size, size)

        for x in range(size):
            for y in range(size):
                r = 0.25 + random.uniform(-0.05, 0.05)
                g = 0.7 + random.uniform(-0.1, 0.1)
                b = 0.25 + random.uniform(-0.05, 0.05)

                r = min(max(r, 0), 1)
                g = min(max(g, 0), 1)
                b = min(max(b, 0), 1)

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
        ground.setZ(0)
        ground.setTexture(texture)

    def setupLights(self):
        dlight = DirectionalLight('dlight')
        dlight.setColor((0.8, 0.8, 0.5, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(0, -60, 0)
        self.render.setLight(dlnp)


app = Test()
app.run()