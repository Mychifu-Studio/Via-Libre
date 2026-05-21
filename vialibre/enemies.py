import math
import os
import random
from panda3d.core import CardMaker, Filename, TransparencyAttrib, Vec3


class MathUtils:
    @staticmethod
    def ray_rectangle_intersection(start, direction, min_x, max_x, min_y, max_y):
        t_values = []
        if abs(direction.x) > 0.0001:
            t_values.append((max_x - start.x) / direction.x if direction.x > 0 else (min_x - start.x) / direction.x)
        if abs(direction.y) > 0.0001:
            t_values.append((max_y - start.y) / direction.y if direction.y > 0 else (min_y - start.y) / direction.y)

        positive_t = [t for t in t_values if t > 0]
        if not positive_t:
            return Vec3(start)

        end = start + direction * min(positive_t)
        end.setZ(0)
        return end

    @staticmethod
    def distance_segment_to_point(start_pos, end_pos, point):
        segment, vector = end_pos - start_pos, point - start_pos
        segment.setZ(0)
        vector.setZ(0)

        sq_len = segment.lengthSquared()
        if sq_len <= 0.0001:
            return vector.length()

        projection = max(0.0, min(1.0, vector.dot(segment) / sq_len))
        closest_point = start_pos + segment * projection
        closest_point.setZ(0)

        p2 = Vec3(point)
        p2.setZ(0)
        return (p2 - closest_point).length()

    @staticmethod
    def clamp_position_to_rectangle(pos, min_x, max_x, min_y, max_y):
        return Vec3(
            max(min_x, min(max_x, pos.x)),
            max(min_y, min(max_y, pos.y)),
            pos.z,
        )

