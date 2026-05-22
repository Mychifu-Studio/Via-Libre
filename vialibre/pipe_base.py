from panda3d.core import Point3, Vec3


class PipeBase:
    MAX_HP = 20
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

    def take_damage(self, amount=1):
        if self.hp <= 0:
            return False

        self.hp = max(0, self.hp - amount)
        self.game.messenger.send("pipe-hp-changed", [self.hp])

        if self.hp <= 0:
            self.game.messenger.send("pipe-destroyed")
            return True

        return False
