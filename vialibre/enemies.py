import math
import os
import random

from direct.actor.Actor import Actor
from panda3d.core import CardMaker, Filename, NodePath, Point2, Point3, TransparencyAttrib, Vec3

from .utils import powLerp, shortest_angle_lerp


BASE_ENEMY_HP = 10
BASE_ENEMY_DAMAGE = 1
BASE_ENEMY_RESOURCE_REWARD = 2
ENEMY_ANIMATION_NAME = "walk"

ENEMY_TYPE_CLASSIC = "classique"
ENEMY_TYPE_FAST = "rapide"
ENEMY_TYPE_HEAVY = "lourd"
ENEMY_TYPE_MINIBOSS = "miniboss"

ENEMY_TYPE_CONFIGS = {
    ENEMY_TYPE_CLASSIC: {
        "asset": "ennemi_classique.bam",
        "hp_multiplier": 1.0,  # à changer pour balance
        "speed_multiplier": 1.0,  # à changer pour balance
        "damage_multiplier": 1.0,  # à changer pour balance
        "objective_damage": 2,  # à changer pour balance
        "resource_multiplier": 1.0,  # à changer pour balance
        "visual_scale_multiplier": 1.0,
        "color_scale": (1.0, 1.0, 1.0, 1.0),
    },
    ENEMY_TYPE_FAST: {
        "asset": "ennemi_rapide.bam",
        "hp_multiplier": 0.5,  # à changer pour balance
        "speed_multiplier": 1.5,  # à changer pour balance
        "damage_multiplier": 1.0,  # à changer pour balance
        "objective_damage": 1,  # à changer pour balance
        "resource_multiplier": 1.0,  # à changer pour balance
        "visual_scale_multiplier": 1.0,
        "color_scale": (1.0, 1.0, 1.0, 1.0),
    },
    ENEMY_TYPE_HEAVY: {
        "asset": "ennemi_lourd.bam",
        "hp_multiplier": 2.0,  # à changer pour balance
        "speed_multiplier": 0.6,  # à changer pour balance
        "damage_multiplier": 2.0,  # à changer pour balance
        "objective_damage": 3,  # à changer pour balance
        "resource_multiplier": 2.0,  # à changer pour balance
        "visual_scale_multiplier": 1.0,
        "color_scale": (1.0, 1.0, 1.0, 1.0),
    },
    ENEMY_TYPE_MINIBOSS: {
        "asset": "miniboss.bam",
        "hp_multiplier": 10.0,  # a changer pour balance
        "speed_multiplier": 0.4,  # a changer pour balance
        "damage_multiplier": 2.0,  # a changer pour balance
        "objective_damage": 25,  # a changer pour balance
        "resource_multiplier": 10.0,  # a changer pour balance
        "visual_scale_multiplier": 1.4,
        "color_scale": (1.0, 1.0, 1.0, 1.0),
    },
}

ENEMY_TYPE_ALIASES = {
    "1": ENEMY_TYPE_CLASSIC,
    "classic": ENEMY_TYPE_CLASSIC,
    "normal": ENEMY_TYPE_CLASSIC,
    "standard": ENEMY_TYPE_CLASSIC,
    "classique": ENEMY_TYPE_CLASSIC,
    "2": ENEMY_TYPE_FAST,
    "fast": ENEMY_TYPE_FAST,
    "speed": ENEMY_TYPE_FAST,
    "rapide": ENEMY_TYPE_FAST,
    "3": ENEMY_TYPE_HEAVY,
    "heavy": ENEMY_TYPE_HEAVY,
    "tank": ENEMY_TYPE_HEAVY,
    "lourd": ENEMY_TYPE_HEAVY,
    "4": ENEMY_TYPE_MINIBOSS,
    "boss": ENEMY_TYPE_MINIBOSS,
    "mini_boss": ENEMY_TYPE_MINIBOSS,
    "miniboss": ENEMY_TYPE_MINIBOSS,
}

RANDOM_ENEMY_TYPE_VALUES = {None, "random", "aleatoire"}
ENEMY_TYPE_CHOICES = (ENEMY_TYPE_CLASSIC, ENEMY_TYPE_FAST, ENEMY_TYPE_HEAVY)
ENEMY_TYPE_SPAWN_ORDER = (ENEMY_TYPE_CLASSIC, ENEMY_TYPE_FAST, ENEMY_TYPE_HEAVY, ENEMY_TYPE_MINIBOSS)
ENEMY_TYPE_BOSS_ORDER = (ENEMY_TYPE_MINIBOSS,)

HEALTH_BAR_VISIBILITY_INTERVAL = 0.15
HEALTH_BAR_MAX_DISTANCE_SQ = 55.0 * 55.0
SPATIAL_CELL_SIZE = 6.0
VALID_POSITION_SCAN_STEP = 2.0


def normalize_enemy_type(enemy_type):
    if enemy_type is None:
        return ENEMY_TYPE_CLASSIC
    key = str(enemy_type).strip().lower()
    return ENEMY_TYPE_ALIASES.get(key, ENEMY_TYPE_CLASSIC)


def get_enemy_type_config(enemy_type):
    return ENEMY_TYPE_CONFIGS[normalize_enemy_type(enemy_type)]


def get_enemy_asset_path(asset_name):
    ...

def load_enemy_actor(game, asset_name):
    path = "assets/"+asset_name
    actor = Actor(path)
    try:
        if ENEMY_ANIMATION_NAME not in actor.getAnimNames():
            actor.loadAnims({ENEMY_ANIMATION_NAME: path})
        actor.loop(ENEMY_ANIMATION_NAME)
    except Exception:
        pass
    return actor


