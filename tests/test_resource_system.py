import unittest

from panda3d.core import CollisionHandlerEvent, CollisionTraverser, NodePath

from vialibre.resource_system import ResourceSystem


class DummyGame:
    def __init__(self):
        self.cTrav = CollisionTraverser()
        self.coll_handler = CollisionHandlerEvent()


class DummyPlayer:
    def __init__(self):
        self.player = NodePath("player-root")
        self.model = self.player.attachNewNode("visual-model")


class ResourceSystemTests(unittest.TestCase):
    def test_player_collider_uses_stable_player_root(self):
        system = ResourceSystem.__new__(ResourceSystem)
        system.game = DummyGame()
        player = DummyPlayer()

        system.setup_player_collider(player)

        self.assertEqual(system.player_col_np.getParent(), player.player)
        player.model.removeNode()
        self.assertFalse(system.player_col_np.isEmpty())
        self.assertEqual(system.player_col_np.getParent(), player.player)


if __name__ == "__main__":
    unittest.main()
