from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TextNode


class IntroScreens:
    """
    Gère :
    - la citation en fondu
    - l'écran d'introduction principal
    - le démarrage du jeu
    """

    def __init__(self, game):
        self.game = game
        self.game.intro_phase = "quote"

    # =========================================================
    # ECRAN 1 - CITATION
    # =========================================================
    def create_quote_screen(self):
        self.quote_bg = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-2, 2, -2, 2),
            pos=(0, 0, 0)
        )

        self.quote_line1 = OnscreenText(
            text="Nuestra Lucha es una Lucha a Muerte",
            pos=(0, 0.15),
            scale=0.07,
            fg=(1, 1, 1, 0),
            align=TextNode.ACenter
        )

        self.quote_line2 = OnscreenText(
            text="Patria o muerte",
            pos=(0, 0.03),
            scale=0.065,
            fg=(1, 1, 1, 0),
            align=TextNode.ACenter
        )

        self.quote_author = OnscreenText(
            text="Ernesto DelaCruz",
            pos=(0, -0.45),
            scale=0.05,
            fg=(0.85, 0.85, 0.85, 0),
            align=TextNode.ACenter
        )

        self.quote_time = 0.0
        self.game.taskMgr.add(self.update_quote_fade, "quote_fade_task")

    def update_quote_fade(self, task):
        dt = globalClock.getDt()
        self.quote_time += dt

        quote_fade_in = 2.0
        author_delay = 1.2
        author_fade_in = 1.2
        hold_duration = 2.0
        fade_out_duration = 2.0

        author_start = author_delay
        hold_start = max(quote_fade_in, author_start + author_fade_in)
        fade_out_start = hold_start + hold_duration
        total_duration = fade_out_start + fade_out_duration

        if self.quote_time < quote_fade_in:
            quote_alpha = self.quote_time / quote_fade_in
        elif self.quote_time < fade_out_start:
            quote_alpha = 1.0
        elif self.quote_time < total_duration:
            t = self.quote_time - fade_out_start
            quote_alpha = 1.0 - (t / fade_out_duration)
        else:
            quote_alpha = 0.0

        if self.quote_time < author_start:
            author_alpha = 0.0
        elif self.quote_time < author_start + author_fade_in:
            t = self.quote_time - author_start
            author_alpha = t / author_fade_in
        elif self.quote_time < fade_out_start:
            author_alpha = 1.0
        elif self.quote_time < total_duration:
            t = self.quote_time - fade_out_start
            author_alpha = 1.0 - (t / fade_out_duration)
        else:
            author_alpha = 0.0

        self.quote_line1.setFg((1, 1, 1, quote_alpha))
        self.quote_line2.setFg((1, 1, 1, quote_alpha))
        self.quote_author.setFg((0.85, 0.85, 0.85, author_alpha))

        if self.quote_time >= total_duration:
            self.destroy_quote_screen()
            self.create_intro_screen()
            self.game.intro_phase = "main_intro"
            return task.done

        return task.cont

    def destroy_quote_screen(self):
        self.quote_bg.destroy()
        self.quote_line1.destroy()
        self.quote_line2.destroy()
        self.quote_author.destroy()

    # =========================================================
    # ECRAN 2 - INTRODUCTION
    # =========================================================
    def create_intro_screen(self):
        self.intro_bg = DirectFrame(
            frameColor=(0, 0, 0, 1),
            frameSize=(-2, 2, -2, 2),
            pos=(0, 0, 0)
        )

        self.intro_title = OnscreenText(
            text="¡Via Libre!",
            pos=(0, 0.45),
            scale=0.12,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter
        )

        self.intro_story = OnscreenText(
            text=(
                "Dans un pays brisé par l’oppression,\n"
                "les ressources sont rares et chaque récolte compte.\n\n"
                "Tu incarnes un survivant de la révolution,\n"
                "chargé de collecter des ressources\n"
                "pour reconstruire, résister et faire naître l’espoir.\n\n"
                "Le peuple attend. La route doit être ouverte."
            ),
            pos=(0, 0.08),
            scale=0.06,
            fg=(0.9, 0.9, 0.9, 1),
            align=TextNode.ACenter,
            wordwrap=22
        )

        self.intro_hint = OnscreenText(
            text="Appuie sur Entrée pour commencer",
            pos=(0, -0.58),
            scale=0.06,
            fg=(1, 0.95, 0.6, 1),
            align=TextNode.ACenter
        )

    def destroy_intro_screen(self):
        self.intro_bg.destroy()
        self.intro_title.destroy()
        self.intro_story.destroy()
        self.intro_hint.destroy()

    # =========================================================
    # DEMARRAGE DU JEU
    # =========================================================
    def start_game(self):
        if self.game.intro_phase != "main_intro":
            return

        if self.game.game_started:
            return

        self.game.game_started = True
        self.destroy_intro_screen()