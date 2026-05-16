import random

from panda3d.core import (
    CollisionNode,
    CollisionSphere,
    CollisionTraverser,
    CollisionHandlerEvent,
    BitMask32,
)


class ResourceSystem:
    """
    Gère :
    - les zones de ressources
    - les collisions joueur <-> zones
    - la récolte avec touche maintenue
    - une seule ressource
    - des gains aléatoires par fourchette
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
        - une fourchette de gain aléatoire
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

        marker = self.game.loader.loadModel("models/misc/sphere")
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
    # GENERATION ALEATOIRE DES ZONES
    # =========================================================
    def generate_random_zones(self, number_of_zones):
        rewards = {
            1.0: (1, 1),
            2.0: (1, 2),
            4.0: (1, 4),
            6.0: (2, 6),
            8.0: (3, 8),
        }

        for _ in range(number_of_zones):
            x = random.uniform(-35, 35)
            y = random.uniform(-35, 35)
            z = 0

            radius = random.uniform(2.0, 4.5)
            harvest_time = random.choice(list(rewards.keys()))
            min_amount, max_amount = rewards[harvest_time]

            self.create_resource_zone(
                (x, y, z),
                radius,
                harvest_time,
                min_amount,
                max_amount
            )

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
            self.harvest_required_time = 0.0
            self.popup_ui.show_popup("Zone invalide.")
            return

        self.current_zone = trigger_node
        self.current_min_amount = int(min_amount_tag)
        self.current_max_amount = int(max_amount_tag)
        self.harvest_required_time = float(harvest_time_tag)

        self.popup_ui.show_popup(
            f"Maintiens E : entre {self.current_min_amount} et "
            f"{self.current_max_amount} ressources ({self.harvest_required_time:.0f}s)"
        )

    def on_trigger_exit(self, entry):
        self.in_trigger = False
        self.current_zone = None
        self.current_min_amount = 0
        self.current_max_amount = 0
        self.harvest_required_time = 0.0
        self.cancel_harvest()
        self.popup_ui.hide_popup()

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
            self.popup_ui.show_popup(
                f"Maintiens E : entre {self.current_min_amount} et "
                f"{self.current_max_amount} ressources ({self.harvest_required_time:.0f}s)"
            )

    def cancel_harvest(self):
        self.is_holding_e = False
        self.harvest_elapsed = 0.0
        self.popup_ui.hide_progress()
        self.game.taskMgr.remove(self.harvest_task_name)

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

        progress = min(self.harvest_elapsed / self.harvest_required_time, 1.0)
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

        gain = random.randint(self.current_min_amount, self.current_max_amount)

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
            self.popup_ui.show_popup(
                f"Maintiens E : entre {self.current_min_amount} et "
                f"{self.current_max_amount} ressources ({self.harvest_required_time:.0f}s)"
            )
        else:
            self.popup_ui.hide_popup()

        return task.done

    # =========================================================
    # UPDATE
    # =========================================================
    def update(self):
        self.game.cTrav.traverse(self.game.render)