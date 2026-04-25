from dataclasses import dataclass, field, asdict
from typing import Any


# ─── Вхідні запити від Godot ──────────────────────────────────────────────────

@dataclass
class GenerateRequest:
    seed: int = 42
    size: int = 20

    @staticmethod
    def from_dict(d: dict) -> "GenerateRequest":
        return GenerateRequest(
            seed=d.get("seed", 42),
            size=d.get("size", 20),
        )


# ─── Вихідні дані до Godot ────────────────────────────────────────────────────

@dataclass
class Room:
    id: int
    x: int
    y: int
    w: int
    h: int
    type: str = "generic"          # combat | treasure | boss | entrance | generic
    center: tuple[int, int] = field(default_factory=lambda: (0, 0))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "type": self.type,
            "center": list(self.center),
        }


@dataclass
class Corridor:
    from_room: int
    to_room: int
    path: list[list[int]] = field(default_factory=list)  # [[x,y], ...]

    def to_dict(self) -> dict:
        return {
            "from": self.from_room,
            "to": self.to_room,
            "path": self.path,
        }


@dataclass
class NPC:
    id: int
    room_id: int
    x: int
    y: int
    kind: str = "skeleton"         # skeleton | goblin | boss | merchant
    hp: int = 10

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LootItem:
    id: int
    room_id: int
    x: int
    y: int
    kind: str = "gold"             # gold | sword | potion | key
    value: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DungeonResponse:
    rooms: list[Room] = field(default_factory=list)
    corridors: list[Corridor] = field(default_factory=list)
    npcs: list[NPC] = field(default_factory=list)
    loot: list[LootItem] = field(default_factory=list)
    flavor: str = ""
    seed: int = 0
    status: str = "ok"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "seed": self.seed,
            "rooms": [r.to_dict() for r in self.rooms],
            "corridors": [c.to_dict() for c in self.corridors],
            "npcs": [n.to_dict() for n in self.npcs],
            "loot": [l.to_dict() for l in self.loot],
            "flavor": self.flavor,
        }


# ─── Службові відповіді ───────────────────────────────────────────────────────

def ok(action: str, **kwargs) -> dict:
    return {"status": "ok", "action": action, **kwargs}


def error(message: str) -> dict:
    return {"status": "error", "message": message}