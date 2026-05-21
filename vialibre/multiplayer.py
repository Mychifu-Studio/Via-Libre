import socket
import json
import sys
import time
import threading
import urllib.request
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass, field
from panda3d.core import Point3

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
SIGNALING_IP   = "141.253.121.76"
SIGNALING_PORT = 8080
PUNCH_ATTEMPTS   = 10
PUNCH_INTERVAL   = 0.2
FALLBACK_TIMEOUT = 3.0
SNAPSHOT_TICK    = 60
SNAPSHOT_PERIOD  = 1.0 / SNAPSHOT_TICK

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def get_public_ip() -> str:
    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=2).read().decode()
    except Exception:
        return "0.0.0.0"


# ─────────────────────────────────────────────────────
# MODELS (avec to_dict/from_dict)
# ─────────────────────────────────────────────────────
class PlayerState:
    def __init__(self, id: str, username: str, x: float, y: float, z: float, h: float = 0.0):
        self.id = id
        self.username = username
        self.x = x
        self.y = y
        self.z = z
        self.h = h

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "h": self.h,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PlayerState":
        return PlayerState(
            id=data["id"],
            username=data["username"],
            x=data["x"],
            y=data["y"],
            z=data["z"],
            h=data.get("h", 0.0),
        )

@dataclass
class Snapshot:
    tick: int
    players: List[PlayerState] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "players": [p.to_dict() for p in self.players],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Snapshot":
        return Snapshot(
            tick=data.get("tick", 0),
            players=[PlayerState.from_dict(p) for p in data.get("players", [])],
        )

@dataclass
class GameEvent:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GameEvent":
        return GameEvent(
            type=data["type"],
            data=data.get("data", {}),
        )


