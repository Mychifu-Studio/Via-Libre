# interaction.py
from panda3d.core import CollisionTraverser, CollisionNode, CollisionRay, CollisionHandlerQueue

class InteractionManager:
    """SRP: Gère uniquement la détection (rayon souris ou proximité) et la mise en surbrillance."""
    def __init__(self, base, player_root, camera, build_manager):
        self.base = base
        self.player_root = player_root
        self.camera = camera
        self.build_manager = build_manager
        
        self.rayon_interaction = 2 
        self.structure_cible = None 
        
        # Système de Raycast isolé ici
        self.picker = CollisionTraverser()
        self.picker_queue = CollisionHandlerQueue()
        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.base.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(CollisionNode.getDefaultCollideMask())
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.picker.addCollider(self.picker_np, self.picker_queue)

    def get_structure_sous_souris(self):
        if not self.base.mouseWatcherNode.hasMouse():
            return None
        mpos = self.base.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(self.base.camNode, mpos.getX(), mpos.getY())
        self.picker.traverse(self.base.render)
        
        if self.picker_queue.getNumEntries() > 0:
            self.picker_queue.sortEntries()
            noeud_touche = self.picker_queue.getEntry(0).getIntoNodePath()
            return noeud_touche.getPythonTag("structure")
        return None

    def update(self):
        # 1. Nettoyer l'état précédent
        for s in self.build_manager.structures:
            s.ui.hide()
            s.retirer_surlignage()
        self.structure_cible = None

        pos_joueur = self.player_root.getPos(self.base.render)
        pos_joueur.setZ(0)

        # 2. Mode Troisième personne (Proximité)
        if self.camera.mode == 1:
            distance_mini = float('inf')
            for s in self.build_manager.structures:
                pos_s = s.np.getPos(self.base.render)
                pos_s.setZ(0)
                dist = (pos_s - pos_joueur).length()
                
                if dist <= self.rayon_interaction and dist < distance_mini:
                    distance_mini = dist
                    self.structure_cible = s
                    
            if self.structure_cible:
                self.structure_cible.ui.show()

        # 3. Mode Satellite (Survol de la souris)
        elif self.camera.mode == 0:
            structure = self.get_structure_sous_souris()
            if structure:
                pos_s = structure.np.getPos(self.base.render)
                pos_s.setZ(0)
                if (pos_s - pos_joueur).length() <= self.build_manager.rayon_max_construction:
                    self.structure_cible = structure
                    self.structure_cible.surligner()
                    
        # Gestion du conflit visuel avec l'hologramme
        if self.structure_cible is not None:
            self.build_manager.hologramme.hide()
        elif self.build_manager.mode_actif:
            self.build_manager.hologramme.show()