class EnemyActorPool:
    """Reuses enemy Actor node paths to avoid load/remove spikes during waves."""

    def __init__(self, game):
        self.game = game
        self._available = {}
        self._templates = {}

    def _get_template(self, asset_name):
        template = self._templates.get(asset_name)
        if template is not None and not template.isEmpty():
            return template

        template = load_enemy_actor(self.game, asset_name)
        template.show()
        template.loop(ENEMY_ANIMATION_NAME)
        template.detachNode()
        self._templates[asset_name] = template
        return template

    def _create_instance(self, asset_name):
        root = NodePath(f"enemy-{asset_name}")
        template = self._get_template(asset_name)
        template.instanceTo(root)
        return root

    def preload(self, asset_name, count):
        bucket = self._available.setdefault(asset_name, [])
        missing = max(0, int(count) - len(bucket))
        for _ in range(missing):
            actor = self._create_instance(asset_name)
            actor.hide()
            actor.detachNode()
            bucket.append(actor)

    def acquire(self, asset_name):
        bucket = self._available.setdefault(asset_name, [])
        while bucket:
            actor = bucket.pop()
            if actor.isEmpty():
                continue
            actor.clearTransform()
            actor.show()
            try:
                actor.loop(ENEMY_ANIMATION_NAME)
            except Exception:
                pass
            return actor
        return self._create_instance(asset_name)

    def release(self, asset_name, actor):
        if actor is None or actor.isEmpty():
            return
        actor.hide()
        actor.detachNode()
        actor.clearTransform()
        actor.clearColorScale()
        self._available.setdefault(asset_name, []).append(actor)

    def clear(self):
        for bucket in self._available.values():
            for actor in bucket:
                if actor.isEmpty():
                    continue
                if hasattr(actor, "cleanup"):
                    actor.cleanup()
                actor.removeNode()
        self._available.clear()
        for template in self._templates.values():
            if not template.isEmpty():
                template.removeNode()
        self._templates.clear()


def get_enemy_actor_pool(game):
    pool = getattr(game, "_enemy_actor_pool", None)
    if pool is None:
        pool = EnemyActorPool(game)
        setattr(game, "_enemy_actor_pool", pool)
    return pool


def acquire_enemy_actor(game, asset_name):
    return get_enemy_actor_pool(game).acquire(asset_name)


def release_enemy_actor(game, asset_name, actor):
    get_enemy_actor_pool(game).release(asset_name, actor)


def _ensure_health_bar(node, width):
    width = float(width)
    root = None
    fill = None
    existing_width = None

    if node.hasPythonTag("enemy_health_bar_root"):
        root = node.getPythonTag("enemy_health_bar_root")
    if node.hasPythonTag("enemy_health_bar_fill"):
        fill = node.getPythonTag("enemy_health_bar_fill")
    if node.hasPythonTag("enemy_health_bar_width"):
        existing_width = node.getPythonTag("enemy_health_bar_width")

    if (
        root is not None
        and fill is not None
        and not root.isEmpty()
        and not fill.isEmpty()
        and existing_width == width
    ):
        root.show()
        return root, fill

    if root is not None and not root.isEmpty():
        root.removeNode()

    root = node.attachNewNode("enemy-health-bar")
    root.setZ(2.4)
    root.setScale(0.9)
    root.setLightOff()
    root.setDepthWrite(False)
    root.setDepthTest(False)
    root.setTransparency(TransparencyAttrib.MAlpha)
    root.setBillboardPointEye()

    background_maker = CardMaker("enemy-health-background")
    background_maker.setFrame(
        -width / 2,
        width / 2,
        -0.07,
        0.07,
    )
    background = root.attachNewNode(background_maker.generate())
    background.setColor(0.02, 0.02, 0.02, 0.8)
    background.setTransparency(TransparencyAttrib.MAlpha)

    fill_maker = CardMaker("enemy-health-fill")
    fill_maker.setFrame(0, width - 0.08, -0.045, 0.045)
    fill = root.attachNewNode(fill_maker.generate())
    fill.setX(-(width - 0.08) / 2)
    fill.setY(-0.01)
    fill.setTransparency(TransparencyAttrib.MAlpha)

    node.setPythonTag("enemy_health_bar_root", root)
    node.setPythonTag("enemy_health_bar_fill", fill)
    node.setPythonTag("enemy_health_bar_width", width)
    return root, fill


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
    def distance_segment_to_point_squared(start_pos, end_pos, point):
        sx, sy = start_pos.x, start_pos.y
        ex, ey = end_pos.x, end_pos.y
        px, py = point.x, point.y
        dx = ex - sx
        dy = ey - sy
        sq_len = dx * dx + dy * dy
        if sq_len <= 0.0001:
            ox = px - sx
            oy = py - sy
            return ox * ox + oy * oy

        projection = ((px - sx) * dx + (py - sy) * dy) / sq_len
        projection = max(0.0, min(1.0, projection))
        closest_x = sx + dx * projection
        closest_y = sy + dy * projection
        ox = px - closest_x
        oy = py - closest_y
        return ox * ox + oy * oy

    @staticmethod
    def distance_xy_squared(left, right):
        dx = left.x - right.x
        dy = left.y - right.y
        return dx * dx + dy * dy

    @staticmethod
    def clamp_position_to_rectangle(pos, min_x, max_x, min_y, max_y):
        return Vec3(
            max(min_x, min(max_x, pos.x)),
            max(min_y, min(max_y, pos.y)),
            pos.z,
        )


