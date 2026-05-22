from panda3d.core import (
    CollisionNode,
    CollisionSphere,
    CollisionTraverser,
    CollisionHandlerEvent,
    BitMask32,
)


class ResourceSystem:
    DIAMOND_ORE_MAX_Y = 12.5
    DIAMOND_ORE_MIN_ABS_X = 25.0

    """
    Gère :
    - les zones de ressources
    - les collisions joueur <-> zones
    - la récolte avec touche maintenue
    - une seule ressource
    - des gains deterministes par zone
    """

    def __init__(self, game, inventory_ui, popup_ui):
        self.game = game
        self.inventory_ui = inventory_ui
        self.popup_ui = popup_ui

        # Etat général
        self.in_trigger = False
        self.current_zone = None
        self.resource_zones = []

        # Données de la zone actuelle
        self.current_min_amount = 0
        self.current_max_amount = 0
        self.base_harvest_required_time = 0.0
        self.harvest_required_time = 0.0

        # Récolte
        self.is_holding_e = False
        self.harvest_elapsed = 0.0
        self.harvest_task_name = "harvest_task"

        # Système de collision
        self.game.cTrav = CollisionTraverser()
        self.game.coll_handler = CollisionHandlerEvent()
        self.game.coll_handler.addInPattern('%fn-into-%in')
        self.game.coll_handler.addOutPattern('%fn-out-%in')

        # Inputs
        self.game.accept("e", self.start_harvest)
        self.game.accept("e-up", self.stop_harvest)

    # =========================================================
    # SETUP
    # =========================================================
    def setup_player_collider(self, player):
        """
        Ajoute une sphère de collision au joueur.
        """
        player_np = (
            getattr(player, "node", None)
            or getattr(player, "model", None)
            or getattr(player, "actor", None)
            or getattr(player, "player", None)
        )

        if player_np is None:
            raise AttributeError(
                "Je ne trouve pas le NodePath du joueur. "
                "Dans Player, expose node/model/actor/player."
            )

        cnode = CollisionNode("player")
        cnode.addSolid(CollisionSphere(0, 0, 0.5, 0.6))
        cnode.setFromCollideMask(BitMask32.bit(1))
        cnode.setIntoCollideMask(BitMask32.allOff())

        self.player_col_np = player_np.attachNewNode(cnode)
        self.game.cTrav.addCollider(self.player_col_np, self.game.coll_handler)

    # =========================================================
    # CREATION D'UNE ZONE
    # =========================================================
    def create_resource_zone(self, pos, radius, harvest_time, min_amount, max_amount):
        """
        Crée une zone avec :
        - une position
        - un rayon
        - un temps de récolte
        - un gain de ressource
        """
        zone_id = len(self.resource_zones)
        zone_name = f"trigger_zone_{zone_id}"

        cnode = CollisionNode(zone_name)
        cnode.addSolid(CollisionSphere(0, 0, 0, radius))
        cnode.setIntoCollideMask(BitMask32.bit(1))
        cnode.setFromCollideMask(BitMask32.allOff())

        zone_np = self.game.render.attachNewNode(cnode)
        zone_np.setPos(*pos)

        zone_np.setTag("harvest_time", str(harvest_time))
        zone_np.setTag("min_amount", str(min_amount))
        zone_np.setTag("max_amount", str(max_amount))

        self.resource_zones.append(zone_np)

        self.game.accept(f"player-into-{zone_name}", self.on_trigger_enter)
        self.game.accept(f"player-out-{zone_name}", self.on_trigger_exit)

        marker = self.game.loader.loadModel("assets/sphere")
        marker.reparentTo(self.game.render)
        marker.setPos(zone_np.getPos(self.game.render))
        marker.setScale(radius)
        marker.setTransparency(True)
        marker.setAlphaScale(0.25)

        if max_amount <= 2:
            marker.setColor(0.3, 0.9, 0.3, 1)
        elif max_amount <= 4:
            marker.setColor(0.9, 0.9, 0.2, 1)
        elif max_amount <= 6:
            marker.setColor(1.0, 0.6, 0.2, 1)
        else:
            marker.setColor(1.0, 0.2, 0.2, 1)

    # =========================================================
    # GENERATION DES ZONES SUR LES MINERAIS DE DIAMANT
    # =========================================================
    def generate_diamond_ore_zones(self):
        zones = self._generate_diamond_ore_zone_definitions()
        if not zones:
            print("Aucune zone de minerai de diamant trouvee pour generer les ressources.")
            return

        for index, zone in enumerate(zones):
            amount = self._resource_amount_for_zone(index, zone.radius)
            harvest_time = self._harvest_time_for_zone(zone.radius)

            self.create_resource_zone(
                (zone.x, zone.y, 0),
                zone.radius,
                harvest_time,
                amount,
                amount
            )

    def _generate_diamond_ore_zone_definitions(self):
        map_collision = getattr(self.game, "map_collision", None)
        if map_collision is None or not hasattr(map_collision, "get_resource_zone_definitions"):
            return []

        zones = map_collision.get_resource_zone_definitions(
            cluster_distance=3.0,
            radius_padding=1.25,
            min_radius=2.0,
        )
        return self._filter_diamond_ore_zones(zones)

    def _filter_diamond_ore_zones(self, zones):
        return [
            zone for zone in zones
            if zone.y <= self.DIAMOND_ORE_MAX_Y
            and abs(zone.x) >= self.DIAMOND_ORE_MIN_ABS_X
        ]

    def _resource_amount_for_zone(self, index, radius):
        return max(1, min(8, int(round(radius / 1.5)) + (index % 2)))

    def _harvest_time_for_zone(self, radius):
        return max(1.0, min(8.0, round(radius * 0.75, 1)))

    # =========================================================
    # COLLISIONS
    # =========================================================
    def on_trigger_enter(self, entry):
        if not self.game.game_started:
            return

        self.in_trigger = True
        trigger_node = entry.getIntoNodePath()

        harvest_time_tag = trigger_node.getTag("harvest_time")
        min_amount_tag = trigger_node.getTag("min_amount")
        max_amount_tag = trigger_node.getTag("max_amount")

        if harvest_time_tag == "" or min_amount_tag == "" or max_amount_tag == "":
            parent_np = trigger_node.getParent()
            harvest_time_tag = parent_np.getTag("harvest_time")
            min_amount_tag = parent_np.getTag("min_amount")
            max_amount_tag = parent_np.getTag("max_amount")

        if harvest_time_tag == "" or min_amount_tag == "" or max_amount_tag == "":
            self.current_zone = None
            self.current_min_amount = 0
            self.current_max_amount = 0
            self.base_harvest_required_time = 0.0
            self.harvest_required_time = 0.0
            self.popup_ui.show_popup("Zone invalide.")
            return

        self.current_zone = trigger_node
        self.current_min_amount = int(min_amount_tag)
        self.current_max_amount = int(max_amount_tag)
        self.base_harvest_required_time = float(harvest_time_tag)
        self.harvest_required_time = self._get_effective_harvest_time(
            self.base_harvest_required_time
        )

        self.show_harvest_hint()

    def on_trigger_exit(self, entry):
        self.in_trigger = False
        self.current_zone = None
        self.current_min_amount = 0
        self.current_max_amount = 0
        self.base_harvest_required_time = 0.0
        self.harvest_required_time = 0.0
        self.cancel_harvest()
        self.popup_ui.hide_popup()

    def _get_effective_harvest_time(self, base_time):
        multiplier = getattr(self.game.player, "harvest_time_multiplier", 1.0)
        return max(0.5, base_time * multiplier)

    def refresh_current_harvest_time(self):
        if self.current_zone is None or self.base_harvest_required_time <= 0:
            return

        self.harvest_required_time = self._get_effective_harvest_time(
            self.base_harvest_required_time
        )
        if self.in_trigger and not self.is_holding_e:
            self.show_harvest_hint()

    # =========================================================
    # RECOLTE
    # =========================================================
    def start_harvest(self):
        if not self.game.game_started:
            return

        if not self.in_trigger:
            return

        if self.current_zone is None:
            return

        if self.is_holding_e:
            return

        self.is_holding_e = True
        self.harvest_elapsed = 0.0

        self.popup_ui.show_progress("Récolte... 0%")

        self.game.taskMgr.remove(self.harvest_task_name)
        self.game.taskMgr.add(self.update_harvest_progress, self.harvest_task_name)

    def stop_harvest(self):
        if not self.is_holding_e:
            return

        self.cancel_harvest()

        if self.in_trigger and self.current_zone is not None:
            self.show_harvest_hint()

    def cancel_harvest(self):
        self.is_holding_e = False
        self.harvest_elapsed = 0.0
        self.popup_ui.hide_progress()
        self.game.taskMgr.remove(self.harvest_task_name)

    def show_harvest_hint(self):
        amount = self.current_max_amount
        resource_label = "ressource" if amount <= 1 else "ressources"
        self.popup_ui.show_popup(
            f"Maintiens E : {amount} {resource_label} "
            f"({self.harvest_required_time:.1f}s)"
        )

    def update_harvest_progress(self, task):
        if not self.is_holding_e:
            return task.done

        if not self.in_trigger:
            self.cancel_harvest()
            return task.done

        if self.current_zone is None:
            self.cancel_harvest()
            return task.done

        dt = globalClock.getDt()  # type: ignore
        self.harvest_elapsed += dt

        progress = min(self.harvest_elapsed / max(self.harvest_required_time, 0.001), 1.0)
        percent = int(progress * 100)

        self.popup_ui.show_progress(f"Récolte... {percent}%")

        if self.harvest_elapsed >= self.harvest_required_time:
            self.finish_harvest()
            return task.done

        return task.cont

    def finish_harvest(self):
        self.cancel_harvest()

        if self.current_min_amount <= 0 or self.current_max_amount <= 0:
            return

        gain = self.current_max_amount

        self.game.inventory["ressource"] += gain
        self.inventory_ui.update()

        self.popup_ui.show_popup(
            f"Ressource +{gain} ! "
            f"(Total : {self.game.inventory['ressource']})"
        )

        self.game.taskMgr.remove("restore_hint")
        self.game.taskMgr.doMethodLater(1.0, self.restore_hint, "restore_hint")

    def restore_hint(self, task):
        if self.in_trigger and self.current_zone is not None:
            self.show_harvest_hint()
        else:
            self.popup_ui.hide_popup()

        return task.done

    # =========================================================
    # UPDATE
    # =========================================================
    def update(self):
        self.game.cTrav.traverse(self.game.render)
