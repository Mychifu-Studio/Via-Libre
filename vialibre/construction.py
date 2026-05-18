# construction.py
from panda3d.core import TransparencyAttrib, Vec3, Point3, Plane, NodePath
from panda3d.core import CollisionNode, CollisionBox, TextNode
from panda3d.core import LineSegs
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval, Func

def load_turret(base, np):
    pivot = base.render.attachNewNode("turret_pivot")
    
    try:
        model = base.loader.loadModel("./assets/Turrets/Crossbow.obj")
        model.reparentTo(pivot)
        
        texture = base.loader.loadTexture("./assets/Turrets/Crossbow.png")
        model.setTexture(texture, 1)
        
        min_bounds, max_bounds = model.getTightBounds()
        center = (min_bounds + max_bounds) / 2.0
        
        tweak_x = 0.0
        tweak_y = 1.0
        tweak_z = 0.0
        
        model.setPos(-center[0] + tweak_x, -center[1] + tweak_y, -center[2] + tweak_z)
        pivot.setHpr(0, 90, 0)
        
    except Exception as e:
        print(f"Erreur de chargement : {e}")

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
        self.ui_np.hide()

        self.ui_np.setDepthTest(False)
        self.ui_np.setDepthWrite(False)
        self.ui_np.setBin("fixed", 0)

    def show(self): self.ui_np.show()
    def hide(self): self.ui_np.hide()