class DogEnemy:
    MAX_HP = BASE_ENEMY_HP
    BASE_DAMAGE = BASE_ENEMY_DAMAGE
    CONTACT_RADIUS = 1.5
    HEALTH_BAR_WIDTH = 1.1

    def __init__(
        self,
        game,
        start_pos,
        end_pos,
        speed=2.0,
        scale=100,
        respawn_callback=None,
        player_node=None,
        detection_radius=12.0,
        chase_speed=None,
        area_bounds=None,
        objective_callback=None,
        objective_reach_radius=1.0,
        enemy_id=None,
        max_hp=None,
        enemy_type=ENEMY_TYPE_CLASSIC,
    ):
        self.game = game
        self.id = enemy_id or f"enemy_{id(self)}"
        self.enemy_type = normalize_enemy_type(enemy_type)
        self.enemy_config = get_enemy_type_config(self.enemy_type)
        self.asset_name = self.enemy_config["asset"]
        self.map_collision = getattr(self.game, "map_collision", None)

        speed_multiplier = self.enemy_config["speed_multiplier"]
        self.base_speed = speed
        self.speed = speed * speed_multiplier
        base_chase_speed = chase_speed if chase_speed is not None else speed * 1.25
        self.chase_speed = base_chase_speed * speed_multiplier
        self.damage = max(1, int(round(self.BASE_DAMAGE * self.enemy_config["damage_multiplier"])))
        self.objective_damage = max(1, int(self.enemy_config["objective_damage"]))
        self.resource_reward = max(0, int(round(BASE_ENEMY_RESOURCE_REWARD * self.enemy_config["resource_multiplier"])))

        self.detection_radius = detection_radius
        self.player_node = player_node
        self.area_bounds = area_bounds
        self.respawn_callback = respawn_callback
        self.objective_callback = objective_callback
        self.objective_reach_radius = objective_reach_radius
        self.is_dead = False

        base_max_hp = max_hp if max_hp is not None else self.MAX_HP
        self.max_hp = max(1, int(round(base_max_hp * self.enemy_config["hp_multiplier"])))
        self.hp = self.max_hp

        self.is_chasing = False
        self._detection_radius_sq = self.detection_radius * self.detection_radius
        self._health_bar_visibility_timer = random.uniform(0.0, HEALTH_BAR_VISIBILITY_INTERVAL)
        self._flat_player_pos = Vec3()
        self._scratch_direction = Vec3()
        self._scratch_next_pos = Vec3()

        self.start_pos = Vec3(start_pos)
        self.end_pos = Vec3(end_pos)

        self.node = self._load_model()
        self.node.reparentTo(self.game.render)
        self.node.setScale(scale * self.enemy_config.get("visual_scale_multiplier", 1.0))
        self.node.setColorScale(*self.enemy_config.get("color_scale", (1.0, 1.0, 1.0, 1.0)))
        self.health_bar_fill = None
        self.health_bar_root = None
        self._create_health_bar()

        self._recalculate_movement()

    def _load_model(self):
        return acquire_enemy_actor(self.game, self.asset_name)

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
        self.health_bar_root, self.health_bar_fill = _ensure_health_bar(self.node, self.HEALTH_BAR_WIDTH)
        self._update_health_bar()

    def _update_health_bar(self):
        if self.health_bar_fill is None:
            return

        ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        if ratio > 0.55:
            color = (0.15, 0.85, 0.28, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)

        self.health_bar_fill.setSx(ratio)
        self.health_bar_fill.setColor(color)
        self._refresh_health_bar_visibility()

    def _is_health_bar_on_screen(self):
        camera = getattr(self.game, "camera", None)
        lens = getattr(self.game, "camLens", None)
        if camera is None or lens is None:
            return True

        pos = self.node.getPos(self.game.render)
        cam_pos = camera.getPos(self.game.render)
        dx = pos.x - cam_pos.x
        dy = pos.y - cam_pos.y
        if dx * dx + dy * dy > HEALTH_BAR_MAX_DISTANCE_SQ:
            return False

        screen_pos = Point2()
        point = camera.getRelativePoint(self.game.render, Point3(pos.x, pos.y, pos.z + 2.4))
        if not lens.project(point, screen_pos):
            return False
        return -1.15 <= screen_pos.x <= 1.15 and -1.15 <= screen_pos.y <= 1.15

    def _refresh_health_bar_visibility(self):
        if self.health_bar_root is None or self.health_bar_root.isEmpty():
            return
        if self.is_dead or self.hp >= self.max_hp or not self._is_health_bar_on_screen():
            self.health_bar_root.hide()
        else:
            self.health_bar_root.show()

    def _update_health_bar_visibility(self, dt):
        self._health_bar_visibility_timer -= dt
        if self._health_bar_visibility_timer > 0:
            return
        self._health_bar_visibility_timer = HEALTH_BAR_VISIBILITY_INTERVAL
        self._refresh_health_bar_visibility()

    def _move_with_collision(self, current_pos, desired_pos):
        if self.map_collision is None or not hasattr(self.map_collision, "move"):
            return desired_pos
        return self.map_collision.move(current_pos, desired_pos)

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

        dx = player_pos.x - current_pos.x
        dy = player_pos.y - current_pos.y
        self._flat_player_pos.set(player_pos.x, player_pos.y, 0)
        return dx * dx + dy * dy <= self._detection_radius_sq, self._flat_player_pos

    def _update_chase(self, current_pos, player_pos, dt):
        chase_direction = self._scratch_direction
        chase_direction.set(player_pos.x - current_pos.x, player_pos.y - current_pos.y, 0)

        distance_sq = chase_direction.lengthSquared()
        if distance_sq <= 0.000001:
            return

        step = self.chase_speed * dt / math.sqrt(distance_sq)
        next_pos = self._scratch_next_pos
        next_pos.set(
            current_pos.x + chase_direction.x * step,
            current_pos.y + chase_direction.y * step,
            current_pos.z,
        )

        if self.area_bounds is not None:
            min_x, max_x, min_y, max_y = self.area_bounds
            next_pos = MathUtils.clamp_position_to_rectangle(next_pos, min_x, max_x, min_y, max_y)

        resolved_pos = self._move_with_collision(current_pos, next_pos)
        self.node.setPos(resolved_pos)

        if (resolved_pos - current_pos).lengthSquared() > 0.0001:
            self.node.lookAt(player_pos)

    def _has_reached_objective(self, pos):
        if self.objective_callback is not None:
            pipe_base = getattr(self.game, "pipe_base", None)
            if pipe_base is not None:
                return pipe_base.is_touching(pos)

        return MathUtils.distance_xy_squared(self.end_pos, pos) <= self.objective_reach_radius * self.objective_reach_radius

    def _reach_objective(self):
        if self.objective_callback is not None:
            self.objective_callback(self)
            return
        self.respawn()

    def _update_straight_line(self, current_pos, dt):
        if self._has_reached_objective(current_pos):
            self._reach_objective()
            return

        step = self.speed * dt
        next_pos = self._scratch_next_pos
        next_pos.set(
            current_pos.x + self.direction.x * step,
            current_pos.y + self.direction.y * step,
            current_pos.z,
        )

        if MathUtils.distance_xy_squared(next_pos, current_pos) >= MathUtils.distance_xy_squared(self.end_pos, current_pos):
            self._reach_objective()
        else:
            resolved_pos = self._move_with_collision(current_pos, next_pos)
            if (resolved_pos - current_pos).lengthSquared() <= 0.0001:
                if self._has_reached_objective(resolved_pos):
                    self._reach_objective()
                else:
                    self.respawn()
                return

            self.node.setPos(resolved_pos)
            self.node.lookAt(self.end_pos)

    def is_touching_point(self, point):
        if self.is_dead:
            return False
        pos = self.node.getPos(self.game.render)
        dx = point.x - pos.x
        dy = point.y - pos.y
        return dx * dx + dy * dy <= self.CONTACT_RADIUS * self.CONTACT_RADIUS

    def update(self, dt):
        if self.is_dead:
            return

        current_pos = self.node.getPos(self.game.render)
        if self.objective_callback is not None and self._has_reached_objective(current_pos):
            self._reach_objective()
            return

        should_chase, player_pos = self._should_chase_player(current_pos)

        if should_chase:
            self.is_chasing = True
            self._update_chase(current_pos, player_pos, dt)
            if not self.is_dead and self._has_reached_objective(self.node.getPos(self.game.render)):
                self._reach_objective()
        else:
            self.is_chasing = False
            self._update_straight_line(current_pos, dt)

        if not self.is_dead:
            self._update_health_bar_visibility(dt)

    def is_touched_by_segment(self, start_pos, end_pos, hit_radius):
        if self.is_dead:
            return False
        dist_sq = MathUtils.distance_segment_to_point_squared(start_pos, end_pos, self.node.getPos(self.game.render))
        return dist_sq <= hit_radius * hit_radius

    def sync_state(self, x, y, z, h, hp, max_hp=None):
        if max_hp is not None:
            self.max_hp = max(1, int(max_hp))
        self.hp = hp
        self.target_pos = Point3(x, y, z)
        self.target_h = h
        if not hasattr(self, 'target_pos_init'):
            self.node.setPos(self.target_pos)
            self.node.setH(self.target_h)
            self.target_pos_init = True
        elif (self.target_pos - self.node.getPos(self.game.render)).length() > 5.0:
            self.node.setPos(self.target_pos)

        self._update_health_bar()
        if self.hp <= 0:
            self.destroy()

    def interpolate(self, dt):
        if not hasattr(self, 'target_pos'):
            return
        curr_pos = self.node.getPos(self.game.render)
        new_x = powLerp(curr_pos.x, self.target_pos.x, dt, 0.1)
        new_y = powLerp(curr_pos.y, self.target_pos.y, dt, 0.1)
        new_z = powLerp(curr_pos.z, self.target_pos.z, dt, 0.1)
        self.node.setPos(new_x, new_y, new_z)

        curr_h = self.node.getH(self.game.render)
        new_h = shortest_angle_lerp(curr_h, self.target_h, dt, 0.1)
        self.node.setH(new_h)
        self._update_health_bar_visibility(dt)

    def respawn(self):
        if self.is_dead:
            return
        self.hp = self.max_hp
        self.is_chasing = False
        if self.respawn_callback:
            self.start_pos, self.end_pos = self.respawn_callback()
        self._recalculate_movement()
        self._update_health_bar()

    def destroy(self):
        if self.is_dead and (self.node is None or self.node.isEmpty()):
            return
        self.is_dead = True
        if self.health_bar_root is not None and not self.health_bar_root.isEmpty():
            self.health_bar_root.hide()
        release_enemy_actor(self.game, self.asset_name, self.node)
        self.node = NodePath()


