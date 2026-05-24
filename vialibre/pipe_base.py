from panda3d.core import Point3, Vec3


class PipeBase:
    MAX_HP = 25
    CONTACT_PADDING = 1.25
    FALLBACK_CONTACT_RADIUS = 3.0

    def __init__(self, game, map_collision=None):
        self.game = game
        self.map_collision = map_collision
        self.hp = self.MAX_HP
        self.bounds = self._find_pipe_bounds()

        if self.bounds is None:
            self.position = Point3(0, 0, 0)
        else:
            self.position = Point3(self.bounds["center"])

    def _find_pipe_bounds(self):
        if self.map_collision is None:
            return None
        if not hasattr(self.map_collision, "find_labeled_bounds"):
            return None
        return self.map_collision.find_labeled_bounds("tuyo", "tuyau", "tuyaux", "pipe")

    def get_position(self):
        return Point3(self.position)

    def is_touching(self, point):
        flat_point = Vec3(point.x, point.y, 0)

        if self.bounds is None:
            flat_base = Vec3(self.position.x, self.position.y, 0)
            return (flat_point - flat_base).length() <= self.FALLBACK_CONTACT_RADIUS

        return (
            self.bounds["min_x"] - self.CONTACT_PADDING
            <= flat_point.x
            <= self.bounds["max_x"] + self.CONTACT_PADDING
            and self.bounds["min_y"] - self.CONTACT_PADDING
            <= flat_point.y
            <= self.bounds["max_y"] + self.CONTACT_PADDING
        )

    def segment_enters(self, start, end):
        if self.is_touching(start) or self.is_touching(end):
            return True

        if self.bounds is None:
            center = Vec3(self.position.x, self.position.y, 0)
            sx, sy = start.x, start.y
            ex, ey = end.x, end.y
            dx = ex - sx
            dy = ey - sy
            length_sq = dx * dx + dy * dy
            if length_sq <= 0.000001:
                return False
            t = ((center.x - sx) * dx + (center.y - sy) * dy) / length_sq
            t = max(0.0, min(1.0, t))
            closest_x = sx + dx * t
            closest_y = sy + dy * t
            ox = center.x - closest_x
            oy = center.y - closest_y
            return ox * ox + oy * oy <= self.FALLBACK_CONTACT_RADIUS * self.FALLBACK_CONTACT_RADIUS

        min_x = self.bounds["min_x"] - self.CONTACT_PADDING
        max_x = self.bounds["max_x"] + self.CONTACT_PADDING
        min_y = self.bounds["min_y"] - self.CONTACT_PADDING
        max_y = self.bounds["max_y"] + self.CONTACT_PADDING
        return _segment_intersects_rect(start.x, start.y, end.x, end.y, min_x, max_x, min_y, max_y)

    def take_damage(self, amount=1):
        if self.hp <= 0:
            return False

        self.hp = max(0, self.hp - amount)
        self.game.messenger.send("pipe-hp-changed", [self.hp])

        if self.hp <= 0:
            self.game.messenger.send("pipe-destroyed")
            return True

        return False


def _segment_intersects_rect(sx, sy, ex, ey, min_x, max_x, min_y, max_y):
    t_min = 0.0
    t_max = 1.0
    dx = ex - sx
    dy = ey - sy

    for start, delta, low, high in ((sx, dx, min_x, max_x), (sy, dy, min_y, max_y)):
        if abs(delta) <= 0.000001:
            if start < low or start > high:
                return False
            continue

        inv_delta = 1.0 / delta
        t1 = (low - start) * inv_delta
        t2 = (high - start) * inv_delta
        if t1 > t2:
            t1, t2 = t2, t1

        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_min > t_max:
            return False

    return True
