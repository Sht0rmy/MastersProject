extends Node

@onready var socket: Node = $SocketClient


func _ready() -> void:
	socket.connected_to_server.connect(_on_connected)
	socket.response_received.connect(_on_response)
	socket.connection_failed.connect(_on_failed)


func _on_connected() -> void:
	print("Main: з'єднання встановлено, надсилаю ping...")
	socket.ping()


func _on_response(data: Dictionary) -> void:
	print("Main: відповідь від сервера: ", data)
	# { "status": "ok", "action": "pong" }


func _on_failed() -> void:
	push_error("Main: не вдалось підключитись до Python")


func _input(event: InputEvent) -> void:
	# Натисни P для ручного ping під час тестування
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_P:
			socket.ping()
