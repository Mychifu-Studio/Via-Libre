import sys
import time
import unittest
from unittest.mock import patch

from panda3d.core import Point3

from vialibre import multiplayer


class FakeNode:
    def getPos(self, _render):
        return Point3(0, 0, 0)

    def getH(self, _render):
        return 0.0


class FakePlayer:
    def __init__(self):
        self.player = FakeNode()
        self.modelNode = FakeNode()


class FakeBase:
    def __init__(self, is_host=False, code=None):
        self.is_host = is_host
        self.code = code
        self.player = FakePlayer()
        self.render = object()


class FakeProtocol:
    instances = []

    def __init__(self, player_name, is_host, is_local, join_code):
        self.player_name = player_name
        self.is_host = is_host
        self.is_local = is_local
        self.join_code = join_code
        self.started = False
        FakeProtocol.instances.append(self)

    def start(self):
        self.started = True


class GameNetworkInterfaceConfigTests(unittest.TestCase):
    def setUp(self):
        FakeProtocol.instances.clear()

    def test_menu_join_code_starts_online_client(self):
        base = FakeBase(is_host=False, code=" abcd ")
        with patch.object(sys, "argv", ["main.py"]), patch.object(multiplayer, "NetworkProtocol", FakeProtocol):
            interface = multiplayer.GameNetworkInterface(base)

        self.assertFalse(interface.is_solo)
        self.assertEqual(FakeProtocol.instances[0].join_code, "abcd")
        self.assertFalse(FakeProtocol.instances[0].is_host)
        self.assertFalse(FakeProtocol.instances[0].is_local)
        self.assertTrue(FakeProtocol.instances[0].started)

    def test_menu_join_ip_starts_local_client(self):
        base = FakeBase(is_host=False, code="127.0.0.1")
        with patch.object(sys, "argv", ["main.py"]), patch.object(multiplayer, "NetworkProtocol", FakeProtocol):
            multiplayer.GameNetworkInterface(base)

        self.assertEqual(FakeProtocol.instances[0].join_code, "127.0.0.1")
        self.assertTrue(FakeProtocol.instances[0].is_local)

    def test_cli_join_keeps_priority_over_menu_code(self):
        base = FakeBase(is_host=False, code="MENU")
        with patch.object(sys, "argv", ["main.py", "--join", "CLI"]), patch.object(multiplayer, "NetworkProtocol", FakeProtocol):
            multiplayer.GameNetworkInterface(base)

        self.assertEqual(FakeProtocol.instances[0].join_code, "CLI")


class NetworkProtocolLocalTests(unittest.TestCase):
    def test_online_host_falls_back_to_lan_when_signaling_fails(self):
        host = None
        try:
            try:
                host = multiplayer.NetworkProtocol("Host", True, False)
            except OSError as exc:
                self.skipTest(f"port local 5555 indisponible: {exc}")

            with patch.object(host, "_recv_blocking", return_value=None):
                host.start()

            self.assertTrue(host.connected)
            self.assertTrue(host.is_local)
            self.assertIsNone(host.game_code)
            self.assertEqual(host.socket.getsockname()[1], 5555)
        finally:
            if host is not None:
                host.close()

    def test_local_udp_handshake_connects_client_to_host(self):
        host = None
        client = None
        try:
            try:
                host = multiplayer.NetworkProtocol("Host", True, True)
            except OSError as exc:
                self.skipTest(f"port local 5555 indisponible: {exc}")
            host.start()
            client = multiplayer.NetworkProtocol("Player_A", False, True, "127.0.0.1")
            client.start()

            messages = []
            deadline = time.time() + 3.0
            while time.time() < deadline:
                messages.extend(host.update())
                client.update()
                if client.connected and "Player_A" in host.clients.values():
                    break
                time.sleep(0.02)

            self.assertTrue(client.connected)
            self.assertIn("Player_A", host.clients.values())
            self.assertTrue(any(msg["kind"] == "_peer_connected" for msg in messages))
        finally:
            if client is not None:
                client.close()
            if host is not None:
                host.close()


if __name__ == "__main__":
    unittest.main()
