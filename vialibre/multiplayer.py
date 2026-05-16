import socket
import json
import sys
import time
import threading
import urllib.request


# ─────────────────────────────────────────────
# CONFIGURATION : Remplacez par l'IP de votre VPS Oracle
# ─────────────────────────────────────────────
SIGNALING_IP   = "145.241.161.19"
SIGNALING_PORT = 8080

PUNCH_ATTEMPTS   = 10
PUNCH_INTERVAL   = 0.2
FALLBACK_TIMEOUT = 3.0


def get_local_ip() -> str:
    """Récupère l'IP locale de la machine (ex: 192.168.1.15)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def get_public_ip() -> str:
    """Récupère l'IP publique de la box internet."""
    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=2).read().decode()
    except Exception:
        return "0.0.0.0"


# ─────────────────────────────────────────────
# Classe bas niveau : Gestion du socket UDP
# ─────────────────────────────────────────────
class Networking:
    def __init__(self, name: str | None = None) -> None:
        self.name        = name if name else "Player"
        self.target_ip   = None
        self.target_port = None

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", 0))
        self.socket.setblocking(True)

        # Verrou protégeant les données partagées entre threads
        self._lock = threading.Lock()
        self.clients: dict[tuple, str] = {}
        self.relay_clients: set[tuple] = set()
        self.use_full_relay: bool = False

        self.game_code   = None
        self.server_ip   = SIGNALING_IP
        self.server_port = SIGNALING_PORT

    def get_local_port(self) -> int:
        return self.socket.getsockname()[1]

    # ── Registre clients : accès thread-safe ──

    def add_client(self, addr: tuple, name: str) -> None:
        with self._lock:
            self.clients[addr] = name

    def remove_client(self, addr: tuple) -> None:
        with self._lock:
            self.clients.pop(addr, None)

    def get_client_name(self, addr: tuple) -> str | None:
        with self._lock:
            return self.clients.get(addr)

    def get_clients_snapshot(self) -> dict:
        with self._lock:
            return dict(self.clients)

    def replace_client(self, stale_keys: list[tuple], addr: tuple, name: str) -> None:
        """Supprime les anciennes entrées et enregistre la nouvelle adresse."""
        with self._lock:
            for k in stale_keys:
                self.clients.pop(k, None)
            self.clients[addr] = name

    def enable_full_relay(self) -> None:
        with self._lock:
            self.use_full_relay = True

    def add_relay_client(self, addr: tuple) -> None:
        with self._lock:
            self.relay_clients.add(addr)

    def is_relay(self, target: tuple) -> bool:
        with self._lock:
            return self.use_full_relay or target in self.relay_clients

    # ── Envoi ─────────────────────────────────

    def send(self, message: dict, address: tuple | None = None) -> bool:
        """Envoie un message UDP, via P2P direct ou via le VPS (TURN)."""
        try:
            target = address if address else (self.target_ip, self.target_port)
            if self.is_relay(target):
                wrapped = {
                    "action":  "relay",
                    "code":    self.game_code,
                    "payload": message,
                }
                data = json.dumps(wrapped).encode("utf-8")
                self.socket.sendto(data, (self.server_ip, self.server_port))
            else:
                data = json.dumps(message).encode("utf-8")
                if target and target[0] and target[1]:
                    self.socket.sendto(data, target)
            return True
        except (BlockingIOError, OSError):
            return False

    # ── Réception ───────────────────────

    def _read_raw(self) -> list[tuple[dict, tuple]]:
        packets = []
        while True:
            try:
                data, source_addr = self.socket.recvfrom(4096)
                packets.append((json.loads(data.decode("utf-8")), source_addr))
            except (BlockingIOError, OSError):
                break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        return packets

    def _resolve_virtual_addr(self, message: dict, source_addr: tuple) -> tuple:
        if (source_addr[0] == self.server_ip
                and source_addr[1] == self.server_port
                and 'v_ip' in message and 'v_port' in message):
            return (message['v_ip'], message['v_port'])
        return source_addr

    def _update_client_registry(self, message: dict, virtual_addr: tuple) -> str:
        m_type = message.get('type')
        if m_type == 'hello':
            name = message.get('content') or message.get('name') or "unknown"
            if not self.get_client_name(virtual_addr):
                self.add_client(virtual_addr, name)
        else:
            name = self.get_client_name(virtual_addr) or "unknown"

        if m_type == 'leave':
            self.remove_client(virtual_addr)

        return name

    def receive(self) -> list[tuple[dict, str, tuple]]:
        results = []
        for message, source_addr in self._read_raw():
            virtual_addr = self._resolve_virtual_addr(message, source_addr)
            player_name  = self._update_client_registry(message, virtual_addr)
            results.append((message, player_name, virtual_addr))
        return results


