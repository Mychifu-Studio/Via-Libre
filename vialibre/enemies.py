import math
import os
import random

from panda3d.core import Filename, Vec3


class DogEnemy:

    def __init__(self, game, start_pos, end_pos, speed=4.0, scale=1.0, respawn_callback=None):
        self.game = game
        self.start_pos = self._to_vec3(start_pos)
        self.end_pos = self._to_vec3(end_pos)
        self.speed = speed
        self.scale = scale
        self.respawn_callback = respawn_callback
        self.is_dead = False

        self.node = self._load_model()
        self.node.reparentTo(self.game.render)
        self.node.setPos(self.start_pos)
        self.node.setScale(scale)

        self._recalculate_movement()

    def _load_model(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = Filename.fromOsSpecific(
            os.path.join(base_dir, "../assets", "dog.bam")
        ).getFullpath()
        return self.game.loader.loadModel(model_path)

    def _to_vec3(self, value):
        if isinstance(value, Vec3):
            return Vec3(value)
        return Vec3(value[0], value[1], value[2])

    def _recalculate_movement(self):
        movement = self.end_pos - self.start_pos
        movement.setZ(0)
        self.total_distance = movement.length()

        if self.total_distance <= 0.001:
            self.direction = Vec3(0, 0, 0)
            self.is_dead = True
        else:
            self.direction = movement.normalized()
            self.node.lookAt(self.end_pos)

    def update(self, dt):
        if self.is_dead:
            return

        current_pos = self.node.getPos(self.game.render)
        next_pos = current_pos + self.direction * self.speed * dt

        distance_left_now = (self.end_pos - current_pos).length()
        distance_to_move = (next_pos - current_pos).length()

        if distance_to_move >= distance_left_now:
            self.respawn()
            return

        self.node.setPos(next_pos)

    def is_touched_by_segment(self, start_pos, end_pos, hit_radius):

        if self.is_dead:
            return False

        enemy_pos = self.node.getPos(self.game.render)

        segment = end_pos - start_pos
        segment.setZ(0)

        enemy_vector = enemy_pos - start_pos
        enemy_vector.setZ(0)

        segment_length_squared = segment.lengthSquared()

        if segment_length_squared <= 0.0001:
            distance = enemy_vector.length()
            return distance <= hit_radius

        projection = enemy_vector.dot(segment) / segment_length_squared
        projection = max(0.0, min(1.0, projection))

        closest_point = start_pos + segment * projection
        closest_point.setZ(0)

        enemy_pos.setZ(0)
        distance = (enemy_pos - closest_point).length()

        return distance <= hit_radius

    def respawn(self):
        if self.is_dead:
            return

        if self.respawn_callback is not None:
            self.start_pos, self.end_pos = self.respawn_callback()
        
        self.node.setPos(self.start_pos)
        self._recalculate_movement()

    def destroy(self):
        if self.is_dead:
            return

        self.is_dead = True
        self.node.removeNode()


class EnemyManager:

    def __init__(self, game):
        self.game = game
        self.enemies = []

    def spawn_dog(self, start_pos, end_pos, speed=4.0, scale=1.0, respawn_callback=None):
        dog = DogEnemy(
            game=self.game,
            start_pos=start_pos,
            end_pos=end_pos,
            speed=speed,
            scale=scale,
            respawn_callback=respawn_callback,
        )

        if not dog.is_dead:
            self.enemies.append(dog)

        return dog

    def spawn_dog_line(self, start_pos, end_pos, count=5, spacing=2.5, speed=4.0, scale=1.0):
        start = self._to_vec3(start_pos)
        end = self._to_vec3(end_pos)

        movement = end - start
        movement.setZ(0)

        if movement.length() <= 0.001:
            return

        movement.normalize()
        perpendicular = Vec3(-movement.y, movement.x, 0)
        first_offset = -((count - 1) * spacing) / 2

        for i in range(count):
            offset = perpendicular * (first_offset + i * spacing)
            dog_start = start + offset
            dog_end = end + offset

            self.spawn_dog(
                start_pos=dog_start,
                end_pos=dog_end,
                speed=speed,
                scale=scale,
            )

    def spawn_random_dogs_in_area(
        self,
        count=10,
        area_min_x=-50,
        area_max_x=50,
        area_min_y=-50,
        area_max_y=50,
        speed=4.0,
        scale=1.0,
        margin=2.0,
    ):
        for _ in range(count):
            callback = lambda: self._random_path_inside_area(
                area_min_x,
                area_max_x,
                area_min_y,
                area_max_y,
                margin,
            )
            start_pos, end_pos = callback()

            self.spawn_dog(
                start_pos=start_pos,
                end_pos=end_pos,
                speed=speed,
                scale=scale,
                respawn_callback=callback,
            )

    def _random_path_inside_area(self, min_x, max_x, min_y, max_y, margin):
        safe_min_x = min_x + margin
        safe_max_x = max_x - margin
        safe_min_y = min_y + margin
        safe_max_y = max_y - margin

        start = Vec3(
            random.uniform(safe_min_x, safe_max_x),
            random.uniform(safe_min_y, safe_max_y),
            0,
        )

        angle = random.uniform(0, math.tau)
        direction = Vec3(math.cos(angle), math.sin(angle), 0)

        end = self._ray_rectangle_intersection(
            start,
            direction,
            safe_min_x,
            safe_max_x,
            safe_min_y,
            safe_max_y,
        )

        return start, end

    def _ray_rectangle_intersection(self, start, direction, min_x, max_x, min_y, max_y):
        possible_t = []

        if abs(direction.x) > 0.0001:
            if direction.x > 0:
                possible_t.append((max_x - start.x) / direction.x)
            else:
                possible_t.append((min_x - start.x) / direction.x)

        if abs(direction.y) > 0.0001:
            if direction.y > 0:
                possible_t.append((max_y - start.y) / direction.y)
            else:
                possible_t.append((min_y - start.y) / direction.y)

        positive_t = [t for t in possible_t if t > 0]

        if not positive_t:
            return Vec3(start)

        t = min(positive_t)
        end = start + direction * t
        end.setZ(0)
        return end

    def kill_enemy(self, enemy):
        if enemy not in self.enemies:
            return False

        enemy.destroy()
        self.enemies.remove(enemy)
        return True

    def check_projectile_hit(self, start_pos, end_pos, hit_radius=1.5):
        for enemy in self.enemies[:]:
            if enemy.is_touched_by_segment(start_pos, end_pos, hit_radius):
                self.kill_enemy(enemy)
                return True

        return False

    def update(self, dt):
        for enemy in self.enemies[:]:
            enemy.update(dt)

            if enemy.is_dead and enemy in self.enemies:
                self.enemies.remove(enemy)

    def clear(self):
        for enemy in self.enemies[:]:
            enemy.destroy()
        self.enemies.clear()

    def _to_vec3(self, value):
        if isinstance(value, Vec3):
            return Vec3(value)
        return Vec3(value[0], value[1], value[2])