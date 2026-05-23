from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TextNode


class IntroScreens:
    """
    Gere :
    - la citation en fondu
    - l'ecran d'introduction principal
    - le passage vers le lobby
    """

    def __init__(self, game):
        self.game = game
        self.game.intro_phase = "quote"
        self.quote_bg = None
        self.quote_line1 = None
        self.quote_line2 = None
        self.quote_author = None
        self.intro_bg = None
        self.intro_title = None
        self.intro_story = None
        self.intro_hint = None
        self.quote_time = 0.0

    def _prepare_gui_node(self, node, sort):
        node.setBin("fixed", sort)
        node.setDepthWrite(False)
        node.setDepthTest(False)

    def _destroy_widget(self, attr_name):
        widget = getattr(self, attr_name, None)
        if widget is None:
            return

        widget.destroy()
        setattr(self, attr_name, None)

    def create_quote_screen(self):
        self.quote_bg = DirectFrame(
            parent=self.game.aspect2d,
            frameColor=(0, 0, 0, 1),
            frameSize=(-2, 2, -2, 2),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(self.quote_bg, 230)

        self.quote_line1 = OnscreenText(
            parent=self.game.aspect2d,
            text="Nuestra Lucha es una Lucha a Muerte",
            pos=(0, 0.15),
            scale=0.07,
            fg=(1, 1, 1, 0),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.quote_line1, 231)

        self.quote_line2 = OnscreenText(
            parent=self.game.aspect2d,
            text="Patria o muerte",
            pos=(0, 0.03),
            scale=0.065,
            fg=(1, 1, 1, 0),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.quote_line2, 231)

        self.quote_author = OnscreenText(
            parent=self.game.aspect2d,
            text="Ernesto DelaCruz - 19XX, Valparaiso",
            pos=(0, -0.45),
            scale=0.05,
            fg=(0.85, 0.85, 0.85, 0),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.quote_author, 231)

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
            if hasattr(self.game, "sound"):
                self.game.sound.start_music()
            return task.done

        return task.cont

    def destroy_quote_screen(self):
        self._destroy_widget("quote_bg")
        self._destroy_widget("quote_line1")
        self._destroy_widget("quote_line2")
        self._destroy_widget("quote_author")

    def create_intro_screen(self):
        self.intro_bg = DirectFrame(
            parent=self.game.aspect2d,
            frameColor=(0, 0, 0, 1),
            frameSize=(-2, 2, -2, 2),
            pos=(0, 0, 0),
        )
        self._prepare_gui_node(self.intro_bg, 230)

        self.intro_title = OnscreenText(
            parent=self.game.aspect2d,
            text="¡Via Libre!",
            pos=(0, 0.45),
            scale=0.12,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.intro_title, 231)

        self.intro_story = OnscreenText(
            parent=self.game.aspect2d,
            text=(
                "Dans un pays brisé par l'oppression,\n"
                "les ressources sont rares et chaque récolte compte.\n\n"
                "Tu incarnes un survivant de la révolution,\n"
                "chargé de collecter des ressources\n"
                "pour reconstruire, résister et faire naître l'espoir.\n\n"
                "Le peuple attend. La route doit être ouverte."
            ),
            pos=(0, 0.08),
            scale=0.06,
            fg=(0.9, 0.9, 0.9, 1),
            align=TextNode.ACenter,
            wordwrap=22,
        )
        self._prepare_gui_node(self.intro_story, 231)

        self.intro_hint = OnscreenText(
            parent=self.game.aspect2d,
            text="Appuie sur Entrée pour commencer",
            pos=(0, -0.58),
            scale=0.06,
            fg=(1, 0.95, 0.6, 1),
            align=TextNode.ACenter,
        )
        self._prepare_gui_node(self.intro_hint, 231)

        self.game.accept("enter", self.finish_intro)
        self.game.accept("raw-enter", self.finish_intro)

    def destroy_intro_screen(self):
        self._destroy_widget("intro_bg")
        self._destroy_widget("intro_title")
        self._destroy_widget("intro_story")
        self._destroy_widget("intro_hint")

    def start_game(self):
        self.finish_intro()

    def finish_intro(self):
        if self.game.intro_phase != "main_intro":
            return

        self.destroy_intro_screen()
        self.game.ignore("enter")
        self.game.ignore("raw-enter")
        self.game.intro_phase = "done"

        if hasattr(self.game, "finish_intro"):
            self.game.finish_intro()

    def destroy(self):
        self.game.taskMgr.remove("quote_fade_task")
        self.destroy_quote_screen()
        self.destroy_intro_screen()
        self.game.ignore("enter")
        self.game.ignore("raw-enter")
        self.game.intro_phase = "done"
