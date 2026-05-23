from direct.gui.DirectGui import DirectLabel, DirectFrame
from panda3d.core import TextNode, Vec3


# ─────────────────────────────────────────────────────────────────────────────
# Chemins des 6 portails vers le tuyau.
# Chaque liste part du portail et aboutit au tuyau.
# ─────────────────────────────────────────────────────────────────────────────
PORTAL_PATHS = [
    # Portail 1
    [Vec3(6, 25, 0), Vec3(23, 0, 0), Vec3(23, -9, 0), Vec3(19, -9, 0)],
    # Portail 2
    [Vec3(-6, 25, 0), Vec3(-23, 0, 0), Vec3(-23, -9, 0), Vec3(-19, -9, 0)],
    # Portail 3
    [Vec3(-40, -9, 0), Vec3(-30, -15, 0), Vec3(-25, -15, 0), Vec3(-23, -10, 0), Vec3(-19, -10, 0)],
    # Portail 4
    [Vec3(40, -9, 0), Vec3(30, -15, 0), Vec3(25, -15, 0), Vec3(23, -10, 0), Vec3(19, -10, 0)],
    # Portail 5
    [Vec3(-23, 17, 0), Vec3(-30, 2, 0), Vec3(-23, 0, 0), Vec3(-23, -9, 0), Vec3(-19, -9, 0)],
    # Portail 6
    [Vec3(23, 17, 0), Vec3(30, 2, 0), Vec3(23, 0, 0), Vec3(23, -9, 0), Vec3(19, -9, 0)],
]

SPAWN_INTERVAL = 1.5   # secondes entre chaque ennemi sur le meme portail


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

        self.area_min_x = -35
        self.area_max_x = 35
        self.area_min_y = -28
        self.area_max_y = 22
        self.margin = 1.5

        # Résolution conflit : on retire chase_speed/detection_radius (non utilisés
        # par WaypointEnemy), on conserve max_hp pour le scaling par niveau.
        self.waves = [
            {
                "name": "Vague 1",
                "enemy_count": 24,   # 4 par portail x 6 portails
                "speed": 4.0,
                "max_hp": 3,
            },
            {
                "name": "Vague 2",
                "enemy_count": 36,   # 6 par portail
                "speed": 4.5,
                "max_hp": 3,
            },
            {
                "name": "Vague 3",
                "enemy_count": 48,   # 8 par portail
                "speed": 5.0,
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

        count_per_portal = wave["enemy_count"] // len(PORTAL_PATHS)
        spawned_count = self.enemy_manager.spawn_wave(
            portal_paths=PORTAL_PATHS,
            count_per_portal=count_per_portal,
            speed=wave["speed"],
            scale=1.0,
            interval=SPAWN_INTERVAL,
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
        if hasattr(self.enemy_manager, "clear"):
            self.enemy_manager.clear()
            return

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

        # Résolution conflit : finish_game() (HEAD) est la bonne logique ici
        # car elle gère le cas niveau final vs niveau intermédiaire via finish_level().
        if is_finished and not self.is_finished:
            self.finish_game()
