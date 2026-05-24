# interaction.py
from panda3d.core import CollisionTraverser, CollisionNode, CollisionRay, CollisionHandlerQueue

class InteractionManager:
    """SRP: Gère uniquement la détection par rayon souris et la mise en surbrillance."""
    def __init__(self, base, player_root, camera, build_manager):
        self.base = base
        self.player_root = player_root
        self.camera = camera
        self.build_manager = build_manager

        self.rayon_interaction = 2
        self.structure_cible = None

        self.picker = CollisionTraverser()
        self.picker_queue = CollisionHandlerQueue()
        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.base.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(CollisionNode.getDefaultCollideMask())
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.picker.addCollider(self.picker_np, self.picker_queue)

        self.picker_node.setIntoCollideMask(0)

    def get_structure_sous_souris(self):
        mouse_watcher = getattr(self.base, "mouseWatcherNode", None)
        if mouse_watcher is None or not mouse_watcher.hasMouse():
            return None
        mpos = mouse_watcher.getMouse()
        self.picker_ray.setFromLens(self.base.camNode, mpos.getX(), mpos.getY())
        structure_root = getattr(self.build_manager, "structure_root", self.base.render)
        self.picker.traverse(structure_root)

        if self.picker_queue.getNumEntries() > 0:
            self.picker_queue.sortEntries()
            noeud_touche = self.picker_queue.getEntry(0).getIntoNodePath()
            return noeud_touche.getPythonTag("structure")
        return None

    def _clear_hover_state(self):
        if self.structure_cible is None:
            return

        self.structure_cible.retirer_surlignage()
        self.structure_cible.ui.hide()
        self.structure_cible = None

    def update(self):
        if not self.build_manager.mode_actif:
            self._clear_hover_state()
            return

        for s in self.build_manager.structures:
            s.ui.hide()
            s.retirer_surlignage()
        self.structure_cible = None

        if not self.build_manager.structures:
            self.build_manager.hologramme.show()
            return

        pos_joueur = self.player_root.getPos(self.base.render)
        pos_joueur.setZ(0)

        structure = self.get_structure_sous_souris()
        if structure and self.build_manager.mode_actif:
            pos_s = structure.np.getPos(self.base.render)
            pos_s.setZ(0)
            if (pos_s - pos_joueur).length() <= self.build_manager.rayon_max_construction:
                self.structure_cible = structure
                self.structure_cible.surligner()
                self.structure_cible.ui.show() # Affiche l'UI quand survolé

        if self.structure_cible is not None:
            self.build_manager.hologramme.hide()
        elif self.build_manager.mode_actif:
            self.build_manager.hologramme.show()
