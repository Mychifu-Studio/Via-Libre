import math
import os
import random

from direct.actor.Actor import Actor
from panda3d.core import CardMaker, Filename, Point3, TransparencyAttrib, Vec3

from .utils import powLerp, shortest_angle_lerp


BASE_ENEMY_HP = 10
BASE_ENEMY_DAMAGE = 1
ENEMY_ANIMATION_NAME = "walk"

ENEMY_TYPE_CLASSIC = "classique"
ENEMY_TYPE_FAST = "rapide"
ENEMY_TYPE_HEAVY = "lourd"

ENEMY_TYPE_CONFIGS = {
    ENEMY_TYPE_CLASSIC: {
        "asset": "ennemi_classique.bam",
        "hp_multiplier": 5.0,
        "speed_multiplier": 0.6,
        "damage_multiplier": 1.0,
        "resource_reward": 2,
    },
    ENEMY_TYPE_FAST: {
        "asset": "ennemi_rapide.bam",
        "hp_multiplier": 3,
        "speed_multiplier": 0.8,
        "damage_multiplier": 1.0,
        "resource_reward": 1,
    },
    ENEMY_TYPE_HEAVY: {
        "asset": "ennemi_lourd.bam",
        "hp_multiplier": 10.0,
        "speed_multiplier": 0.4,
        "damage_multiplier": 2.0,
        "resource_reward": 3,
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
}

RANDOM_ENEMY_TYPE_VALUES = {None, "random", "aleatoire"}
ENEMY_TYPE_CHOICES = tuple(ENEMY_TYPE_CONFIGS.keys())


def normalize_enemy_type(enemy_type):
    if enemy_type is None:
        return ENEMY_TYPE_CLASSIC
    key = str(enemy_type).strip().lower()
    return ENEMY_TYPE_ALIASES.get(key, ENEMY_TYPE_CLASSIC)


def get_enemy_type_config(enemy_type):
    return ENEMY_TYPE_CONFIGS[normalize_enemy_type(enemy_type)]


def get_enemy_asset_path(asset_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "../assets", asset_name)
    return Filename.fromOsSpecific(path).getFullpath()


def load_enemy_actor(asset_name):
    path = get_enemy_asset_path(asset_name)
    actor = Actor(path)
    try:
        if ENEMY_ANIMATION_NAME not in actor.getAnimNames():
            actor.loadAnims({ENEMY_ANIMATION_NAME: path})
        actor.loop(ENEMY_ANIMATION_NAME)
    except Exception:
        pass
    return actor


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
        self.resource_reward = max(0, int(self.enemy_config["resource_reward"]))

        self.detection_radius = detection_radius
        self.player_node = player_node
        self.area_bounds = area_bounds
        self.respawn_callback = respawn_callback
        self.objective_callback = objective_callback
        self.objective_reach_radius = objective_reach_radius
        self.is_dead = False

        type_max_hp = self.MAX_HP * self.enemy_config["hp_multiplier"]
        self.max_hp = max(1, int(round(max_hp if max_hp is not None else type_max_hp)))
        self.hp = self.max_hp

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
        return load_enemy_actor(self.asset_name)

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

        ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        if ratio > 0.55:
            color = (0.15, 0.85, 0.28, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)

        self.health_bar_fill.setSx(ratio)
        self.health_bar_fill.setColor(color)

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

        resolved_pos = self._move_with_collision(current_pos, next_pos)
        self.node.setPos(resolved_pos)

        if (resolved_pos - current_pos).lengthSquared() > 0.0001:
            self.node.lookAt(player_pos)

    def _has_reached_objective(self, pos):
        if self.objective_callback is not None:
            pipe_base = getattr(self.game, "pipe_base", None)
            if pipe_base is not None:
                return pipe_base.is_touching(pos)

        diff = self.end_pos - pos
        diff.setZ(0)
        return diff.length() <= self.objective_reach_radius

    def _reach_objective(self):
        if self.objective_callback is not None:
            self.objective_callback(self)
            return
        self.respawn()

    def _update_straight_line(self, current_pos, dt):
        if self._has_reached_objective(current_pos):
            self._reach_objective()
            return

        next_pos = current_pos + self.direction * self.speed * dt

        if (next_pos - current_pos).length() >= (self.end_pos - current_pos).length():
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
        diff = Vec3(point.x - pos.x, point.y - pos.y, 0)
        return diff.length() <= self.CONTACT_RADIUS

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

    def is_touched_by_segment(self, start_pos, end_pos, hit_radius):
        if self.is_dead:
            return False
        dist = MathUtils.distance_segment_to_point(start_pos, end_pos, self.node.getPos(self.game.render))
        return dist <= hit_radius

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
        self.is_dead = True
        if hasattr(self.node, "cleanup"):
            self.node.cleanup()
        self.node.removeNode()


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
        # max_hp explicite > config hp_multiplier > MAX_HP constant
        type_max_hp = self.MAX_HP * self.enemy_config["hp_multiplier"]
        self.max_hp = max(1, int(round(max_hp if max_hp is not None else type_max_hp)))
        self.hp = self.max_hp
        self.damage = max(1, int(round(self.BASE_DAMAGE * self.enemy_config["damage_multiplier"])))
        self.resource_reward = max(0, int(self.enemy_config["resource_reward"]))
        self._index = 0
        self.health_bar_fill = None

        self.node = self._load_model()
        self.node.reparentTo(self.game.render)
        self.node.setScale(scale)
        self.node.setPos(self.waypoints[0])

        if len(self.waypoints) > 1:
            self.node.lookAt(self.waypoints[1])

        self._create_health_bar()

    def _load_model(self):
        return load_enemy_actor(self.asset_name)

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
        ratio = max(0.0, min(1.0, self.hp / self.max_hp))
        if ratio > 0.55:
            color = (0.15, 0.85, 0.28, 0.95)
        elif ratio > 0.25:
            color = (0.95, 0.72, 0.18, 0.95)
        else:
            color = (0.95, 0.22, 0.18, 0.95)
        self.health_bar_fill.setSx(max(ratio, 0.001))
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

    def has_reached_end(self):
        return self._index >= len(self.waypoints) - 1

    def is_touched_by_segment(self, start_pos, end_pos, hit_radius):
        if self.is_dead:
            return False
        dist = MathUtils.distance_segment_to_point(start_pos, end_pos, self.node.getPos(self.game.render))
        return dist <= hit_radius

    def is_touching_point(self, point):
        if self.is_dead:
            return False
        pos = self.node.getPos(self.game.render)
        return Vec3(point.x - pos.x, point.y - pos.y, 0).length() <= self.CONTACT_RADIUS

    def update(self, dt):
        if self.is_dead:
            return

        next_index = self._index + 1
        if next_index >= len(self.waypoints):
            return

        target = self.waypoints[next_index]
        current_pos = self.node.getPos(self.game.render)
        to_target = Vec3(target.x - current_pos.x, target.y - current_pos.y, 0)
        dist = to_target.length()

        if dist <= self.WAYPOINT_REACH_THRESHOLD:
            self._index = next_index
            self.node.setPos(target)
            if self._index + 1 < len(self.waypoints):
                self.node.lookAt(self.waypoints[self._index + 1])
            return

        direction = to_target / dist
        step = min(self.speed * dt, dist)
        self.node.setPos(Vec3(current_pos.x + direction.x * step, current_pos.y + direction.y * step, current_pos.z))

    def destroy(self):
        if self.is_dead:
            return
        self.is_dead = True
        if hasattr(self.node, "cleanup"):
            self.node.cleanup()
        self.node.removeNode()
        if self.on_finish:
            self.on_finish()


class PortalSpawner:
    """File d'attente d'un portail : spawne les ennemis un par un avec un delai."""

    def __init__(self, game, waypoints, count, speed, scale, interval, enemy_type=ENEMY_TYPE_CLASSIC):
        self.game       = game
        self.waypoints  = waypoints
        self.speed      = speed
        self.scale      = scale
        self.interval   = interval
        self.enemy_type = enemy_type
        self.remaining  = count
        self.timer      = 0.0
        self.done       = False

    def update(self, dt, enemy_list):
        if self.done:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        enemy = WaypointEnemy(
            self.game,
            self.waypoints,
            speed=self.speed,
            scale=self.scale,
            enemy_type=self.enemy_type,
        )
        enemy_list.append(enemy)
        self.remaining -= 1
        self.timer = self.interval if self.remaining > 0 else 0.0
        if self.remaining <= 0:
            self.done = True


class EnemyManager:
    BASE_DAMAGE_PER_ENEMY = BASE_ENEMY_DAMAGE

    def __init__(self, game):
        self.game = game
        self.enemies = []
        self._spawners = []
        self._next_id = 0
        self._player_cooldowns = {}

    def _choose_enemy_type(self, enemy_type=None):
        if enemy_type in RANDOM_ENEMY_TYPE_VALUES:
            return random.choice(ENEMY_TYPE_CHOICES)
        if isinstance(enemy_type, str) and enemy_type.strip().lower() in RANDOM_ENEMY_TYPE_VALUES:
            return random.choice(ENEMY_TYPE_CHOICES)
        return normalize_enemy_type(enemy_type)

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
            self.game.damage_pipe(self._get_enemy_damage(enemy))
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

    def spawn_wave(self, portal_paths, count_per_portal, speed=4.0, scale=19, interval=1.5, enemy_type=ENEMY_TYPE_CLASSIC):
        """
        Lance une vague depuis les portails definis dans portal_paths.
        Ajoute dynamiquement la position du tuyau comme dernier waypoint de chaque chemin.
        """
        self._spawners.clear()

        pipe_pos = self._get_pipe_target_pos()
        chosen_type = self._choose_enemy_type(enemy_type)

        for path in portal_paths:
            full_path = [Vec3(wp) for wp in path]
            full_path.append(Vec3(pipe_pos.x, pipe_pos.y, 0))
            spawner = PortalSpawner(
                game       = self.game,
                waypoints  = full_path,
                count      = count_per_portal,
                speed      = speed,
                scale      = scale,
                interval   = interval,
                enemy_type = chosen_type,
            )
            self._spawners.append(spawner)

        return count_per_portal * len(portal_paths)

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
        self.enemies.append(enemy)
        return enemy

    def _random_valid_position(self, min_x, max_x, min_y, max_y):
        for _ in range(200):
            pos = Vec3(random.uniform(min_x, max_x), random.uniform(min_y, max_y), 0)
            if self._is_valid_position(pos):
                return pos

        for x in self._scan_range(min_x, max_x, 2.0):
            for y in self._scan_range(min_y, max_y, 2.0):
                pos = Vec3(x, y, 0)
                if self._is_valid_position(pos):
                    return pos

        return Vec3(0, 0, 0)

    def _random_valid_position_away(self, min_x, max_x, min_y, max_y, target_pos, min_distance):
        flat_target = Vec3(target_pos.x, target_pos.y, 0)

        for _ in range(200):
            pos = Vec3(random.uniform(min_x, max_x), random.uniform(min_y, max_y), 0)
            if not self._is_valid_position(pos):
                continue
            if (pos - flat_target).length() >= min_distance:
                return pos

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
        for enemy in self.enemies:
            if enemy.is_touching_point(player_pos):
                return enemy
        return None

    def _get_enemy_damage(self, enemy):
        return max(1, int(getattr(enemy, "damage", self.BASE_DAMAGE_PER_ENEMY)))

    def _damage_local_player(self, damage):
        damage = max(1, int(damage))
        if hasattr(self.game, "damage_player"):
            self.game.damage_player(damage)
            return
        for _ in range(damage):
            self.game.messenger.send("player-take-damage")

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

    def check_projectile_hit(self, start_pos, end_pos, hit_radius, apply_damage=True, damage=1):
        for enemy in self.enemies[:]:
            if enemy.is_touched_by_segment(start_pos, end_pos, hit_radius):
                if apply_damage:
                    killed = enemy.take_damage(max(1, int(damage)))
                    if killed:
                        if enemy in self.enemies:
                            self.enemies.remove(enemy)
                        self._grant_enemy_resources(enemy)
                        self.game.messenger.send("enemy-hit")
                return True
        return False

    def check_player_contact(self, player_pos):
        return self._get_touching_enemy(player_pos) is not None

    def update(self, dt):
        is_host = True
        net_iface = getattr(self.game, 'network', None)
        if net_iface is not None and getattr(net_iface, 'net', None) is not None:
            is_host = net_iface.net.is_host

        if is_host:
            for spawner in self._spawners:
                spawner.update(dt, self.enemies)

            for enemy in self.enemies:
                if isinstance(enemy, WaypointEnemy) and enemy.has_reached_end():
                    self.game.damage_pipe(self._get_enemy_damage(enemy))
                    self.game.messenger.send("enemy-hit")
                    enemy.destroy()
                    continue
                enemy.update(dt)

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
                enemy.interpolate(dt)

        self.enemies = [e for e in self.enemies if not e.is_dead]

    def _enemy_type_from_snapshot(self, enemy_data):
        return normalize_enemy_type(enemy_data.get("enemy_type", enemy_data.get("type", ENEMY_TYPE_CLASSIC)))

    def sync_from_snapshot(self, enemies_data):
        known_ids = set()
        for e_data in enemies_data:
            eid = e_data['id']
            enemy_type = self._enemy_type_from_snapshot(e_data)
            known_ids.add(eid)
            existing = next((e for e in self.enemies if e.id == eid), None)

            if existing and getattr(existing, "enemy_type", ENEMY_TYPE_CLASSIC) != enemy_type:
                existing.destroy()
                if existing in self.enemies:
                    self.enemies.remove(existing)
                existing = None

            if existing:
                existing.sync_state(e_data['x'], e_data['y'], e_data['z'], e_data['h'], e_data['hp'], e_data.get('max_hp'))
            else:
                dog = DogEnemy(
                    self.game,
                    (e_data['x'], e_data['y'], e_data['z']),
                    (e_data['x'] + 0.1, e_data['y'], e_data['z']),
                    enemy_id=eid,
                    max_hp=e_data.get('max_hp'),
                    enemy_type=enemy_type,
                )
                dog.is_dead = False
                dog.sync_state(e_data['x'], e_data['y'], e_data['z'], e_data['h'], e_data['hp'], e_data.get('max_hp'))
                self.enemies.append(dog)

        for enemy in list(self.enemies):
            if enemy.id not in known_ids:
                enemy.destroy()

        self.enemies = [e for e in self.enemies if not e.is_dead]

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