# ─────────────────────────────────────────────
# 1. NETWORK PROTOCOL (Socket, Connexion, P2P/TRN)
# ─────────────────────────────────────────────
class NetworkProtocol:
    def __init__(self, player_name: str, is_host: bool, is_local: bool, join_code: Optional[str] = None):
        self.player_name = player_name
        self.is_host     = is_host
        self.is_local    = is_local
        self.join_arg    = join_code
        self.target_ip   = None
        self.target_port = None
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", 5555 if (is_host and is_local) else 0))
        self.socket.setblocking(True)

        self._lock = threading.Lock()
        self.clients: Dict[tuple, str] = {}
        self.relay_clients: set[tuple] = set()
        self.use_full_relay: bool = False
        self.game_code   = None
        self.client_id   = None
        self.local_ip    = get_local_ip()
        self.seq         = 0
        self.last_processed_seq_client = -1   # dernier seq traité pour input client
        self.connected   = False
        self.last_heartbeat = 0.0

    def start(self):
        if self.is_local:
            if self.is_host: self._setup_as_local_host()
            else:            self._setup_as_local_client()
        else:
            if self.is_host: self._setup_as_host()
            else:            self._setup_as_client()
        self.socket.setblocking(False)

    def _next_seq(self) -> int:
        with self._lock:
            self.seq += 1
            return self.seq

    def _is_relay(self, target: tuple) -> bool:
        with self._lock:
            return self.use_full_relay or target in self.relay_clients

    def _send_raw(self, msg: Dict[str, Any], address: tuple) -> None:
        try:
            data = json.dumps(msg).encode("utf-8")
            self.socket.sendto(data, address)
        except (BlockingIOError, OSError):
            pass

    def send_msg(self, kind: str, payload: Dict[str, Any], dest_addr: Optional[tuple] = None) -> None:
        target = dest_addr if dest_addr else (self.target_ip, self.target_port)
        if not target or not target[0]:
            return

        envelope = {
            "f": self.player_name,
            "s": self._next_seq(),
            "k": kind,
            "p": payload,
        }

        if self._is_relay(target):
            relay_wrapper = {
                "action": "relay",
                "code": self.game_code,
                "payload": envelope,
            }
            self._send_raw(relay_wrapper, (SIGNALING_IP, SIGNALING_PORT))
        else:
            self._send_raw(envelope, target)

    def broadcast_msg(self, kind: str, payload: Dict[str, Any], ignore_addr: Optional[tuple] = None):
        with self._lock:
            addrs = list(self.clients.keys())
        for addr in addrs:
            if addr != ignore_addr:
                self.send_msg(kind, payload, addr)

    def _recv_blocking(self, timeout: float = 10.0) -> Optional[Dict]:
        self.socket.settimeout(timeout)
        try:
            data, _ = self.socket.recvfrom(1024)
            return json.loads(data.decode("utf-8"))
        except socket.timeout:
            print("SYSTEM : ERREUR - Timeout serveur.")
            return None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        finally:
            self.socket.setblocking(True)

    def _setup_as_local_host(self):
        print(f"SYSTEM : HÉBERGEMENT LOCAL. IP -> {self.local_ip}:5555")
        self.connected = True

    def _setup_as_local_client(self):
        print(f"SYSTEM : Connexion locale à {self.join_arg}:5555...")
        self.target_ip = self.join_arg
        self.target_port = 5555
        threading.Thread(target=self._punch_lan_thread, daemon=True).start()

    def _setup_as_host(self):
        print("SYSTEM : Création du salon...")
        self._send_raw({
            "action": "host", 
            "localIp": self.local_ip, 
            "localPort": self.socket.getsockname()[1]
        }, (SIGNALING_IP, SIGNALING_PORT))

        resp = self._recv_blocking()
        if not resp or resp.get('type') != 'hosted':
            sys.exit("SYSTEM : Impossible de créer le salon.")

        self.game_code = resp['code']
        self.connected = True
        self.last_heartbeat = time.time()
        print(f"SYSTEM : MULTIJOUEUR ACTIF. CODE -> {self.game_code}")

    def _setup_as_client(self):
        self.game_code = self.join_arg.upper()
        self._send_raw({"action": "join", "code": self.game_code}, (SIGNALING_IP, SIGNALING_PORT))

        resp = self._recv_blocking()
        if not resp or resp.get('type') == 'error':
            sys.exit(f"SYSTEM : ERREUR - {resp.get('message') if resp else 'No response'}")

        if resp.get('type') == 'punch_target':
            self.client_id = resp.get('clientId')
            host_pub_ip = resp['ip']
            host_pub_port = resp['port']
            host_loc_ip = resp.get('hostLocalIp')
            
            if get_public_ip() == host_pub_ip and host_loc_ip:
                print("SYSTEM : Même réseau détecté ! Basculement LAN.")
                self.target_ip = "127.0.0.1" if self.local_ip == host_loc_ip else host_loc_ip
                self.target_port = resp.get('hostLocalPort')
                threading.Thread(target=self._punch_lan_thread, daemon=True).start()
            else:
                self.target_ip = host_pub_ip
                self.target_port = host_pub_port
                threading.Thread(target=self._punch_thread, daemon=True).start()

    def _punch_lan_thread(self):
        self.socket.setblocking(False)
        for _ in range(15):
            if self.connected: break
            self.send_msg('hello', {"name": self.player_name, "route": "lan"})
            time.sleep(0.1)

    def _punch_thread(self):
        self.socket.setblocking(False)
        for _ in range(PUNCH_ATTEMPTS):
            self.send_msg('hello', {"name": self.player_name, "route": "p2p"})
            time.sleep(PUNCH_INTERVAL)
        self._check_fallback()

    def _punch_specific(self, target_ip: str, target_port: int):
        dummy_addr = (target_ip, target_port)
        with self._lock:
            if dummy_addr not in self.clients:
                self.clients[dummy_addr] = "Connecting..."
        for _ in range(PUNCH_ATTEMPTS):
            self.send_msg('hello', {"name": self.player_name}, dest_addr=dummy_addr)
            time.sleep(PUNCH_INTERVAL)

    def _check_fallback(self):
        for _ in range(int(FALLBACK_TIMEOUT * 10)):
            if self.connected: return
            time.sleep(0.1)

        if not self.connected:
            print("SYSTEM : P2P échoué. Basculement sur le Relais (TURN)...")
            with self._lock: self.use_full_relay = True
            self.send_msg('fallback', {"name": self.player_name})
            for _ in range(10):
                if self.connected: return
                self.send_msg('hello', {"name": self.player_name})
                time.sleep(0.5)

    def _resolve_virtual_addr(self, msg: Dict, source_addr: tuple) -> tuple:
        if source_addr == (SIGNALING_IP, SIGNALING_PORT):
            if 'v_ip' in msg and 'v_port' in msg:
                return (msg['v_ip'], msg['v_port'])
        return source_addr

    def update(self) -> List[Dict[str, Any]]:
        self._send_heartbeat()
        game_messages = []

        while True:
            try:
                data, source_addr = self.socket.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))
            except (BlockingIOError, OSError, json.JSONDecodeError):
                break

            if msg.get('type') == 'punch_target' and self.is_host:
                threading.Thread(target=self._punch_specific, args=(msg['ip'], msg['port']), daemon=True).start()
                continue

            virtual_addr = self._resolve_virtual_addr(msg, source_addr)
            kind = msg.get('k')
            if not kind:
                continue

            sender_id = msg.get('f', 'unknown')
            payload   = msg.get('p', {})

            if kind == 'input':
                seq = payload.get("seq", -1)
                if seq != -1:
                    with self._lock:
                        if seq > self.last_processed_seq_client:
                            self.last_processed_seq_client = seq
                    payload = {k: v for k, v in payload.items() if k != "seq"}
                payload = {"seq": seq, **payload}

            if kind == 'hello':
                self._handle_hello(payload, sender_id, virtual_addr, game_messages)
            elif kind == 'fallback':
                self._handle_fallback(payload, virtual_addr, game_messages)
            else:
                game_messages.append({
                    "kind": kind,
                    "payload": payload,
                    "sender_id": sender_id,
                    "addr": virtual_addr
                })

        return game_messages

    def _handle_hello(self, payload: dict, sender_id: str, addr: tuple, game_messages: list):
        if sender_id not in ("Connecting...", "unknown"):
            with self._lock:
                self.clients[addr] = sender_id

        if not self.connected and not self.is_host:
            self.connected = True
            print(f"SYSTEM : Connecté au salon ! (Mode: {payload.get('route', 'P2P')})")

        if self.is_host:
            self.send_msg('hello', {"name": self.player_name, "route": "p2p"}, dest_addr=addr)
            game_messages.append({"kind": "_peer_connected", "sender_id": sender_id, "addr": addr})

    def _handle_fallback(self, payload: dict, addr: tuple, game_messages: list):
        if not self.is_host: return
        client_name = payload.get('name')
        with self._lock:
            for client_addr, c_name in self.clients.items():
                if c_name in (client_name, "Connecting..."):
                    self.relay_clients.add(client_addr)
                    self.clients[client_addr] = client_name
                    game_messages.append({"kind": "_peer_connected", "sender_id": client_name, "addr": client_addr})
                    return
            self.use_full_relay = True

    def _send_heartbeat(self):
        if self.is_local or not self.game_code or time.time() - self.last_heartbeat <= 15.0:
            return
        msg = {"action": "ping"}
        if not self.is_host:
            msg.update({"code": self.game_code, "clientId": self.client_id})
        self._send_raw(msg, (SIGNALING_IP, SIGNALING_PORT))
        self.last_heartbeat = time.time()

    def close(self):
        if self.game_code and not self.is_local:
            act = "close_lobby" if self.is_host else "leave"
            self._send_raw({"action": act, "code": self.game_code}, (SIGNALING_IP, SIGNALING_PORT))
        try: self.socket.close()
        except: pass


