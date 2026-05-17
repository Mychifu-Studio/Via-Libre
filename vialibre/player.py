# player.py
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, NodePath
from direct.showbase.DirectObject import DirectObject

from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib
from direct.interval.IntervalGlobal import LerpScaleInterval

from vialibre.camera import Camera
from vialibre.construction import BuildManager
from vialibre.interaction import InteractionManager
from math import degrees, atan2

class Player(DirectObject):
    def __init__(self, showbase: ShowBase = None):
        self.base = showbase if showbase else base

        self.player = self.base.render.attachNewNode('player')
        self.modelNode = self.player.attachNewNode('player-model')
       
        self.model = self.base.loader.loadModel('./assets/dog.bam')
        self.model.setScale(self.model.getScale())
        self.model.reparentTo(self.modelNode)

        self.shoulderNode = self.modelNode.attach_new_node('shoulder')
        self.shoulderNode.setZ(3)

        self.heading = 0

        self.camera = Camera(self.player)

        self.build_manager = BuildManager(self.base, self.player, self.camera)
        self.interaction_manager = InteractionManager(self.base, self.player, self.camera, self.build_manager)

        self.movementVector = Vec3(0)
        self.lastMovement = Vec3(0)
        self.playerSpeed = 10
        self.turnSpeed = 10.0 

        self.is_paused = False

        self.cursorRoot = NodePath("cursorRoot")
        self.cursorRoot.reparentTo(self.base.aspect2d)
        self.cursorRoot.setBin("gui-popup", 100)
        self.cursorRoot.setDepthTest(False)
        self.cursorRoot.setDepthWrite(False)

        self.cursor = OnscreenImage(image='./assets/cursor_resized.png', parent=self.cursorRoot)
        self.cursor.setTransparency(TransparencyAttrib.MAlpha)
        self.cursor.setPos(1, 0, -1)

        scale = (0.04, 1, 0.04)
        scale_anim = (0.03, 1, 0.03)
        self.cursorRoot.setScale(*scale)

        self.cursorScaleDown = LerpScaleInterval(self.cursorRoot, duration=0.05, scale=scale_anim, startScale=scale)
        self.cursorScaleUp = LerpScaleInterval(self.cursorRoot, duration=0.1, scale=scale, startScale=scale_anim)

        # Crosshair retiré

        self.accept('raw-w', self.updateKeyMap, ['forward', True])
        self.accept('raw-w-up', self.updateKeyMap, ['forward', False])
        self.accept('raw-a', self.updateKeyMap, ['left', True])
        self.accept('raw-a-up', self.updateKeyMap, ['left', False])
        self.accept('raw-s', self.updateKeyMap, ['backward', True])
        self.accept('raw-s-up', self.updateKeyMap, ['backward', False])
        self.accept('raw-d', self.updateKeyMap, ['right', True])
        self.accept('raw-d-up', self.updateKeyMap, ['right', False])

        self.accept('control', self.updateKeyMap, ['ctrl', True])
        self.accept('control-up', self.updateKeyMap, ['ctrl', False])

        self.accept('c', self.build_manager.basculer_mode)
        self.accept('space', self.build_manager.valider_construction)
        self.accept('mouse1', self.handleLeftClick)
        self.accept('mouse1-up', self.cursorScaleUp.start)

        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "ctrl": False,
        }

    def handleLeftClick(self):
        self.cursorScaleDown.start()
        
        cible = self.interaction_manager.structure_cible
        if cible:
            cible.detruire()
            return

        if self.build_manager.mode_actif:
            self.build_manager.valider_construction()

    def update(self, dt):
        self.updateCursor()

        if self.is_paused:
            self.cursor.show()
            return
       
        forward = self.base.render.getRelativeVector(self.camera.pivot, Vec3(0, 1, 0))
        right = self.base.render.getRelativeVector(self.camera.pivot, Vec3(1, 0, 0))

        forward.setZ(0)
        right.setZ(0)

        if forward.lengthSquared() > 0: forward.normalize()
        if right.lengthSquared() > 0: right.normalize()

        input_vec = Vec3(0)

        if self.keyMap['forward']:
            input_vec += forward
        if self.keyMap['backward']:
            input_vec -= forward
        if self.keyMap['right']:
            input_vec += right
        if self.keyMap['left']:
            input_vec -= right

        if input_vec.lengthSquared() > 0:
            input_vec.normalize()

        if input_vec.length() > self.lastMovement.length():
            self.modelNode.lookAt(self.modelNode.getPos() + input_vec)

        for axis in range(3):
            maxSpeedTime = .5 if input_vec[axis] else .08
            self.movementVector[axis] = self.camera.powLerp(self.lastMovement[axis], input_vec[axis], dt, maxSpeedTime)

        self.player.setPos(self.player.getPos() + self.movementVector * self.playerSpeed * dt)

        new_cam_pos = self.camera.calculateCameraPos(dt, self.movementVector, self.lastMovement, self.keyMap["ctrl"] or self.is_paused)
        self.camera.setPos(new_cam_pos)
        
        if not (self.is_paused or self.keyMap['ctrl']):
            self.camera.updateFov(dt, any(self.keyMap.values()))

        self.lastMovement = self.movementVector

        self.interaction_manager.update() 
        self.build_manager.update()
           
    def updateCursor(self):
        if getattr(self.base, 'win', None) is None:
            return
       
        if self.base.mouseWatcherNode.hasMouse():
            self.cursor.show()
            x = self.base.mouseWatcherNode.getMouseX()
            y = self.base.mouseWatcherNode.getMouseY()
            ratio = self.base.getAspectRatio()
            self.cursorRoot.setPos(x * ratio, 0, y)
        else:
            self.cursor.hide()

    def updateKeyMap(self, key, value):
        self.keyMap[key] = value
        if key == 'ctrl' and value == False:
            self.camera.mouse.centerMouse()