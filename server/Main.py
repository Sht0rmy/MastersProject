import asyncio
import json
import logging
import random

from protocol import GenerateRequest, DungeonResponse, ok, error
from dungeon import generate_bsp, build_corridors
from placement import place_npcs, place_loot
from csp import ac3, build_neighbor_graph

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 9000


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    log.info(f"Godot підключився: {addr}")

    try:
        while True:
            header = await reader.readexactly(4)
            msg_len = int.from_bytes(header, "big")

            raw = await reader.readexactly(msg_len)
            request = json.loads(raw.decode("utf-8"))
            log.info(f"Отримано: {request}")

            response = await process_request(request)

            payload = json.dumps(response, ensure_ascii=False).encode("utf-8")
            writer.write(len(payload).to_bytes(4, "big") + payload)
            await writer.drain()
            log.info(
                f"Відповідь: rooms={len(response.get('rooms', []))}, "
                f"corridors={len(response.get('corridors', []))}, "
                f"npcs={len(response.get('npcs', []))}, "
                f"loot={len(response.get('loot', []))}"
            )

    except asyncio.IncompleteReadError:
        log.info(f"Godot відключився: {addr}")
    except json.JSONDecodeError as e:
        log.error(f"JSON помилка: {e}")
    except Exception as e:
        log.error(f"Помилка: {e}", exc_info=True)
    finally:
        writer.close()
        await writer.wait_closed()


async def process_request(request: dict) -> dict:
    action = request.get("action")

    if action == "ping":
        return ok("pong")

    if action == "generate":
        req = GenerateRequest.from_dict(request)
        return await handle_generate(req)

    return error(f"Невідома дія: {action}")


async def handle_generate(req: GenerateRequest) -> dict:
    log.info(f"Генерація: seed={req.seed}, size={req.size}")
    rng = random.Random(req.seed)

    # 1. BSP — кімнати
    result = generate_bsp(size=req.size, seed=req.seed)

    # 2. A* — коридори
    corridors = build_corridors(result.pairs, grid_w=req.size, grid_h=req.size)

    # 3. AC-3 — призначаємо типи кімнат з урахуванням constraints
    neighbor_graph = build_neighbor_graph(corridors)
    room_types = ac3(result.rooms, neighbor_graph, rng)

    # Застосовуємо типи до кімнат
    for room in result.rooms:
        room.type = room_types.get(room.id, "generic")

    log.info(f"AC-3 типи: { {v: sum(1 for t in room_types.values() if t == v) for v in set(room_types.values())} }")

    # 4. NPC placement
    npcs = place_npcs(result.rooms, rng)

    # 5. Loot placement
    occupied = {(n.x, n.y) for n in npcs}
    loot = place_loot(result.rooms, occupied, rng)

    # 6. Збираємо відповідь
    response = DungeonResponse(
        seed  = req.seed,
        rooms = result.rooms,
        npcs  = npcs,
        loot  = loot,
    )

    data = response.to_dict()
    data["corridors"] = corridors
    data["action"]    = "generate"
    return data


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    log.info(f"TCP сервер запущено на {HOST}:{PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())