class WaypointEnemy:
    """Ennemi qui suit une liste de waypoints a vitesse fixe puis disparait."""
    # Résolution conflit : on garde MAX_HP=25 (HEAD) comme demandé,
    # tout en conservant le système de types et dégâts (main).
    MAX_HP = 25
    BASE_DAMAGE = BASE_ENEMY_DAMAGE
    CONTACT_RADIUS = 1.5
    WAYPOINT_REACH_THRESHOLD = 0.3
    HEALTH_BAR_WIDTH = 1.5

    def __init__(self, game, waypoints, speed=2.0, scale=19, on_finish=None, enemy_type=ENEMY_TYPE_CLASSIC, enemy_id=None, max_hp=None):
        self.game = game
        self.id = enemy_id or f"waypoint_enemy_{id(self)}"
        self.enemy_type = normalize_enemy_type(enemy_type)
        self.enemy_config = get_enemy_type_config(self.enemy_type)
        self.asset_name = self.enemy_config["asset"]

        speed_multiplier = self.enemy_config["speed_multiplier"]
        self.waypoints = [Vec3(wp) for wp in waypoints]
        self.speed = speed * speed_multiplier
        self.on_finish = on_finish
        self.is_dead = False
        base_max_hp = max_hp if max_hp is not None else self.MAX_HP
        self.max_hp = max(1, int(round(base_max_hp * self.enemy_config["hp_multiplier"])))
        self.hp = self.max_hp
        self.damage = max(1, int(round(self.BASE_DAMAGE * self.enemy_config["damage_multiplier"])))
        self.objective_damage = max(1, int(self.enemy_config["objective_damage"]))
        self.resource_reward = max(0, int(round(BASE_ENEMY_RESOURCE_REWARD * self.enemy_config["resource_multiplier"])))
        self._index = 0
        self.health_bar_fill = None
        self.health_bar_root = None
        self._health_bar_visibility_timer = random.uniform(0.0, HEALTH_BAR_VISIBILITY_INTERVAL)

        self.node = self._load_model()
        self.node.reparentTo(self.game.render)
        self.node.setScale(scale * self.enemy_config.get("visual_scale_multiplier", 1.0))
        self.node.setColorScale(*self.enemy_config.get("color_scale", (1.0, 1.0, 1.0, 1.0)))
        self.node.setPos(self.waypoints[0])

        if len(self.waypoints) > 1:
            self.node.lookAt(self.waypoints[1])

        self._create_health_bar()

    def _load_model(self):
        return acquire_enemy_actor(self.game, self.asset_name)

    def _create_health_bar(self):
        self.health_bar_root, self.health_bar_fill = _ensure_health_bar(self.node, self.HEALTH_BAR_WIDTH)
        self._update_health_bar()

    def _update_health_bar(self):
        if self.health_bar_fill is None:
            return
        ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        if ratio > 0.55:
            color = (0.15, 0.85, 0.28, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)
        self.health_bar_fill.setSx(max(ratio, 0.001))
        self.health_bar_fill.setColor(color)
        self._refresh_health_bar_visibility()

    def _is_health_bar_on_screen(self):
        camera = getattr(self.game, "camera", None)
        lens = getattr(self.game, "camLens", None)
        if camera is None or lens is None:
            return True

        pos = self.node.getPos(self.game.render)
        cam_pos = camera.getPos(self.game.render)
        dx = pos.x - cam_pos.x
        dy = pos.y - cam_pos.y
        if dx * dx + dy * dy > HEALTH_BAR_MAX_DISTANCE_SQ:
            return False

        screen_pos = Point2()
        point = camera.getRelativePoint(self.game.render, Point3(pos.x, pos.y, pos.z + 2.4))
        if not lens.project(point, screen_pos):
            return False
        return -1.15 <= screen_pos.x <= 1.15 and -1.15 <= screen_pos.y <= 1.15

    def _refresh_health_bar_visibility(self):
        if self.health_bar_root is None or self.health_bar_root.isEmpty():
            return
        if self.is_dead or self.hp >= self.max_hp or not self._is_health_bar_on_screen():
            self.health_bar_root.hide()
        else:
            self.health_bar_root.show()

    def _update_health_bar_visibility(self, dt):
        self._health_bar_visibility_timer -= dt
        if self._health_bar_visibility_timer > 0:
            return
        self._health_bar_visibility_timer = HEALTH_BAR_VISIBILITY_INTERVAL
        self._refresh_health_bar_visibility()

    def take_damage(self, amount=1):
        if self.is_dead:
            return False
        self.hp -= amount
        self._update_health_bar()
        if self.hp <= 0:
            self.destroy()
            return True
        return False

    def has_reached_end(self):
        return self._index >= len(self.waypoints) - 1

    def enters_pipe_between(self, start_pos, end_pos):
        pipe_base = getattr(self.game, "pipe_base", None)
        if pipe_base is None:
            return False
        if hasattr(pipe_base, "segment_enters"):
            return pipe_base.segment_enters(start_pos, end_pos)
        return pipe_base.is_touching(end_pos)

    def is_touched_by_segment(self, start_pos, end_pos, hit_radius):
        if self.is_dead:
            return False
        dist_sq = MathUtils.distance_segment_to_point_squared(start_pos, end_pos, self.node.getPos(self.game.render))
        return dist_sq <= hit_radius * hit_radius

    def is_touching_point(self, point):
        if self.is_dead:
            return False
        pos = self.node.getPos(self.game.render)
        dx = point.x - pos.x
        dy = point.y - pos.y
        return dx * dx + dy * dy <= self.CONTACT_RADIUS * self.CONTACT_RADIUS

    def update(self, dt):
        if self.is_dead:
            return

        next_index = self._index + 1
        if next_index >= len(self.waypoints):
            return

        target = self.waypoints[next_index]
        current_pos = self.node.getPos(self.game.render)
        if self.enters_pipe_between(current_pos, current_pos):
            self._index = len(self.waypoints) - 1
            return

        dx = target.x - current_pos.x
        dy = target.y - current_pos.y
        dist_sq = dx * dx + dy * dy
        dist = math.sqrt(dist_sq)

        if dist <= self.WAYPOINT_REACH_THRESHOLD:
            self._index = next_index
            self.node.setPos(target)
            if self._index + 1 < len(self.waypoints):
                self.node.lookAt(self.waypoints[self._index + 1])
            self._update_health_bar_visibility(dt)
            return

        step = min(self.speed * dt, dist)
        inv_dist = 1.0 / dist
        next_pos = Vec3(current_pos.x + dx * inv_dist * step, current_pos.y + dy * inv_dist * step, current_pos.z)
        if self.enters_pipe_between(current_pos, next_pos):
            self._index = len(self.waypoints) - 1
            self.node.setPos(next_pos)
            self._update_health_bar_visibility(dt)
            return

        self.node.setPos(next_pos)
        self._update_health_bar_visibility(dt)

    def destroy(self):
        if self.is_dead and (self.node is None or self.node.isEmpty()):
            return
        self.is_dead = True
        if self.health_bar_root is not None and not self.health_bar_root.isEmpty():
            self.health_bar_root.hide()
        release_enemy_actor(self.game, self.asset_name, self.node)
        self.node = NodePath()
        if self.on_finish:
            self.on_finish()


