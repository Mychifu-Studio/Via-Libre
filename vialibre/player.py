# player.py
from direct.showbase.ShowBase import ShowBase
from direct.showbase.DirectObject import DirectObject

from panda3d.core import Vec3

from vialibre.camera import Camera
from vialibre.construction import BuildManager
from vialibre.interaction import InteractionManager

from vialibre.utils import shortest_angle_lerp, powLerp


class Player(DirectObject):
    MAX_HP = 10
    DAMAGE_COOLDOWN = 0.5

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

        self.build_manager = BuildManager(self.base, self.player, self.camera, self.camera.mouse)
        self.interaction_manager = InteractionManager(self.base, self.player, self.camera, self.build_manager)

        self.movementVector = Vec3(0)
        self.lastMovement = Vec3(0)
        self.playerSpeed = 10
        self.turnSpeed = 10.0

        self.hp = self.MAX_HP
        self._damage_cooldown_remaining = 0.0

        self.is_paused = False

        self.accept('raw-w',    self.updateKeyMap, ['forward',  True])
        self.accept('raw-w-up', self.updateKeyMap, ['forward',  False])
        self.accept('raw-a',    self.updateKeyMap, ['left',     True])
        self.accept('raw-a-up', self.updateKeyMap, ['left',     False])
        self.accept('raw-s',    self.updateKeyMap, ['backward', True])
        self.accept('raw-s-up', self.updateKeyMap, ['backward', False])
        self.accept('raw-d',    self.updateKeyMap, ['right',    True])
        self.accept('raw-d-up', self.updateKeyMap, ['right',    False])
        self.accept('control',    self.updateKeyMap, ['ctrl', True])
        self.accept('control-up', self.updateKeyMap, ['ctrl', False])

        self.accept('c',     self.build_manager.basculer_mode)

        self.accept('mouse1', self.handleLeftClick)

        self.keyMap = {
            "forward": False, "backward": False,
            "left": False,    "right": False,
            "ctrl": False,
        }

    def take_damage(self, amount=1):
        if self._damage_cooldown_remaining > 0:
            return
        self.hp -= amount
        self._damage_cooldown_remaining = self.DAMAGE_COOLDOWN
        self.base.messenger.send("player-hp-changed", [self.hp])
        if self.hp <= 0:
            self.base.messenger.send("player-dead")

    def handleLeftClick(self):
        cible = self.interaction_manager.structure_cible
        if cible:
            cible.detruire()
            return
        if self.build_manager.mode_actif:
            pass

    def update(self, dt):
        self.camera.updateCursor()
        if self.build_manager.mode_actif:
            self.camera.mouse.hideCursor()

        if self._damage_cooldown_remaining > 0:
            self._damage_cooldown_remaining = max(0.0, self._damage_cooldown_remaining - dt)

        if self.is_paused:
            self.camera.mouse.showCursor()
            return

        forward = self.base.render.getRelativeVector(self.camera.pivot, Vec3(0, 1, 0))
        right   = self.base.render.getRelativeVector(self.camera.pivot, Vec3(1, 0, 0))

        forward.setZ(0)
        right.setZ(0)

        if forward.lengthSquared() > 0: forward.normalize()
        if right.lengthSquared() > 0:   right.normalize()

        input_vec = Vec3(0)
        if self.keyMap['forward']:  input_vec += forward
        if self.keyMap['backward']: input_vec -= forward
        if self.keyMap['right']:    input_vec += right
        if self.keyMap['left']:     input_vec -= right

        if input_vec.lengthSquared() > 0:
            input_vec.normalize()

        from math import atan2, degrees
        
        current_H = self.modelNode.getH(self.base.render)

        if input_vec.length() > self.lastMovement.length():
            target_H = degrees(atan2(-input_vec.x, input_vec.y))  # adapte les axes si besoin
            new_H = shortest_angle_lerp(current_H, target_H, dt, .1)
            self.modelNode.setH(self.base.render, new_H)

        for axis in range(3):
            maxSpeedTime = .5 if input_vec[axis] else .08
            self.movementVector[axis] = powLerp(self.lastMovement[axis], input_vec[axis], dt, maxSpeedTime)

        self.player.setPos(self.player.getPos() + self.movementVector * self.playerSpeed * dt)

        new_cam_pos = self.camera.calculateCameraPos(dt, self.movementVector, self.lastMovement, self.keyMap["ctrl"] or self.is_paused)
        self.camera.setPos(new_cam_pos)

        if not (self.is_paused or self.keyMap['ctrl']):
            self.camera.updateFov(dt, any(self.keyMap.values()))

        self.lastMovement = self.movementVector

        self.interaction_manager.update()
        self.build_manager.update()

    def updateKeyMap(self, key, value):
        self.keyMap[key] = value
        if key == 'ctrl' and not value:
            self.camera.mouse.centerMouse()