# construction.py
import math
from dataclasses import dataclass

from panda3d.core import TransparencyAttrib, Vec3, Point3, Plane, NodePath
from panda3d.core import CollisionNode, CollisionBox, TextNode
from panda3d.core import LineSegs
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval, Func, Wait
from direct.showbase.DirectObject import DirectObject

from vialibre.radialMenu import RadialMenu
from panda3d.core import BillboardEffect


@dataclass(frozen=True)
class TurretConfig:
    key: str
    display_name: str
    cost: int
    damage: int
    static_model: str
    moving_model: str
    ammo_model: str
    menu_icon: str
    activation_radius: float
    fire_rate: float
    hit_radius: float
    area_radius: float
    projectile_speed: float
    ammo_scale: float = 1.0
    turret_scale: float = 1.0
    heading_offset: float = 180.0
    impact_color: tuple[float, float, float, float] = (1.0, 0.8, 0.2, 1.0)


DEFAULT_TURRET_TYPE = "canon"
TURRET_CONFIGS = {
    "canon": TurretConfig(
        key="canon",
        display_name="Canon",
        cost=15,
        damage=2,
        static_model="./assets/Turrets/Canon_static.bam",
        moving_model="./assets/Turrets/Canon_moving.bam",
        ammo_model="./assets/Turrets/Canon_ammo.bam",
        menu_icon="./assets/Turrets/canon.png",
        activation_radius=15.0,
        fire_rate=1.0,
        hit_radius=1.0,
        area_radius=0.0,
        projectile_speed=85.0,
        ammo_scale=1.0,
        turret_scale=0.75,
        impact_color=(1.0, 0.74, 0.22, 1.0),
    ),
    "tesla": TurretConfig(
        key="tesla",
        display_name="Tesla",
        cost=35,
        damage=1,
        static_model="./assets/Turrets/Tesla_static.bam",
        moving_model="./assets/Turrets/Tesla_moving.bam",
        ammo_model="./assets/Turrets/Tesla_ammo.bam",
        menu_icon="./assets/Turrets/tesla.png",
        activation_radius=14.0,
        fire_rate=0.35,
        hit_radius=0.7,
        area_radius=0.7,
        projectile_speed=130.0,
        ammo_scale=0.5,
        turret_scale=0.45,
        impact_color=(0.35, 0.85, 1.0, 1.0),
    ),
    "bomb": TurretConfig(
        key="bomb",
        display_name="Bomb",
        cost=75,
        damage=7,
        static_model="./assets/Turrets/Bomb_static.bam",
        moving_model="./assets/Turrets/Bomb_moving.bam",
        ammo_model="./assets/Turrets/Bomb_ammo.bam",
        menu_icon="./assets/Turrets/bomb.png",
        activation_radius=13.0,
        fire_rate=2.2,
        hit_radius=0.8,
        area_radius=1.4,
        projectile_speed=65.0,
        ammo_scale=1.0,
        turret_scale=0.5,
        impact_color=(1.0, 0.35, 0.12, 1.0),
    ),
}
RADIAL_TURRET_ORDER = ("canon", "tesla", "bomb")


def get_turret_config(turret_type):
    key = str(turret_type or DEFAULT_TURRET_TYPE).strip().lower()
    return TURRET_CONFIGS.get(key, TURRET_CONFIGS[DEFAULT_TURRET_TYPE])


def _safe_tight_bounds(node):
    bounds = node.getTightBounds()
    if bounds is None or bounds[0] is None or bounds[1] is None:
        return Point3(-0.5, -0.5, 0.0), Point3(0.5, 0.5, 1.5)
    return bounds


def load_turret(base, np, turret_config=None):
    config = turret_config or get_turret_config(DEFAULT_TURRET_TYPE)
    root = np.attachNewNode(f"{config.key}_turret")
    moving_pivot = root.attachNewNode(f"{config.key}_moving_pivot")

    static_model = NodePath()
    moving_model = NodePath()

    try:
        static_model = base.loader.loadModel(config.static_model)
        static_model.reparentTo(root)
    except Exception as e:
        print(f"Erreur de chargement {config.static_model} : {e}")

    try:
        moving_model = base.loader.loadModel(config.moving_model)
        moving_model.reparentTo(moving_pivot)
    except Exception as e:
        print(f"Erreur de chargement {config.moving_model} : {e}")

    root.setScale(config.turret_scale)

    root.setPythonTag("turret_aim_node", moving_pivot)
    root.setPythonTag("turret_static_node", static_model)
    root.setPythonTag("turret_moving_node", moving_model)
    return root


