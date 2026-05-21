from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, Point3, NodePath
from math import exp

from vialibre.mouseHandler import Mouse

SATELLITE_PITCH = -30

class Camera(DirectObject):
    def __init__(self, target: NodePath, showbase: ShowBase = None):
        self.target: NodePath = target
        self.base = showbase if showbase else base

        self.mouse = Mouse(self.base)
        self.base.disableMouse()

        self.fov = 50
        self.zoomLevel = 0
        self.maxZoomOut = 5
        self.zoomInSpeed = 3
        self.zoomOutSpeed = .2
        self.zoom_locked = False

        self.lookAhead = Vec3(0)
        self.smoothingAhead = 3
        self.smoothingBack = .5
        self.maxLookAhead = .25

        self.heading = 0.0
        self.pitch = -10

        self.camDistance = 10.0
        self.minCamDistance = 5.0
        self.maxCamDistance = 40.0
        self.zoomScrollSpeed = 0.125
        
        self.rotate = False
        self.rotationSensitivity = 0.2

        self.setupCamera()
        self.applyCameraDistance()

        self.accept('wheel_up', self.zoomCamera, [-(self.zoomScrollSpeed)])
        self.accept('wheel_down', self.zoomCamera, [self.zoomScrollSpeed])
        self.accept('mouse3', self.rotateStatus)
        self.accept('mouse3-up', self.rotateStatus)

    def rotateStatus(self):
        self.rotate = not self.rotate
        if self.rotate: self.mouse.centerMouse()

    def setupCamera(self):
        self.camPivot = self.base.render.attach_new_node('camPivot')
        self.pivot = self.camPivot.attach_new_node('pivot')
        self.base.camera.reparent_to(self.pivot)
        self.base.camera.setHpr(0, 0, 0)

    def setZoomLock(self, is_locked: bool):
        self.zoom_locked = is_locked

    def zoomCamera(self, delta: float):
        if self.zoom_locked:
            return
        self.camDistance = max(self.minCamDistance, min(self.maxCamDistance, self.camDistance + (delta * self.camDistance)))
        self.applyCameraDistance()

    def applyCameraDistance(self):
        self.base.camera.setPos(0, -self.camDistance, 0)
        self.mouse.captureMouse()

    def setPos(self, pos: Point3):
        self.camPivot.setPos(pos)

    def calculateCameraPos(self, dt, movementVector: Vec3, lastMovement: Vec3, is_locked = False):
        currentLookAhead = self.lookAhead
        if movementVector.length() >= lastMovement.length() and lastMovement.length() > 0:
            targetLookAhead = movementVector * self.maxLookAhead
            smoothing = self.smoothingAhead
        else:
            targetLookAhead = Vec3(0)
            smoothing = self.smoothingBack

        self.lookAhead = self.powLerp(currentLookAhead, targetLookAhead, dt, smoothing)

        if not is_locked:
            transition_speed = .3
            self.pitch = self.powLerp(self.pitch, SATELLITE_PITCH - 1.5 * self.camDistance, dt, transition_speed)

            if self.rotate and self.mouse.hasMouse():
                dx, _ = self.mouse.getMouseDelta()
                self.heading -= dx * self.rotationSensitivity
                self.mouse.centerMouse()

        self.pivot.setH(self.heading)
        self.pitch = max(-80, min(80, self.pitch))
        self.pivot.setP(self.pitch)

        height_offset = Vec3(0, 0, 1.5)
        return self.target.getPos() + self.lookAhead + height_offset

    def updateFov(self, dt, isMoving):
        self.zoomLevel = self.maxZoomOut if isMoving else 0
        targetFov = self.fov + self.zoomLevel
        currentFov = self.base.camLens.getFov()[0]

        if targetFov > currentFov:
            smoothingSpeed = self.zoomOutSpeed
        else:
            smoothingSpeed = self.zoomInSpeed

        currentFov += (targetFov - currentFov) * (1 - exp(-smoothingSpeed * dt))
        self.base.camLens.setFov(currentFov)