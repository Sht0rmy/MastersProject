extends Node2D

@onready var tilemap: TileMap = $TileMap

const TILE_SIZE := 16
const LAYER_FLOOR := 0
const LAYER_WALL  := 1
const LAYER_NPC   := 2
const LAYER_LOOT  := 3
const SOURCE_ID   := 1

# Підлога
const TILE_FLOOR    := Vector2i(0, 0)
const TILE_CORRIDOR := Vector2i(1, 0)
const TILE_ENTRANCE := Vector2i(2, 0)
const TILE_TREASURE := Vector2i(3, 0)
const TILE_COMBAT   := Vector2i(0, 1)
const TILE_MERCHANT := Vector2i(3, 1)

# Стіни та двері
const TILE_WALL := Vector2i(4, 3)
const TILE_DOOR := Vector2i(9, 3)

# NPC
const TILE_NPC_SKELETON := Vector2i(1, 9)
const TILE_NPC_GOBLIN   := Vector2i(0, 9)
const TILE_NPC_BOSS     := Vector2i(2, 9)
const TILE_NPC_MERCHANT := Vector2i(0, 7)

# Лут
const TILE_LOOT_GOLD    := Vector2i(5, 8)
const TILE_LOOT_SWORD   := Vector2i(8, 8)
const TILE_LOOT_POTION  := Vector2i(7, 9)
const TILE_LOOT_KEY     := Vector2i(10, 10)

var _floor_cells: Dictionary = {}
var _corridor_cells: Dictionary = {}
var _room_wall_cells: Dictionary = {}


func render_dungeon(data: Dictionary) -> void:
	tilemap.clear()
	_floor_cells.clear()
	_corridor_cells.clear()
	_room_wall_cells.clear()

	var corridors: Array = data.get("corridors", [])
	var rooms: Array     = data.get("rooms", [])
	var npcs: Array      = data.get("npcs", [])
	var loot: Array      = data.get("loot", [])

	# 1. Збираємо метадані кімнат
	for room in rooms:
		_collect_room_data(room)

	# 2. Збираємо ВСІ тайли всіх коридорів одразу
	for corridor in corridors:
		for point in corridor.get("path", []):
			_corridor_cells[Vector2i(int(point[0]), int(point[1]))] = true

	# 3. Підлога коридорів
	for corridor in corridors:
		_draw_corridor_floor(corridor)

	# 4. Стіни коридорів
	for corridor in corridors:
		_draw_corridor_walls(corridor)

	# 5. Кімнати поверх
	for room in rooms:
		_draw_room(room)

	# 6. Двері — тільки перший і останній тайл коридору що торкається стіни
	for corridor in corridors:
		_punch_doorways(corridor)

	# 7. NPC та лут
	for npc in npcs:
		_draw_npc(npc)
	for item in loot:
		_draw_loot(item)

	_center_camera(rooms)
	print("DungeonLoader: rooms=%d corridors=%d npcs=%d loot=%d" % [
		rooms.size(), corridors.size(), npcs.size(), loot.size()
	])


# ─── Збір метаданих ───────────────────────────────────────────────────────────

func _collect_room_data(room: Dictionary) -> void:
	var x := int(room.get("x", 0))
	var y := int(room.get("y", 0))
	var w := int(room.get("w", 0))
	var h := int(room.get("h", 0))
	for ty in range(y, y + h):
		for tx in range(x, x + w):
			var pos := Vector2i(tx, ty)
			var is_wall := (tx == x or tx == x + w - 1 or ty == y or ty == y + h - 1)
			if is_wall:
				_room_wall_cells[pos] = true
			else:
				_floor_cells[pos] = true


# ─── Коридори ─────────────────────────────────────────────────────────────────

func _draw_corridor_floor(corridor: Dictionary) -> void:
	for point in corridor.get("path", []):
		var pos := Vector2i(int(point[0]), int(point[1]))
		if not _room_wall_cells.has(pos) and not _floor_cells.has(pos):
			tilemap.set_cell(LAYER_FLOOR, pos, SOURCE_ID, TILE_CORRIDOR)


func _draw_corridor_walls(corridor: Dictionary) -> void:
	for point in corridor.get("path", []):
		var pos := Vector2i(int(point[0]), int(point[1]))
		for dx in range(-1, 2):
			for dy in range(-1, 2):
				if dx == 0 and dy == 0:
					continue
				var nb := Vector2i(pos.x + dx, pos.y + dy)
				if _corridor_cells.has(nb):
					continue
				if _floor_cells.has(nb):
					continue
				if _room_wall_cells.has(nb):
					continue
				if tilemap.get_cell_source_id(LAYER_WALL, nb) == -1:
					tilemap.set_cell(LAYER_WALL, nb, SOURCE_ID, TILE_WALL)