def load_hologram(base, np):
    pivot = base.render.attachNewNode("hologram_pivot")

    try:
        model = base.loader.loadModel("./assets/arrow.bam")
        model.setScale(0.1)
        model.reparentTo(pivot)

        min_bounds, max_bounds = model.getTightBounds()
        center = (min_bounds + max_bounds) / 2.0

        tweak_x = 0.0
        tweak_y = -0.4
        tweak_z = 0.0

        model.setPos(-center[0] + tweak_x, -center[1] + tweak_y, -center[2] + tweak_z)
        pivot.setHpr(0, -90, 0)

    except Exception as e:
        print(f"Erreur de chargement : {e}")

    pivot.setPos(0, 0, 0)
    pivot.reparentTo(np)

    return pivot


class FloatingUI:
    """SRP: Gère uniquement la création et l'affichage d'un texte flottant en 3D."""
    def __init__(self, base, parent_node, text):
        self.text_node = TextNode('ui_floating')
        self.text_node.setText(text)
        self.text_node.setTextColor(1, 0.2, 0.2, 1)
        self.text_node.setAlign(TextNode.ACenter)
        self.text_node.setCardColor(0, 0, 0, 0.7)
        self.text_node.setCardAsMargin(0.2, 0.2, 0.1, 0.1)
        self.text_node.setCardDecal(True)

        self.ui_np = parent_node.attachNewNode(self.text_node)
        self.ui_np.setScale(0.25)
        self.ui_np.setPos(0, 0, 1)
        self.ui_np.setBillboardPointEye()
        self.ui_np.hide()

        self.ui_np.setDepthTest(False)
        self.ui_np.setDepthWrite(False)
        self.ui_np.setBin("fixed", 0)

    def show(self):
        self.ui_np.show()

    def hide(self):
        self.ui_np.hide()


