extends Node

@onready var socket: Node = $SocketClient
@onready var dungeon_loader: Node2D = $DungeonLoader


func _ready() -> void:
	socket.connected_to_server.connect(_on_connected)
	socket.response_received.connect(_on_response)


func _on_connected() -> void:
	print("Main: підключено, надсилаю ping...")
	socket.ping()


func _on_response(data: Dictionary) -> void:
	var action: String = data.get("action", "")
	var status: String = data.get("status", "")

	match action:
		"pong":
			print("Main: pong отримано — зв'язок працює! Натисни G для генерації.")

		"generate":
			if status == "ok":
				_handle_dungeon(data)
			else:
				push_error("Main: помилка генерації — " + data.get("message", ""))

		_:
			push_warning("Main: невідома відповідь: %s" % str(data))


func _handle_dungeon(data: Dictionary) -> void:
	var rooms: Array = data.get("rooms", [])
	var corridors: Array = data.get("corridors", [])
	var dungeon_seed: int = data.get("seed", 0)

	print("Main: данжен отримано — seed=%d, rooms=%d, corridors=%d" % [
		dungeon_seed, rooms.size(), corridors.size()
	])

	dungeon_loader.render_dungeon(data)


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_P:
				socket.ping()
			KEY_G:
				var dungeon_seed := randi()
				print("Main: генерація, seed=%d" % dungeon_seed)
				socket.request_generate(dungeon_seed, 40)
