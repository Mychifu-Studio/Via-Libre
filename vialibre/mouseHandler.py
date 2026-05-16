from panda3d.core import WindowProperties
from direct.showbase.ShowBase import ShowBase

class Mouse():
    def __init__(self, base: ShowBase):
        self.base = base

    def captureMouse(self):
        properties = WindowProperties()
        properties.set_cursor_hidden(True)
        # On utilise le mode M_relative, le seul fiable sous Linux pour récupérer les deltas.
        properties.setMouseMode(WindowProperties.M_relative)
        self.base.win.requestProperties(properties)

    def releaseMouse(self):
        properties = WindowProperties()
        properties.set_cursor_hidden(False) # Souvent souhaitable d'afficher le curseur quand on relâche
        # On remet le mode standard quand on libère la souris
        properties.setMouseMode(WindowProperties.M_absolute)
        self.base.win.requestProperties(properties)

    def centerMouse(self):
        # Cette fonction ne doit plus forcer la position avec le mode M_relative.
        # Le système s'assure déjà que le curseur renvoie des mouvements relatifs 
        # depuis le centre de la fenêtre de façon invisible.
        # Nous la laissons vide pour ne pas casser le reste du code qui l'appelle,
        # ou nous pourrions l'utiliser seulement comme un fallback si M_relative échoue.
        pass

    def getMouseDelta(self) -> tuple[int, int]:
        # En mode M_relative, les valeurs renvoyées par getMouseX/Y
        # ne sont plus bornées entre -1 et 1, ce sont des mouvements continus.
        # Mais getPointer(0) renvoie directement le mouvement en pixels (delta)
        # depuis la dernière interrogation (la remise à zéro est gérée par Panda).
        
        md = self.base.win.getPointer(0)
        dx = md.getX()
        dy = md.getY()
        
        # En mode relatif, la position est lue en tant que delta par rapport
        # au centre fictif de la fenêtre, nous devons réinitialiser ces deltas
        # en "re-centrant" virtuellement pour la prochaine frame via un movePointer.
        # Attention : Contrairement au mode absolu, ici movePointer en mode relatif 
        # ne déplace pas la souris physique (interdit sous Wayland), 
        # mais il réinitialise simplement les compteurs de deltas internes de Panda3D.
        
        centerX = self.base.win.getXSize() // 2
        centerY = self.base.win.getYSize() // 2
        self.base.win.movePointer(0, centerX, centerY)

        return (dx - centerX, dy - centerY)

    def hasMouse(self) -> bool:
        # hasMouse() fonctionne toujours, mais comme la souris est invisible et confinée 
        # au centre via M_relative, elle retournera quasiment toujours True
        return self.base.mouseWatcherNode.hasMouse()