class Structure:
    """SRP: Gère la représentation d'une structure placée dans le monde et son comportement."""
    def __init__(self, base, position, rotation, on_destroy_callback, enemy_manager=None):
        self.base = base
        self.on_destroy_callback = on_destroy_callback
        self.enemy_manager = enemy_manager
        
        self.np = NodePath("structure_root")
        self.np.reparentTo(self.base.render)
        self.np.setPos(position)
        self.np.setHpr(rotation)
        
        self.model = load_turret(self.base, self.np)

        min_point, max_point = self.model.getTightBounds()
        c_box = CollisionBox(min_point, max_point)
        col_node = CollisionNode('structure_col')
        col_node.addSolid(c_box)
        
        self.col_np = self.np.attachNewNode(col_node)
        self.col_np.setPythonTag("structure", self)

        self.ui = FloatingUI(self.base, self.np, "Supprimer [Clic]")

        # --- NOUVEAU : Paramètres de combat ---
        self.activation_radius = 15.0  # Distance à partir de laquelle on vise/tire
        self.fire_rate = 1.0           # Temps en secondes entre chaque tir
        self.time_since_last_shot = 0.0

        self.offset_turret = Vec3(0, 0, 0.5)
        self.offset_enemies = Vec3(0, 0, 0)
        
        # --- NOUVEAU : Tâche de mise à jour propre à la tourelle ---
        self.task_name = f"turret_update_{id(self)}"
        self.base.taskMgr.add(self.update_task, self.task_name)

    def create_tracer_effect(self, start_pos, target_pos):
        # 1. Création de la forme du tracer
        lines = LineSegs()
        lines.setThickness(4.0)
        lines.setColor(1.0, 0.8, 0.2, 1.0) # Couleur jaune-orangée
        
        direction = target_pos - start_pos
        distance = direction.length()
        if distance < 0.1: 
            return
            
        direction.normalize()
        # Le tracer est un petit segment (max 1.5 unité de long)
        tracer_length = min(1.5, distance) 
        
        lines.moveTo(0, 0, 0)
        lines.drawTo(direction * tracer_length)
        
        # 2. Ajout du tracer dans le monde
        tracer_np = self.base.render.attachNewNode(lines.create())
        tracer_np.setPos(start_pos)
        tracer_np.setLightOff() # Rend le tracer lumineux même sans lumière dynamique
        
        # 3. Animation
        speed = 120.0 # Vitesse de déplacement très rapide
        duration = distance / speed
        
        # Sequence exécute les actions l'une après l'autre :
        # - Déplace le tracer de A vers B
        # - Puis appelle une fonction pour le supprimer
        seq = Sequence(
            LerpPosInterval(tracer_np, duration, target_pos, startPos=start_pos),
            Func(tracer_np.removeNode)
        )
        seq.start()

    def update_task(self, task):
        # Calcul du deltaTime
        dt = task.time - getattr(task, 'last_time', task.time)
        task.last_time = task.time

        if not self.enemy_manager or not self.enemy_manager.enemies:
            return task.cont

        my_pos = self.np.getPos(self.base.render)
        closest_enemy = None
        min_dist = float('inf')

        # 1. Trouver l'ennemi le plus proche
        for enemy in self.enemy_manager.enemies:
            enemy_pos = enemy.node.getPos(self.base.render)
            dist = (enemy_pos - my_pos).length()
            if dist < min_dist:
                min_dist = dist
                closest_enemy = enemy

        # 2. S'orienter et tirer si dans le rayon d'activation
        if closest_enemy and min_dist <= self.activation_radius:
            enemy_pos = closest_enemy.node.getPos(self.base.render)
            
            # Orienter la tourelle (sécurité pour éviter une erreur si distance == 0)
            if min_dist > 0.1:
                self.np.lookAt(enemy_pos)
                # On bloque le pitch/roll à 0 pour que la base de la tourelle reste droite sur le sol
                self.np.setHpr(self.np.getH() + 180, 0, 0) # +180 sinon ça pointait du cul

            # Gérer la cadence de tir
            self.time_since_last_shot += dt
            if self.time_since_last_shot >= self.fire_rate:
                self.time_since_last_shot = 0.0

                start_pos_visuel = Point3(my_pos.x, my_pos.y, my_pos.z + 1.2) + self.offset_turret
                target_pos_visuel = Point3(enemy_pos.x, enemy_pos.y, enemy_pos.z + 0.5) + self.offset_enemies

                self.create_tracer_effect(start_pos_visuel, target_pos_visuel)
                
                # Le tir est calculé comme un segment instantané (hitscan)
                # Si le segment "touche" l'ennemi le plus proche, la méthode l'éliminera.
                self.enemy_manager.check_projectile_hit(my_pos, enemy_pos, hit_radius=1.0)

        return task.cont

    def detruire(self):
        # Nettoyer la tâche lorsqu'on supprime la tourelle
        self.base.taskMgr.remove(self.task_name)
        
        self.np.removeNode()
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
    """SRP: Orchestre la logique de construction."""
    # --- MODIFIÉ : Ajout de enemy_manager en argument ---
    def __init__(self, showbase, player_root, camera):
        self.base = showbase
        self.player_root = player_root
        self.camera = camera
        self.enemy_manager = self.base.enemies # <-- Sauvegarde de la référence
        
        self.mode_actif = False
        self.distance_construction = 2.5 
        self.distance_min = 1        
        self.rayon_max_construction = 5

        self.cost = 5
        
        self.plan_sol = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
        self.structures = []
        self.hologramme = Hologram(self.base)

    def basculer_mode(self):
        self.mode_actif = not self.mode_actif
        self.camera.setZoomLock(self.mode_actif)
        if self.mode_actif: self.hologramme.show()
        else: self.hologramme.hide()

    def valider_construction(self):
        if self.mode_actif and self.base.inventory["ressource"] >= self.cost:
            # --- MODIFIÉ : On passe l'enemy_manager à la nouvelle structure ---
            nouvelle_structure = Structure(
                self.base, 
                self.hologramme.get_pos(), 
                self.hologramme.get_hpr(), 
                self._on_structure_detruite,
                self.enemy_manager
            )
            self.structures.append(nouvelle_structure)
            self.base.inventory["ressource"] -= self.cost
            self.basculer_mode()

    def _on_structure_detruite(self, structure):
        if structure in self.structures:
            self.structures.remove(structure)

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
            
        if self.base.mouseWatcherNode.hasMouse():
            mpos = self.base.mouseWatcherNode.getMouse()
            p1, p2 = Point3(), Point3()
            self.base.camLens.extrude(mpos, p1, p2)
            
            p1_global = self.base.render.getRelativePoint(self.base.camera, p1)
            p2_global = self.base.render.getRelativePoint(self.base.camera, p2)
            
            point_intersection = Point3()
            if self.plan_sol.intersectsLine(point_intersection, p1_global, p2_global):
                position_restreinte = self.contraindre_distance(point_intersection)
                self.hologramme.update_transform(position_restreinte, (self.base.camera.getH(self.base.render), 0, 0))