# ─────────────────────────────────────────────
# 2. GAME NETWORK INTERFACE (Client-side prediction + reconciliation)
# ─────────────────────────────────────────────
class GameNetworkInterface:
    def __init__(self, base):
        self.base = base
        self.local_player = base.player

        is_host  = "--host"  in sys.argv
        is_local = "--local" in sys.argv
        join_arg = sys.argv[sys.argv.index("--join") + 1] if "--join" in sys.argv else None

        player_name = "Host" if is_host else f"Player_{id(self.base) % 1000}"
        self.net = NetworkProtocol(player_name, is_host, is_local, join_arg)
        self.other_players = {}
        
        self.tick = 0
        self.last_snapshot_time = 0.0
        self.predicted_pos = self.local_player.player.getPos()
        self.predicted_h   = self.local_player.player.getHpr(base.render).x

        self.last_sent_pos = self.predicted_pos
        self.last_sent_h   = self.predicted_h
        self.send_threshold_pos = 0.05
        self.send_threshold_h   = 1.0
        self.correct_threshold_pos = 0.5  # se corrige seulement si diff > 0.5 unité
        self.correct_threshold_h   = 30.0 # se corrige seulement si diff > 30°

        self.next_input_seq = 0
        self.last_processed_seq = -1
        self.input_history = []

        self.net.start()

    def _next_input_seq(self) -> int:
        self.next_input_seq += 1
        return self.next_input_seq

    def _pos_changed_significantly(self, pos1, pos2) -> bool:
        dx = pos1.x - pos2.x
        dy = pos1.y - pos2.y
        dz = pos1.z - pos2.z
        dist = (dx*dx + dy*dy + dz*dz)**0.5
        return dist > self.send_threshold_pos

    def _h_changed_significantly(self, h1: float, h2: float) -> bool:
        dh = abs(h1 - h2) % 360
        if dh > 180: dh = 360 - dh
        return dh > self.send_threshold_h

    def _apply_authoritative_correction(self, payload: dict):
        server_pos = None
        server_h   = None
        last_seq   = payload.get("last_processed_seq", -1)

        for p_data in payload.get("players", []):
            if p_data.get("id") == self.net.player_name:
                server_pos = Point3(p_data["x"], p_data["y"], p_data["z"])
                server_h   = p_data.get("h", 0.0)
                break
        if not server_pos:
            return

        current_local = self.local_player.player.getPos()
        current_h     = self.local_player.modelNode.getH(self.base.render)

        # 1. Calcul de la différence (position)
        diff = Point3(server_pos - current_local)
        dist = diff.length()

        # 2. Calcul de la diff (h)
        dh = (server_h - current_h) % 360
        if dh > 180:
            dh = 360 - dh

        # 3. On corrige seulement si la déviation est grossière
        if dist > self.correct_threshold_pos or abs(dh) > self.correct_threshold_h:
            strength = 0.3  # 0.1 à 0.3, pas trop fort
            correction = Point3(diff * strength)
            self.local_player.player.setPos(current_local + correction)
            self.local_player.modelNode.setH(current_h + dh * strength)

        # 4. Re‑réplication des inputs non‑acquittés
        for seq, inp in self.input_history:
            if seq <= last_seq:
                continue
            self._replay_local_input(inp)

    def _replay_local_input(self, inp: dict):
        # → on ne force que la position de base, pas la vélocité
        self.local_player.player.setPos(inp.get("x", 0), inp.get("y", 0), inp.get("z", 0))
        self.local_player.modelNode.setH(inp.get("h", 0.0))  # mais on tient compte de la H serveur

    def _send_input(self):
        if not self.net.connected:
            return

        pos = self.local_player.player.getPos()
        h   = self.local_player.modelNode.getH(self.base.render)  # H monde

        need_send = self._pos_changed_significantly(pos, self.last_sent_pos)
        need_send |= self._h_changed_significantly(h, self.last_sent_h)

        if not need_send:
            return

        seq = self._next_input_seq()
        raw_input = {
            "x": pos.x,
            "y": pos.y,
            "z": pos.z,
            "h": h,
        }

        self.input_history.append((seq, raw_input.copy()))
        self.input_history = sorted(self.input_history, key=lambda x: x[0])

        self.net.send_msg("input", {
            "seq": seq,
            **raw_input,
        })

        self.last_sent_pos = pos
        self.last_sent_h   = h

    def _broadcast_snapshot(self):
        now = time.time()
        if now - self.last_snapshot_time < SNAPSHOT_PERIOD:
            return
        if self.net.is_host:
            snap = self._build_snapshot()
            snap["last_processed_seq"] = self.net.last_processed_seq_client
            self.net.broadcast_msg("snapshot", snap)
            self.last_snapshot_time = now
        self.tick += 1

    def _build_snapshot(self) -> Dict[str, Any]:
        players = [PlayerState(
            id=self.net.player_name,
            username=self.net.player_name,
            x=self.local_player.player.getX(),
            y=self.local_player.player.getY(),
            z=self.local_player.player.getZ(),
            h=self.local_player.player.getH(),
        )]
        for name, model in self.other_players.items():
            players.append(PlayerState(
                id=name,
                username=name,
                x=model.getX(),
                y=model.getY(),
                z=model.getZ(),
                h=model.getH(),
            ))
        return Snapshot(tick=self.tick, players=players).to_dict()

    def _spawn_player(self, name: str):
        if name in self.other_players or name == self.net.player_name:
            return
        model = self.base.loader.loadModel("./assets/dog.bam")
        model.reparentTo(self.base.render)
        self.other_players[name] = model
        print(f"SYSTEM : {name} a rejoint la partie.")

    def _despawn_player(self, name: str):
        if name in self.other_players:
            self.other_players[name].removeNode()
            del self.other_players[name]
            print(f"SYSTEM : {name} a quitté la partie.")

    def _apply_input(self, sender_id: str, payload: dict):
        if not self.net.is_host or sender_id not in self.other_players:
            return
        model = self.other_players[sender_id]
        model.setPos(payload["x"], payload["y"], payload["z"])
        model.setH(payload.get("h", 0.0))

    def _apply_snapshot(self, payload: dict):
        self.tick = payload.get("tick", self.tick)
        if not self.net.is_host:
            self.last_processed_seq = payload.get("last_processed_seq", -1)
            self._apply_authoritative_correction(payload)

        known_players = set()
        for p_data in payload.get("players", []):
            pid = p_data.get("id")
            known_players.add(pid)

            if pid == self.net.player_name:
                continue

            if pid not in self.other_players:
                self._spawn_player(pid)

            model = self.other_players[pid]
            model.setPos(p_data["x"], p_data["y"], p_data["z"])
            model.setH(p_data.get("h", 0.0))

        for name in list(self.other_players.keys()):
            if name not in known_players:
                self._despawn_player(name)

    def update(self):
        game_messages = self.net.update()

        for msg in game_messages:
            kind = msg["kind"]
            payload = msg.get("payload", {})
            sender_id = msg["sender_id"]

            if kind == "_peer_connected":
                if self.net.is_host:
                    self._spawn_player(sender_id)
                    self._broadcast_snapshot()

            elif kind == "snapshot":
                self._apply_snapshot(payload)

            elif kind == "input":
                self._apply_input(sender_id, payload)

            elif kind == "event":
                if payload.get("type") == "player_joined":
                    self._spawn_player(payload.get("data", {}).get("name"))
                elif payload.get("type") == "player_left":
                    self._despawn_player(payload.get("data", {}).get("name"))

            elif kind == "leave":
                self._despawn_player(payload.get("name", sender_id))

        if not self.net.is_host:
            self._send_input()
        elif self.net.is_host:
            self._broadcast_snapshot()

    def exit(self):
        self.net.broadcast_msg("leave", {"name": self.net.player_name})
        self.net.close()