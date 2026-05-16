from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, Point3, NodePath
from math import exp


from vialibre.mouseHandler import Mouse


SATELLITE_PITCH = -30
SATELLITE_HEADING = 0


class Camera(DirectObject):
    def __init__(self, target: NodePath, showbase: ShowBase = None):
        self.target: NodePath = target
        self.base = showbase if showbase else base
       
        self.mouse = Mouse(self.base)


        # /!\ TRÈS IMPORTANT : Désactiver le Trackball par défaut de Panda3D
        self.base.disableMouse()


        #----- FOV variables declaration -----------#
        self.fov = 50
        self.zoomLevel = 0
        self.maxZoomOut = 5
        self.zoomInSpeed = 3
        self.zoomOutSpeed = .2
        self.zoom_locked = False


        #----- LookAhead variables declaration -----#
        self.lookAhead = Vec3(0)
        self.smoothingAhead = 3
        self.smoothingBack = .5
        self.maxLookAhead = .25      


        #----- Variables Rotation & Mode -----------#
        self.heading = 0.0
        self.pitch = -10
        # self.orbitHeading = 0.0
        self.orbitPitch = -10


        self.inTransition = False
        self.mode = -1 # Force la mise à jour au premier lancement


        #----- Initate the camera ------------------#
        self.camDistance = 10.0
        self.minCamDistance = 5.0
        self.maxCamDistance = 40.0
        self.zoomScrollSpeed = 0.125
       
        self.setupCamera()
        self.applyCameraDistance()


        self.accept('wheel_up', self.zoomCamera, [-(self.zoomScrollSpeed)])
        self.accept('wheel_down', self.zoomCamera, [self.zoomScrollSpeed])


    def setupCamera(self):
        self.camPivot = self.base.render.attach_new_node('camPivot')
        self.pivot = self.camPivot.attach_new_node('pivot')
        self.base.camera.reparent_to(self.pivot)
       
        # /!\ TRÈS IMPORTANT : Remettre la rotation à 0 pour qu'elle fixe le joueur
        self.base.camera.setHpr(0, 0, 0)


    def setZoomLock(self, is_locked: bool):
        """Verrouille ou déverrouille la possibilité de zoomer avec la caméra"""
        self.zoom_locked = is_locked


    def zoomCamera(self, delta: float):
        if self.zoom_locked:
            return
       
        self.camDistance = max(self.minCamDistance, min(self.maxCamDistance, self.camDistance + (delta * self.camDistance)))
        self.applyCameraDistance()


    def applyCameraDistance(self):
        self.base.camera.setPos(0, -self.camDistance, 0)
       
        threshold = 0.35 * self.maxCamDistance
        new_mode = 0 if self.camDistance > threshold else 1


        if new_mode != self.mode:
            self.mode = new_mode


            self.inTransition = True
           
            if self.mode == 1:
                # Mode Orbite : Cacher la souris
                # props.setCursorHidden(True)
                # props.
                self.mouse.captureMouse()
            else:
                # Mode Satellite : Réafficher la souris
                # props.setCursorHidden(True)
                # props.setMouseMode(WindowProperties.M_absolute)
                self.mouse.captureMouse()
           
            # Centrage immédiat pour éviter un bond de caméra au changement de mode
            # if self.mode == 1:
            #     self.mouse.centerMouse()


    def setPos(self, pos: Point3):
        self.camPivot.setPos(pos)


    def calculateCameraPos(self, dt, movementVector: Vec3, lastMovement: Vec3, is_locked = False):
        """Calculates a new position for the camera."""
        currentLookAhead = self.lookAhead
        if movementVector.length() >= lastMovement.length() and lastMovement.length() > 0:
            targetLookAhead = movementVector * self.maxLookAhead
            smoothing = self.smoothingAhead
        else:
            targetLookAhead = Vec3(0)
            smoothing = self.smoothingBack


        self.lookAhead = self.powLerp(currentLookAhead, targetLookAhead, dt, smoothing)


        # --- Gestion des Rotations ---
        if is_locked:
            pass
        elif self.mode == 1:
            self.lastMode = 1
            # MÉTHODE ROBUSTE : Vérifier que la souris est bien dans la fenêtre via le mouseWatcher
            if self.mouse.hasMouse():
                dx, dy = self.mouse.getMouseDelta()


                # Application de la sensitivité (0.2 est une bonne valeur de base pour des pixels)
                sensitivity = 0.2


                if self.inTransition:
                    transition_speed = 0.1
                #     self.heading = self.lerpAngle(self.heading, self.orbitHeading, dt, transition_speed)
                    self.pitch = self.powLerp(self.pitch, self.orbitPitch, dt, transition_speed)
                    self.heading -=  dx * sensitivity
                   
                #     # Vérifie si la caméra est arrivée à destination (marge d'erreur de 0.5°)
                #     diff_h = abs((self.orbitHeading - self.heading + 180) % 360 - 180)
                    diff_p = abs(self.orbitPitch - self.pitch)
                    if diff_p < 0.5:
                        self.inTransition = False # Fin de la transition !
                # else:
                #     # 100% RAW : aucune latence
                #     self.heading = self.orbitHeading
                #     self.pitch = self.orbitPitch
                else:
                    self.pitch -= dy * sensitivity
                    self.heading -=  dx * sensitivity
                # self.orbitHeading -= dx * sensitivity
                # self.orbitPitch -= dy * sensitivity
                # self.orbitPitch = max(-80, min(80, self.orbitPitch))


                # self.mouse.centerMouse()
               
        else:
            self.lastMode = 0


            transition_speed = .3
            # self.heading = self.lerpAngle(self.heading, SATELLITE_HEADING, dt, transition_speed)
            self.pitch = self.powLerp(self.pitch, SATELLITE_PITCH - 1.5 * self.camDistance, dt, transition_speed)
       
        self.pivot.setH(self.heading)
        self.pitch = max(-80, min(80, self.pitch))
        self.pivot.setP(self.pitch)


        height_offset = Vec3(0, 0, 1.5)
        return self.target.getPos() + self.lookAhead + height_offset


    def powLerp(self, current, target, dt, smoothTime):
        if smoothTime <= 0:
            return target
        return current + (target - current) * (1 - exp(-dt / smoothTime))
   
    def lerpAngle(self, current, target, dt, smoothTime):
        """Un powLerp adapté aux angles pour prendre le chemin le plus court (évite les tours complets)."""
        if smoothTime <= 0:
            return target
        # Calcule la différence d'angle la plus courte (entre -180 et 180)
        diff = (target - current + 180) % 360 - 180
        return current + diff * (1 - exp(-dt / smoothTime))



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