class DogEnemy:
    MAX_HP = 3
    CONTACT_RADIUS = 1.5
    HEALTH_BAR_WIDTH = 1.1
    
    def __init__(
        self,
        game,
        start_pos,
        end_pos,
        speed=4.0,
        scale=1.0,
        respawn_callback=None,
        player_node=None,
        detection_radius=12.0,
        chase_speed=None,
        area_bounds=None,
    ):
        self.game = game
        self.speed = speed
        self.chase_speed = chase_speed if chase_speed is not None else speed * 1.25
        self.detection_radius = detection_radius
        self.player_node = player_node
        self.area_bounds = area_bounds
        self.respawn_callback = respawn_callback
        self.is_dead = False
        self.hp = self.MAX_HP

        self.is_chasing = False
        
        self.start_pos = Vec3(start_pos)
        self.end_pos = Vec3(end_pos)

        self.node = self._load_model()
        self.node.reparentTo(self.game.render)
        self.node.setScale(scale)
        self.health_bar_fill = None
        self.health_bar_root = None
        self._create_health_bar()

        self._recalculate_movement()

    def _load_model(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = Filename.fromOsSpecific(os.path.join(base_dir, "../assets", "dog.bam")).getFullpath()
        return self.game.loader.loadModel(path)

    def _recalculate_movement(self):
        self.node.setPos(self.start_pos)
        movement = self.end_pos - self.start_pos
        movement.setZ(0)

        if movement.length() <= 0.001:
            self.direction = Vec3(0, 0, 0)
            self.is_dead = True
        else:
            self.direction = movement.normalized()
            self.node.lookAt(self.end_pos)

    def _create_health_bar(self):
        self.health_bar_root = self.node.attachNewNode("enemy-health-bar")
        self.health_bar_root.setZ(2.4)
        self.health_bar_root.setScale(0.9)
        self.health_bar_root.setLightOff()
        self.health_bar_root.setDepthWrite(False)
        self.health_bar_root.setDepthTest(False)
        self.health_bar_root.setTransparency(TransparencyAttrib.MAlpha)
        self.health_bar_root.setBillboardPointEye()

        background_maker = CardMaker("enemy-health-background")
        background_maker.setFrame(
            -self.HEALTH_BAR_WIDTH / 2,
            self.HEALTH_BAR_WIDTH / 2,
            -0.07,
            0.07,
        )
        background = self.health_bar_root.attachNewNode(background_maker.generate())
        background.setColor(0.02, 0.02, 0.02, 0.8)
        background.setTransparency(TransparencyAttrib.MAlpha)

        fill_maker = CardMaker("enemy-health-fill")
        fill_maker.setFrame(0, self.HEALTH_BAR_WIDTH - 0.08, -0.045, 0.045)
        self.health_bar_fill = self.health_bar_root.attachNewNode(fill_maker.generate())
        self.health_bar_fill.setX(-(self.HEALTH_BAR_WIDTH - 0.08) / 2)
        self.health_bar_fill.setY(-0.01)
        self.health_bar_fill.setTransparency(TransparencyAttrib.MAlpha)
        self._update_health_bar()

    def _update_health_bar(self):
        if self.health_bar_fill is None:
            return

        ratio = max(0.0, min(1.0, self.hp / self.MAX_HP))
        if ratio > 0.55:
            color = (0.15, 0.85, 0.28, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)

        self.health_bar_fill.setSx(ratio)
        self.health_bar_fill.setColor(color)

    def take_damage(self, amount=1):
        if self.is_dead:
            return False
        self.hp -= amount
        self._update_health_bar()
        if self.hp <= 0:
            self.destroy()
            return True
        return False

    def _get_player_pos(self):
        if self.player_node is None:
            return None
        return self.player_node.getPos(self.game.render)

    def _should_chase_player(self, current_pos):
        player_pos = self._get_player_pos()
        if player_pos is None:
            return False, None

        flat_current = Vec3(current_pos.x, current_pos.y, 0)
        flat_player = Vec3(player_pos.x, player_pos.y, 0)
        return (flat_player - flat_current).length() <= self.detection_radius, flat_player

    def _update_chase(self, current_pos, player_pos, dt):
        chase_direction = player_pos - Vec3(current_pos.x, current_pos.y, 0)
        chase_direction.setZ(0)

        if chase_direction.length() <= 0.001:
            return

        chase_direction.normalize()
        next_pos = current_pos + chase_direction * self.chase_speed * dt
        next_pos.setZ(current_pos.z)

        if self.area_bounds is not None:
            min_x, max_x, min_y, max_y = self.area_bounds
            next_pos = MathUtils.clamp_position_to_rectangle(next_pos, min_x, max_x, min_y, max_y)

        self.node.setPos(next_pos)
        self.node.lookAt(player_pos)

    def _update_straight_line(self, current_pos, dt):
        next_pos = current_pos + self.direction * self.speed * dt

        if (next_pos - current_pos).length() >= (self.end_pos - current_pos).length():
            self.respawn()
        else:
            self.node.setPos(next_pos)

    def is_touching_point(self, point):
        if self.is_dead:
            return False
        pos = self.node.getPos(self.game.render)
        diff = Vec3(point.x - pos.x, point.y - pos.y, 0)
        return diff.length() <= self.CONTACT_RADIUS

    def update(self, dt):
        if self.is_dead:
            return

        current_pos = self.node.getPos(self.game.render)
        should_chase, player_pos = self._should_chase_player(current_pos)

        if should_chase:
            self.is_chasing = True
            self._update_chase(current_pos, player_pos, dt)
        else:
            self.is_chasing = False
            self._update_straight_line(current_pos, dt)

    def is_touched_by_segment(self, start_pos, end_pos, hit_radius):
        if self.is_dead:
            return False
        dist = MathUtils.distance_segment_to_point(start_pos, end_pos, self.node.getPos(self.game.render))
        return dist <= hit_radius

    def respawn(self):
        if self.is_dead:
            return
        self.hp = self.MAX_HP
        self.is_chasing = False
        if self.respawn_callback:
            self.start_pos, self.end_pos = self.respawn_callback()
        self._recalculate_movement()
        self._update_health_bar()

    def destroy(self):
        self.is_dead = True
        self.node.removeNode()


class EnemyManager:
    def __init__(self, game):
        self.game = game
        self.enemies = []

    def spawn_dog(self, start_pos, end_pos, **kwargs):
        dog = DogEnemy(self.game, start_pos, end_pos, **kwargs)
        if not dog.is_dead:
            self.enemies.append(dog)
        return dog

    def spawn_random_dogs_in_area(
        self,
        count=10,
        area_min_x=-50,
        area_max_x=50,
        area_min_y=-50,
        area_max_y=50,
        margin=2.0,
        detection_radius=12.0,
        chase_speed=6.0,
        **kwargs
    ):
        safe_min_x, safe_max_x = area_min_x + margin, area_max_x - margin
        safe_min_y, safe_max_y = area_min_y + margin, area_max_y - margin
        area_bounds = (safe_min_x, safe_max_x, safe_min_y, safe_max_y)

        player_node = None
        if hasattr(self.game, "player") and hasattr(self.game.player, "player"):
            player_node = self.game.player.player

        for _ in range(count):
            callback = lambda: self._generate_random_path(area_min_x, area_max_x, area_min_y, area_max_y, margin)
            start_pos, end_pos = callback()
            self.spawn_dog(
                start_pos,
                end_pos,
                respawn_callback=callback,
                player_node=player_node,
                detection_radius=detection_radius,
                chase_speed=chase_speed,
                area_bounds=area_bounds,
                **kwargs
            )

    def _generate_random_path(self, min_x, max_x, min_y, max_y, margin):
        safe_min_x, safe_max_x = min_x + margin, max_x - margin
        safe_min_y, safe_max_y = min_y + margin, max_y - margin

        start = Vec3(random.uniform(safe_min_x, safe_max_x), random.uniform(safe_min_y, safe_max_y), 0)
        angle = random.uniform(0, math.tau)
        direction = Vec3(math.cos(angle), math.sin(angle), 0)

        end = MathUtils.ray_rectangle_intersection(start, direction, safe_min_x, safe_max_x, safe_min_y, safe_max_y)
        return start, end

    def check_projectile_hit(self, start_pos, end_pos, hit_radius):
        for enemy in self.enemies[:]:
            if enemy.is_touched_by_segment(start_pos, end_pos, hit_radius):
                killed = enemy.take_damage(1)
                if killed:
                    self.enemies.remove(enemy)
                    self.game.messenger.send("enemy-hit")
                return True
        return False

    def check_player_contact(self, player_pos):
        for enemy in self.enemies:
            if enemy.is_touching_point(player_pos):
                return True
        return False

    def update(self, dt):
        for enemy in self.enemies:
            enemy.update(dt)
        self.enemies = [e for e in self.enemies if not e.is_dead]

        if hasattr(self.game, 'player'):
            player_np = getattr(self.game.player, 'player', None)
            if player_np is not None:
                player_pos = player_np.getPos(self.game.render)
                if self.check_player_contact(player_pos):
                    self.game.messenger.send("player-take-damage")
                    
    def clear(self):
        for enemy in self.enemies:
            enemy.destroy()
        self.enemies.clear()
