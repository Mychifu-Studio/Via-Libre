from direct.gui.DirectGui import DirectLabel, DirectFrame
from panda3d.core import TextNode


class VagueManager:
    def __init__(self, game, enemy_manager):
        self.game = game
        self.enemy_manager = enemy_manager

        self.current_wave_index = 0
        self.killed_in_current_wave = 0
        self.current_enemy_target = 0
        self.is_finished = False

        self.next_wave_timer = 0.0
        self.waiting_next_wave = False

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
            },
            {
                "name": "Vague 2",
                "enemy_count": 8,
                "speed": 4.5,
                "chase_speed": 6.5,
                "detection_radius": 14.0,
            },
            {
                "name": "Vague 3",
                "enemy_count": 12,
                "speed": 5.0,
                "chase_speed": 7.0,
                "detection_radius": 16.0,
            },
        ]

        self.wave_label = DirectLabel(
            text="",
            scale=0.09,
            pos=(0, 0, 0.78),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
        )
        self.wave_label.hide()

        self.final_screen = DirectFrame(
            frameColor=(0, 0, 0, 0.85),
            frameSize=(-1.4, 1.4, -0.8, 0.8),
            pos=(0, 0, 0),
        )
        self.final_screen.hide()

        self.final_label = DirectLabel(
            parent=self.final_screen,
            text="Bien joué !\nTu as survécu à toutes les vagues.",
            scale=0.12,
            pos=(0, 0, 0.1),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
        )

    def start(self):
        self.current_wave_index = 0
        self.killed_in_current_wave = 0
        self.current_enemy_target = 0
        self.is_finished = False
        self.waiting_next_wave = False
        self.start_current_wave()

    def start_current_wave(self):
        if self.current_wave_index >= len(self.waves):
            self.finish_game()
            return

        wave = self.waves[self.current_wave_index]

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
        )
        self.current_enemy_target = spawned_count or wave["enemy_count"]

        self.show_message(
            f"{wave['name']}\nÉlimine {self.current_enemy_target} ennemis !",
            duration=2.5,
        )

    def enemy_killed(self):
        if self.is_finished:
            return

        if self.waiting_next_wave:
            return

        self.killed_in_current_wave += 1

        print(
            f"Ennemi tué : {self.killed_in_current_wave}/{self.current_enemy_target}"
        )

        if self.killed_in_current_wave >= self.current_enemy_target:
            self.current_wave_index += 1

            if self.current_wave_index >= len(self.waves):
                self.finish_game()
            else:
                self.waiting_next_wave = True
                self.next_wave_timer = 2.0
                self.show_message("Vague terminée !", duration=2.0)

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.wave_label.hide()

        if self.waiting_next_wave:
            self.next_wave_timer -= dt

            if self.next_wave_timer <= 0:
                self.waiting_next_wave = False
                self.start_current_wave()

    def show_message(self, text, duration=2.0):
        self.wave_label["text"] = text
        self.wave_label.show()
        self.message_timer = duration

    def finish_game(self):
        self.is_finished = True
        self.waiting_next_wave = False
        self.clear_enemies()
        self.wave_label.hide()
        self.final_screen.show()

    def clear_enemies(self):
        for enemy in list(self.enemy_manager.enemies):
            enemy.destroy()

        self.enemy_manager.enemies.clear()
