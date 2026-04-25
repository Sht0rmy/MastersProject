extends Node

@onready var socket: Node = $SocketClient


func _ready() -> void:
	socket.connected_to_server.connect(_on_connected)
	socket.response_received.connect(_on_response)


func _on_connected() -> void:
	print("Main: з'єднання встановлено, надсилаю ping...")
	socket.ping()


func _on_response(data: Dictionary) -> void:
	var action: String = data.get("action", "")
	var status: String = data.get("status", "")

	print("Main: відповідь [%s] status=%s" % [action, status])

	match action:
		"pong":
			print("  Pong отримано — зв'язок працює!")

		"generate":
			_handle_dungeon(data)

		_:
			push_warning("Main: невідома відповідь: %s" % str(data))


func _handle_dungeon(data: Dictionary) -> void:
	var rooms: Array = data.get("rooms", [])
	var corridors: Array = data.get("corridors", [])
	var npcs: Array = data.get("npcs", [])
	var loot: Array = data.get("loot", [])
	var seed: int = data.get("seed", 0)

	print("  Данжен отримано: seed=%d, rooms=%d, corridors=%d, npcs=%d, loot=%d" % [
		seed, rooms.size(), corridors.size(), npcs.size(), loot.size()
	])
	# TODO: передати дані в DungeonLoader → TileMap


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_P:
				socket.ping()
			KEY_G:
				# G — згенерувати данжен з випадковим seed
				var seed := randi()
				print("Main: запит на генерацію, seed=%d" % seed)
				socket.request_generate(seed, 20)
