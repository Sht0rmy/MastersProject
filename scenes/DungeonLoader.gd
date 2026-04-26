extends Node2D

@onready var tilemap: TileMap = $TileMap

const TILE_SIZE := 16

const LAYER_FLOOR := 0
const LAYER_WALL  := 1

# source_id атласу в TileSet (зазвичай 0)
const SOURCE_ID := 0

# Координати тайлів в атласі (column, row)
const TILE_WALL     := Vector2i(0, 0)
const TILE_FLOOR    := Vector2i(1, 0)
const TILE_CORRIDOR := Vector2i(1, 0)
const TILE_ENTRANCE := Vector2i(2, 0)
const TILE_TREASURE := Vector2i(3, 0)
const TILE_COMBAT   := Vector2i(0, 1)


func render_dungeon(data: Dictionary) -> void:
	print("DungeonLoader: render_dungeon викликано, tilemap=", tilemap)
	tilemap.clear()

	var corridors: Array = data.get("corridors", [])
	var rooms: Array     = data.get("rooms", [])

	for corridor in corridors:
		_draw_corridor(corridor)

	for room in rooms:
		_draw_room(room)

	_center_camera(rooms)

	print("DungeonLoader: намальовано rooms=%d corridors=%d" % [rooms.size(), corridors.size()])


func _draw_room(room: Dictionary) -> void:
	var x := int(room.get("x", 0))
	var y := int(room.get("y", 0))
	var w := int(room.get("w", 0))
	var h := int(room.get("h", 0))
	var type: String = room.get("type", "generic")
	var floor_tile := _floor_tile_for_type(type)

	for ty in range(y, y + h):
		for tx in range(x, x + w):
			var is_wall := (tx == x or tx == x + w - 1 or ty == y or ty == y + h - 1)
			if is_wall:
				tilemap.set_cell(LAYER_WALL, Vector2i(tx, ty), SOURCE_ID, TILE_WALL)
			else:
				tilemap.set_cell(LAYER_FLOOR, Vector2i(tx, ty), SOURCE_ID, floor_tile)


func _draw_corridor(corridor: Dictionary) -> void:
	var path: Array = corridor.get("path", [])
	for point in path:
		var tx := int(point[0])
		var ty := int(point[1])
		tilemap.set_cell(LAYER_FLOOR, Vector2i(tx, ty), SOURCE_ID, TILE_CORRIDOR)


func _floor_tile_for_type(type: String) -> Vector2i:
	match type:
		"entrance": return TILE_ENTRANCE
		"treasure": return TILE_TREASURE
		"combat":   return TILE_COMBAT
		_:          return TILE_FLOOR


func _center_camera(rooms: Array) -> void:
	if rooms.is_empty():
		return

	var min_x := INF
	var min_y := INF
	var max_x := -INF
	var max_y := -INF

	for room in rooms:
		min_x = min(min_x, float(room.get("x", 0)))
		min_y = min(min_y, float(room.get("y", 0)))
		max_x = max(max_x, float(int(room.get("x", 0)) + int(room.get("w", 0))))
		max_y = max(max_y, float(int(room.get("y", 0)) + int(room.get("h", 0))))

	var center_x := (min_x + max_x) / 2.0 * TILE_SIZE
	var center_y := (min_y + max_y) / 2.0 * TILE_SIZE
	var viewport_size := get_viewport().get_visible_rect().size
	position = Vector2(
		viewport_size.x / 2.0 - center_x,
		viewport_size.y / 2.0 - center_y
	)
