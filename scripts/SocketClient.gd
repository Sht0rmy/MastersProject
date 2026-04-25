extends Node

## TCP клієнт для зв'язку з Python сервером
## Протокол: [4 байти довжина big-endian][JSON payload]

signal response_received(data: Dictionary)
signal connection_failed()
signal connected_to_server()

const HOST := "127.0.0.1"
const PORT := 9000
const RECONNECT_DELAY := 2.0

var _tcp := StreamPeerTCP.new()
var _connected := false
var _recv_buffer := PackedByteArray()


func _ready() -> void:
	set_process(true)
	_connect_to_server()


func _connect_to_server() -> void:
	var err := _tcp.connect_to_host(HOST, PORT)
	if err != OK:
		push_error("SocketClient: не вдалось підключитись — %d" % err)
		_schedule_reconnect()


func _process(_delta: float) -> void:
	_tcp.poll()
	var status := _tcp.get_status()

	match status:
		StreamPeerTCP.STATUS_CONNECTED:
			if not _connected:
				_connected = true
				print("SocketClient: підключено до Python сервера")
				connected_to_server.emit()
			_try_read()

		StreamPeerTCP.STATUS_NONE, StreamPeerTCP.STATUS_ERROR:
			if _connected:
				_connected = false
				push_warning("SocketClient: з'єднання втрачено, перепідключення...")
				_schedule_reconnect()


func _try_read() -> void:
	var available := _tcp.get_available_bytes()
	if available <= 0:
		return

	_recv_buffer.append_array(_tcp.get_data(available)[1])

	while _recv_buffer.size() >= 4:
		var msg_len := (
			(_recv_buffer[0] << 24)
			| (_recv_buffer[1] << 16)
			| (_recv_buffer[2] << 8)
			| _recv_buffer[3]
		)

		if _recv_buffer.size() < 4 + msg_len:
			break

		var body := _recv_buffer.slice(4, 4 + msg_len)
		_recv_buffer = _recv_buffer.slice(4 + msg_len)

		var json_str := body.get_string_from_utf8()
		var parsed: Variant = JSON.parse_string(json_str)

		if parsed is Dictionary:
			response_received.emit(parsed)
		else:
			push_error("SocketClient: не вдалось розпарсити JSON: %s" % json_str)


func send_request(data: Dictionary) -> void:
	if not _connected:
		push_warning("SocketClient: не підключено, запит скинуто")
		return

	var json_str := JSON.stringify(data)
	var payload := json_str.to_utf8_buffer()
	var header := PackedByteArray()
	header.resize(4)
	var size := payload.size()
	header[0] = (size >> 24) & 0xFF
	header[1] = (size >> 16) & 0xFF
	header[2] = (size >> 8) & 0xFF
	header[3] = size & 0xFF

	_tcp.put_data(header + payload)


func ping() -> void:
	send_request({"action": "ping"})


func request_generate(seed: int = 42, size: int = 20) -> void:
	send_request({
		"action": "generate",
		"seed": seed,
		"size": size,
	})


func _schedule_reconnect() -> void:
	_connected = false
	await get_tree().create_timer(RECONNECT_DELAY).timeout
	_tcp = StreamPeerTCP.new()
	_connect_to_server()