class PortalSpawner:
    """File d'attente d'un portail : spawne les ennemis un par un avec un delai."""

    def __init__(self, game, waypoints, count, speed, scale, interval, enemy_type=ENEMY_TYPE_CLASSIC, max_hp=None, enemy_types=None):
        self.game       = game
        self.waypoints  = waypoints
        self.speed      = speed
        self.scale      = scale
        self.interval   = interval
        self.max_hp     = max_hp
        if enemy_types is None:
            self.enemy_types = [enemy_type] * max(0, int(count))
        else:
            self.enemy_types = [normalize_enemy_type(enemy_type) for enemy_type in enemy_types]
        self._spawn_index = 0
        self.remaining  = len(self.enemy_types)
        self.timer      = 0.0
        self.done       = self.remaining <= 0

    def update(self, dt):
        if self.done:
            return None
        self.timer -= dt
        if self.timer > 0:
            return None
        enemy_type = self.enemy_types[self._spawn_index]
        enemy = WaypointEnemy(
            self.game,
            self.waypoints,
            speed=self.speed,
            scale=self.scale,
            enemy_type=enemy_type,
            max_hp=self.max_hp,
        )
        self._spawn_index += 1
        self.remaining = len(self.enemy_types) - self._spawn_index
        self.timer = self.interval if self.remaining > 0 else 0.0
        if self.remaining <= 0:
            self.done = True
        return enemy


