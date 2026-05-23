from direct.gui.DirectGui import DirectLabel, DirectFrame
from panda3d.core import TextNode


class VagueManager:
    DEFAULT_MAX_LEVELS = 5
    LEVEL_RETURN_DELAY = 2.0

    def __init__(self, game, enemy_manager):
        self.game = game
        self.enemy_manager = enemy_manager

        self.max_levels = getattr(self.game, "max_levels", self.DEFAULT_MAX_LEVELS)
        self.current_level = getattr(self.game, "current_level", 1)
        self.current_wave_index = 0
        self.killed_in_current_wave = 0
        self.current_enemy_target = 0
        self.is_finished = False
        self.level_completed = False

        self.next_wave_timer = 0.0
        self.waiting_next_wave = False
        self.return_to_lobby_timer = 0.0

        self.message_timer = 0.0

        # Limites interieures de l'arene.
        self.area_min_x = -35
        self.area_max_x = 35
        self.area_min_y = -28
        self.area_max_y = 22
        self.margin = 1.5

        self.waves = [
            {
                "name": "Vague 1",
                "enemy_count": 5,
                "speed": 4.0,
                "chase_speed": 6.0,
                "detection_radius": 12.0,
                "max_hp": 3,
            },
            {
                "name": "Vague 2",
                "enemy_count": 8,
                "speed": 4.5,
                "chase_speed": 6.5,
                "detection_radius": 14.0,
                "max_hp": 3,
            },
            {
                "name": "Vague 3",
                "enemy_count": 12,
                "speed": 5.0,
                "chase_speed": 7.0,
                "detection_radius": 16.0,
                "max_hp": 3,
            },
        ]

        self.wave_panel = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0.02, 0.02, 0.02, 0.72),
            frameSize=(-0.72, 0.72, -0.10, 0.10),
            pos=(0, 0, 0.84),
        )
        self.wave_panel.setBin("fixed", 85)
        self.wave_panel.setDepthWrite(False)
        self.wave_panel.setDepthTest(False)
        self.wave_panel.hide()

        self.wave_label = DirectLabel(
            parent=self.wave_panel,
            text="",
            scale=0.052,
            pos=(0, 0, -0.024),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=24,
        )
        self.wave_label.setBin("fixed", 86)
        self.wave_label.setDepthWrite(False)
        self.wave_label.setDepthTest(False)

        self.final_screen = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0, 0, 0, 0.88),
            frameSize=(-1.4, 1.4, -0.8, 0.8),
            pos=(0, 0, 0),
        )
        self.final_screen.setBin("fixed", 200)
        self.final_screen.setDepthWrite(False)
        self.final_screen.setDepthTest(False)
        self.final_screen.hide()

        self.final_label = DirectLabel(
            parent=self.final_screen,
            text="Bien joue !\nTu as termine les 5 niveaux.",
            scale=0.09,
            pos=(0, 0, 0.08),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=22,
        )
        self.final_label.setBin("fixed", 201)
        self.final_label.setDepthWrite(False)
        self.final_label.setDepthTest(False)

    def start(self):
        self.set_level(getattr(self.game, "current_level", self.current_level))
        self.current_wave_index = 0
        self.killed_in_current_wave = 0
        self.current_enemy_target = 0
        self.is_finished = False
        self.level_completed = False
        self.waiting_next_wave = False
        self.return_to_lobby_timer = 0.0
        self.final_screen.hide()
        self.start_current_wave()

    def set_level(self, level_number):
        self.max_levels = getattr(self.game, "max_levels", self.max_levels)
        self.current_level = max(1, min(int(level_number), self.max_levels))

    def _level_index(self):
        return max(0, self.current_level - 1)

    def _scaled_wave(self, wave):
        level_index = self._level_index()
        wave_index = self.current_wave_index
        return {
            **wave,
            "enemy_count": wave["enemy_count"] + level_index * 3 + level_index * wave_index,
            "speed": wave["speed"] + level_index * 0.45,
            "chase_speed": wave["chase_speed"] + level_index * 0.55,
            "detection_radius": wave["detection_radius"] + level_index * 1.5,
            "max_hp": wave["max_hp"] + level_index,
        }

    def _is_host(self):
        net_iface = getattr(self.game, "network", None)
        if net_iface is None or getattr(net_iface, "net", None) is None:
            return True
        return net_iface.net.is_host

    def start_current_wave(self):
        if not self._is_host():
            return

        if self.current_wave_index >= len(self.waves):
            self.finish_level()
            return

        wave = self._scaled_wave(self.waves[self.current_wave_index])

        self.killed_in_current_wave = 0
        self.clear_enemies()

        spawned_count = self.enemy_manager.spawn_random_dogs_in_area(
            count=wave["enemy_count"],
            area_min_x=self.area_min_x,
            area_max_x=self.area_max_x,
            area_min_y=self.area_min_y,
            area_max_y=self.area_max_y,
            speed=wave["speed"],
            scale=1.0,
            margin=self.margin,
            chase_speed=wave["chase_speed"],
            detection_radius=wave["detection_radius"],
            max_hp=wave["max_hp"],
        )
        self.current_enemy_target = spawned_count or wave["enemy_count"]

        self.show_message(
            f"Niveau {self.current_level}/{self.max_levels} - {wave['name']}\n"
            f"Protege le tuyau contre {self.current_enemy_target} ennemis !",
            duration=2.5,
        )

    def enemy_killed(self):
        if not self._is_host():
            return

        if self.is_finished:
            return

        if self.waiting_next_wave:
            return

        self.killed_in_current_wave += 1

        print(f"Ennemi retire : {self.killed_in_current_wave}/{self.current_enemy_target}")

        if self.killed_in_current_wave >= self.current_enemy_target:
            self.current_wave_index += 1

            if self.current_wave_index >= len(self.waves):
                self.finish_level()
            else:
                self.waiting_next_wave = True
                self.next_wave_timer = 2.0
                self.show_message("Vague terminee !", duration=2.0)

    def enemy_reached_base(self):
        self.enemy_killed()

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.wave_panel.hide()

        if not self._is_host():
            return

        if self.level_completed:
            self.return_to_lobby_timer -= dt
            if self.return_to_lobby_timer <= 0:
                self.level_completed = False
                if hasattr(self.game, "complete_current_level"):
                    self.game.complete_current_level()
            return

        if self.waiting_next_wave:
            self.next_wave_timer -= dt

            if self.next_wave_timer <= 0:
                self.waiting_next_wave = False
                self.start_current_wave()

    def show_message(self, text, duration=2.0):
        self.wave_label["text"] = text
        self.wave_panel.show()
        self.message_timer = duration

    def finish_level(self):
        if self.current_level >= self.max_levels:
            self.finish_game()
            return

        self.is_finished = True
        self.level_completed = True
        self.waiting_next_wave = False
        self.return_to_lobby_timer = self.LEVEL_RETURN_DELAY
        self.clear_enemies()
        self.show_message(
            f"Niveau {self.current_level}/{self.max_levels} termine !\nRetour au lobby...",
            duration=self.LEVEL_RETURN_DELAY,
        )

    def finish_game(self):
        self.is_finished = True
        self.level_completed = False
        self.waiting_next_wave = False
        self.clear_enemies()
        self.wave_panel.hide()
        self.final_label["text"] = f"Bien joue !\nTu as termine les {self.max_levels} niveaux."
        self.final_screen.show()
        if hasattr(self.game, "mark_game_completed"):
            self.game.mark_game_completed()

    def game_over(self):
        self.is_finished = True
        self.level_completed = False
        self.waiting_next_wave = False
        self.clear_enemies()
        self.wave_panel.hide()
        self.final_screen.hide()

    def clear_enemies(self):
        for enemy in list(self.enemy_manager.enemies):
            enemy.destroy()

        self.enemy_manager.enemies.clear()

    def sync_from_snapshot(
        self,
        wave_index,
        is_finished,
        is_game_over=False,
        current_level=None,
        game_completed=False,
    ):
        if is_game_over:
            self.game_over()
            return

        if current_level is not None:
            self.set_level(current_level)

        if game_completed:
            self.finish_game()
            return

        if self.current_wave_index != wave_index and not is_finished:
            self.current_wave_index = wave_index
            if self.current_wave_index < len(self.waves):
                wave = self._scaled_wave(self.waves[self.current_wave_index])
                self.show_message(
                    f"Niveau {self.current_level}/{self.max_levels} - {wave['name']}\n"
                    f"Elimine {wave['enemy_count']} ennemis !",
                    duration=2.5,
                )

        if is_finished and not self.is_finished:
            self.is_finished = True
            self.waiting_next_wave = False
            self.clear_enemies()
            self.show_message(
                f"Niveau {self.current_level}/{self.max_levels} termine !\nRetour au lobby...",
                duration=self.LEVEL_RETURN_DELAY,
            )
