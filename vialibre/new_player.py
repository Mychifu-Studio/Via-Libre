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
    MIN_HARVEST_TIME_MULTIPLIER = 0.35

    def __init__(self, showbase: ShowBase = None, map_collision=None):
        self.base = showbase if showbase else base
        self.map_collision = map_collision

        self.player = self.base.render.attachNewNode('player')
        self.modelNode = self.player.attachNewNode('player-model')

                self.model = Actor(
            './assets/Tony_idle.bam',
            {
                'idle': './assets/Tony_idle.bam',
                'run': './assets/Tony_run.bam',
            }
        )
        self.model.reparentTo(self.modelNode)

        self.model.setScale(0.4)
        self.model.setH(180)
        self.model.setZ(0)

        self.current_anim = 'idle'
        self.model.loop('idle')

        # Gun séparé attaché à la main droite
        self.right_hand = None
        possible_hand_bones = [
            "RightHand",
            "Hand.R",
            "hand_r",
            "mixamorig:RightHand",
            "Bip001 R Hand",
        ]

        for bone_name in possible_hand_bones:
            joint = self.model.exposeJoint(None, "modelRoot", bone_name)
            if not joint.isEmpty():
                self.right_hand = joint
                print("Main droite trouvée :", bone_name)
                break

        self.hand_gun = None
        if self.right_hand is None:
            print("Impossible de trouver le bone de la main droite.")
        else:
            self.hand_gun = self.base.loader.loadModel("./assets/hand_gun.bam")
            self.hand_gun.reparentTo(self.right_hand)

            # REGLAGES DU GUN — à ajuster
            self.hand_gun.setScale(0.40)
            self.hand_gun.setPos(0, 0, 0)
            self.hand_gun.setHpr(0, -90, 0)

            # Caché au départ, visible seulement quand on court
            self.hand_gun.hide()

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

        self.MAX_HP = type(self).MAX_HP
        self.hp = self.MAX_HP
        self.damage = 1
        self.harvest_time_multiplier = 1.0
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
        
    def play_anim(self, anim_name):
        if self.current_anim != anim_name:
            self.model.loop(anim_name)
            self.current_anim = anim_name

        if self.hand_gun is not None:
            if anim_name == 'run':
                self.hand_gun.show()
            else:
                self.hand_gun.hide()

    def take_damage(self, amount=1):
        if self._damage_cooldown_remaining > 0:
            return
        self.hp -= amount
        self._damage_cooldown_remaining = self.DAMAGE_COOLDOWN
        self.base.messenger.send("player-hp-changed", [self.hp])
        if self.hp <= 0:
            self.base.messenger.send("player-dead")

    def upgrade_max_hp(self, amount):
        self.MAX_HP += amount
        self.hp = min(self.MAX_HP, self.hp + amount)
        self.base.messenger.send("player-hp-changed", [self.hp])

    def upgrade_damage(self, amount):
        self.damage += amount

    def upgrade_harvest_speed(self, multiplier_reduction):
        self.harvest_time_multiplier = max(
            self.MIN_HARVEST_TIME_MULTIPLIER,
            self.harvest_time_multiplier - multiplier_reduction,
        )

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
            self.play_anim('idle')
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



        from math import atan2, degrees

        current_H = self.modelNode.getH(self.base.render)

        if input_vec.length() > self.lastMovement.length():
            target_H = degrees(atan2(-input_vec.x, input_vec.y))  # adapte les axes si besoin
            new_H = shortest_angle_lerp(current_H, target_H, dt, .1)
            self.modelNode.setH(self.base.render, new_H)

        for axis in range(3):
            maxSpeedTime = .5 if input_vec[axis] else .08
            self.movementVector[axis] = powLerp(self.lastMovement[axis], input_vec[axis], dt, maxSpeedTime)

        current_pos = self.player.getPos(self.base.render)
        desired_pos = current_pos + self.movementVector * self.playerSpeed * dt
        if self.map_collision is not None:
            desired_pos = self.map_collision.move(current_pos, desired_pos)

        self.player.setPos(desired_pos)

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