class EnemyManager:
    BASE_DAMAGE_PER_ENEMY = BASE_ENEMY_DAMAGE

    def __init__(self, game):
        self.game = game
        self.enemies = []
        self._spawners = []
        self._next_id = 0
        self._player_cooldowns = {}
        self._enemy_by_id = {}
        self._spatial_grid = {}
        self._spatial_dirty = True
        self._valid_position_cache = {}
        self._actor_pool = get_enemy_actor_pool(game)

    def _add_enemy(self, enemy):
        if enemy is None or enemy.is_dead:
            return None
        self.enemies.append(enemy)
        self._enemy_by_id[enemy.id] = enemy
        self._spatial_dirty = True
        return enemy

    def _remove_enemy(self, enemy):
        if enemy is None:
            return
        self._enemy_by_id.pop(getattr(enemy, "id", None), None)
        try:
            self.enemies.remove(enemy)
        except ValueError:
            pass
        self._spatial_dirty = True

    def _remove_dead_enemies(self):
        removed = False
        for index in range(len(self.enemies) - 1, -1, -1):
            enemy = self.enemies[index]
            if not enemy.is_dead:
                continue
            self._enemy_by_id.pop(getattr(enemy, "id", None), None)
            self.enemies.pop(index)
            removed = True
        if removed:
            self._spatial_dirty = True

    def _cell_for_position(self, pos):
        return (
            int(math.floor(pos.x / SPATIAL_CELL_SIZE)),
            int(math.floor(pos.y / SPATIAL_CELL_SIZE)),
        )

    def _cell_range_for_bounds(self, min_x, max_x, min_y, max_y):
        min_cell_x = int(math.floor(min_x / SPATIAL_CELL_SIZE))
        max_cell_x = int(math.floor(max_x / SPATIAL_CELL_SIZE))
        min_cell_y = int(math.floor(min_y / SPATIAL_CELL_SIZE))
        max_cell_y = int(math.floor(max_y / SPATIAL_CELL_SIZE))
        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1):
                yield cell_x, cell_y

    def _rebuild_spatial_grid(self):
        self._spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_dead:
                continue
            pos = enemy.node.getPos(self.game.render)
            self._spatial_grid.setdefault(self._cell_for_position(pos), []).append(enemy)
        self._spatial_dirty = False

    def _iter_candidates_in_bounds(self, min_x, max_x, min_y, max_y):
        if self._spatial_dirty:
            self._rebuild_spatial_grid()
        seen = set()
        for cell in self._cell_range_for_bounds(min_x, max_x, min_y, max_y):
            for enemy in self._spatial_grid.get(cell, ()):
                identity = id(enemy)
                if identity in seen or enemy.is_dead:
                    continue
                seen.add(identity)
                yield enemy

    def iter_enemies_in_radius(self, center, radius):
        radius_sq = radius * radius
        for enemy in self._iter_candidates_in_bounds(
            center.x - radius,
            center.x + radius,
            center.y - radius,
            center.y + radius,
        ):
            pos = enemy.node.getPos(self.game.render)
            if MathUtils.distance_xy_squared(pos, center) <= radius_sq:
                yield enemy

    def _iter_enemies_along_segment(self, start_pos, end_pos, radius):
        min_x = min(start_pos.x, end_pos.x) - radius
        max_x = max(start_pos.x, end_pos.x) + radius
        min_y = min(start_pos.y, end_pos.y) - radius
        max_y = max(start_pos.y, end_pos.y) + radius
        return self._iter_candidates_in_bounds(min_x, max_x, min_y, max_y)

    def _preload_enemy_type(self, enemy_type, count):
        asset_name = get_enemy_type_config(enemy_type)["asset"]
        self._actor_pool.preload(asset_name, count)

    def _choose_enemy_type(self, enemy_type=None):
        if enemy_type in RANDOM_ENEMY_TYPE_VALUES:
            return random.choice(ENEMY_TYPE_CHOICES)
        if isinstance(enemy_type, str) and enemy_type.strip().lower() in RANDOM_ENEMY_TYPE_VALUES:
            return random.choice(ENEMY_TYPE_CHOICES)
        return normalize_enemy_type(enemy_type)

    def _normalise_enemy_counts(self, enemy_counts, portal_count, count_per_portal, enemy_type):
        if enemy_counts is None:
            chosen_type = self._choose_enemy_type(enemy_type)
            return {chosen_type: max(0, int(count_per_portal or 0)) * portal_count}

        counts_by_type = {}
        for raw_type, raw_count in enemy_counts.items():
            enemy_type = normalize_enemy_type(raw_type)
            count = max(0, int(raw_count))
            counts_by_type[enemy_type] = counts_by_type.get(enemy_type, 0) + count
        return counts_by_type

    def _distribute_count_by_portal(self, total_count, portal_count):
        base_count = total_count // portal_count
        remainder = total_count % portal_count
        return [
            base_count + (1 if portal_index < remainder else 0)
            for portal_index in range(portal_count)
        ]

    def _interleave_enemy_types(self, counts_by_type):
        remaining_by_type = {
            enemy_type: max(0, int(counts_by_type.get(enemy_type, 0)))
            for enemy_type in ENEMY_TYPE_SPAWN_ORDER
        }
        boss_sequence = []
        for enemy_type in ENEMY_TYPE_BOSS_ORDER:
            boss_sequence.extend([enemy_type] * remaining_by_type.pop(enemy_type, 0))
        sequence = []

        while sum(remaining_by_type.values()) > 0:
            for enemy_type in remaining_by_type:
                if remaining_by_type[enemy_type] <= 0:
                    continue
                sequence.append(enemy_type)
                remaining_by_type[enemy_type] -= 1

        sequence.extend(boss_sequence)
        return sequence

    def _build_portal_enemy_sequences(self, enemy_counts, portal_count):
        counts_by_portal = [dict.fromkeys(ENEMY_TYPE_SPAWN_ORDER, 0) for _ in range(portal_count)]

        for enemy_type in ENEMY_TYPE_SPAWN_ORDER:
            for portal_index, count in enumerate(
                self._distribute_count_by_portal(enemy_counts.get(enemy_type, 0), portal_count)
            ):
                counts_by_portal[portal_index][enemy_type] = count

        return [
            self._interleave_enemy_types(portal_counts)
            for portal_counts in counts_by_portal
        ]

    def spawn_dog(self, start_pos, end_pos, **kwargs):
        allow_blocked_end = kwargs.pop("allow_blocked_end", False)
        enemy_type = self._choose_enemy_type(kwargs.pop("enemy_type", None))
        if not self._is_valid_position(start_pos):
            return None
        if not allow_blocked_end and not self._is_valid_position(end_pos):
            return None

        enemy_id = f"enemy_{self._next_id}"
        self._next_id += 1
        kwargs["enemy_id"] = enemy_id

        dog = DogEnemy(self.game, start_pos, end_pos, enemy_type=enemy_type, **kwargs)
        if dog.is_dead:
            dog.destroy()
            return None
        return self._add_enemy(dog)

    def spawn_random_dogs_in_area(
        self,
        count=10,
        area_min_x=-50,
        area_max_x=50,
        area_min_y=-50,
        area_max_y=50,
        margin=2.0,
        detection_radius=12.0,
        chase_speed=2.0,
        **kwargs
    ):
        safe_min_x, safe_max_x = area_min_x + margin, area_max_x - margin
        safe_min_y, safe_max_y = area_min_y + margin, area_max_y - margin
        area_bounds = (safe_min_x, safe_max_x, safe_min_y, safe_max_y)

        player_node = None
        if hasattr(self.game, "player") and hasattr(self.game.player, "player"):
            player_node = self.game.player.player

        spawned = 0
        attempts = 0
        max_attempts = count * 25
        target_pos = self._get_pipe_target_pos()

        while spawned < count and attempts < max_attempts:
            attempts += 1
            start_pos = self._random_valid_position_away(
                safe_min_x, safe_max_x, safe_min_y, safe_max_y,
                target_pos, min_distance=8.0,
            )
            dog = self.spawn_dog(
                start_pos,
                target_pos,
                player_node=player_node,
                detection_radius=detection_radius,
                chase_speed=chase_speed,
                area_bounds=area_bounds,
                objective_callback=self._handle_enemy_reached_base,
                objective_reach_radius=1.0,
                allow_blocked_end=True,
                **kwargs
            )
            if dog is not None:
                spawned += 1

        return spawned

    def _get_pipe_target_pos(self):
        pipe_base = getattr(self.game, "pipe_base", None)
        if pipe_base is None:
            return Vec3(0, 0, 0)
        return Vec3(pipe_base.get_position())

    def _handle_enemy_reached_base(self, enemy):
        if enemy.is_dead:
            return
        if hasattr(self.game, "damage_pipe"):
            self.game.damage_pipe(self._get_enemy_objective_damage(enemy))
        if not enemy.is_dead:
            enemy.destroy()
        vague_manager = getattr(self.game, "vague_manager", None)
        if vague_manager is not None and hasattr(vague_manager, "enemy_reached_base"):
            vague_manager.enemy_reached_base()

    def _generate_random_path(self, min_x, max_x, min_y, max_y, margin):
        safe_min_x, safe_max_x = min_x + margin, max_x - margin
        safe_min_y, safe_max_y = min_y + margin, max_y - margin

        start = self._random_valid_position(safe_min_x, safe_max_x, safe_min_y, safe_max_y)
        end = self._random_valid_position(safe_min_x, safe_max_x, safe_min_y, safe_max_y)

        for _ in range(20):
            if (end - start).length() >= 6.0:
                break
            end = self._random_valid_position(safe_min_x, safe_max_x, safe_min_y, safe_max_y)

        return start, end

    def spawn_wave(
        self,
        portal_paths,
        count_per_portal=None,
        speed=4.0,
        scale=19,
        interval=1.5,
        enemy_type=ENEMY_TYPE_CLASSIC,
        max_hp=None,
        enemy_counts=None,
    ):
        """
        Lance une vague depuis les portails definis dans portal_paths.
        Ajoute dynamiquement la position du tuyau comme dernier waypoint de chaque chemin.
        """
        self._spawners.clear()

        portal_count = len(portal_paths)
        if portal_count <= 0:
            return 0

        pipe_pos = self._get_pipe_target_pos()
        counts_by_type = self._normalise_enemy_counts(enemy_counts, portal_count, count_per_portal, enemy_type)
        total_count = sum(counts_by_type.values())
        if total_count <= 0:
            return 0

        for preload_type, count in counts_by_type.items():
            self._preload_enemy_type(preload_type, count)

        portal_sequences = self._build_portal_enemy_sequences(counts_by_type, portal_count)
        for path, enemy_sequence in zip(portal_paths, portal_sequences):
            if not enemy_sequence:
                continue
            full_path = [Vec3(wp) for wp in path]
            full_path.append(Vec3(pipe_pos.x, pipe_pos.y, 0))
            spawner = PortalSpawner(
                game       = self.game,
                waypoints  = full_path,
                count      = len(enemy_sequence),
                speed      = speed,
                scale      = scale,
                interval   = interval,
                enemy_type = enemy_type,
                max_hp     = max_hp,
                enemy_types = enemy_sequence,
            )
            self._spawners.append(spawner)

        return total_count

    def spawn_waypoint_dog(self, waypoints, speed=2.0, scale=19, on_finish=None, enemy_type=None):
        """
        Spawne un ennemi qui parcourt la liste de waypoints a vitesse fixe
        et disparait apres le dernier point.
        """
        if len(waypoints) < 2:
            raise ValueError("Il faut au moins 2 waypoints.")
        enemy = WaypointEnemy(
            self.game,
            waypoints,
            speed=speed,
            scale=scale,
            on_finish=on_finish,
            enemy_type=self._choose_enemy_type(enemy_type),
        )
        return self._add_enemy(enemy)

    def _valid_position_cache_key(self, min_x, max_x, min_y, max_y, step):
        return (
            id(getattr(self.game, "map_collision", None)),
            round(min_x, 3),
            round(max_x, 3),
            round(min_y, 3),
            round(max_y, 3),
            round(step, 3),
        )

    def _valid_positions_for_bounds(self, min_x, max_x, min_y, max_y, step=VALID_POSITION_SCAN_STEP):
        key = self._valid_position_cache_key(min_x, max_x, min_y, max_y, step)
        cached = self._valid_position_cache.get(key)
        if cached is not None:
            return cached

        positions = []
        for x in self._scan_range(min_x, max_x, step):
            for y in self._scan_range(min_y, max_y, step):
                pos = Vec3(x, y, 0)
                if self._is_valid_position(pos):
                    positions.append(pos)

        self._valid_position_cache[key] = positions
        return positions

    def _random_valid_position(self, min_x, max_x, min_y, max_y):
        for _ in range(200):
            pos = Vec3(random.uniform(min_x, max_x), random.uniform(min_y, max_y), 0)
            if self._is_valid_position(pos):
                return pos

        positions = self._valid_positions_for_bounds(min_x, max_x, min_y, max_y)
        if positions:
            return Vec3(random.choice(positions))

        return Vec3(0, 0, 0)

    def _random_valid_position_away(self, min_x, max_x, min_y, max_y, target_pos, min_distance):
        min_distance_sq = min_distance * min_distance

        for _ in range(200):
            pos = Vec3(random.uniform(min_x, max_x), random.uniform(min_y, max_y), 0)
            if not self._is_valid_position(pos):
                continue
            if MathUtils.distance_xy_squared(pos, target_pos) >= min_distance_sq:
                return pos

        far_positions = [
            pos
            for pos in self._valid_positions_for_bounds(min_x, max_x, min_y, max_y)
            if MathUtils.distance_xy_squared(pos, target_pos) >= min_distance_sq
        ]
        if far_positions:
            return Vec3(random.choice(far_positions))

        return self._random_valid_position(min_x, max_x, min_y, max_y)

    def _scan_range(self, min_value, max_value, step):
        current = min_value
        while current <= max_value:
            yield current
            current += step

    def _is_valid_position(self, pos):
        map_collision = getattr(self.game, "map_collision", None)
        if map_collision is None:
            return True
        return map_collision.is_position_allowed(pos)

    def _get_touching_enemy(self, player_pos):
        contact_radius = max(DogEnemy.CONTACT_RADIUS, WaypointEnemy.CONTACT_RADIUS)
        for enemy in self.iter_enemies_in_radius(player_pos, contact_radius):
            if enemy.is_touching_point(player_pos):
                return enemy
        return None

    def _get_enemy_damage(self, enemy):
        return max(1, int(getattr(enemy, "damage", self.BASE_DAMAGE_PER_ENEMY)))

    def _get_enemy_objective_damage(self, enemy):
        return max(1, int(getattr(enemy, "objective_damage", self._get_enemy_damage(enemy))))

    def _damage_local_player(self, damage):
        damage = max(1, int(damage))
        if hasattr(self.game, "damage_player"):
            self.game.damage_player(damage)
            return
        self.game.messenger.send("player-take-damage", [damage])

    def _grant_enemy_resources(self, enemy):
        gain = max(0, int(getattr(enemy, "resource_reward", 0)))
        if gain <= 0:
            return

        resource_system = getattr(self.game, "resource_system", None)
        if resource_system is not None and hasattr(resource_system, "grant_resources"):
            resource_system.grant_resources(gain)
            return

        inventory = getattr(self.game, "inventory", None)
        if inventory is None:
            return

        inventory["ressource"] = inventory.get("ressource", 0) + gain
        inventory_ui = getattr(self.game, "inventory_ui", None)
        if inventory_ui is not None and hasattr(inventory_ui, "update"):
            inventory_ui.update()

    def _handle_enemy_killed(self, enemy):
        self._remove_enemy(enemy)
        self._grant_enemy_resources(enemy)
        self.game.messenger.send("enemy-killed")

    def _handle_waypoint_enemy_reached_base(self, enemy):
        self.game.damage_pipe(self._get_enemy_objective_damage(enemy))
        enemy.destroy()
        vague_manager = getattr(self.game, "vague_manager", None)
        if vague_manager is not None and hasattr(vague_manager, "enemy_reached_base"):
            vague_manager.enemy_reached_base()

    def check_projectile_hit(self, start_pos, end_pos, hit_radius, apply_damage=True, damage=1):
        for enemy in self._iter_enemies_along_segment(start_pos, end_pos, hit_radius):
            if enemy.is_touched_by_segment(start_pos, end_pos, hit_radius):
                if apply_damage:
                    killed = enemy.take_damage(max(1, int(damage)))
                    if killed:
                        self._handle_enemy_killed(enemy)
                return True
        return False

    def damage_enemies_in_radius(self, center_pos, radius, apply_damage=True, damage=1):
        hit_any = False
        for enemy in list(self.iter_enemies_in_radius(center_pos, radius)):
            if enemy.is_dead:
                continue

            hit_any = True
            if not apply_damage:
                continue

            killed = enemy.take_damage(max(1, int(damage)))
            if killed:
                self._handle_enemy_killed(enemy)

        return hit_any

    def check_player_contact(self, player_pos):
        return self._get_touching_enemy(player_pos) is not None

    def update(self, dt):
        is_host = True
        net_iface = getattr(self.game, 'network', None)
        if net_iface is not None and getattr(net_iface, 'net', None) is not None:
            is_host = net_iface.net.is_host

        if is_host:
            for index in range(len(self._spawners) - 1, -1, -1):
                spawner = self._spawners[index]
                enemy = spawner.update(dt)
                if enemy is not None:
                    self._add_enemy(enemy)
                if spawner.done:
                    self._spawners.pop(index)

            for enemy in self.enemies:
                if enemy.is_dead:
                    continue
                if isinstance(enemy, WaypointEnemy) and enemy.has_reached_end():
                    self._handle_waypoint_enemy_reached_base(enemy)
                    continue
                enemy.update(dt)
                if isinstance(enemy, WaypointEnemy) and enemy.has_reached_end():
                    self._handle_waypoint_enemy_reached_base(enemy)

            self._spatial_dirty = True

            if hasattr(self.game, 'player'):
                player_np = getattr(self.game.player, 'player', None)
                if player_np is not None:
                    player_pos = player_np.getPos(self.game.render)
                    touching_enemy = self._get_touching_enemy(player_pos)
                    if touching_enemy is not None:
                        self._damage_local_player(self._get_enemy_damage(touching_enemy))

            if net_iface is not None:
                for name, model in net_iface.other_players.items():
                    if name not in self._player_cooldowns:
                        self._player_cooldowns[name] = 0.0
                    if self._player_cooldowns[name] > 0:
                        self._player_cooldowns[name] = max(0.0, self._player_cooldowns[name] - dt)
                        continue

                    p_pos = model.getPos(self.game.render)
                    touching_enemy = self._get_touching_enemy(p_pos)
                    if touching_enemy is not None:
                        if hasattr(model, "hasPythonTag") and model.hasPythonTag("hp"):
                            current_hp = model.getPythonTag("hp")
                        else:
                            current_hp = 10
                        if current_hp > 0:
                            model.setPythonTag("hp", current_hp - self._get_enemy_damage(touching_enemy))
                            self._player_cooldowns[name] = 0.5
        else:
            for enemy in self.enemies:
                if enemy.is_dead:
                    continue
                enemy.interpolate(dt)
            self._spatial_dirty = True

        self._remove_dead_enemies()

    def _enemy_type_from_snapshot(self, enemy_data):
        return normalize_enemy_type(enemy_data.get("enemy_type", enemy_data.get("type", ENEMY_TYPE_CLASSIC)))

    def sync_from_snapshot(self, enemies_data):
        known_ids = set()
        for e_data in enemies_data:
            eid = e_data['id']
            enemy_type = self._enemy_type_from_snapshot(e_data)
            known_ids.add(eid)
            existing = self._enemy_by_id.get(eid)

            if existing and getattr(existing, "enemy_type", ENEMY_TYPE_CLASSIC) != enemy_type:
                existing.destroy()
                self._remove_enemy(existing)
                existing = None

            if existing:
                existing.sync_state(e_data['x'], e_data['y'], e_data['z'], e_data['h'], e_data['hp'], e_data.get('max_hp'))
            else:
                dog = DogEnemy(
                    self.game,
                    (e_data['x'], e_data['y'], e_data['z']),
                    (e_data['x'] + 0.1, e_data['y'], e_data['z']),
                    scale=1.0,
                    enemy_id=eid,
                    max_hp=e_data.get('max_hp'),
                    enemy_type=enemy_type,
                )
                dog.is_dead = False
                dog.sync_state(e_data['x'], e_data['y'], e_data['z'], e_data['h'], e_data['hp'], e_data.get('max_hp'))
                self._add_enemy(dog)

        for enemy in self.enemies:
            if enemy.id not in known_ids:
                enemy.destroy()

        self._spatial_dirty = True
        self._remove_dead_enemies()

    def get_snapshot(self):
        return [self._enemy_to_snapshot(enemy) for enemy in self.enemies if not enemy.is_dead]

    def _enemy_to_snapshot(self, enemy):
        pos = enemy.node.getPos(self.game.render)
        return {
            "id": enemy.id,
            "enemy_type": getattr(enemy, "enemy_type", ENEMY_TYPE_CLASSIC),
            "x": pos.x,
            "y": pos.y,
            "z": pos.z,
            "h": enemy.node.getH(self.game.render),
            "hp": enemy.hp,
            "max_hp": getattr(enemy, "max_hp", enemy.hp),
        }

    def clear(self):
        self._spawners.clear()
        for enemy in self.enemies:
            enemy.destroy()
        self.enemies.clear()
        self._enemy_by_id.clear()
        self._spatial_grid.clear()
        self._spatial_dirty = True
