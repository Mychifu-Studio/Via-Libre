from dataclasses import dataclass
from math import ceil, floor, sqrt

from panda3d.core import GeomVertexReader, MaterialAttrib, Point3, TextureAttrib, Vec3


@dataclass(frozen=True)
class CollisionTriangle:
    a: Vec3
    b: Vec3
    c: Vec3
    label: str

    @property
    def min_x(self):
        return min(self.a.x, self.b.x, self.c.x)

    @property
    def max_x(self):
        return max(self.a.x, self.b.x, self.c.x)

    @property
    def min_y(self):
        return min(self.a.y, self.b.y, self.c.y)

    @property
    def max_y(self):
        return max(self.a.y, self.b.y, self.c.y)

    @property
    def min_z(self):
        return min(self.a.z, self.b.z, self.c.z)

    @property
    def max_z(self):
        return max(self.a.z, self.b.z, self.c.z)

    def height_at(self, x, y):
        denominator = (
            (self.b.y - self.c.y) * (self.a.x - self.c.x)
            + (self.c.x - self.b.x) * (self.a.y - self.c.y)
        )
        if abs(denominator) <= 0.000001:
            return None

        u = (
            (self.b.y - self.c.y) * (x - self.c.x)
            + (self.c.x - self.b.x) * (y - self.c.y)
        ) / denominator
        v = (
            (self.c.y - self.a.y) * (x - self.c.x)
            + (self.a.x - self.c.x) * (y - self.c.y)
        ) / denominator
        w = 1.0 - u - v

        if u < -0.0001 or v < -0.0001 or w < -0.0001:
            return None
        return self.a.z * u + self.b.z * v + self.c.z * w

    def overlaps_circle(self, x, y, radius):
        if (
            x < self.min_x - radius
            or x > self.max_x + radius
            or y < self.min_y - radius
            or y > self.max_y + radius
        ):
            return False

        if self.height_at(x, y) is not None:
            return True

        radius_squared = radius * radius
        points = ((self.a.x, self.a.y), (self.b.x, self.b.y), (self.c.x, self.c.y))
        for px, py in points:
            if _distance_squared(x, y, px, py) <= radius_squared:
                return True

        return (
            _segment_distance_squared(x, y, points[0], points[1]) <= radius_squared
            or _segment_distance_squared(x, y, points[1], points[2]) <= radius_squared
            or _segment_distance_squared(x, y, points[2], points[0]) <= radius_squared
        )

    def has_walkable_slope(self, min_normal_z):
        normal = (self.b - self.a).cross(self.c - self.a)
        if normal.lengthSquared() <= 0.000001:
            return False
        normal.normalize()
        return abs(normal.z) >= min_normal_z


@dataclass(frozen=True)
class ResourceZoneDefinition:
    x: float
    y: float
    radius: float