class Structure:
    """SRP: Gère la représentation d'une structure placée dans le monde et son comportement."""
    def __init__(self, base, position, rotation, on_destroy_callback, enemy_manager=None, struct_id=None, turret_type=DEFAULT_TURRET_TYPE):
        self.base = base
        self.id = struct_id or f"struct_{id(self)}"
        self.on_destroy_callback = on_destroy_callback
        self.enemy_manager = enemy_manager
        self.config = get_turret_config(turret_type)
        self.turret_type = self.config.key
        self.is_destroyed = False

        parent = getattr(self.base, "structure_root", self.base.render)
        self.np = NodePath("structure_root")
        self.np.reparentTo(parent)
        self.np.setPos(position)
        self.np.setHpr(rotation)

        self.model = load_turret(self.base, self.np, self.config)
        self.aim_node = self.model.getPythonTag("turret_aim_node")

        min_point, max_point = _safe_tight_bounds(self.model)
        c_box = CollisionBox(min_point, max_point)
        col_node = CollisionNode('structure_col')
        col_node.addSolid(c_box)

        self.col_np = self.np.attachNewNode(col_node)
        self.col_np.setPythonTag("structure", self)

        self.ui = FloatingUI(self.base, self.np, "Supprimer [Clic]")

        self.activation_radius = self.config.activation_radius
        self.fire_rate = self.config.fire_rate
        self.damage = self.config.damage
        self.hit_radius = self.config.hit_radius
        self.area_radius = self.config.area_radius
        self.time_since_last_shot = 0.0

        self.targeting_mode = "closest"

        self.offset_turret = Vec3(0, 0, 0.5)
        self.offset_enemies = Vec3(0, 0, 0)

        self.task_name = f"turret_update_{id(self)}"
        self.base.taskMgr.add(self.update_task, self.task_name)

    def _is_host_authority(self):
        net_iface = getattr(self.base, 'network', None)
        if net_iface is None or getattr(net_iface, 'net', None) is None:
            return True
        return net_iface.net.is_host

    def _create_fallback_tracer(self, start_pos, target_pos):
        lines = LineSegs()
        lines.setThickness(4.0)
        lines.setColor(*self.config.impact_color)

        direction = target_pos - start_pos
        distance = direction.length()
        if distance < 0.1:
            return

        direction.normalize()
        tracer_length = min(1.5, distance)

        lines.moveTo(0, 0, 0)
        lines.drawTo(direction * tracer_length)

        tracer_np = self.base.render.attachNewNode(lines.create())
        tracer_np.setPos(start_pos)
        tracer_np.setLightOff()

        duration = max(0.03, distance / self.config.projectile_speed)
        Sequence(
            LerpPosInterval(tracer_np, duration, target_pos, startPos=start_pos),
            Func(tracer_np.removeNode),
        ).start()

    def _create_area_impact_effect(self, target_pos):
        if self.area_radius <= 0:
            return

        lines = LineSegs()
        lines.setThickness(2.0)
        lines.setColor(*self.config.impact_color)

        segments = 28
        for i in range(segments + 1):
            angle = (math.tau * i) / segments
            point = Vec3(
                math.cos(angle) * self.area_radius,
                math.sin(angle) * self.area_radius,
                0.05,
            )
            if i == 0:
                lines.moveTo(point)
            else:
                lines.drawTo(point)

        ring_np = self.base.render.attachNewNode(lines.create())
        ring_np.setPos(target_pos)
        ring_np.setLightOff()
        Sequence(Wait(0.18), Func(ring_np.removeNode)).start()

    def create_projectile_effect(self, start_pos, target_pos):
        direction = target_pos - start_pos
        distance = direction.length()
        if distance < 0.1:
            return

        duration = max(0.03, distance / self.config.projectile_speed)
        projectile_np = None

        try:
            projectile_np = self.base.loader.loadModel(self.config.ammo_model)
        except Exception as e:
            print(f"Erreur de chargement {self.config.ammo_model} : {e}")

        if projectile_np is None or projectile_np.isEmpty():
            self._create_fallback_tracer(start_pos, target_pos)
        else:
            projectile_np.reparentTo(self.base.render)
            projectile_np.setPos(start_pos)
            projectile_np.setScale(self.config.ammo_scale)
            projectile_np.lookAt(target_pos)
            projectile_np.setLightOff()

            Sequence(
                LerpPosInterval(projectile_np, duration, target_pos, startPos=start_pos),
                Func(projectile_np.removeNode),
            ).start()

        if self.area_radius > 0:
            Sequence(Wait(duration), Func(self._create_area_impact_effect, target_pos)).start()

        self.base.sound.play("turret")
        self.base.sound.play("turret_reload")

    def create_tracer_effect(self, start_pos, target_pos):
        self.create_projectile_effect(start_pos, target_pos)

    def _aim_at(self, enemy_pos):
        if self.aim_node is None or self.aim_node.isEmpty():
            return

        pivot_pos = self.aim_node.getPos(self.base.render)
        dx = enemy_pos.x - pivot_pos.x
        dy = enemy_pos.y - pivot_pos.y
        if dx * dx + dy * dy <= 0.0001:
            return

        world_heading = math.degrees(math.atan2(-dx, dy))
        parent_heading = self.aim_node.getParent().getH(self.base.render)
        self.aim_node.setH(world_heading - parent_heading + self.config.heading_offset)
        self.aim_node.setP(0)
        self.aim_node.setR(0)

    def _apply_turret_damage(self, start_pos, target_pos):
        if self.area_radius > 0 and hasattr(self.enemy_manager, "damage_enemies_in_radius"):
            return self.enemy_manager.damage_enemies_in_radius(
                target_pos,
                self.area_radius,
                damage=self.damage,
            )

        return self.enemy_manager.check_projectile_hit(
            start_pos,
            target_pos,
            hit_radius=self.hit_radius,
            damage=self.damage,
        )

    def update_task(self, task):
        dt = task.time - getattr(task, 'last_time', task.time)
        task.last_time = task.time

        if not self._is_host_authority():
            return task.cont

        if not self.enemy_manager or not self.enemy_manager.enemies:
            return task.cont

        my_pos = self.np.getPos(self.base.render)

        best_enemy = None
        best_distance_sq = None
        best_key = None
        radius_sq = self.activation_radius * self.activation_radius
        enemy_iter = self.enemy_manager.enemies
        if hasattr(self.enemy_manager, "iter_enemies_in_radius"):
            enemy_iter = self.enemy_manager.iter_enemies_in_radius(my_pos, self.activation_radius)

        for enemy in enemy_iter:
            if enemy.is_dead:
                continue
            enemy_pos = enemy.node.getPos(self.base.render)
            dx = enemy_pos.x - my_pos.x
            dy = enemy_pos.y - my_pos.y
            dist_sq = dx * dx + dy * dy

            if dist_sq > radius_sq:
                continue

            if self.targeting_mode == "lowest_hp":
                key = (enemy.hp, dist_sq)
            else:
                key = (dist_sq,)

            if best_key is None or key < best_key:
                best_key = key
                best_enemy = enemy
                best_distance_sq = dist_sq

        if best_enemy is None:
            return task.cont

        target_enemy = best_enemy
        min_dist = best_distance_sq if best_distance_sq is not None else 0.0
        enemy_pos = target_enemy.node.getPos(self.base.render)

        if min_dist > 0.01:
            self._aim_at(enemy_pos)

        self.time_since_last_shot += dt
        if self.time_since_last_shot >= self.fire_rate:
            self.time_since_last_shot = 0.0

            start_pos_visuel = Point3(my_pos.x, my_pos.y, my_pos.z + 1.2) + self.offset_turret
            target_pos_visuel = Point3(enemy_pos.x, enemy_pos.y, enemy_pos.z + 0.5) + self.offset_enemies

            self.create_projectile_effect(start_pos_visuel, target_pos_visuel)
            self._apply_turret_damage(my_pos, enemy_pos)

            if getattr(self.base, 'network', None) and getattr(self.base.network, 'net', None) and self.base.network.net.is_host:
                self.base.network.net.broadcast_msg('turret_shoot', {
                    'struct_id': self.id,
                    'turret_type': self.turret_type,
                    'start_pos': {'x': start_pos_visuel.x, 'y': start_pos_visuel.y, 'z': start_pos_visuel.z},
                    'target_pos': {'x': target_pos_visuel.x, 'y': target_pos_visuel.y, 'z': target_pos_visuel.z}
                })

        return task.cont

    def detruire(self):
        if self.is_destroyed:
            return
        self.is_destroyed = True

        # Nettoyer la tâche lorsqu'on supprime la tourelle
        self.base.taskMgr.remove(self.task_name)
        self.np.removeNode()
        if self.on_destroy_callback:
            self.on_destroy_callback(self)

    def surligner(self):
        self.model.setColorScale(1.5, 0.5, 0.5, 1.0)

    def retirer_surlignage(self):
        self.model.clearColorScale()


