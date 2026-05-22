import math
import os
import random
from panda3d.core import CardMaker, Filename, Point3, TransparencyAttrib, Vec3
from .utils import powLerp, shortest_angle_lerp


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
        objective_callback=None,
        objective_reach_radius=1.0,
        enemy_id=None,
    ):
        self.game = game
        self.id = enemy_id or f"enemy_{id(self)}"
        self.map_collision = getattr(self.game, "map_collision", None)
        self.speed = speed
        self.chase_speed = chase_speed if chase_speed is not None else speed * 1.25
        self.detection_radius = detection_radius
        self.player_node = player_node
        self.area_bounds = area_bounds
        self.respawn_callback = respawn_callback
        self.objective_callback = objective_callback
        self.objective_reach_radius = objective_reach_radius
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

    def sync_state(self, x, y, z, h, hp):
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
        self.hp = self.MAX_HP
        self.is_chasing = False
        if self.respawn_callback:
            self.start_pos, self.end_pos = self.respawn_callback()
        self._recalculate_movement()
        self._update_health_bar()

    def destroy(self):
        self.is_dead = True
        self.node.removeNode()



class WaypointEnemy:
    """Ennemi qui suit une liste de waypoints a vitesse fixe puis disparait."""
    MAX_HP = 3
    CONTACT_RADIUS = 1.5
    WAYPOINT_REACH_THRESHOLD = 0.3

    def __init__(self, game, waypoints, speed=4.0, scale=1.0, on_finish=None):
        self.game      = game
        self.waypoints = [Vec3(wp) for wp in waypoints]
        self.speed     = speed
        self.on_finish = on_finish
        self.is_dead   = False
        self.hp        = self.MAX_HP
        self._index    = 0

        self.node = self._load_model()
        self.node.reparentTo(self.game.render)
        self.node.setScale(scale)
        self.node.setPos(self.waypoints[0])

        if len(self.waypoints) > 1:
            self.node.lookAt(self.waypoints[1])

    def _load_model(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = Filename.fromOsSpecific(os.path.join(base_dir, "../assets", "dog.bam")).getFullpath()
        return self.game.loader.loadModel(path)

    def take_damage(self, amount=1):
        if self.is_dead:
            return False
        self.hp -= amount
        if self.hp <= 0:
            self.destroy()
            return True
        return False

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
            self.destroy()
            return

        target      = self.waypoints[next_index]
        current_pos = self.node.getPos(self.game.render)
        to_target   = Vec3(target.x - current_pos.x, target.y - current_pos.y, 0)
        dist        = to_target.length()

        if dist <= self.WAYPOINT_REACH_THRESHOLD:
            self._index = next_index
            self.node.setPos(target)
            if self._index + 1 < len(self.waypoints):
                self.node.lookAt(self.waypoints[self._index + 1])
            return

        direction = to_target / dist
        step      = min(self.speed * dt, dist)
        self.node.setPos(Vec3(current_pos.x + direction.x * step, current_pos.y + direction.y * step, current_pos.z))

    def destroy(self):
        if self.is_dead:
            return
        self.is_dead = True
        self.node.removeNode()
        if self.on_finish:
            self.on_finish()

class EnemyManager:
    BASE_DAMAGE_PER_ENEMY = 1

    def __init__(self, game):
        self.game = game
        self.enemies = []
        self._next_id = 0
        self._player_cooldowns = {}

    def spawn_dog(self, start_pos, end_pos, **kwargs):
        allow_blocked_end = kwargs.pop("allow_blocked_end", False)
        if not self._is_valid_position(start_pos):
            return None
        if not allow_blocked_end and not self._is_valid_position(end_pos):
            return None

        enemy_id = f"enemy_{self._next_id}"
        self._next_id += 1
        kwargs["enemy_id"] = enemy_id

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

        spawned = 0
        attempts = 0
        max_attempts = count * 25
        target_pos = self._get_pipe_target_pos()

        while spawned < count and attempts < max_attempts:
            attempts += 1
            start_pos = self._random_valid_position_away(
                safe_min_x,
                safe_max_x,
                safe_min_y,
                safe_max_y,
                target_pos,
                min_distance=8.0,
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
            self.game.damage_pipe(self.BASE_DAMAGE_PER_ENEMY)

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

    def spawn_waypoint_dog(self, waypoints, speed=4.0, scale=1.0, on_finish=None):
        """
        Spawne un ennemi qui parcourt la liste de waypoints a vitesse fixe
        et disparait apres le dernier point.

        waypoints : liste de Vec3 ou de tuples (x, y, z).
                    Le premier point est la position d'apparition.
        on_finish : callback optionnel appele quand l'ennemi atteint le dernier point.
        """
        if len(waypoints) < 2:
            raise ValueError("Il faut au moins 2 waypoints.")
        enemy = WaypointEnemy(self.game, waypoints, speed=speed, scale=scale, on_finish=on_finish)
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

    def check_projectile_hit(self, start_pos, end_pos, hit_radius, apply_damage=True, damage=1):
        for enemy in self.enemies[:]:
            if enemy.is_touched_by_segment(start_pos, end_pos, hit_radius):
                if apply_damage:
                    killed = enemy.take_damage(max(1, int(damage)))
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
        is_host = True
        net_iface = getattr(self.game, 'network', None)
        if net_iface is not None and getattr(net_iface, 'net', None) is not None:
            is_host = net_iface.net.is_host

        if is_host:
            for enemy in self.enemies:
                enemy.update(dt)

            if hasattr(self.game, 'player'):
                player_np = getattr(self.game.player, 'player', None)
                if player_np is not None:
                    player_pos = player_np.getPos(self.game.render)
                    if self.check_player_contact(player_pos):
                        self.game.messenger.send("player-take-damage")

            if net_iface is not None:
                for name, model in net_iface.other_players.items():
                    if name not in self._player_cooldowns:
                        self._player_cooldowns[name] = 0.0
                    if self._player_cooldowns[name] > 0:
                        self._player_cooldowns[name] = max(0.0, self._player_cooldowns[name] - dt)
                        continue

                    p_pos = model.getPos(self.game.render)
                    if self.check_player_contact(p_pos):
                        if hasattr(model, "hasPythonTag") and model.hasPythonTag("hp"):
                            current_hp = model.getPythonTag("hp")
                        else:
                            current_hp = 10
                        if current_hp > 0:
                            model.setPythonTag("hp", current_hp - 1)
                            self._player_cooldowns[name] = 0.5
        else:
            for enemy in self.enemies:
                enemy.interpolate(dt)

        self.enemies = [e for e in self.enemies if not e.is_dead]

    def sync_from_snapshot(self, enemies_data):
        known_ids = set()
        for e_data in enemies_data:
            eid = e_data['id']
            known_ids.add(eid)
            existing = next((e for e in self.enemies if e.id == eid), None)
            if existing:
                existing.sync_state(e_data['x'], e_data['y'], e_data['z'], e_data['h'], e_data['hp'])
            else:
                dog = DogEnemy(self.game, (e_data['x'], e_data['y'], e_data['z']), (e_data['x'] + 0.1, e_data['y'], e_data['z']), enemy_id=eid)
                dog.is_dead = False
                dog.sync_state(e_data['x'], e_data['y'], e_data['z'], e_data['h'], e_data['hp'])
                self.enemies.append(dog)

        for enemy in list(self.enemies):
            if enemy.id not in known_ids:
                enemy.destroy()

        self.enemies = [e for e in self.enemies if not e.is_dead]

    def clear(self):
        for enemy in self.enemies:
            enemy.destroy()
        self.enemies.clear()
