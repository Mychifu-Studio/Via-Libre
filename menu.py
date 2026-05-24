from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, DirectButton
from panda3d.core import LVecBase3f
from panda3d.core import CardMaker
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib

widgets = []  # Liste globale qui contient tous les widgets à détruire

def jouer():
    global widgets
    print("Démarrage du jeu avec le nom : ", menu.entry.get())

    # On supprime tous les widgets GUI
    for w in widgets:
        w.destroy()
    widgets.clear()


class MenuBase(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        # Créer une image de fond
        bg_tex = loader.loadTexture("assets/intro.png")  # fichier image
        cm = CardMaker("bg")
        cm.setFrameFullscreenQuad()
        bg = render2d.attachNewNode(cm.generate())
        bg.setTexture(bg_tex)
        bg.setBin("background", 0)

        # === Image avec transparence (logo) ===
        logo = OnscreenImage(
            image="assets/Titre.png",          # chemin vers ton PNG
            pos=(0, 0, 0.6),          # centré en haut de l'écran
            scale=(0.8, 1, 0.4),      # ajuste la taille (x, y, z → width/height)
            parent=base.aspect2d      # ou render2d, mais aspect2d respecte le ratio
        )
        logo.setTransparency(TransparencyAttrib.MAlpha)  # active la transparence

        global menu
        menu = self

        # Boutons
        btn_jouer = DirectButton(
            text="Jouer",
            scale=0.1,
            pos=LVecBase3f(0, 0, 0.1),
            command=jouer,
            # Fond transparent
            frameColor=(1, 1, 1, 0),
            # Optionnel : relief plat pour éviter l’effet 3D
            relief=None
        )

        btn_options = DirectButton(
            text="Options",
            scale=0.1,
            pos=LVecBase3f(0, 0, ),
            # Fond transparent
            frameColor=(1, 1, 1, 0),
            # Optionnel : relief plat pour éviter l’effet 3D
            relief=None
        )

        btn_quitter = DirectButton(
            text="Quitter",
            scale=0.1,
            pos=LVecBase3f(0, 0, -0.2),
            command=base.userExit,
            # Fond transparent
            frameColor=(1, 1, 1, 0),
            # Optionnel : relief plat pour éviter l’effet 3D
            relief=None
        )

        # On ajoute tous les widgets à la liste
        widgets.extend([btn_jouer, btn_options, btn_quitter])


base = MenuBase()
base.run()