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
        self.player = player
        self.bullets = []
        
        # On écoute le clic gauche pour tirer
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
        return Vec3(
            near_w.x + t * (far_w.x - near_w.x), 
            near_w.y + t * (far_w.y - near_w.y), 
            0
        )

    def shoot(self):
        target = self._get_mouse_world_pos()
        if target is None: 
            return

        player_pos = self.player.getPos(self.game.render)
        direction = Vec3(target.x - player_pos.x, target.y - player_pos.y, 0)
        
        if direction.length() < 0.001: 
            return
            
        direction.normalize()

        # Création de la balle
        node = self.game.loader.loadModel("assets/bullet.bam")
        node.setScale(self.BULLET_SCALE)
        node.reparentTo(self.game.render)
        node.setPos(player_pos + Vec3(0, 0, 1)) # Départ légèrement en hauteur depuis le joueur

        self.bullets.append(Bullet(node, direction, self.BULLET_SPEED, self.BULLET_LIFE))

    def update(self):
        dt = globalClock.getDt() # pyright: ignore

        surviving_bullets = []
        for bullet in self.bullets:
            old_pos = bullet.node.getPos(self.game.render)
            is_alive = bullet.update(dt)
            new_pos = bullet.node.getPos(self.game.render)

            has_hit = False
            # Vérification des collisions avec les ennemis
            if hasattr(self.game, "enemies"):
                has_hit = self.game.enemies.check_projectile_hit(old_pos, new_pos, self.HIT_RADIUS)

            if has_hit:
                # Émission de l'événement global (capté par main.py)
                self.game.messenger.send("enemy-hit")
                bullet.destroy()
            elif is_alive:
                surviving_bullets.append(bullet)
            else:
                bullet.destroy()

        self.bullets = surviving_bullets