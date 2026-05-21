from panda3d.core import Vec3, Point3


class Bullet:
    """SRP: Représente le cycle de vie et le déplacement d'un projectile."""
    def __init__(self, node, direction, speed, life):
        self.node = node
        self.direction = direction
        self.speed = speed
        self.life = life

    def update(self, dt):
        """Retourne False si la balle doit être détruite (fin de vie)."""
        self.life -= dt
        if self.life <= 0:
            return False
        old_pos = self.node.getPos(self.node.getParent())
        new_pos = old_pos + self.direction * self.speed * dt
        self.node.setPos(new_pos)
        return True

    def destroy(self):
        self.node.removeNode()


class ShootingSystem:
    """SRP: Gère uniquement la logique de tir et la trajectoire des balles."""
    BULLET_SPEED = 50.0
    BULLET_LIFE = 3.0
    BULLET_SCALE = 10
    HIT_RADIUS = 1.5

    def __init__(self, game, player):
        self.game = game
        self.player_sys = player
        self.player = player.player
        self.bullets = []
        self.was_building_last_frame = False
        self._local_shot_seq = 0
        self._handled_remote_shots = set()
        self.game.accept("mouse1", self.shoot)

    def _get_mouse_world_pos(self):
        mw = self.game.mouseWatcherNode
        if not mw.hasMouse():
            return None
        mpos = mw.getMouse()
        near_point, far_point = Point3(), Point3()
        self.game.camLens.extrude(mpos, near_point, far_point)
        cam, render = self.game.camera, self.game.render
        near_w = render.getRelativePoint(cam, near_point)
        far_w = render.getRelativePoint(cam, far_point)
        dz = far_w.z - near_w.z
        if abs(dz) < 0.0001:
            return None
        t = -near_w.z / dz
        return Vec3(near_w.x + t * (far_w.x - near_w.x), near_w.y + t * (far_w.y - near_w.y), 0)

    def _spawn_bullet(self, origin, direction, speed=None, life=None, shot_id=None):
        speed = speed if speed is not None else self.BULLET_SPEED
        life = life if life is not None else self.BULLET_LIFE
        if shot_id is not None and shot_id in self._handled_remote_shots:
            return None
        if shot_id is not None:
            self._handled_remote_shots.add(shot_id)
        direction = Vec3(direction.x, direction.y, direction.z)
        if direction.length() < 0.001:
            return None
        direction.normalize()
        node = self.game.loader.loadModel("assets/bullet.bam")
        node.setScale(self.BULLET_SCALE)
        node.reparentTo(self.game.render)
        node.setPos(origin)
        node.lookAt(origin + direction)
        node.setH(node.getH() + 90)
        bullet = Bullet(node, direction, speed, life)
        self.bullets.append(bullet)
        return bullet

    def spawn_network_bullet(self, origin, direction, speed=None, life=None, shot_id=None):
        return self._spawn_bullet(origin, direction, speed, life, shot_id=shot_id)

    def _send_shoot_network(self, origin, direction):
        net_iface = getattr(self.game, "network", None)
        if net_iface is None or getattr(net_iface, "net", None) is None:
            self._spawn_bullet(origin, direction)
            return
        self._local_shot_seq += 1
        shot_id = f"{net_iface.net.player_name}:{self._local_shot_seq}"
        payload = {
            "shot_id": shot_id,
            "origin": {"x": origin.x, "y": origin.y, "z": origin.z},
            "direction": {"x": direction.x, "y": direction.y, "z": direction.z},
            "speed": self.BULLET_SPEED,
            "life": self.BULLET_LIFE,
        }
        if net_iface.net.is_host:
            self._spawn_bullet(origin, direction, shot_id=shot_id)
            net_iface.net.broadcast_msg("shoot", payload)
        else:
            net_iface.net.send_msg("shoot_request", payload)

    def shoot(self):
        if self.player_sys.build_manager.mode_actif or self.was_building_last_frame:
            return
        target = self._get_mouse_world_pos()
        if target is None:
            return
        player_pos = self.player.getPos(self.game.render)
        direction = Vec3(target.x - player_pos.x, target.y - player_pos.y, 0)
        if direction.length() < 0.001:
            return
        direction.normalize()
        origin = player_pos + Vec3(0, 0, 1)
        self._send_shoot_network(origin, direction)

    def handle_network_message(self, msg: dict):
        kind = msg.get("kind")
        payload = msg.get("payload", {})
        if kind == "shoot":
            origin = payload.get("origin", {})
            direction = payload.get("direction", {})
            self.spawn_network_bullet(Vec3(origin.get("x", 0), origin.get("y", 0), origin.get("z", 0)), Vec3(direction.get("x", 0), direction.get("y", 0), direction.get("z", 0)), payload.get("speed", self.BULLET_SPEED), payload.get("life", self.BULLET_LIFE), shot_id=payload.get("shot_id"))
        elif kind == "shoot_request":
            net_iface = getattr(self.game, "network", None)
            if net_iface is None or not net_iface.net.is_host:
                return
            origin = payload.get("origin", {})
            direction = payload.get("direction", {})
            shot_id = payload.get("shot_id")
            self.spawn_network_bullet(Vec3(origin.get("x", 0), origin.get("y", 0), origin.get("z", 0)), Vec3(direction.get("x", 0), direction.get("y", 0), direction.get("z", 0)), payload.get("speed", self.BULLET_SPEED), payload.get("life", self.BULLET_LIFE), shot_id=shot_id)
            net_iface.net.broadcast_msg("shoot", payload)

    def update(self):
        dt = globalClock.getDt()  # pyright: ignore
        self.was_building_last_frame = self.player_sys.build_manager.mode_actif
        surviving_bullets = []
        for bullet in self.bullets:
            old_pos = bullet.node.getPos(self.game.render)
            is_alive = bullet.update(dt)
            new_pos = bullet.node.getPos(self.game.render)
            has_hit = False
            if hasattr(self.game, "enemies"):
                has_hit = self.game.enemies.check_projectile_hit(old_pos, new_pos, self.HIT_RADIUS)
            if has_hit:
                bullet.destroy()
            elif is_alive:
                surviving_bullets.append(bullet)
            else:
                bullet.destroy()
        self.bullets = surviving_bullets