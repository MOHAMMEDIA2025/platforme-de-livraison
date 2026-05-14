from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # commande_id -> liste de WebSockets clients qui écoutent
        self.commande_rooms: Dict[int, List[WebSocket]] = {}
        # livreur_id -> WebSocket du livreur
        self.livreur_connections: Dict[int, WebSocket] = {}

    async def connect_client(self, websocket: WebSocket, commande_id: int):
        await websocket.accept()
        if commande_id not in self.commande_rooms:
            self.commande_rooms[commande_id] = []
        self.commande_rooms[commande_id].append(websocket)

    async def connect_livreur(self, websocket: WebSocket, livreur_id: int):
        await websocket.accept()
        self.livreur_connections[livreur_id] = websocket

    def disconnect_client(self, websocket: WebSocket, commande_id: int):
        if commande_id in self.commande_rooms:
            self.commande_rooms[commande_id].remove(websocket)

    def disconnect_livreur(self, livreur_id: int):
        self.livreur_connections.pop(livreur_id, None)

    async def broadcast_to_commande(self, commande_id: int, data: dict):
        """Envoie un message à tous les clients qui suivent cette commande"""
        if commande_id in self.commande_rooms:
            dead = []
            for ws in self.commande_rooms[commande_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.commande_rooms[commande_id].remove(ws)

manager = ConnectionManager()