class Hologram:
    """SRP: Gère exclusivement l'affichage du fantôme de construction."""
    def __init__(self, base):
        self.base = base
        self.np = NodePath("hologramme_root")
        self.np.reparentTo(self.base.render)

        self.model = load_hologram(self.base, self.np)

        self.np.setTransparency(TransparencyAttrib.MAlpha)
        self.np.setColorScale(0.2, 0.5, 1.0, 0.5)
        self.np.hide()

    def show(self):
        self.np.show()

    def hide(self):
        self.np.hide()

    def get_pos(self):
        return self.np.getPos(self.base.render)

    def get_hpr(self):
        return self.np.getHpr(self.base.render)

    def update_transform(self, pos, hpr):
        self.np.setPos(pos)
        self.np.setHpr(hpr)


class BuildManager(DirectObject):
    def __init__(self, showbase, player_root, camera, mouse):
        super().__init__()
        self.base = showbase
        self.player_root = player_root
        self.camera = camera
        self.mouse = mouse
        self.enemy_manager = getattr(self.base, "enemies", None)

        self.mode_actif = False
        self.distance_construction = 2.5
        self.distance_min = 1
        self.rayon_max_construction = 5

        self.plan_sol = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
        self.structures = []
        self.structure_root = self._ensure_structure_root()
        self.hologramme = Hologram(self.base)

        self.locked_build_pos = None
        self.locked_build_hpr = None

        self.radial_menu = RadialMenu(
            base=self.base,
            mouse=self.mouse,
            name="Tourelles",
            options=[
                (f"{TURRET_CONFIGS[key].cost} Ressources", TURRET_CONFIGS[key].menu_icon)
                for key in RADIAL_TURRET_ORDER
            ],
            open_event="mouse1",
            close_event="mouse1-up",
            bind_events=False,
            on_select=self.on_radial_select,
            on_cancel=self.on_radial_cancel
        )

    def _turret_type_for_index(self, index):
        if index < 0 or index >= len(RADIAL_TURRET_ORDER):
            return DEFAULT_TURRET_TYPE
        return RADIAL_TURRET_ORDER[index]

    def _ensure_structure_root(self):
        root = getattr(self.base, "structure_root", None)
        if root is None or root.isEmpty():
            root = self.base.render.attachNewNode("structure_collision_root")
            self.base.structure_root = root
        return root

    def _show_message(self, message):
        popup_ui = getattr(self.base, "popup_ui", None)
        if popup_ui is not None and hasattr(popup_ui, "show_popup"):
            popup_ui.show_popup(message)
        else:
            print(message)

    def ouvrir_menu_construction(self):
        if not self.mode_actif or self.radial_menu.is_open:
            return

        self.locked_build_pos = Point3(self.hologramme.get_pos())
        self.locked_build_hpr = Vec3(self.hologramme.get_hpr())
        self.radial_menu.open_menu()

    def fermer_menu_construction(self):
        if not self.radial_menu.is_open:
            return

        self.radial_menu.close_menu()
        self.locked_build_pos = None
        self.locked_build_hpr = None

    def basculer_mode(self):
        if not getattr(self.base, "game_started", True):
            return

        self.mode_actif = not self.mode_actif
        self.camera.setZoomLock(self.mode_actif)
        if self.mode_actif:
            self.hologramme.show()
            self.accept("mouse1", self.ouvrir_menu_construction)
            self.accept("mouse1-up", self.fermer_menu_construction)
        else:
            self.hologramme.hide()
            self.ignore("mouse1")
            self.ignore("mouse1-up")
            if self.radial_menu.is_open:
                self.fermer_menu_construction()

    def on_radial_select(self, index, option):
        if not getattr(self.base, "game_started", True):
            return

        if not self.mode_actif:
            return

        turret_type = self._turret_type_for_index(index)
        turret_config = get_turret_config(turret_type)

        if self.base.inventory["ressource"] < turret_config.cost:
            self._show_message("Ressources insuffisantes !")
            self.basculer_mode()
            return

        pos = self.locked_build_pos if self.locked_build_pos is not None else self.hologramme.get_pos()
        hpr = self.locked_build_hpr if self.locked_build_hpr is not None else self.hologramme.get_hpr()

        net_iface = getattr(self.base, 'network', None)
        is_client = net_iface is not None and getattr(net_iface, 'net', None) is not None and not net_iface.net.is_host

        if is_client:
            net_iface.net.send_msg('build_request', {
                'x': pos.x, 'y': pos.y, 'z': pos.z,
                'h': hpr.x, 'p': hpr.y, 'r': hpr.z,
                'turret_type': turret_type,
            })
        else:
            self.host_create_structure(pos, hpr, turret_type=turret_type)

        self.basculer_mode()

    def host_create_structure(self, pos, hpr, struct_id=None, turret_type=DEFAULT_TURRET_TYPE):
        turret_config = get_turret_config(turret_type)
        if self.base.inventory["ressource"] < turret_config.cost:
            return False

        nouvelle_structure = Structure(
            self.base, pos, hpr,
            self._on_structure_detruite,
            self.enemy_manager,
            struct_id=struct_id,
            turret_type=turret_config.key,
        )
        self.structures.append(nouvelle_structure)
        self.base.inventory["ressource"] -= turret_config.cost

        if hasattr(self.base, 'inventory_ui'):
            self.base.inventory_ui.update()

        net_iface = getattr(self.base, 'network', None)
        if net_iface is not None and getattr(net_iface, 'net', None) is not None and net_iface.net.is_host:
            net_iface._broadcast_snapshot(force=True)

        return True

    def request_destroy_structure(self, structure):
        if structure is None:
            return False

        net_iface = getattr(self.base, 'network', None)
        is_client = net_iface is not None and getattr(net_iface, 'net', None) is not None and not net_iface.net.is_host

        if is_client:
            net_iface.net.send_msg('destroy_structure_request', {'struct_id': structure.id})
            return True

        return self.host_destroy_structure(structure.id)

    def host_destroy_structure(self, struct_id):
        if not struct_id:
            return False

        structure = next((s for s in self.structures if getattr(s, 'id', None) == struct_id), None)
        if structure is None:
            return False

        structure.detruire()

        net_iface = getattr(self.base, 'network', None)
        if net_iface is not None and getattr(net_iface, 'net', None) is not None and net_iface.net.is_host:
            net_iface._broadcast_snapshot(force=True)

        return True

    def sync_from_snapshot(self, structures_data):
        known_ids = set()

        for s_data in structures_data:
            sid = s_data['id']
            known_ids.add(sid)
            turret_type = get_turret_config(s_data.get('turret_type', DEFAULT_TURRET_TYPE)).key
            existing = next((s for s in self.structures if s.id == sid), None)

            if existing and getattr(existing, "turret_type", DEFAULT_TURRET_TYPE) != turret_type:
                existing.detruire()
                existing = None

            if existing:
                existing.np.setPos(s_data['x'], s_data['y'], s_data['z'])
                existing.np.setHpr(s_data.get('h', 0.0), s_data.get('p', 0.0), s_data.get('r', 0.0))
            else:
                struct = Structure(
                    self.base,
                    Point3(s_data['x'], s_data['y'], s_data['z']),
                    Vec3(s_data['h'], s_data['p'], s_data['r']),
                    self._on_structure_detruite,
                    self.enemy_manager,
                    struct_id=sid,
                    turret_type=turret_type,
                )
                self.structures.append(struct)

        for struct in list(self.structures):
            if struct.id not in known_ids:
                struct.detruire()

    def on_radial_cancel(self):
        pass

    def _on_structure_detruite(self, structure):
        if structure in self.structures:
            self.structures.remove(structure)

    def clear_structures(self):
        if self.radial_menu.is_open:
            self.fermer_menu_construction()

        self.mode_actif = False
        self.locked_build_pos = None
        self.locked_build_hpr = None
        self.camera.setZoomLock(False)
        self.hologramme.hide()
        self.ignore("mouse1")
        self.ignore("mouse1-up")

        for structure in list(self.structures):
            structure.detruire()
        self.structures.clear()

    def contraindre_distance(self, position_cible):
        pos_joueur = self.player_root.getPos(self.base.render)
        pos_joueur.setZ(0)
        vecteur_diff = position_cible - pos_joueur
        distance_actuelle = vecteur_diff.length()

        if distance_actuelle > self.rayon_max_construction:
            vecteur_diff.normalize()
            return pos_joueur + (vecteur_diff * self.rayon_max_construction)
        elif distance_actuelle < self.distance_min:
            if distance_actuelle > 0.001:
                vecteur_diff.normalize()
            else:
                vecteur_diff = self.base.render.getRelativeVector(self.base.camera, Vec3(0, 1, 0))
                vecteur_diff.setZ(0)
                vecteur_diff.normalize()
            return pos_joueur + (vecteur_diff * self.distance_min)

        return position_cible

    def update(self):
        if not self.mode_actif or self.radial_menu.is_open:
            return

        mouse_watcher = getattr(self.base, "mouseWatcherNode", None)
        if mouse_watcher is not None and mouse_watcher.hasMouse():
            mpos = mouse_watcher.getMouse()
            p1, p2 = Point3(), Point3()
            self.base.camLens.extrude(mpos, p1, p2)

            p1_global = self.base.render.getRelativePoint(self.base.camera, p1)
            p2_global = self.base.render.getRelativePoint(self.base.camera, p2)

            point_intersection = Point3()
            if self.plan_sol.intersectsLine(point_intersection, p1_global, p2_global):
                position_restreinte = self.contraindre_distance(point_intersection)

                self.hologramme.np.setPos(position_restreinte)
                self.hologramme.np.lookAt(self.base.camera)
                heading = self.hologramme.np.getH() + 90

                self.hologramme.update_transform(position_restreinte, (heading, 0, 0))