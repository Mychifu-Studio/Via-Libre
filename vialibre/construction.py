# construction.py
from panda3d.core import TransparencyAttrib, Vec3, Point3, Plane, NodePath
from panda3d.core import CollisionNode, CollisionBox, TextNode
from panda3d.core import LineSegs
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval, Func
from direct.showbase.DirectObject import DirectObject

from vialibre.radialMenu import RadialMenu

# ============================================================
# ORDRE DU MENU RADIAL
# index 0 = haut   = canon
# index 1 = droite = tesla
# index 2 = bas    = barbz
# index 3 = gauche = bomb
# ============================================================
TURRET_ORDER = ["canon", "tesla", "barbz", "bomb"]

# ============================================================
# REGLAGES GLOBAUX DES TOURELLES
#
# LES VARIABLES LES PLUS IMPORTANTES A AJUSTER SONT :
# - static_scale
# - static_offset
# - moving_scale
# - moving_offset
# - ammo_scale
# - ammo_offset
# - moving_pivot_offset
# - ammo_spawn_offset
# - turret_h_offset
#
# Si une pièce est mal placée :
# - trop à droite/gauche : change X
# - trop devant/derrière : change Y
# - trop haut/bas : change Z
#
# Si une pièce est trop grande/petite :
# - change *_scale
# ============================================================
TURRET_CONFIGS = {
    "canon": {
        "cost": 1,
        "activation_radius": 15.0,
        "fire_rate": 1.0,
        "targeting_mode": "lowest_hp",
        "damage_radius": 1.0,
        "tracer_color": (1.0, 0.8, 0.2, 1.0),
        "tracer_thickness": 4.0,

        # Si la partie mobile regarde dans le mauvais sens, change ici
        "turret_h_offset": 180,

        # ----------------------------
        # REGLAGES VISUELS A AJUSTER
        # ----------------------------

        # Scale de la base fixe
        "static_scale": 1.0,
        # Offset de la base fixe
        "static_offset": (0.0, 0.0, 1.0),

        # Position du pivot de rotation par rapport à la base
        "moving_pivot_offset": (0.0, 0.0, 0.5),

        # Scale de la partie qui tourne
        "moving_scale": 1.0,
        # Offset de la partie qui tourne PAR RAPPORT A SON PIVOT
        "moving_offset": (0.0, 0, 0.5),

        # Position d'où part la munition
        "ammo_spawn_offset": (0.0, 0.8, 0.5),

        # Scale de la munition
        "ammo_scale": 1.0,
        # Offset visuel de la munition sur son spawn
        "ammo_offset": (0.0, 0.0, 0.0),
    },

    "tesla": {
        "cost": 1,
        "activation_radius": 13.0,
        "fire_rate": 0.15,
        "targeting_mode": "closest",
        "damage_radius": 5.0,
        "tracer_color": (0.35, 0.8, 1.0, 1.0),
        "tracer_thickness": 1.0,
        "turret_h_offset": 180,

        "static_scale": 0.5,
        "static_offset": (0.0, 0.0, 1.5),

        "moving_pivot_offset": (0.0, 0.0, 0.0),
        "moving_scale": 0.5,
        "moving_offset": (0.0, 0.0, 2),

        "ammo_spawn_offset": (0.0, 0.8, 0.5),
        "ammo_scale": 0.05,
        "ammo_offset": (0.0, 0.0, 0.0),
    },

    "barbz": {
        "cost": 5,
        "activation_radius": 16.0,
        "fire_rate": 0.8,
        "targeting_mode": "lowest_hp",
        "damage_radius": 1.2,
        "tracer_color": (1.0, 0.25, 0.25, 1.0),
        "tracer_thickness": 4.5,
        "turret_h_offset": 180,

        "static_scale": 1.0,
        "static_offset": (0.0, 0.0, 0.0),

        "moving_pivot_offset": (0.0, 0.0, 0.0),
        "moving_scale": 1.0,
        "moving_offset": (0.0, 0.0, 0.0),

        "ammo_spawn_offset": (0.0, 0.8, 0.5),
        "ammo_scale": 1.0,
        "ammo_offset": (0.0, 0.0, 0.0),
    },

    "bomb": {
        "cost": 1,
        "activation_radius": 17.0,
        "fire_rate": 1.9,
        "targeting_mode": "closest",
        "damage_radius": 7,
        "tracer_color": (1.0, 0.55, 0.15, 1.0),
        "tracer_thickness": 6.0,
        "turret_h_offset": 0,

        "static_scale": 0.6,
        "static_offset": (0.0, 0.0, 1.5),

        "moving_pivot_offset": (0.0, 0.0, 0.0),
        "moving_scale": 0.6,
        "moving_offset": (0.0, 0.0, 3),

        "ammo_spawn_offset": (0.0, 0.8, 0.5),
        "ammo_scale": 1.0,
        "ammo_offset": (0.0, 0.0, 0.0),
    },
}


