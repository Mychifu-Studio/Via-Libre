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

        # ----- Setup Player ----- #
        self.player = self.base.render.attachNewNode('player')
        self.modelNode = self.player.attachNewNode('player-model')
       
        self.model = self.base.loader.loadModel('./assets/dog.bam')
        self.model.setScale(self.model.getScale())
        self.model.reparentTo(self.modelNode)


        self.shoulderNode = self.modelNode.attach_new_node('shoulder')
        self.shoulderNode.setZ(3)


        self.heading = 0


        # ----- Setup Camera ----- #
        self.camera = Camera(self.player)
        # Supprimé: self.camera.setOffset() et self.camera.setP()
        # La nouvelle caméra gère elle-même son offset et son pitch en fonction du mode.

        # ----- Setup Build System & Interactions ----- #
        self.build_manager = BuildManager(self.base, self.player, self.camera)
        self.interaction_manager = InteractionManager(self.base, self.player, self.camera, self.build_manager)


        # ----- Setup Movements ----- #
        self.movementVector = Vec3(0)
        self.lastMovement = Vec3(0)
        self.playerSpeed = 10
        self.turnSpeed = 10.0 # Higher = snappier, lower = smoother


        self.is_paused = False


        # ----- Setup crosshair & cursor ----- #
        # 1. Créer le point de pivot (le parent qui suivra réellement la souris)
        self.cursorRoot = NodePath("cursorRoot")
        self.cursorRoot.reparentTo(self.base.aspect2d)
        self.cursorRoot.setBin("gui-popup", 100)
        self.cursorRoot.setDepthTest(False)
        self.cursorRoot.setDepthWrite(False)


        # 2. Créer l'image et l'attacher au noeud parent
        self.cursor = OnscreenImage(image='./assets/cursor_resized.png', parent=self.cursorRoot)
        self.cursor.setTransparency(TransparencyAttrib.MAlpha)


        # 3. Décaler l'image pour que le coin supérieur gauche soit à (0,0)
        # (On la pousse de +1 en X et -1 en Z)
        self.cursor.setPos(1, 0, -1)


        # 4. Appliquer les échelles et animations SUR LE NOEUD PARENT
        scale = (0.04, 1, 0.04)
        scale_anim = (0.03, 1, 0.03)
        self.cursorRoot.setScale(*scale)


        self.cursorScaleDown = LerpScaleInterval(self.cursorRoot, duration=0.05, scale=scale_anim, startScale=scale)
        self.cursorScaleUp = LerpScaleInterval(self.cursorRoot, duration=0.1, scale=scale, startScale=scale_anim)

        self.crosshair = OnscreenImage(image='./assets/crosshair.png', pos=(0, 0, 0))
        self.crosshair.setTransparency(TransparencyAttrib.MAlpha)
        self.crosshair.setScale(.05, 1, .05)

                # ----- Setup Keys ----- #
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
        self.accept('e', self.supprimer_structure_clavier)
        self.accept('wheel_up', self.build_manager.ajuster_distance, [0.5])
        self.accept('wheel_down', self.build_manager.ajuster_distance, [-0.5])
        self.accept('mouse1', self.handleLeftClick)
        self.accept('mouse1-up', self.cursorScaleUp.start)


        # ----- Setup KeyMap ----- #
        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,


            "ctrl":False,
        }

    def supprimer_structure_clavier(self):
        if self.camera.mode == 1 and self.interaction_manager.structure_cible:
            self.interaction_manager.structure_cible.detruire()

    def handleLeftClick(self):
        self.cursorScaleDown.start()
        
        # En mode satellite (on vérifie d'abord si on clique sur une structure)
        if self.camera.mode == 0:
            cible = self.interaction_manager.structure_cible
            if cible:
                cible.detruire()
                return # On arrête ici, on ne construit pas par-dessus

        # Si on clique dans le vide et que le mode construction est actif
        if self.build_manager.mode_actif:
            self.build_manager.valider_construction()


    def update(self, dt):
        self.updateCursor()


        if self.is_paused:
            self.cursor.show()
            return
       
        # RELATIF
        forward = self.base.render.getRelativeVector(self.camera.pivot, Vec3(0, 1, 0))
        right = self.base.render.getRelativeVector(self.camera.pivot, Vec3(1, 0, 0))


        # ABSOLUE
        # forward = Vec3(0, 1, 0)
        # right = Vec3(1, 0, 0)


        # On supprime l'axe Z pour que le joueur ne s'envole pas ou ne s'enfonce pas dans le sol
        forward.setZ(0)
        right.setZ(0)


        # Normalisation
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


        # 2. Lissage des mouvements (Inertie)
        for axis in range(3):
            maxSpeedTime = .5 if input_vec[axis] else .08
            self.movementVector[axis] = self.camera.powLerp(self.lastMovement[axis], input_vec[axis], dt, maxSpeedTime)


        # 4. Appliquer la position au joueur
        self.player.setPos(self.player.getPos() + self.movementVector * self.playerSpeed * dt)


        # 5. Mise à jour de la caméra
        # Note : on ne fait PLUS de lookAt() sur la caméra, elle s'oriente toute seule.
       
        new_cam_pos = self.camera.calculateCameraPos(dt, self.movementVector, self.lastMovement, self.keyMap["ctrl"] or self.is_paused)
        self.camera.setPos(new_cam_pos)
        if not (self.is_paused or self.keyMap['ctrl']):
            self.camera.updateFov(dt, any(self.keyMap.values()))


        self.lastMovement = self.movementVector


        self.interaction_manager.update() # Remplace gerer_surbrillance_interactions()
        self.build_manager.update()
           
    def updateCursor(self):
        # Si la fenêtre a été détruite, on annule l'exécution
        if getattr(self.base, 'win', None) is None:
            return
       
        if self.base.mouseWatcherNode.hasMouse() and (self.camera.mode == 0 or self.is_paused or self.keyMap['ctrl']):
            self.cursor.show()
            self.crosshair.hide()
            # Récupère les coordonnées normalisées (-1 à 1)
            x = self.base.mouseWatcherNode.getMouseX()
            y = self.base.mouseWatcherNode.getMouseY()
           
            # Récupère le ratio de l'écran pour corriger la position sur l'axe horizontal
            ratio = self.base.getAspectRatio()
           
            # On applique le ratio à X, Y est à 0 (profondeur), Z prend la valeur verticale
            self.cursorRoot.setPos(x * ratio, 0, y)
        else:
            self.cursor.hide()
            if self.camera.mode == 1:
                self.crosshair.show()


    def updateKeyMap(self, key, value):
        self.keyMap[key] = value
        if key == 'ctrl' and value == False:
            self.camera.mouse.centerMouse()

    def gerer_surbrillance_interactions(self):
        """Gère l'affichage visuel des objets interactifs autour du joueur"""
        
        # 1. On commence par réinitialiser TOUTES les structures
        for s in self.build_system.structures:
            s.cacher_ui()
            s.retirer_surlignage()
        self.build_system.structure_cible = None

        # Position du joueur au sol
        pos_joueur = self.player.getPos(self.base.render)
        pos_joueur.setZ(0)

        # === MODE 1 : TROISIÈME PERSONNE (Proximité = Fenêtre UI) ===
        if self.camera.mode == 1:
            structure_proche = None
            distance_mini = float('inf')
            
            for s in self.build_system.structures:
                pos_s = s.np.getPos(self.base.render)
                pos_s.setZ(0)
                dist = (pos_s - pos_joueur).length()
                
                if dist <= self.build_system.rayon_interaction and dist < distance_mini:
                    distance_mini = dist
                    structure_proche = s
                    
            self.build_system.structure_cible = structure_proche
            if self.build_system.structure_cible:
                self.build_system.structure_cible.afficher_ui()

        # === MODE 0 : VUE SATELLITE (Raycast Souris = Changement de couleur) ===
        elif self.camera.mode == 0:
            if self.base.mouseWatcherNode.hasMouse():
                mpos = self.base.mouseWatcherNode.getMouse()
                
                # On utilise les outils de raycast du build_system
                self.build_system.picker_ray.setFromLens(self.base.camNode, mpos.getX(), mpos.getY())
                self.build_system.picker.traverse(self.base.render)
                
                if self.build_system.picker_queue.getNumEntries() > 0:
                    self.build_system.picker_queue.sortEntries()
                    entry = self.build_system.picker_queue.getEntry(0)
                    noeud_touche = entry.getIntoNodePath()
                    
                    structure = noeud_touche.getPythonTag("structure")
                    if structure:
                        pos_s = structure.np.getPos(self.base.render)
                        pos_s.setZ(0)
                        
                        if (pos_s - pos_joueur).length() <= self.build_system.rayon_max_construction:
                            self.build_system.structure_cible = structure
                            self.build_system.structure_cible.surligner()