import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
log = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 9000


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    log.info(f"Godot підключився: {addr}")

    try:
        while True:
            # Читаємо довжину повідомлення (4 байти, big-endian)
            header = await reader.readexactly(4)
            msg_len = int.from_bytes(header, "big")

            # Читаємо тіло повідомлення
            raw = await reader.readexactly(msg_len)
            request = json.loads(raw.decode("utf-8"))
            log.info(f"Отримано: {request}")

            response = await process_request(request)

            # Відповідаємо з тим самим length-prefix протоколом
            payload = json.dumps(response).encode("utf-8")
            writer.write(len(payload).to_bytes(4, "big") + payload)
            await writer.drain()
            log.info(f"Відповідь надіслана: {response}")

    except asyncio.IncompleteReadError:
        log.info(f"Godot відключився: {addr}")
    except Exception as e:
        log.error(f"Помилка: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def process_request(request: dict) -> dict:
    action = request.get("action")

    if action == "ping":
        return {"status": "ok", "action": "pong"}

    # Заглушки для майбутніх модулів
    if action == "generate":
        return {
            "status": "ok",
            "action": "generate",
            "rooms": [],
            "npcs": [],
            "loot": [],
            "flavor": "",
        }

    return {"status": "error", "message": f"Невідома дія: {action}"}


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    log.info(f"TCP сервер запущено на {HOST}:{PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())