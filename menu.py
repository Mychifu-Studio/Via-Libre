from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectEntry, DirectButton
from panda3d.core import LVecBase3f
from panda3d.core import CardMaker



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
        bg_tex = loader.loadTexture("bg.jpg")  # fichier image
        cm = CardMaker("bg")
        cm.setFrameFullscreenQuad()
        bg = render2d.attachNewNode(cm.generate())
        bg.setTexture(bg_tex)
        bg.setBin("background", 0)

        # Champ de texte
        self.entry = DirectEntry(
            text="",
            scale=0.1,
            initialText="nom du jeu",
            width=10,
            numLines=1,
            pos=LVecBase3f(-1.0, 0, 0),
            focusInCommand=lambda: self.entry.set("")
        )
        global menu
        menu = self

        # Boutons
        btn_jouer = DirectButton(
            text="Jouer",
            scale=0.1,
            pos=LVecBase3f(0.8, 0, 0.2),
            command=jouer
        )

        btn_options = DirectButton(
            text="Options",
            scale=0.1,
            pos=LVecBase3f(0.8, 0, 0.0)
        )

        btn_quitter = DirectButton(
            text="Quitter",
            scale=0.1,
            pos=LVecBase3f(0.8, 0, -0.2),
            command=base.userExit
        )

        # On ajoute tous les widgets à la liste
        widgets.extend([self.entry, btn_jouer, btn_options, btn_quitter])


base = MenuBase()
base.run()