import asyncio
import json
import logging

from protocol import GenerateRequest, DungeonResponse, ok, error

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
            log.info(f"Відповідь надіслана: {response}")

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
    # Заглушка — повертає порожній данжен
    # Буде замінено на реальний генератор у наступному кроці
    response = DungeonResponse(seed=req.seed)
    log.info(f"Generate запит: seed={req.seed}, size={req.size}")
    return response.to_dict()


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    log.info(f"TCP сервер запущено на {HOST}:{PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())