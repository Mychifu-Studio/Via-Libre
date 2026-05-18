import os
import math

from panda3d.core import Vec3, Point3, Filename
from direct.gui.OnscreenImage import OnscreenImage


class ShootingSystem:
    """
    Système de tir vue du dessus.

    Usage dans main.py :
        self.shooting = ShootingSystem(game=self, player=self.player)

    Dans la boucle update :
        self.shooting.update()
    """

    BULLET_SPEED = 50.0   # unités/seconde
    BULLET_LIFE  = 3.0    # secondes avant destruction
    BULLET_SCALE = 0.2

    def __init__(self, game, player):
        self.game   = game
        self.player = player
        self.bullets = []

        self._setupCrosshair()
        self.game.accept("mouse1", self.shoot)

    # ──────────────────────────────────────────────────────────────────────
    # Crosshair
    # ──────────────────────────────────────────────────────────────────────

    def _setupCrosshair(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        crosshair_path = Filename.fromOsSpecific(
            os.path.join(base_dir, "../assets", "crosshair.png")
        ).getFullpath()

        self.crosshair = OnscreenImage(
            image=crosshair_path,
            pos=(0, 0, 0),
            scale=0.05
        )
        self.crosshair.setTransparency(True)

    # ──────────────────────────────────────────────────────────────────────
    # Projection souris → plan z=0 dans le monde 3D
    # ──────────────────────────────────────────────────────────────────────

    def _getMouseWorldPos(self):
        """
        Projette la position de la souris sur le plan z=0.
        Retourne un Vec3 ou None si la souris est hors fenêtre.
        """
        mw = self.game.mouseWatcherNode
        if not mw.hasMouse():
            return None

        mpos = mw.getMouse()

        near_point = Point3()
        far_point  = Point3()
        self.game.camLens.extrude(mpos, near_point, far_point)

        cam      = self.game.camera
        render   = self.game.render
        near_w   = render.getRelativePoint(cam, near_point)
        far_w    = render.getRelativePoint(cam, far_point)

        dz = far_w.z - near_w.z
        if abs(dz) < 0.0001:
            return None

        t = -near_w.z / dz
        return Vec3(
            near_w.x + t * (far_w.x - near_w.x),
            near_w.y + t * (far_w.y - near_w.y),
            0
        )

    # ──────────────────────────────────────────────────────────────────────
    # Tir
    # ──────────────────────────────────────────────────────────────────────

    def shoot(self):
        target = self._getMouseWorldPos()
        if target is None:
            return

        bullet = self.game.loader.loadModel("models/misc/sphere")
        bullet.setScale(self.BULLET_SCALE)
        bullet.reparentTo(self.game.render)

        # Départ depuis la position actuelle du joueur (légèrement en hauteur)
        player_pos = self.player.getPos(self.game.render)
        start_pos  = player_pos + Vec3(0, 0, 1)
        bullet.setPos(start_pos)

        # Direction horizontale vers le point visé
        direction = Vec3(
            target.x - player_pos.x,
            target.y - player_pos.y,
            0
        )
        if direction.length() < 0.001:
            bullet.removeNode()
            return
        direction.normalize()

        self.bullets.append({
            "node":  bullet,
            "dir":   direction,
            "speed": self.BULLET_SPEED,
            "life":  self.BULLET_LIFE,
        })
        
    def update(self):
        dt = globalClock.getDt()  # pyright: ignore[reportUndefinedVariable]

        # Crosshair suit la souris
        mw = self.game.mouseWatcherNode
        if mw.hasMouse():
            mpos = mw.getMouse()
            self.crosshair.setPos(mpos.x, 0, mpos.y)

        # Déplacement, collision avec les ennemis, et durée de vie des balles
        for bullet in self.bullets[:]:
            old_pos = bullet["node"].getPos(self.game.render)
            new_pos = old_pos + bullet["dir"] * bullet["speed"] * dt
            bullet["node"].setPos(new_pos)

            if hasattr(self.game, "enemies"):
                has_hit_enemy = self.game.enemies.check_projectile_hit(
                    old_pos,
                    new_pos,
                    hit_radius=1.5,
                )

                if has_hit_enemy:
                    bullet["node"].removeNode()
                    self.bullets.remove(bullet)
                    self.game.messenger.send("enemy-hit")
                    continue

            bullet["life"] -= dt
            if bullet["life"] <= 0:
                bullet["node"].removeNode()
                self.bullets.remove(bullet)