# ─────────────────────────────────────────────
# Classe haut niveau : Gestion du multijoueur
# ─────────────────────────────────────────────
class MultiplayerManager:
    def __init__(self, base, local_player):
        self.base         = base
        self.local_player = local_player

        self.is_host  = "--host"  in sys.argv
        self.is_join  = "--join"  in sys.argv
        self.is_local = "--local" in sys.argv
        self.join_arg = self._parse_join_arg()

        self.player_name = "Host" if self.is_host else f"Player_{id(self.base) % 1000}"
        self.game_code   = None
        self.client_id   = None

        self.net           = Networking(self.player_name)
        self.other_players = {}
        self.connected     = False
        self.last_heartbeat  = 0.0
        self.last_player_pos = None

        # IP locale mise en cache
        self._local_ip = get_local_ip()

        if self.is_host and self.is_local:
            try:
                self.net.socket.close()
                self.net.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.net.socket.bind(("0.0.0.0", 5555))
                self.net.socket.setblocking(True)
            except Exception:
                pass

        self._setup_connection()

        self.net.socket.setblocking(False)
        self.last_player_pos = self.local_player.player.getPos()

    # ──────────────────────────────────────────
    # Initialisation
    # ──────────────────────────────────────────

    def _parse_join_arg(self) -> str | None:
        try:
            return sys.argv[sys.argv.index("--join") + 1]
        except (ValueError, IndexError):
            return None

    def _is_lan_addr(self, ip: str) -> bool:
        return ip in ("127.0.0.1", self._local_ip)

    def _recv_blocking(self, timeout: float = 10.0) -> dict | None:
        self.net.socket.settimeout(timeout)
        try:
            data, _ = self.net.socket.recvfrom(1024)
            return json.loads(data.decode("utf-8"))
        except socket.timeout:
            print("SYSTEM : ERREUR - Timeout en attente du serveur.")
            return None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        finally:
            self.net.socket.setblocking(True)

    def _setup_connection(self):
        if self.is_local:
            if self.is_host:   self._setup_as_local_host()
            elif self.is_join: self._setup_as_local_client()
        else:
            if self.is_host:   self._setup_as_host()
            elif self.is_join: self._setup_as_client()

    def _setup_as_local_host(self):
        print("\n====================================")
        print(" SYSTEM : HÉBERGEMENT LOCAL (FORCÉ)")
        print(f" SYSTEM : IP À REJOINDRE -> {self._local_ip}")
        print("====================================\n")
        self.connected = True

    def _setup_as_local_client(self):
        if not self.join_arg:
            print("SYSTEM : ERREUR - Fournissez l'IP. Ex: --join 192.168.1.15 --local")
            sys.exit(1)

        print(f"SYSTEM : Connexion locale à {self.join_arg}:5555...")
        self.net.target_ip   = self.join_arg
        self.net.target_port = 5555
        threading.Thread(target=self._punch_lan_thread, daemon=True).start()

    def _setup_as_host(self):
        print("SYSTEM : Création du salon via le serveur de signalisation...")
        self.net.send(
            {
                "action":    "host",
                "localIp":   self._local_ip,
                "localPort": self.net.get_local_port(),
            },
            (SIGNALING_IP, SIGNALING_PORT),
        )

        resp = self._recv_blocking(timeout=10.0)
        if not resp or resp.get('type') != 'hosted':
            print("SYSTEM : ERREUR - Impossible de créer le salon.")
            sys.exit(1)

        self.game_code      = resp['code']
        self.net.game_code  = self.game_code
        self.last_heartbeat = time.time()
        self.connected      = True # FIX ASYMETRIE : L'hôte est toujours considéré connecté à son propre salon

        print("\n====================================")
        print(" SYSTEM : HÉBERGEMENT MULTIJOUEUR ACTIF")
        print(f" SYSTEM : CODE DE PARTIE -> {self.game_code}")
        print("====================================\n")
        print("SYSTEM : En attente de joueurs...")

    def _setup_as_client(self):
        if not self.join_arg:
            print("SYSTEM : ERREUR - Fournissez un code. Ex: --join 8F3A2")
            sys.exit(1)

        self.game_code     = self.join_arg.upper()
        self.net.game_code = self.game_code
        print(f"SYSTEM : Connexion au salon {self.game_code}...")

        self.net.send(
            {"action": "join", "code": self.game_code},
            (SIGNALING_IP, SIGNALING_PORT),
        )

        resp = self._recv_blocking(timeout=10.0)
        if not resp:
            sys.exit(1)

        if resp.get('type') == 'error':
            print(f"SYSTEM : ERREUR - {resp.get('message')}")
            sys.exit(1)

        if resp.get('type') == 'punch_target':
            target_public_ip   = resp['ip']
            target_public_port = resp['port']
            host_local_ip      = resp.get('hostLocalIp')
            host_local_port    = resp.get('hostLocalPort')
            self.client_id     = resp.get('clientId')

            print(f"[DEBUG CLIENT] Cible détectée : {target_public_ip}:{target_public_port}")

            my_public_ip = get_public_ip()

            # --- SMART LAN FALLBACK ---
            if my_public_ip == target_public_ip and host_local_ip and host_local_port:
                print("SYSTEM : Même réseau internet détecté ! Basculement en LAN IP Direct.")
                self.net.target_ip   = "127.0.0.1" if self._local_ip == host_local_ip else host_local_ip
                self.net.target_port = host_local_port
                threading.Thread(target=self._punch_lan_thread, daemon=True).start()
            else:
                self.net.target_ip   = target_public_ip
                self.net.target_port = target_public_port
                self._punch()

    # ──────────────────────────────────────────
    # Phase 2 : Perçage UDP & Fallback Relais
    # ──────────────────────────────────────────

    def _punch_lan_thread(self):
        self.net.socket.setblocking(False)
        for _ in range(15):
            if self.connected: break
            self.net.send({'type': 'hello', 'content': self.player_name})
            time.sleep(0.1)

    def _punch(self):
        threading.Thread(target=self._punch_thread, daemon=True).start()

    def _punch_thread(self):
        print(f"[DEBUG] Tentative de Hole Punching vers {self.net.target_ip}:{self.net.target_port}")
        self.net.socket.setblocking(False)
        for _ in range(PUNCH_ATTEMPTS):
            self.net.send({'type': 'hello', 'content': self.player_name})
            time.sleep(PUNCH_INTERVAL)
        print("[DEBUG] Paquets de perçage envoyés. Démarrage du chrono de fallback...")
        self._check_fallback()

    def _punch_specific(self, target_ip: str, target_port: int):
        print(f"[DEBUG HOST] Perçage Internet vers {target_ip}:{target_port}")
        dummy_addr = (target_ip, target_port)
        if not self.net.get_client_name(dummy_addr):
            self.net.add_client(dummy_addr, "Connecting...")
        for _ in range(PUNCH_ATTEMPTS):
            self.net.send({'type': 'hello', 'content': self.player_name}, dummy_addr)
            time.sleep(PUNCH_INTERVAL)

    def _check_fallback(self):
        for _ in range(int(FALLBACK_TIMEOUT * 10)):
            if self.connected: return
            time.sleep(0.1)

        if not self.connected:
            print("SYSTEM : P2P non établi. Basculement sur le Relais Serveur (TURN)...")
            self.net.enable_full_relay()
            self.net.send({'type': 'fallback', 'content': self.player_name})
            self._retry_hello_via_relay()

    def _retry_hello_via_relay(self):
        for _ in range(10):
            if self.connected: return
            self.net.send({'type': 'hello', 'content': self.player_name})
            time.sleep(0.5)

    # ──────────────────────────────────────────
    # Utilitaires & Sync
    # ──────────────────────────────────────────

    def broadcast(self, message: dict, ignore_addr=None):
        for addr in self.net.get_clients_snapshot():
            if addr != ignore_addr:
                self.net.send(message, addr)

    def spawn(self, name: str, pos: list):
        if name not in self.other_players and name != self.player_name:
            model = self.base.loader.loadModel("./assets/dog.bam")
            model.reparentTo(self.base.render)
            model.setPos(*pos)
            self.other_players[name] = model

    # FIX ASYMETRIE : Nouvelle méthode pour renvoyer la totalité de l'état du monde
    def _sync_state_to(self, target_addr: tuple, target_name: str):
        """Force l'envoi de l'Hôte et des autres joueurs vers un client (idéal après un basculement relais)."""
        self.net.send({'type': 'spawn', 'content': {
            'name': self.player_name,
            'pos': list(self.local_player.player.getPos()),
        }}, target_addr)
        
        for other_name, model in self.other_players.items():
            if other_name != target_name:
                self.net.send({'type': 'spawn', 'content': {
                    'name': other_name,
                    'pos': list(model.getPos()),
                }}, target_addr)

    # ──────────────────────────────────────────
    # Handlers de messages (dispatch pattern)
    # ──────────────────────────────────────────

    def _on_punch_target(self, msg: dict, sender_id: str, addr: tuple):
        if self.is_host:
            threading.Thread(
                target=self._punch_specific,
                args=(msg.get('ip'), msg.get('port')),
                daemon=True,
            ).start()

    def _on_fallback(self, msg: dict, sender_id: str, addr: tuple):
        if not self.is_host:
            return
        client_name = msg.get('content')
        for client_addr, c_name in self.net.get_clients_snapshot().items():
            if c_name in (client_name, "Connecting..."):
                print(f"[DEBUG HOST] Relais ciblé activé pour {client_addr}")
                self.net.add_relay_client(client_addr)
                self.net.add_client(client_addr, client_name)
                
                # FIX ASYMETRIE : On renvoie immédiatement l'état via le relais qui vient d'être activé
                self._sync_state_to(client_addr, client_name)
                return
                
        self.net.enable_full_relay()

    def _on_hello(self, msg: dict, sender_id: str, addr: tuple):
        if sender_id not in ("Connecting...", "unknown"):
            if self.is_host and self._is_lan_addr(addr[0]):
                stale = [k for k, v in self.net.get_clients_snapshot().items()
                         if v in (sender_id, "Connecting...")]
                self.net.replace_client(stale, addr, sender_id)
            else:
                self.net.add_client(addr, sender_id)

            if self.is_host:
                self.net.send({'type': 'hello', 'content': self.player_name}, addr)

        # Affichage du message de connexion uniquement pour le client
        if not self.connected and not self.is_host:
            self.connected = True
            is_lan = (self.is_local
                      or self._is_lan_addr(self.net.target_ip or "")
                      or self._is_lan_addr(addr[0]))
            mode = ("Relais (TURN)" if self.net.use_full_relay
                    else ("Réseau Local/LAN" if is_lan else "P2P Internet"))
            print(f"SYSTEM : Connecté au salon ! (Mode : {mode})")

        name = msg.get('content')
        if name:
            if name not in self.other_players:
                self.spawn(name, [0, 0, 0])
                print(f"SYSTEM : {name} a rejoint la partie.")
                
                if self.is_host:
                    self.broadcast(
                        {'type': 'spawn', 'content': {'name': name, 'pos': [0, 0, 0]}},
                        ignore_addr=addr,
                    )
                    # FIX ASYMETRIE : On utilise le sync complet plutôt qu'un seul spawn
                    self._sync_state_to(addr, name)
                else:
                    self.net.send(
                        {'type': 'spawn', 'content': {
                            'name': self.player_name,
                            'pos': list(self.local_player.player.getPos()),
                        }},
                        addr,
                    )
            elif self.is_host:
                # FIX ASYMETRIE : Si le joueur est déjà là, on renvoie tout pour rattraper 
                # les paquets P2P qui ont pu être perdus par le NAT strict.
                self._sync_state_to(addr, name)

    def _on_spawn(self, msg: dict, sender_id: str, addr: tuple):
        if not self.connected and not self.is_host:
            self.connected = True
            print("SYSTEM : Connecté au salon !")
        data = msg.get('content', {})
        if data.get('name') and data.get('pos'):
            self.spawn(data['name'], data['pos'])

    def _on_update(self, msg: dict, sender_id: str, addr: tuple):
        name    = msg.get('name')
        content = msg.get('content')

        if self.is_host and self._is_lan_addr(addr[0]):
            if not self.net.get_client_name(addr):
                stale = [k for k, v in self.net.get_clients_snapshot().items()
                         if v in (name, "Connecting...")]
                self.net.replace_client(stale, addr, name)

        if name in self.other_players and content and len(content) == 2:
            pos, hpr = content
            self.other_players[name].setPos(*pos)
            self.other_players[name].setHpr(*hpr)

        if self.is_host:
            self.broadcast(msg, ignore_addr=addr)

    def _on_leave(self, msg: dict, sender_id: str, addr: tuple):
        name = msg.get('name', sender_id)
        if name in self.other_players:
            print(f"SYSTEM : {name} a quitté la partie.")
            self.other_players[name].removeNode()
            del self.other_players[name]
        if self.is_host:
            self.broadcast(msg, ignore_addr=addr)

    # ──────────────────────────────────────────
    # Boucle de jeu
    # ──────────────────────────────────────────

    def _send_heartbeat(self):
        if self.is_local or not self.game_code:
            return
        if time.time() - self.last_heartbeat <= 15.0:
            return

        if self.is_host:
            self.net.send({"action": "ping"}, (SIGNALING_IP, SIGNALING_PORT))
        elif self.client_id:
            self.net.send(
                {"action": "ping", "code": self.game_code, "clientId": self.client_id},
                (SIGNALING_IP, SIGNALING_PORT),
            )
        self.last_heartbeat = time.time()

    def _broadcast_position(self):
        if not self.connected:
            return
        pos = self.local_player.player.getPos()
        hpr = self.local_player.modelNode.getHpr()
        if pos == self.last_player_pos:
            return

        self.last_player_pos = pos
        update_msg = {
            'type':    'update',
            'name':    self.player_name,
            'v_ip':    self._local_ip if not self.is_host else None,
            'content': [(pos.x, pos.y, pos.z), (hpr.x, hpr.y, hpr.z)],
        }
        if self.net.use_full_relay:
            self.net.send(update_msg)
        elif self.is_host:
            self.broadcast(update_msg)
        else:
            self.net.send(update_msg)

    def update(self):
        self._send_heartbeat()
        for msg, sender_id, addr in self.net.receive():
            
            # Dispatch propre vers les handlers _on_*
            handler = {
                'punch_target': self._on_punch_target,
                'fallback':     self._on_fallback,
                'hello':        self._on_hello,
                'spawn':        self._on_spawn,
                'update':       self._on_update,
                'leave':        self._on_leave,
            }.get(msg.get('type'))
            
            if handler:
                handler(msg, sender_id, addr)
                
        self._broadcast_position()

    def exit(self):
        leave_msg = {'type': 'leave', 'content': None, 'name': self.player_name}
        if self.net.use_full_relay:
            self.net.send(leave_msg)
        else:
            for client_addr in self.net.get_clients_snapshot():
                self.net.send(leave_msg, client_addr)

        if self.game_code and not self.is_local:
            if self.is_host:
                self.net.send(
                    {"action": "close_lobby", "code": self.game_code},
                    (SIGNALING_IP, SIGNALING_PORT),
                )
            else:
                self.net.send(
                    {"action": "leave", "code": self.game_code},
                    (SIGNALING_IP, SIGNALING_PORT),
                )

        try:
            self.net.socket.close()
        except Exception:
            pass
