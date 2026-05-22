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
                "enemy_count": 24,   # 4 par portail x 6 portails
                "speed": 4.0,
            },
            {
                "name": "Vague 2",
                "enemy_count": 36,   # 6 par portail
                "speed": 4.5,
            },
            {
                "name": "Vague 3",
                "enemy_count": 48,   # 8 par portail
                "speed": 5.0,
            },
        ]

        self.wave_panel = DirectFrame(
            parent=base.aspect2d,
            frameColor=(0.02, 0.02, 0.02, 0.72),
            frameSize=(-0.62, 0.62, -0.10, 0.10),
            pos=(0, 0, 0.84),
        )
        self.wave_panel.setBin("fixed", 85)
        self.wave_panel.setDepthWrite(False)
        self.wave_panel.setDepthTest(False)
        self.wave_panel.hide()

        self.wave_label = DirectLabel(
            parent=self.wave_panel,
            text="",
            scale=0.055,
            pos=(0, 0, -0.024),
            frameColor=(0, 0, 0, 0),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ACenter,
            text_wordwrap=20,
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
            text="Bien joué !\nTu as survécu à toutes les vagues.",
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
        self.current_wave_index = 0
        self.killed_in_current_wave = 0
        self.current_enemy_target = 0
        self.is_finished = False
        self.waiting_next_wave = False
        self.start_current_wave()

    def _is_host(self):
        net_iface = getattr(self.game, 'network', None)
        if net_iface is None or getattr(net_iface, 'net', None) is None:
            return True
        return net_iface.net.is_host

    def start_current_wave(self):
        if not self._is_host():
            return

        if self.current_wave_index >= len(self.waves):
            self.finish_game()
            return

        wave = self.waves[self.current_wave_index]

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
            f"{wave['name']}\nProtege le tuyau contre {self.current_enemy_target} ennemis !",
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
                self.finish_game()
            else:
                self.waiting_next_wave = True
                self.next_wave_timer = 2.0
                self.show_message("Vague terminée !", duration=2.0)

    def enemy_reached_base(self):
        self.enemy_killed()

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.wave_panel.hide()

        if not self._is_host():
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

    def finish_game(self):
        self.is_finished = True
        self.waiting_next_wave = False
        self.clear_enemies()
        self.wave_panel.hide()
        self.final_screen.show()

    def game_over(self):
        self.is_finished = True
        self.waiting_next_wave = False
        self.clear_enemies()
        self.wave_panel.hide()
        self.final_screen.hide()

    def clear_enemies(self):
        for enemy in list(self.enemy_manager.enemies):
            enemy.destroy()

        self.enemy_manager.enemies.clear()

    def sync_from_snapshot(self, wave_index, is_finished, is_game_over=False):
        if is_game_over:
            self.game_over()
            return

        if self.current_wave_index != wave_index and not is_finished:
            self.current_wave_index = wave_index
            if self.current_wave_index < len(self.waves):
                wave = self.waves[self.current_wave_index]
                self.show_message(f"{wave['name']}\nÉlimine {wave['enemy_count']} ennemis !", duration=2.5)

        if is_finished and not self.is_finished:
            self.finish_game()