class MapCollisionManager:
    COLLISION_FREE_REGIONS = (
        (-3.2, 3.2, -0.5, 9.5),  # Tablier du pont central.
    )
    WALKABLE_TERMS = ("ground", "path")
    DECORATIVE_TERMS = ("leaves", "leaf")
    RESOURCE_TERMS = ("minerai", "diamant", "diamond")
    CAMPFIRE_TERMS = ("fireplace", "campfire", "fire_place", "feu_de_camp", "charbon")
    BLOCKING_TERMS = (
        "wall",
        "walls",
        "mur",
        "muraille",
        "rock",
        "rocks",
        "tronc",
        "root",
        "portal",
        "frame",
        "tent",
        "chaise",
        "charbon",
        "tuyo",
    )

    def __init__(
        self,
        render,
        map_root,
        player_radius=0.55,
        max_step_height=0.55,
        min_walkable_height=-0.45,
        player_body_height=1.35,
        cell_size=3.0,
    ):
        self.render = render
        self.map_root = map_root
        self.player_radius = player_radius
        self.max_step_height = max_step_height
        self.min_walkable_height = min_walkable_height
        self.player_body_height = player_body_height
        self.cell_size = cell_size

        self.blocking_grid = {}
        self.walkable_grid = {}
        self.blocking_triangles = 0
        self.walkable_triangles = 0
        self.resource_points = []
        self._resource_point_cells = set()
        self.campfire_points = []
        self._campfire_point_cells = set()

        if self.map_root is not None and not self.map_root.isEmpty():
            self._load_from_model(self.map_root)

    def move(self, current_pos, desired_pos):
        current = Point3(current_pos)
        desired = Point3(desired_pos)
        desired.setZ(current.z)

        delta = desired - current
        flat_distance = Vec3(delta.x, delta.y, 0).length()
        if flat_distance <= 0.0001:
            return desired if self.is_position_allowed(desired) else current

        steps = max(1, int(ceil(flat_distance / (self.player_radius * 0.5))))
        step = delta / steps
        position = Point3(current)

        for _ in range(steps):
            next_pos = Point3(position + step)
            position = self._resolve_step(position, next_pos)

        return position

    def is_position_allowed(self, pos):
        if self._is_in_collision_free_region(pos):
            return True

        if self.walkable_triangles > 0 and not self._is_supported(pos):
            return False
        return not self._is_blocked(pos)

    def get_resource_zone_definitions(
        self,
        cluster_distance=3.0,
        radius_padding=1.25,
        min_radius=2.0,
        min_cluster_points=3,
    ):
        clusters = self._cluster_resource_points(cluster_distance)
        zones = []

        for cluster in clusters:
            if len(cluster) < min_cluster_points:
                continue

            min_x = min(point.x for point in cluster)
            max_x = max(point.x for point in cluster)
            min_y = min(point.y for point in cluster)
            max_y = max(point.y for point in cluster)
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0
            radius = max(
                sqrt(_distance_squared(center_x, center_y, point.x, point.y))
                for point in cluster
            )

            zones.append(
                ResourceZoneDefinition(
                    center_x,
                    center_y,
                    max(min_radius, radius + radius_padding),
                )
            )

        return sorted(zones, key=lambda zone: (zone.y, zone.x))

    def get_campfire_zone_definitions(
        self,
        cluster_distance=3.0,
        radius_padding=2.0,
        min_radius=3.5,
        min_cluster_points=2,
    ):
        clusters = self._cluster_points(self.campfire_points, cluster_distance)
        zones = []

        for cluster in clusters:
            if len(cluster) < min_cluster_points:
                continue

            min_x = min(point.x for point in cluster)
            max_x = max(point.x for point in cluster)
            min_y = min(point.y for point in cluster)
            max_y = max(point.y for point in cluster)
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0
            radius = max(
                sqrt(_distance_squared(center_x, center_y, point.x, point.y))
                for point in cluster
            )

            zones.append(
                ResourceZoneDefinition(
                    center_x,
                    center_y,
                    max(min_radius, radius + radius_padding),
                )
            )

        return sorted(zones, key=lambda zone: (zone.y, zone.x))

    def _is_in_collision_free_region(self, pos):
        for min_x, max_x, min_y, max_y in self.COLLISION_FREE_REGIONS:
            if min_x <= pos.x <= max_x and min_y <= pos.y <= max_y:
                return True
        return False

    def _resolve_step(self, current, desired):
        if self.is_position_allowed(desired):
            return desired

        x_only = Point3(desired.x, current.y, current.z)
        if self.is_position_allowed(x_only):
            return x_only

        y_only = Point3(current.x, desired.y, current.z)
        if self.is_position_allowed(y_only):
            return y_only

        return current

    def _load_from_model(self, model):
        for node_path in model.findAllMatches("**/+GeomNode"):
            geom_node = node_path.node()
            transform = node_path.getMat(self.render)

            for geom_index in range(geom_node.getNumGeoms()):
                geom = geom_node.getGeom(geom_index)
                state = geom_node.getGeomState(geom_index)
                category, label = self._classify_geom(state)
                if category == "ignore":
                    continue

                vertices = self._read_vertices(geom, transform)
                for primitive_index in range(geom.getNumPrimitives()):
                    primitive = geom.getPrimitive(primitive_index).decompose()
                    for tri_index in range(primitive.getNumPrimitives()):
                        start = primitive.getPrimitiveStart(tri_index)
                        end = primitive.getPrimitiveEnd(tri_index)
                        if end - start < 3:
                            continue

                        indices = [primitive.getVertex(i) for i in range(start, start + 3)]
                        triangle = CollisionTriangle(
                            vertices[indices[0]],
                            vertices[indices[1]],
                            vertices[indices[2]],
                            label,
                        )
                        self._store_triangle(triangle, category)

    def _read_vertices(self, geom, transform):
        reader = GeomVertexReader(geom.getVertexData(), "vertex")
        vertices = []
        while not reader.isAtEnd():
            vertices.append(transform.xformPoint(reader.getData3f()))
        return vertices

    def _store_triangle(self, triangle, category):
        if category == "resource":
            self._store_resource_point(triangle)
            category = "blocker"
        elif category == "campfire":
            self._store_campfire_point(triangle)
            category = "blocker"

        if category in ("walkable", "low_surface"):
            if not triangle.has_walkable_slope(0.35):
                if category == "walkable":
                    return
            elif category == "walkable" or (
                triangle.max_z <= self.max_step_height
                and triangle.min_z >= self.min_walkable_height
            ):
                self._add_to_grid(self.walkable_grid, triangle)
                self.walkable_triangles += 1
                return

            if category == "walkable":
                return

        if category == "water":
            return

        if (
            triangle.max_z >= self.max_step_height
            and triangle.min_z <= self.player_body_height
        ):
            self._add_to_grid(self.blocking_grid, triangle)
            self.blocking_triangles += 1

    def _classify_geom(self, state):
        labels, colors = self._read_state_labels(state)
        label_text = " ".join(labels).lower()

        if self._is_water_color(colors):
            return "water", label_text or "water"

        if any(term in label_text for term in self.WALKABLE_TERMS):
            return "walkable", label_text

        if any(term in label_text for term in self.RESOURCE_TERMS):
            return "resource", label_text

        if any(term in label_text for term in self.CAMPFIRE_TERMS):
            return "campfire", label_text

        if any(term in label_text for term in self.BLOCKING_TERMS):
            return "blocker", label_text

        if any(term in label_text for term in self.DECORATIVE_TERMS):
            return "ignore", label_text

        return "low_surface", label_text or "unknown"

    def _read_state_labels(self, state):
        labels = []
        colors = []

        material_attrib = state.getAttrib(MaterialAttrib)
        if material_attrib:
            material = material_attrib.getMaterial()
            if material is not None:
                if material.getName():
                    labels.append(material.getName())
                colors.append(material.getDiffuse())
                colors.append(material.getBaseColor())

        texture_attrib = state.getAttrib(TextureAttrib)
        if texture_attrib:
            for stage_index in range(texture_attrib.getNumOnStages()):
                stage = texture_attrib.getOnStage(stage_index)
                texture = texture_attrib.getOnTexture(stage)
                if stage.getName():
                    labels.append(stage.getName())
                if texture is not None and texture.getName():
                    labels.append(texture.getName())

        return labels, colors

    def _is_water_color(self, colors):
        for color in colors:
            red, green, blue = color.x, color.y, color.z
            if blue > 0.01 and blue > red * 2.0 and blue > green * 1.5:
                return True
        return False

    def _is_supported(self, pos):
        sample_radius = self.player_radius * 0.65
        samples = (
            (pos.x, pos.y),
            (pos.x + sample_radius, pos.y),
            (pos.x - sample_radius, pos.y),
            (pos.x, pos.y + sample_radius),
            (pos.x, pos.y - sample_radius),
        )

        return all(self._sample_has_walkable_surface(x, y) for x, y in samples)

    def _sample_has_walkable_surface(self, x, y):
        for triangle in self._triangles_near_point(self.walkable_grid, x, y, 0.0):
            height = triangle.height_at(x, y)
            if height is None:
                continue
            if self.min_walkable_height <= height <= self.max_step_height:
                return True
        return False

    def _is_blocked(self, pos):
        for triangle in self._triangles_near_point(
            self.blocking_grid, pos.x, pos.y, self.player_radius
        ):
            if triangle.overlaps_circle(pos.x, pos.y, self.player_radius):
                return True
        return False

    def _store_resource_point(self, triangle):
        center = Point3(
            (triangle.a.x + triangle.b.x + triangle.c.x) / 3.0,
            (triangle.a.y + triangle.b.y + triangle.c.y) / 3.0,
            0,
        )
        for point in (triangle.a, triangle.b, triangle.c, center):
            self._store_resource_sample(point)

    def _store_resource_sample(self, point):
        cell = (int(round(point.x * 2.0)), int(round(point.y * 2.0)))
        if cell in self._resource_point_cells:
            return

        self._resource_point_cells.add(cell)
        self.resource_points.append(Point3(point.x, point.y, 0))

    def _store_campfire_point(self, triangle):
        center = Point3(
            (triangle.a.x + triangle.b.x + triangle.c.x) / 3.0,
            (triangle.a.y + triangle.b.y + triangle.c.y) / 3.0,
            0,
        )
        for point in (triangle.a, triangle.b, triangle.c, center):
            self._store_campfire_sample(point)

    def _store_campfire_sample(self, point):
        cell = (int(round(point.x * 2.0)), int(round(point.y * 2.0)))
        if cell in self._campfire_point_cells:
            return

        self._campfire_point_cells.add(cell)
        self.campfire_points.append(Point3(point.x, point.y, 0))

    def _cluster_resource_points(self, cluster_distance):
        return self._cluster_points(self.resource_points, cluster_distance)

    def _cluster_points(self, points, cluster_distance):
        points = sorted(points, key=lambda point: (point.x, point.y))
        if not points:
            return []

        parents = list(range(len(points)))
        max_distance_squared = cluster_distance * cluster_distance

        def find(index):
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        def union(left, right):
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parents[right_root] = left_root

        for left_index, left_point in enumerate(points):
            for right_index in range(left_index + 1, len(points)):
                right_point = points[right_index]
                x_distance = right_point.x - left_point.x
                if x_distance * x_distance > max_distance_squared:
                    break

                if (
                    _distance_squared(
                        left_point.x,
                        left_point.y,
                        right_point.x,
                        right_point.y,
                    )
                    <= max_distance_squared
                ):
                    union(left_index, right_index)

        clusters_by_root = {}
        for index, point in enumerate(points):
            clusters_by_root.setdefault(find(index), []).append(point)

        return sorted(
            clusters_by_root.values(),
            key=lambda cluster: (
                min(point.y for point in cluster),
                min(point.x for point in cluster),
            ),
        )

    def _add_to_grid(self, grid, triangle):
        min_cell_x = int(floor(triangle.min_x / self.cell_size))
        max_cell_x = int(floor(triangle.max_x / self.cell_size))
        min_cell_y = int(floor(triangle.min_y / self.cell_size))
        max_cell_y = int(floor(triangle.max_y / self.cell_size))

        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1):
                grid.setdefault((cell_x, cell_y), []).append(triangle)

    def _triangles_near_point(self, grid, x, y, radius):
        min_cell_x = int(floor((x - radius) / self.cell_size))
        max_cell_x = int(floor((x + radius) / self.cell_size))
        min_cell_y = int(floor((y - radius) / self.cell_size))
        max_cell_y = int(floor((y + radius) / self.cell_size))
        seen = set()

        for cell_x in range(min_cell_x, max_cell_x + 1):
            for cell_y in range(min_cell_y, max_cell_y + 1):
                for triangle in grid.get((cell_x, cell_y), ()):
                    identity = id(triangle)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    yield triangle


def _distance_squared(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def _segment_distance_squared(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    length_squared = dx * dx + dy * dy
    if length_squared <= 0.000001:
        return _distance_squared(px, py, ax, ay)

    t = ((px - ax) * dx + (py - ay) * dy) / length_squared
    t = max(0.0, min(1.0, t))
    closest_x = ax + dx * t
    closest_y = ay + dy * t
    return _distance_squared(px, py, closest_x, closest_y)