def center_model_on_pivot(model, tweak_x=0.0, tweak_y=0.0, tweak_z=0.0):
    min_bounds, max_bounds = model.getTightBounds()
    center = (min_bounds + max_bounds) / 2.0
    model.setPos(
        -center[0] + tweak_x,
        -center[1] + tweak_y,
        -center[2] + tweak_z
    )


def apply_model_transform(model, scale=1.0, offset=(0.0, 0.0, 0.0)):
    # IMPORTANT :
    # On scale le modèle visible, PAS le parent pivot.
    # Sinon les offsets hérités deviennent vite faux.
    model.setScale(scale)
    center_model_on_pivot(model, offset[0], offset[1], offset[2])


def load_turret(base, np, turret_type="canon"):
    config = TURRET_CONFIGS[turret_type]

    turret_root = np.attachNewNode(f"{turret_type}_root")

    # Partie fixe
    static_root = turret_root.attachNewNode(f"{turret_type}_static_root")
    static_root.setPos(0, 0, 0)

    # Pivot de rotation de la partie mobile
    moving_pivot = turret_root.attachNewNode(f"{turret_type}_moving_pivot")
    moving_pivot.setPos(*config["moving_pivot_offset"])

    # Point d'apparition de la munition
    ammo_spawn = moving_pivot.attachNewNode(f"{turret_type}_ammo_spawn")
    ammo_spawn.setPos(*config["ammo_spawn_offset"])

    static_model = None
    moving_model = None
    ammo_model = None

    try:
        static_model = base.loader.loadModel(f"./assets/Turrets/{turret_type}_static.bam")
        static_model.reparentTo(static_root)
        apply_model_transform(
            static_model,
            scale=config["static_scale"],
            offset=config["static_offset"],
        )
    except Exception as e:
        print(f"Erreur de chargement static {turret_type}: {e}")

    try:
        moving_model = base.loader.loadModel(f"./assets/Turrets/{turret_type}_moving.bam")
        moving_model.reparentTo(moving_pivot)
        apply_model_transform(
            moving_model,
            scale=config["moving_scale"],
            offset=config["moving_offset"],
        )
    except Exception as e:
        print(f"Erreur de chargement moving {turret_type}: {e}")

    try:
        ammo_model = base.loader.loadModel(f"./assets/Turrets/{turret_type}_ammo.bam")
        ammo_model.reparentTo(ammo_spawn)
        if turret_type == "tesla":
            ammo_model.setHpr(0, 0, 0)
        apply_model_transform(
            ammo_model,
            scale=config["ammo_scale"],
            offset=config["ammo_offset"],
        )
        ammo_model.hide()
    except Exception as e:
        print(f"Erreur de chargement ammo {turret_type}: {e}")

    turret_root.setPos(0, 0, 0)

    return {
        "root": turret_root,
        "static_root": static_root,
        "moving_pivot": moving_pivot,
        "ammo_spawn": ammo_spawn,
        "static_model": static_model,
        "moving_model": moving_model,
        "ammo_model": ammo_model,
    }


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


from panda3d.core import BillboardEffect


class FloatingUI:
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

    def show(self): self.ui_np.show()
    def hide(self): self.ui_np.hide()


