# construction.py
from panda3d.core import TransparencyAttrib, Vec3, Point3, Plane, NodePath
from panda3d.core import CollisionNode, CollisionBox, TextNode

def load_turret(base, np):
    pivot = base.render.attachNewNode("turret_pivot")
    
    try:
        model = base.loader.loadModel("./assets/Turrets/Crossbow.obj")
        model.reparentTo(pivot)
        
        texture = base.loader.loadTexture("./assets/Turrets/Crossbow.png")
        model.setTexture(texture, 1)
        
        # 1. Obtenir les dimensions mathématiques
        min_bounds, max_bounds = model.getTightBounds()
        center = (min_bounds + max_bounds) / 2.0
        
        # 2. Variables d'ajustement visuel (à modifier selon vos tests)
        # Comme nous tournons le modèle de 90° plus bas, les axes locaux peuvent être inversés !
        tweak_x = 0.0  # Modifiez si la tourelle n'est pas bien centrée gauche/droite
        tweak_y = 1.0  # Modifiez pour régler la hauteur (si le modèle d'origine utilise Y pour le haut)
        tweak_z = 0.0  # Modifiez pour régler la hauteur (si le modèle d'origine utilise Z pour le haut)
        
        # On centre mathématiquement, puis on applique vos ajustements
        model.setPos(-center[0] + tweak_x, -center[1] + tweak_y, -center[2] + tweak_z)
        
        # 3. Orientation
        pivot.setHpr(0, 90, 0)
        
    except Exception as e:
        print(f"Erreur de chargement : {e}")

    
    # 4. CORRECTION : On place le pivot exactement sur la position demandée (0,0,0 local)
    # C'est ce qui règle votre problème de décalage sur le côté.
    pivot.setPos(0, 0, 0) 
    pivot.reparentTo(np)
    
    return pivot

from panda3d.core import BillboardEffect
class FloatingUI:
    """SRP: Gère uniquement la création et l'affichage d'un texte flottant en 3D."""
    def __init__(self, base, parent_node, text):
        self.text_node = TextNode('ui_floating')
        self.text_node.setText(text)
        self.text_node.setTextColor(1, 0.2, 0.2, 1)
        self.text_node.setAlign(TextNode.ACenter)
        self.text_node.setCardColor(0, 0, 0, 0.7)
        self.text_node.setCardAsMargin(0.2, 0.2, 0.1, 0.1)
        self.text_node.setCardDecal(True)
        
        self.ui_np = parent_node.attachNewNode(self.text_node)
        self.ui_np.setScale(0.25)
        self.ui_np.setPos(0, 0, 1)
        self.ui_np.setBillboardPointEye()
        # effect = BillboardEffect.make(
        #         up_vector=(0,0,0),
        #         eye_relative=True,
        #         axial_rotate=True,
        #         offset=5,
        #         look_at=base.camera,
        #         look_at_point=Point3(0, 0, 0)
        # )
        # self.ui_np.setEffect(effect)
        self.ui_np.hide()

        self.ui_np.setDepthTest(False)
        self.ui_np.setDepthWrite(False)
        self.ui_np.setBin("fixed", 0)


    def show(self): self.ui_np.show()
    def hide(self): self.ui_np.hide()


class Structure:
    """SRP: Gère uniquement la représentation d'une structure placée dans le monde."""
    def __init__(self, base, position, rotation, on_destroy_callback):
        self.base = base
        self.on_destroy_callback = on_destroy_callback # Callback pour informer le manager
        
        self.np = NodePath("structure_root")
        self.np.reparentTo(self.base.render)
        self.np.setPos(position)
        self.np.setHpr(rotation)
        
        self.model = load_turret(self.base, self.np)

        # ---------------------------------------------------------
        # ADAPTATION AUTOMATIQUE DE LA COLLISION AU MODÈLE 3D
        # ---------------------------------------------------------
        
        # 1. On récupère les limites géométriques exactes du modèle
        min_point, max_point = self.model.getTightBounds()
        
        # 2. On crée la boîte de collision à partir de ces deux points opposés
        c_box = CollisionBox(min_point, max_point)
        
        # 3. On attache la boîte au noeud de collision
        col_node = CollisionNode('structure_col')
        col_node.addSolid(c_box)
        
        self.col_np = self.np.attachNewNode(col_node)
        self.col_np.setPythonTag("structure", self)

        # Astuce de debug : Décommentez la ligne ci-dessous pour voir la boîte !
        # self.col_np.show()
        
        # col_node = CollisionNode('structure_col')
        # col_node.addSolid(CollisionBox(Point3(0, 0, 0.25), 0.25, 0.25, 0.25))
        # self.col_np = self.np.attachNewNode(col_node)
        # self.col_np.setPythonTag("structure", self)
        
        # On délègue l'UI
        self.ui = FloatingUI(self.base, self.np, "Supprimer [E]")

    def detruire(self):
        self.np.removeNode()
        # La structure ne se supprime plus elle-même de la liste, elle prévient le manager
        if self.on_destroy_callback:
            self.on_destroy_callback(self)

    def surligner(self):
        self.model.setColorScale(1.5, 0.5, 0.5, 1.0)

    def retirer_surlignage(self):
        self.model.clearColorScale()


