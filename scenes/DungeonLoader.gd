extends Node2D

@onready var tilemap: TileMap = $TileMap

const TILE_SIZE := 16
const LAYER_FLOOR := 0
const LAYER_WALL  := 1
const SOURCE_ID   := 1

# Тайли підлоги
const TILE_WALL     := Vector2i(0, 0)
const TILE_FLOOR    := Vector2i(1, 0)
const TILE_CORRIDOR := Vector2i(1, 0)
const TILE_ENTRANCE := Vector2i(2, 0)
const TILE_TREASURE := Vector2i(1, 4)
const TILE_COMBAT   := Vector2i(0, 1)

# Тайли NPC (ряд 3 в тайлсеті — персонажі)
const TILE_NPC_SKELETON := Vector2i(1, 9)
const TILE_NPC_GOBLIN   := Vector2i(0, 9)
const TILE_NPC_BOSS     := Vector2i(2, 9)
const TILE_NPC_MERCHANT := Vector2i(0, 7)
const TILE_NPC_DEFAULT  := Vector2i(4, 7)

# Тайли луту (ряд 4)
const TILE_LOOT_GOLD    := Vector2i(5, 8)
const TILE_LOOT_SWORD   := Vector2i(8, 8)
const TILE_LOOT_POTION  := Vector2i(7, 9)
const TILE_LOOT_KEY     := Vector2i(10, 10)

const LAYER_NPC  := 2
const LAYER_LOOT := 3

# Зберігаємо всі тайли підлоги для перевірки при побудові стін коридору
var _floor_cells: Dictionary = {}


func render_dungeon(data: Dictionary) -> void:
	tilemap.clear()
	_floor_cells.clear()

	var corridors: Array = data.get("corridors", [])
	var rooms: Array     = data.get("rooms", [])
	var npcs: Array      = data.get("npcs", [])
	var loot: Array      = data.get("loot", [])

	# 1. Збираємо всі тайли підлоги кімнат
	for room in rooms:
		_collect_room_floor(room)

	# 2. Малюємо підлогу коридорів
	for corridor in corridors:
		_draw_corridor_floor(corridor)

	# 3. Малюємо стіни коридорів
	for corridor in corridors:
		_draw_corridor_walls(corridor)

	# 4. Малюємо кімнати (підлога + стіни)
	for room in rooms:
		_draw_room(room)

	# 5. Малюємо NPC
	for npc in npcs:
		_draw_npc(npc)

	# 6. Малюємо лут
	for item in loot:
		_draw_loot(item)

	_center_camera(rooms)
	print("DungeonLoader: намальовано rooms=%d corridors=%d npcs=%d loot=%d" % [
		rooms.size(), corridors.size(), npcs.size(), loot.size()
	])


# ─── Кімнати ──────────────────────────────────────────────────────────────────

func _collect_room_floor(room: Dictionary) -> void:
	var x := int(room.get("x", 0))
	var y := int(room.get("y", 0))
	var w := int(room.get("w", 0))
	var h := int(room.get("h", 0))
	for ty in range(y, y + h):
		for tx in range(x, x + w):
			_floor_cells[Vector2i(tx, ty)] = true


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
				# Прибираємо коридорну підлогу під стіною кімнати
				tilemap.erase_cell(LAYER_FLOOR, Vector2i(tx, ty))
			else:
				tilemap.set_cell(LAYER_FLOOR, Vector2i(tx, ty), SOURCE_ID, floor_tile)


# ─── Коридори ─────────────────────────────────────────────────────────────────

func _draw_corridor_floor(corridor: Dictionary) -> void:
	var path: Array = corridor.get("path", [])
	for point in path:
		var pos := Vector2i(int(point[0]), int(point[1]))
		# Малюємо підлогу тільки якщо це не стіна кімнати
		if not _is_room_wall(pos):
			tilemap.set_cell(LAYER_FLOOR, pos, SOURCE_ID, TILE_CORRIDOR)


func _draw_corridor_walls(corridor: Dictionary) -> void:
	var path: Array = corridor.get("path", [])
	var path_set: Dictionary = {}

	# Збираємо всі тайли коридору в set для швидкої перевірки
	for point in path:
		path_set[Vector2i(int(point[0]), int(point[1]))] = true

	# Для кожного тайлу коридору — перевіряємо сусідів (8 напрямків)
	for point in path:
		var cx := int(point[0])
		var cy := int(point[1])

		for dx in range(-1, 2):
			for dy in range(-1, 2):
				if dx == 0 and dy == 0:
					continue
				var neighbor := Vector2i(cx + dx, cy + dy)

				# Якщо сусід не є ні коридором ні кімнатою — ставимо стіну
				if not path_set.has(neighbor) and not _floor_cells.has(neighbor):
					# Не перезаписуємо вже існуючі стіни кімнат
					if tilemap.get_cell_source_id(LAYER_WALL, neighbor) == -1:
						tilemap.set_cell(LAYER_WALL, neighbor, SOURCE_ID, TILE_WALL)


func _is_room_wall(pos: Vector2i) -> bool:
	return tilemap.get_cell_source_id(LAYER_WALL, pos) != -1


# ─── NPC ──────────────────────────────────────────────────────────────────────

func _draw_npc(npc: Dictionary) -> void:
	var x := int(npc.get("x", 0))
	var y := int(npc.get("y", 0))
	var kind: String = npc.get("kind", "skeleton")
	var tile := _npc_tile(kind)
	tilemap.set_cell(LAYER_NPC, Vector2i(x, y), SOURCE_ID, tile)


func _npc_tile(kind: String) -> Vector2i:
	match kind:
		"skeleton": return TILE_NPC_SKELETON
		"goblin":   return TILE_NPC_GOBLIN
		"boss":     return TILE_NPC_BOSS
		"merchant": return TILE_NPC_MERCHANT
		_:          return TILE_NPC_DEFAULT


# ─── Лут ──────────────────────────────────────────────────────────────────────

func _draw_loot(item: Dictionary) -> void:
	var x := int(item.get("x", 0))
	var y := int(item.get("y", 0))
	var kind: String = item.get("kind", "gold")
	var tile := _loot_tile(kind)
	tilemap.set_cell(LAYER_LOOT, Vector2i(x, y), SOURCE_ID, tile)


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
	var center_x := (min_x + max_x) / 2.0 * TILE_SIZE
	var center_y := (min_y + max_y) / 2.0 * TILE_SIZE
	var vp := get_viewport().get_visible_rect().size
	position = Vector2(vp.x / 2.0 - center_x, vp.y / 2.0 - center_y)