class Structure:
    def __init__(self, base, position, rotation, on_destroy_callback, enemy_manager=None, struct_id=None, turret_type="canon"):
        self.base = base
        self.id = struct_id or f"struct_{id(self)}"
        self.on_destroy_callback = on_destroy_callback
        self.enemy_manager = enemy_manager
        self.turret_type = turret_type if turret_type in TURRET_CONFIGS else "canon"
        self.config = TURRET_CONFIGS[self.turret_type]

        self.np = NodePath("structure_root")
        self.np.reparentTo(self.base.render)
        self.np.setPos(position)
        self.np.setHpr(rotation)

        self.parts = load_turret(self.base, self.np, self.turret_type)
        self.model = self.parts["root"]
        self.static_model = self.parts["static_model"]
        self.moving_model = self.parts["moving_model"]
        self.moving_pivot = self.parts["moving_pivot"]
        self.ammo_model = self.parts["ammo_model"]
        self.ammo_spawn = self.parts["ammo_spawn"]

        min_point, max_point = self.model.getTightBounds()
        c_box = CollisionBox(min_point, max_point)
        col_node = CollisionNode('structure_col')
        col_node.addSolid(c_box)

        self.col_np = self.np.attachNewNode(col_node)
        self.col_np.setPythonTag("structure", self)

        self.ui = FloatingUI(self.base, self.np, "Supprimer [Clic]")

        self.activation_radius = self.config["activation_radius"]
        self.fire_rate = self.config["fire_rate"]
        self.time_since_last_shot = 0.0
        self.targeting_mode = self.config["targeting_mode"]
        self.damage_radius = self.config["damage_radius"]
        self.tracer_color = self.config["tracer_color"]
        self.tracer_thickness = self.config["tracer_thickness"]
        self.turret_h_offset = self.config["turret_h_offset"]

        # Ajuste ici si le départ du tir est trop haut/bas
        self.offset_turret = Vec3(0, 0, 0.0)
        self.offset_enemies = Vec3(0, 0, 0)

        self.task_name = f"turret_update_{id(self)}"
        self.base.taskMgr.add(self.update_task, self.task_name)

    def _is_host_authority(self):
        net_iface = getattr(self.base, 'network', None)
        if net_iface is None or getattr(net_iface, 'net', None) is None:
            return True
        return net_iface.net.is_host

    def create_tracer_effect(self, start_pos, target_pos):
        lines = LineSegs()
        lines.setThickness(self.tracer_thickness)
        lines.setColor(*self.tracer_color)

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

        speed = 120.0
        duration = distance / speed

        seq = Sequence(
            LerpPosInterval(tracer_np, duration, target_pos, startPos=start_pos),
            Func(tracer_np.removeNode)
        )
        seq.start()

        if hasattr(self.base, "sound"):
            self.base.sound.play("turret")
            self.base.sound.play("turret_reload")

    def animate_ammo_shot(self, target_pos):
        try:
            shot_np = self.base.loader.loadModel(f"./assets/Turrets/{self.turret_type}_ammo.bam")
            shot_np.reparentTo(self.base.render)

            start_pos = self.ammo_spawn.getPos(self.base.render)
            shot_np.setPos(start_pos)
            shot_np.lookAt(target_pos)

            # IMPORTANT :
            # Reprend les mêmes réglages visuels que la munition "de base"
            apply_model_transform(
                shot_np,
                scale=self.config["ammo_scale"],
                offset=self.config["ammo_offset"],
            )

            distance = (target_pos - start_pos).length()
            speed = 40.0
            duration = max(0.05, distance / speed)

            seq = Sequence(
                LerpPosInterval(shot_np, duration, target_pos, startPos=start_pos),
                Func(shot_np.removeNode)
            )
            seq.start()
        except Exception as e:
            print(f"Erreur animation ammo {self.turret_type}: {e}")

    def update_task(self, task):
        dt = task.time - getattr(task, 'last_time', task.time)
        task.last_time = task.time

        if not self._is_host_authority():
            return task.cont

        if not self.enemy_manager or not self.enemy_manager.enemies:
            return task.cont

        my_pos = self.np.getPos(self.base.render)

        valid_enemies = []
        for enemy in self.enemy_manager.enemies:
            enemy_pos = enemy.node.getPos(self.base.render)
            dist = (enemy_pos - my_pos).length()

            if dist <= self.activation_radius:
                valid_enemies.append((enemy, dist, enemy.hp))

        if not valid_enemies:
            return task.cont

        if self.targeting_mode == "lowest_hp":
            best_target_data = min(valid_enemies, key=lambda x: (x[2], x[1]))
        else:
            best_target_data = min(valid_enemies, key=lambda x: x[1])

        target_enemy = best_target_data[0]
        min_dist = best_target_data[1]
        enemy_pos = target_enemy.node.getPos(self.base.render)

        if min_dist > 0.1:
            self.moving_pivot.lookAt(enemy_pos)
            self.moving_pivot.setHpr(- self.moving_pivot.getH() + self.turret_h_offset, 0, 0)

        self.time_since_last_shot += dt
        if self.time_since_last_shot >= self.fire_rate:
            self.time_since_last_shot = 0.0

            start_pos_visuel = self.ammo_spawn.getPos(self.base.render) + self.offset_turret
            target_pos_visuel = Point3(enemy_pos.x, enemy_pos.y, enemy_pos.z + 0.5) + self.offset_enemies

            self.create_tracer_effect(start_pos_visuel, target_pos_visuel)
            self.animate_ammo_shot(target_pos_visuel)

            self.enemy_manager.check_projectile_hit(my_pos, enemy_pos, hit_radius=self.damage_radius)

            if getattr(self.base, 'network', None) and getattr(self.base.network, 'net', None) and self.base.network.net.is_host:
                self.base.network.net.broadcast_msg('turret_shoot', {
                    'struct_id': self.id,
                    'target_pos': {'x': target_pos_visuel.x, 'y': target_pos_visuel.y, 'z': target_pos_visuel.z}
                })

        return task.cont

    def detruire(self):
        self.base.taskMgr.remove(self.task_name)
        self.np.removeNode()
        if self.on_destroy_callback:
            self.on_destroy_callback(self)

    def surligner(self):
        self.model.setColorScale(1.5, 0.5, 0.5, 1.0)

    def retirer_surlignage(self):
        self.model.clearColorScale()