# ─── Кімнати ──────────────────────────────────────────────────────────────────

func _draw_room(room: Dictionary) -> void:
	var x := int(room.get("x", 0))
	var y := int(room.get("y", 0))
	var w := int(room.get("w", 0))
	var h := int(room.get("h", 0))
	var floor_tile := _floor_tile_for_type(room.get("type", "generic"))

	for ty in range(y, y + h):
		for tx in range(x, x + w):
			var pos := Vector2i(tx, ty)
			var is_wall := (tx == x or tx == x + w - 1 or ty == y or ty == y + h - 1)
			if is_wall:
				tilemap.set_cell(LAYER_WALL, pos, SOURCE_ID, TILE_WALL)
				tilemap.erase_cell(LAYER_FLOOR, pos)
			else:
				tilemap.set_cell(LAYER_FLOOR, pos, SOURCE_ID, floor_tile)
				tilemap.erase_cell(LAYER_WALL, pos)


# ─── Двері ────────────────────────────────────────────────────────────────────

func _punch_doorways(corridor: Dictionary) -> void:
	var path: Array = corridor.get("path", [])
	if path.size() < 2:
		return

	# Шукаємо перехід: підлога кімнати → стіна кімнати (вихід з кімнати)
	# і стіна кімнати → підлога кімнати (вхід в кімнату)
	var door_positions: Array[Vector2i] = []

	for i in range(1, path.size()):
		var prev := Vector2i(int(path[i-1][0]), int(path[i-1][1]))
		var curr := Vector2i(int(path[i][0]),   int(path[i][1]))

		# Перехід підлога→стіна або стіна→підлога = місце дверей
		var prev_is_floor := _floor_cells.has(prev)
		var curr_is_wall  := _room_wall_cells.has(curr)
		var prev_is_wall  := _room_wall_cells.has(prev)
		var curr_is_floor := _floor_cells.has(curr)

		if (prev_is_floor and curr_is_wall) or (prev_is_wall and curr_is_floor):
			var door_pos := curr if curr_is_wall else prev
			if not door_positions.has(door_pos):
				door_positions.append(door_pos)

	for pos in door_positions:
		tilemap.set_cell(LAYER_WALL, pos, SOURCE_ID, TILE_DOOR)
		tilemap.set_cell(LAYER_FLOOR, pos, SOURCE_ID, TILE_CORRIDOR)


# ─── NPC та лут ───────────────────────────────────────────────────────────────

func _draw_npc(npc: Dictionary) -> void:
	var pos := Vector2i(int(npc.get("x", 0)), int(npc.get("y", 0)))
	tilemap.set_cell(LAYER_NPC, pos, SOURCE_ID, _npc_tile(npc.get("kind", "skeleton")))


func _npc_tile(kind: String) -> Vector2i:
	match kind:
		"skeleton": return TILE_NPC_SKELETON
		"goblin":   return TILE_NPC_GOBLIN
		"boss":     return TILE_NPC_BOSS
		"merchant": return TILE_NPC_MERCHANT
		_:          return TILE_NPC_SKELETON


func _draw_loot(item: Dictionary) -> void:
	var pos := Vector2i(int(item.get("x", 0)), int(item.get("y", 0)))
	tilemap.set_cell(LAYER_LOOT, pos, SOURCE_ID, _loot_tile(item.get("kind", "gold")))


func _loot_tile(kind: String) -> Vector2i:
	match kind:
		"gold":   return TILE_LOOT_GOLD
		"sword":  return TILE_LOOT_SWORD
		"potion": return TILE_LOOT_POTION
		"key":    return TILE_LOOT_KEY
		_:        return TILE_LOOT_GOLD


# ─── Утиліти ──────────────────────────────────────────────────────────────────

func _floor_tile_for_type(type: String) -> Vector2i:
	match type:
		"entrance": return TILE_ENTRANCE
		"treasure": return TILE_TREASURE
		"combat":   return TILE_COMBAT
		"merchant": return TILE_MERCHANT
		_:          return TILE_FLOOR


func _center_camera(rooms: Array) -> void:
	if rooms.is_empty():
		return
	var min_x := INF; var min_y := INF
	var max_x := -INF; var max_y := -INF
	for room in rooms:
		min_x = min(min_x, float(room.get("x", 0)))
		min_y = min(min_y, float(room.get("y", 0)))
		max_x = max(max_x, float(int(room.get("x", 0)) + int(room.get("w", 0))))
		max_y = max(max_y, float(int(room.get("y", 0)) + int(room.get("h", 0))))
	var cx := (min_x + max_x) / 2.0 * TILE_SIZE
	var cy := (min_y + max_y) / 2.0 * TILE_SIZE
	var vp := get_viewport().get_visible_rect().size
	position = Vector2(vp.x / 2.0 - cx, vp.y / 2.0 - cy)