class Hologram:
    """SRP: Gère exclusivement l'affichage du fantôme de construction."""
    def __init__(self, base):
        self.base = base
        self.np = NodePath("hologramme_root")
        self.np.reparentTo(self.base.render)
        
        self.model = load_turret(self.base, self.np)
        
        self.np.setTransparency(TransparencyAttrib.MAlpha)
        self.np.setColorScale(0.2, 0.5, 1.0, 0.5) 
        self.np.hide() 

    def show(self): self.np.show()
    def hide(self): self.np.hide()
    def get_pos(self): return self.np.getPos(self.base.render)
    def get_hpr(self): return self.np.getHpr(self.base.render)
    
    def update_transform(self, pos, hpr):
        self.np.setPos(pos)
        self.np.setHpr(hpr)


class BuildManager:
    """SRP: Orchestre la logique de construction (mode actif, validation, contraintes).
       NOTE: Il n'hérite plus de DirectObject. Il ne gère plus les touches."""
    def __init__(self, showbase, player_root, camera):
        self.base = showbase
        self.player_root = player_root
        self.camera = camera
        
        self.mode_actif = False
        self.distance_construction = 2.5 
        self.distance_min = 1        
        self.rayon_max_construction = 5
        
        self.plan_sol = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
        self.structures = []
        self.hologramme = Hologram(self.base)

    def ajuster_distance(self, delta):
        if self.mode_actif and self.camera.mode == 1:
            nouvelle_distance = self.distance_construction + delta
            self.distance_construction = max(self.distance_min, min(self.rayon_max_construction, nouvelle_distance))

    def basculer_mode(self):
        self.mode_actif = not self.mode_actif
        self.camera.setZoomLock(self.mode_actif)
        if self.mode_actif: self.hologramme.show()
        else: self.hologramme.hide()

    def valider_construction(self):
        if self.mode_actif:
            nouvelle_structure = Structure(
                self.base, 
                self.hologramme.get_pos(), 
                self.hologramme.get_hpr(), 
                self._on_structure_detruite # Callback propre
            )
            self.structures.append(nouvelle_structure)
            self.basculer_mode()

    def _on_structure_detruite(self, structure):
        if structure in self.structures:
            self.structures.remove(structure)
            print("Structure détruite proprement.")

    def contraindre_distance(self, position_cible):
        pos_joueur = self.player_root.getPos(self.base.render)
        pos_joueur.setZ(0)
        vecteur_diff = position_cible - pos_joueur
        distance_actuelle = vecteur_diff.length()
        
        if distance_actuelle > self.rayon_max_construction:
            vecteur_diff.normalize()
            return pos_joueur + (vecteur_diff * self.rayon_max_construction)
        elif distance_actuelle < self.distance_min:
            if distance_actuelle > 0.001:
                vecteur_diff.normalize()
            else:
                vecteur_diff = self.base.render.getRelativeVector(self.base.camera, Vec3(0, 1, 0))
                vecteur_diff.setZ(0)
                vecteur_diff.normalize()
            return pos_joueur + (vecteur_diff * self.distance_min)
        return position_cible

    def update(self):
        if not self.mode_actif:
            return
            
        if self.camera.mode == 1:
            vecteur_avant = self.base.render.getRelativeVector(self.base.camera, Vec3(0, 1, 0))
            vecteur_avant.setZ(0) 
            if vecteur_avant.lengthSquared() > 0:
                vecteur_avant.normalize()
                
            position_cible = self.player_root.getPos(self.base.render) + (vecteur_avant * self.distance_construction)
            self.hologramme.update_transform(position_cible, (self.base.camera.getH(self.base.render), 0, 0))

        elif self.camera.mode == 0 and self.base.mouseWatcherNode.hasMouse():
            mpos = self.base.mouseWatcherNode.getMouse()
            p1, p2 = Point3(), Point3()
            self.base.camLens.extrude(mpos, p1, p2)
            
            p1_global = self.base.render.getRelativePoint(self.base.camera, p1)
            p2_global = self.base.render.getRelativePoint(self.base.camera, p2)
            
            point_intersection = Point3()
            if self.plan_sol.intersectsLine(point_intersection, p1_global, p2_global):
                position_restreinte = self.contraindre_distance(point_intersection)
                self.hologramme.update_transform(position_restreinte, (self.base.camera.getH(self.base.render), 0, 0))