class Hologram:
    def __init__(self, base):
        self.base = base
        self.np = NodePath("hologramme_root")
        self.np.reparentTo(self.base.render)

        self.model = load_hologram(self.base, self.np)

        self.np.setTransparency(TransparencyAttrib.MAlpha)
        self.np.setColorScale(0.2, 0.5, 1.0, 0.5)
        self.np.hide()

    def show(self): self.np.show()
    def hide(self): self.np.hide()
    def get_pos(self): return self.np.getPos(self.base.render)
    def get_hpr(self): return self.np.getHpr(self.base.render)

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
        self.enemy_manager = self.base.enemies

        self.mode_actif = False
        self.distance_construction = 2.5
        self.distance_min = 1
        self.rayon_max_construction = 5

        self.cost = 5

        self.plan_sol = Plane(Vec3(0, 0, 1), Point3(0, 0, 0))
        self.structures = []
        self.hologramme = Hologram(self.base)

        self.locked_build_pos = None
        self.locked_build_hpr = None

        self.radial_menu = RadialMenu(
            base=self.base,
            mouse=self.mouse,
            name="Tourelles",
            options=[
                ("5 Ressources", "./assets/Turrets/canon.png"),
                ("5 Ressources", "./assets/Turrets/tesla.png"),
                ("5 Ressources", "./assets/Turrets/barbz.png"),
                ("5 Ressources", "./assets/Turrets/bomb.png"),
            ],
            open_event="mouse1",
            close_event="mouse1-up",
            bind_events=False,
            on_select=self.on_radial_select,
            on_cancel=self.on_radial_cancel
        )

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
        if not self.mode_actif:
            return

        selected_type = TURRET_ORDER[index] if 0 <= index < len(TURRET_ORDER) else "canon"
        selected_cost = TURRET_CONFIGS[selected_type]["cost"]

        if self.base.inventory["ressource"] < selected_cost:
            print("Ressources insufisantes !")
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
                'turret_type': selected_type
            })
        else:
            self.host_create_structure(pos, hpr, turret_type=selected_type)

        self.basculer_mode()

    def host_create_structure(self, pos, hpr, struct_id=None, turret_type="canon"):
        turret_type = turret_type if turret_type in TURRET_CONFIGS else "canon"
        turret_cost = TURRET_CONFIGS[turret_type]["cost"]

        if self.base.inventory["ressource"] < turret_cost:
            return False

        nouvelle_structure = Structure(
            self.base, pos, hpr,
            self._on_structure_detruite,
            self.enemy_manager,
            struct_id=struct_id,
            turret_type=turret_type,
        )
        self.structures.append(nouvelle_structure)
        self.base.inventory["ressource"] -= turret_cost

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
            existing = next((s for s in self.structures if s.id == sid), None)
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
                    turret_type=s_data.get('turret_type', 'canon')
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