# PacSnake - No Return
# A grid-based arcade game where Pac-Man leaves a fading trail you can't cross.
# The level is defined by a text map, and movement/AI stay aligned to tile centers.

import random
import arcade
from arcade import shape_list
from arcade.types import Color
from array import array
import math

# ----------------------------
# Core tuning constants
# ----------------------------
TILE = 28                     # Size of one grid tile in pixels
MOVE_SPEED = 4                # Player movement speed (pixels per frame)
GHOST_SPEED = 3               # Ghost movement speed (pixels per frame)
WAVE_BANNER_SECONDS = 2.0     # How long the "WAVE X" banner shows after a clear
GHOST_RELEASE_DELAY = 1.0     # Seconds after the player's first move before ghosts start
TURN_SNAP_PX = 5              # Turn assist tolerance (pixels) for snappy input
# This lets you buffer a turn a bit early so movement feels responsive.

# ----------------------------
# HUD styling
# ----------------------------
HUD_HEIGHT = 56
HUD_PADDING = 8
HUD_BG = (8, 12, 24)
HUD_PANEL = (16, 20, 36)
HUD_BORDER = (90, 110, 160)
HUD_LABEL = (170, 210, 255)
HUD_VALUE = (255, 230, 150)
HUD_SUBTEXT = (200, 200, 200)
HUD_FONT = ("Consolas", "Courier New", "Arial")

# ----------------------------
# Maze styling
# ----------------------------
FLOOR_BASE = (6, 9, 18)
FLOOR_ALT = (7, 10, 19)  # ultra-subtle checker tint
WALL_BASE = (10, 18, 45)
WALL_EDGE = (70, 140, 235, 90)  # inner edge, low alpha
WALL_INSET = 4
WALL_EDGE_WIDTH = 1.5
FLOOR_BASE_POWER = (4, 7, 14)
FLOOR_ALT_POWER = (5, 8, 15)
CORRIDOR_TINT = (12, 14, 20, 40)
CORRIDOR_TINT_POWER = (10, 12, 18, 40)
WALL_GLOW = (70, 140, 235)
WALL_GLOW_ALPHA_INNER = 45
WALL_GLOW_ALPHA_OUTER = 16
WALL_GLOW_SCALE_INNER = 1.6
WALL_GLOW_SCALE_OUTER = 2.0
WALL_GLOW_PULSE_PERIOD = 4.0
WALL_GLOW_PULSE_DEPTH = 0.12
WALL_GLOW_POWER_BOOST = 1.06

# ----------------------------
# Orb styling
# ----------------------------
ORB_SMALL_BASE = (235, 225, 205)
ORB_SMALL_GLOW = (255, 240, 215)
ORB_SMALL_GLOW_ALPHA = 45
ORB_SMALL_GLOW_SCALE = 1.48
ORB_SMALL_PULSE_PERIOD = 0.7
ORB_SMALL_MIN_BRIGHT = 0.92
ORB_SMALL_PULSE_DEPTH = 0.08

ORB_BIG_CORE = (235, 250, 255)
ORB_BIG_GLOW = (70, 140, 235)
ORB_BIG_GLOW_ALPHA = 120
ORB_BIG_GLOW_PULSE = 70
ORB_BIG_GLOW_SCALE = 1.6
ORB_BIG_PULSE_PERIOD = 0.8
ORB_BIG_SCALE_MIN = 0.9
ORB_BIG_SCALE_MAX = 1.1
ORB_RING_PERIOD = 1.0
ORB_RING_SPAN = 9
ORB_RING_ALPHA = 60
COIN_PULSE_STEP = 0.05
SHOW_FPS = True
TRAIL_LIFETIME = 1.15
TRAIL_GRACE = 0.15
TRAIL_ALPHA = 170
TRAIL_COLOR = (220, 190, 120)
TRAIL_RADIUS = 0.22  # as a fraction of TILE
TRAIL_WAVE_BONUS_PCT = 0.12
TRAIL_TOP_ROW_FIX = 6
TRAIL_TOP_HIT_BOOST = 1.25

# ----------------------------
# Level layout
#   # = wall
#   . = normal dot
#   o = power pellet
#   P = player spawn
#   G = ghost spawn
#   space = empty corridor
# ----------------------------
LEVEL_MAP = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.#####.##.#####.######",
    "      .#####.##.#####.      ", 
    "      .#####.##.#####.      ", 
    "######.##...GGGG...##.######",
    "######.##.###..###.##.######",
    "#............P.............#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......##.......##..o#",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

# ----------------------------
# Derived map dimensions and window dimensions
# ----------------------------
ROWS = len(LEVEL_MAP)
COLS = len(LEVEL_MAP[0])
SCREEN_W = COLS * TILE
SCREEN_H = ROWS * TILE + 60   # Extra space for HUD text at the top
TITLE = "PacSnake - No Return"

# ----------------------------
# Direction dictionary
# Each direction maps to a (dx, dy) in grid space, but we later apply it to pixels.
# ----------------------------
DIRS = {
    "U": (0, 1),
    "D": (0, -1),
    "L": (-1, 0),
    "R": (1, 0),
    "S": (0, 0),
}

# ----------------------------
# Chase/Scatter timing schedule, classic Pac-Man style feel
# Ghosts alternate between:
#   scatter: go to their corner targets
#   chase: target the player based on ghost personality
# ----------------------------
CHASE_SCATTER_SCHEDULE = [
    ("scatter", 7.0),
    ("chase", 20.0),
    ("scatter", 7.0),
    ("chase", 20.0),
    ("scatter", 5.0),
    ("chase", 20.0),
    ("scatter", 5.0),
    ("chase", 9999.0),
]

# ----------------------------
# High level game states
# Menu -> Playing -> Game Over transitions are handled in _start_game/_lose_life.
# ----------------------------
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"

# ----------------------------
# Movement / Grid helpers
#   grid_to_world: (col,row) -> (x,y) in pixels
#   world_to_grid: (x,y) in pixels -> (col,row)
# These keep movement and AI aligned to the grid even while sprites move per frame.
# ----------------------------
# Convert a grid cell (col,row) into the pixel center for drawing/movement.
def grid_to_world(c, r):
    """Convert grid cell (col,row) into the pixel center used for drawing/movement.
    Keeps sprites locked to tile centers for clean intersections.
    """
    x = c * TILE + TILE / 2
    y = (ROWS - 1 - r) * TILE + TILE / 2
    return x, y

# Convert a world pixel position into its grid cell (col,row).
def world_to_grid(x, y):
    """Convert pixel position into LEVEL_MAP grid coordinates.
    Used so movement/AI decisions snap to tiles, not raw pixels.
    """
    c = int(x // TILE)
    r = ROWS - 1 - int(y // TILE)
    return c, r

# Returns True when a sprite is very close to the center of a tile
# Used to only allow turning and AI decisions at intersections for clean movement
# True when a sprite is near a tile center (clean turns + AI decisions).
def at_tile_center(x, y):
    """True when a position is close enough to a tile center.
    This is the safe window to allow turning and AI direction changes.
    """
    return (abs((x - TILE / 2) % TILE) < 1.2) and (abs((y - TILE / 2) % TILE) < 1.2)

# Rotate a 2D point around origin by angle (radians).
def _rotate_point(px, py, angle_rad):
    ca = math.cos(angle_rad)
    sa = math.sin(angle_rad)
    return px * ca - py * sa, px * sa + py * ca


# Map direction letter to angle in radians.
def _dir_angle(d):
    if d == "R":
        return 0.0
    if d == "U":
        return math.pi / 2
    if d == "L":
        return math.pi
    if d == "D":
        return -math.pi / 2
    return 0.0



# ----------------------------
# Small math helpers used by ghost AI
# ----------------------------
# Clamp a value to a [lo, hi] range.
def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# Brightness scale for an RGB/RGBA color.
def _scale_color(color, factor):
    r = int(clamp(color[0] * factor, 0, 255))
    g = int(clamp(color[1] * factor, 0, 255))
    b = int(clamp(color[2] * factor, 0, 255))
    if len(color) == 4:
        return (r, g, b, color[3])
    return (r, g, b)


# Return same RGB color with a new alpha.
def _with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)

# Opposite direction, used for no reverse rule and frightened reversal
# Opposite direction helper (no-reverse rule).
def opp_dir(d):
    if d == "U":
        return "D"
    if d == "D":
        return "U"
    if d == "L":
        return "R"
    if d == "R":
        return "L"
    return "S"

# Manhattan distance in grid cells, used for choosing best direction to target
# Manhattan distance in grid cells (pathing heuristic).
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# Checks if a grid cell is not a wall and inside bounds
# True if a grid cell is inside the map and not a wall.
def is_walkable_cell(c, r):
    """True when a cell is inside bounds and not a wall."""
    if r < 0 or r >= ROWS or c < 0 or c >= COLS:
        return False
    return LEVEL_MAP[r][c] != "#"

# Wrap the column if the row is a tunnel row (open on both left and right edges)
# This supports the classic "exit one side, appear on the other" behavior at grid level
# Apply tunnel wrap for open left/right edges.
def wrap_cell_if_tunnel(c, r):
    """Wrap columns only on rows that have open left/right edges.
    This matches classic tunnel behavior and prevents accidental wrap.
    """
    if r in {rr for rr in range(ROWS) if LEVEL_MAP[rr][0] != "#" and LEVEL_MAP[rr][COLS - 1] != "#"}:
        if c < 0:
            return COLS - 1, r
        if c >= COLS:
            return 0, r
    return c, r


# ----------------------------
# Sprite classes
# Using simple shapes for visuals
# ----------------------------
# Wall tile sprite (solid block).
class Wall(arcade.SpriteSolidColor):
    """Wall tile: blocks movement and defines the maze layout."""
    # A single solid block wall tile
    def __init__(self, x, y):
        super().__init__(TILE, TILE, WALL_BASE)
        self.center_x = x
        self.center_y = y

# Dot / power pellet sprite, with pulse metadata.
class Coin(arcade.SpriteSolidColor):
    """Dot/pellet state: value and pulse timing for visuals."""
    # Dot or power pellet
    # value controls score and also acts as a simple way to detect power pellets (50)
    def __init__(self, x, y, value=10, big=False):
        size = 12 if big else 7
        super().__init__(size, size, arcade.color.WHITE)
        self.center_x = x
        self.center_y = y
        self.value = value
        self.big = big
        self.pulse_offset = random.random() * 10.0
        self.pulse_value = 0.0

# Player sprite + score/lives + mouth animation state.
class Player(arcade.Sprite):
    """Player state: score/lives + direction buffering + mouth animation."""
    def __init__(self, x, y, lives=3):
        super().__init__()
        self.width = TILE - 6
        self.height = TILE - 6
        self.center_x = x
        self.center_y = y
        self.score = 0
        self.lives = lives
        self.dir = "S"        # Current movement direction
        self.want_dir = "S"   # Buffered desired direction from input

        self.mouth_open = True
        self.mouth_timer = 0.0
        self.mouth_period = 0.12

    def update_mouth(self, dt, is_moving):
        if not is_moving:
            self.mouth_open = True
            self.mouth_timer = 0.0
            return
        self.mouth_timer += dt
        if self.mouth_timer >= self.mouth_period:
            self.mouth_timer = 0.0
            self.mouth_open = not self.mouth_open

    def draw(self):
        r = self.width / 2
        cx = self.center_x
        cy = self.center_y

        arcade.draw_circle_filled(cx, cy, r, arcade.color.YELLOW)

        d = self.dir
        if d == "S":
            d = self.want_dir
        if d == "S":
            d = "R"

        if self.mouth_open:
            ang = _dir_angle(d)

            p1 = (r * 1.05, 0.0)
            p2 = (r * 0.2, r * 0.65)
            p3 = (r * 0.2, -r * 0.65)

            x1, y1 = _rotate_point(p1[0], p1[1], ang)
            x2, y2 = _rotate_point(p2[0], p2[1], ang)
            x3, y3 = _rotate_point(p3[0], p3[1], ang)

            arcade.draw_polygon_filled(
                [(cx, cy), (cx + x2, cy + y2), (cx + x1, cy + y1), (cx + x3, cy + y3)],
                arcade.color.BLACK
            )


# Ghost sprite with AI metadata, respawn, and visuals.
class Enemy(arcade.Sprite):
    """Ghost state: AI type, scatter target, and respawn timers."""
    def __init__(self, x, y, ghost_type, color, scatter_target):
        super().__init__()
        self.width = TILE - 6
        self.height = TILE - 6
        self.center_x = x
        self.center_y = y
        self.start_x = x
        self.start_y = y
        self.ghost_type = ghost_type
        self.color = color
        self.base_color = color
        self.scatter_target = scatter_target
        self.dir = random.choice(["U", "D", "L", "R"])
        self.respawn_timer = 0.0
        self.is_dead = False
        self.exit_timer = 0.0

    def draw(self):
        w = self.width
        h = self.height
        cx = self.center_x
        cy = self.center_y
        col = self.color

        top_r = w * 0.5
        top_cy = cy + h * 0.15

        arcade.draw_circle_filled(cx, top_cy, top_r, col)

        rect_w = w
        rect_h = h * 0.55
        rect_cy = cy - h * 0.15
        arcade.draw_rect_filled(arcade.XYWH(cx, rect_cy, rect_w, rect_h), col)

        bump_r = w * 0.18
        bump_y = cy - h * 0.42
        arcade.draw_circle_filled(cx - w * 0.28, bump_y, bump_r, col)
        arcade.draw_circle_filled(cx, bump_y, bump_r, col)
        arcade.draw_circle_filled(cx + w * 0.28, bump_y, bump_r, col)

        eye_r = w * 0.14
        eye_y = cy + h * 0.10
        eye_x1 = cx - w * 0.16
        eye_x2 = cx + w * 0.16

        arcade.draw_circle_filled(eye_x1, eye_y, eye_r, arcade.color.WHITE)
        arcade.draw_circle_filled(eye_x2, eye_y, eye_r, arcade.color.WHITE)

        pdx, pdy = 0.0, 0.0
        if self.dir == "R":
            pdx = eye_r * 0.35
        elif self.dir == "L":
            pdx = -eye_r * 0.35
        elif self.dir == "U":
            pdy = eye_r * 0.35
        elif self.dir == "D":
            pdy = -eye_r * 0.35

        pupil_r = eye_r * 0.45
        arcade.draw_circle_filled(eye_x1 + pdx, eye_y + pdy, pupil_r, arcade.color.BLACK)
        arcade.draw_circle_filled(eye_x2 + pdx, eye_y + pdy, pupil_r, arcade.color.BLACK)



# Main game window and all gameplay systems.
class PacmanGame(arcade.Window):
    """Main game window: owns sprites, timers, and core game state."""
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE)
        arcade.set_background_color(FLOOR_BASE)

        # SpriteLists store and draw/update groups efficiently
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        self.coins = arcade.SpriteList(use_spatial_hash=True)
        self.ghosts = arcade.SpriteList()
        self.player_list = arcade.SpriteList()
        self.floor_shapes = shape_list.ShapeElementList()
        self.wall_base_shapes = shape_list.ShapeElementList()
        self.wall_edge_shapes = shape_list.ShapeElementList()
        self.wall_glow_shapes = shape_list.ShapeElementList()
        self.corridor_shapes = shape_list.ShapeElementList()

        # Core entities
        self.player = None
        self.spawn_pos = (0, 0)
        self.ghost_spawn_positions = []

        # Timers and game state
        self.power_mode_timer = 0.0     # > 0 means ghosts are frightened and edible
        self.state = STATE_MENU
        self.end_timer = 0.0
        self.wave = 1
        self.banner_timer = WAVE_BANNER_SECONDS

        # Tunnel rows are any rows where both ends are open (not '#')
        self.tunnel_rows = {r for r in range(ROWS) if LEVEL_MAP[r][0] != "#" and LEVEL_MAP[r][COLS - 1] != "#"}  # Open edge rows

        # Mode system for chase/scatter cycling
        self.mode_index = 0
        self.ghost_mode = CHASE_SCATTER_SCHEDULE[0][0]
        self.mode_timer = CHASE_SCATTER_SCHEDULE[0][1]

        #fps counter
        self.fps_value = 0
        self.fps_accum_time = 0.0
        self.fps_accum_frames = 0
        self.game_time = 0.0
        self.glow_update_timer = 0.0
        self.glow_intensity = 1.0
        self.coin_pulse_timer = 0.0
        # Trail uses two structures: segments for drawing, cells for collisions.
        self.trail_segments = []
        self.trail_cells = {}  # Map of visited cells -> timestamp (fast grid collision checks)
        self.last_trail_cell = None
        self.trail_skip_next = False
        # Ghosts wait for the player's first move, then delay briefly before moving.
        self.ghost_wait_for_move = True
        self.ghost_hold_timer = 0.0

        # Build level once at start
        self._build_level()
        self._update_coin_pulses(COIN_PULSE_STEP)
        self._build_static_layers()
        self.power_mode_active = False
        self._update_wall_edge_colors(False)
        self._update_floor_colors(False)
        self._update_wall_glow(1.0)

        self.ghost_house_pos = self.ghost_spawn_positions[0] if len(self.ghost_spawn_positions) > 0 else self.spawn_pos
    

    # ----------------------------
    # Ghost AI helpers (grid based)
    # ----------------------------
    # Convert sprite world position to grid cell.
    def _cell_of_sprite(self, spr):
        """Return (col,row) for a sprite. Keeps AI decisions grid-aligned."""
        # Convert sprite world position to grid cell
        return world_to_grid(spr.center_x, spr.center_y)

    # Player grid cell convenience.
    def _player_cell(self):
        """Player grid cell helper. Used heavily by ghost targeting."""
        # Player grid cell
        return self._cell_of_sprite(self.player)

    # Direction letter -> (dx,dy) unit vector.
    def _dir_to_vec(self, d):
        """Direction char -> (dx,dy) unit vector in grid space."""
        # Convert direction char to (dx,dy)
        return DIRS[d]

    # Walk n cells ahead, stopping at walls (used by Pinky/Inky).
    def _cell_ahead(self, cell, direction, n):
        """Walk n grid cells ahead, stopping at walls.
        Used for Pinky/Inky style targeting.
        """
        # Walk n cells forward in a direction, stopping if we hit a wall
        # Used for Pinky and Inky targeting behavior
        dx, dy = self._dir_to_vec(direction)
        c, r = cell
        for _ in range(n):
            nc = c + dx
            nr = r - dy
            nc, nr = wrap_cell_if_tunnel(nc, nr)
            if not is_walkable_cell(nc, nr):
                return c, r
            c, r = nc, nr
        return c, r

    # Valid movement directions from a cell (intersections).
    def _valid_dirs_from_cell(self, cell):
        """List valid movement directions from a grid cell.
        Keeps turns and AI decisions inside walkable space.
        """
        # Returns all valid movement directions out of a grid cell
        # Used for intersection decisions
        c, r = cell
        options = []
        for d in ["U", "D", "L", "R"]:
            dx, dy = self._dir_to_vec(d)
            nc = c + dx
            nr = r - dy
            nc, nr = wrap_cell_if_tunnel(nc, nr)
            if is_walkable_cell(nc, nr):
                options.append(d)
        return options

    # Choose a direction toward a target cell (or random if frightened).
    def _choose_dir_to_target(self, ghost, target_cell, frightened=False):
        """Pick a direction toward a target tile, respecting no-reverse rule.
        Frightened mode chooses randomly among valid options.
        """
        # Core direction chooser:
        # - At intersections, pick the direction that minimizes distance to target
        # - Avoid reversing unless forced
        # - In frightened mode, move randomly but still valid
        cell = self._cell_of_sprite(ghost)
        options = self._valid_dirs_from_cell(cell)
        if len(options) == 0:
            return "S"

        back = opp_dir(ghost.dir)
        if len(options) > 1 and back in options:
            options.remove(back)

        if frightened:
            return random.choice(options)

        best = None
        best_score = None
        for d in options:
            dx, dy = self._dir_to_vec(d)
            nc = cell[0] + dx
            nr = cell[1] - dy
            nc, nr = wrap_cell_if_tunnel(nc, nr)
            score = manhattan((nc, nr), target_cell)
            if best is None or score < best_score:
                best = d
                best_score = score
            elif score == best_score and random.random() < 0.35:
                best = d

        return best if best is not None else random.choice(options)

    # Compute ghost chase target based on ghost personality.
    def _ghost_target_cell(self, ghost):
        """Return the chase target tile for each ghost personality.
        Scatter mode overrides chase and sends them to corners.
        """
        # Computes the chase target tile depending on ghost personality
        # Scatter mode overrides all and returns ghost.corner target
        p_cell = self._player_cell()
        p_dir = self.player.dir if self.player.dir != "S" else self.player.want_dir
        if p_dir == "S":
            p_dir = "L"

        if self.ghost_mode == "scatter":
            return ghost.scatter_target

        if ghost.ghost_type == "blinky":
            # Red: direct chase of player tile
            return p_cell

        if ghost.ghost_type == "pinky":
            # Pink: aims 4 tiles ahead of player direction
            return self._cell_ahead(p_cell, p_dir, 4)

        if ghost.ghost_type == "inky":
            # Cyan: vector targeting using Blinky and a point 2 tiles ahead
            blinky = None
            for g in self.ghosts:
                if g.ghost_type == "blinky":
                    blinky = g
                    break
            two_ahead = self._cell_ahead(p_cell, p_dir, 2)
            if blinky is None:
                return two_ahead
            b_cell = self._cell_of_sprite(blinky)
            vx = two_ahead[0] - b_cell[0]
            vy = two_ahead[1] - b_cell[1]
            tc = (two_ahead[0] + vx, two_ahead[1] + vy)
            return (clamp(tc[0], 0, COLS - 1), clamp(tc[1], 0, ROWS - 1))

        if ghost.ghost_type == "clyde":
            # Orange: chases unless close, then scatters
            g_cell = self._cell_of_sprite(ghost)
            if manhattan(g_cell, p_cell) <= 6:
                return ghost.scatter_target
            return p_cell

        return p_cell

    # Advance chase/scatter schedule and reverse ghosts on mode switch.
    def _update_mode_timer(self, dt):
        """Advance chase/scatter schedule and reverse ghosts on mode switch."""
        # Advances chase/scatter schedule over time
        # When switching modes, reverse ghost direction (classic behavior)
        self.mode_timer -= dt
        if self.mode_timer > 0:
            return
        self.mode_index = min(self.mode_index + 1, len(CHASE_SCATTER_SCHEDULE) - 1)
        self.ghost_mode = CHASE_SCATTER_SCHEDULE[self.mode_index][0]
        self.mode_timer = CHASE_SCATTER_SCHEDULE[self.mode_index][1]
        for g in self.ghosts:
            if not g.is_dead:
                g.dir = opp_dir(g.dir)


    # ----------------------------
    # Level building and resets
    # ----------------------------
    # Parse LEVEL_MAP and create walls, coins, player, and ghost spawns.
    def _build_level(self):
        """Parse LEVEL_MAP into walls, coins, player spawn, and ghost spawns."""
        # Read LEVEL_MAP and spawn walls, coins, player, and ghost spawn points
        for r in range(ROWS):
            for c in range(COLS):
                ch = LEVEL_MAP[r][c]
                x, y = grid_to_world(c, r)
                if ch == "#":
                    self.walls.append(Wall(x, y))
                elif ch == ".":
                    self.coins.append(Coin(x, y, value=10, big=False))
                elif ch == "o":
                    self.coins.append(Coin(x, y, value=50, big=True))
                elif ch == "P":
                    self.player = Player(x, y, lives=3)
                    self.spawn_pos = (x, y)
                elif ch == "G":
                    self.ghost_spawn_positions.append((x, y))

        # Add player sprite to the list so it gets drawn
        self.player_list.append(self.player)

        # Ghost definitions:
        # Each ghost gets a type (behavior), a color, and a scatter corner target
        ghost_defs = [
            ("blinky", arcade.color.RED, (COLS - 2, 1)),
            ("pinky", arcade.color.PINK, (1, 1)),
            ("inky", arcade.color.CYAN, (COLS - 2, ROWS - 2)),
            ("clyde", arcade.color.ORANGE, (1, ROWS - 2)),
        ]

        # Spawn ghosts using the map G positions and rotate through the 4 ghost types
        for i, (x, y) in enumerate(self.ghost_spawn_positions):
            gt, col, scat = ghost_defs[i % len(ghost_defs)]
            self.ghosts.append(Enemy(x, y, gt, col, scat))

    # Prebuild static floor/wall/glow layers for fast rendering.
    def _build_static_layers(self):
        """Prebuild floor/wall/glow shapes for faster drawing each frame."""
        self.floor_shapes = shape_list.ShapeElementList()
        self.wall_base_shapes = shape_list.ShapeElementList()
        self.wall_edge_shapes = shape_list.ShapeElementList()
        self.wall_glow_shapes = shape_list.ShapeElementList()

        for r in range(ROWS):
            for c in range(COLS):
                if (r + c) % 2 != 0:
                    x, y = grid_to_world(c, r)
                    self.floor_shapes.append(
                        shape_list.create_rectangle_filled(x, y, TILE, TILE, FLOOR_ALT)
                    )
                if LEVEL_MAP[r][c] != "#":
                    x, y = grid_to_world(c, r)
                    self.corridor_shapes.append(
                        shape_list.create_rectangle_filled(x, y, TILE, TILE, CORRIDOR_TINT)
                    )

        def is_wall_cell(c, r):
            return 0 <= r < ROWS and 0 <= c < COLS and LEVEL_MAP[r][c] == "#"

        inner_w = TILE - WALL_INSET * 2
        inner_h = TILE - WALL_INSET * 2
        edge_half = WALL_EDGE_WIDTH / 2
        glow_outer_w = TILE * WALL_GLOW_SCALE_OUTER
        glow_outer_h = TILE * WALL_GLOW_SCALE_OUTER
        glow_inner_w = TILE * WALL_GLOW_SCALE_INNER
        glow_inner_h = TILE * WALL_GLOW_SCALE_INNER
        for wall in self.walls:
            c, r = world_to_grid(wall.center_x, wall.center_y)
            open_up = not is_wall_cell(c, r - 1)
            open_down = not is_wall_cell(c, r + 1)
            open_left = not is_wall_cell(c - 1, r)
            open_right = not is_wall_cell(c + 1, r)
            is_boundary = open_up or open_down or open_left or open_right

            if is_boundary:
                outer = shape_list.create_rectangle_filled(
                    wall.center_x,
                    wall.center_y,
                    glow_outer_w,
                    glow_outer_h,
                    (WALL_GLOW[0], WALL_GLOW[1], WALL_GLOW[2], WALL_GLOW_ALPHA_OUTER),
                )
                outer._base_alpha = WALL_GLOW_ALPHA_OUTER
                self.wall_glow_shapes.append(outer)

                inner = shape_list.create_rectangle_filled(
                    wall.center_x,
                    wall.center_y,
                    glow_inner_w,
                    glow_inner_h,
                    (WALL_GLOW[0], WALL_GLOW[1], WALL_GLOW[2], WALL_GLOW_ALPHA_INNER),
                )
                inner._base_alpha = WALL_GLOW_ALPHA_INNER
                self.wall_glow_shapes.append(inner)

            self.wall_base_shapes.append(
                shape_list.create_rectangle_filled(wall.center_x, wall.center_y, TILE, TILE, WALL_BASE)
            )
            if inner_w > 0 and inner_h > 0 and is_boundary:
                if open_up:
                    self.wall_edge_shapes.append(
                        shape_list.create_rectangle_filled(
                            wall.center_x,
                            wall.center_y + inner_h / 2 - edge_half,
                            inner_w,
                            WALL_EDGE_WIDTH,
                            WALL_EDGE,
                        )
                    )
                if open_down:
                    self.wall_edge_shapes.append(
                        shape_list.create_rectangle_filled(
                            wall.center_x,
                            wall.center_y - inner_h / 2 + edge_half,
                            inner_w,
                            WALL_EDGE_WIDTH,
                            WALL_EDGE,
                        )
                    )
                if open_left:
                    self.wall_edge_shapes.append(
                        shape_list.create_rectangle_filled(
                            wall.center_x - inner_w / 2 + edge_half,
                            wall.center_y,
                            WALL_EDGE_WIDTH,
                            inner_h,
                            WALL_EDGE,
                        )
                    )
                if open_right:
                    self.wall_edge_shapes.append(
                        shape_list.create_rectangle_filled(
                            wall.center_x + inner_w / 2 - edge_half,
                            wall.center_y,
                            WALL_EDGE_WIDTH,
                            inner_h,
                            WALL_EDGE,
                        )
                    )

    # Update a ShapeElement color buffer (Arcade 3.3 compatible).
    def _set_shape_color(self, shape, color):
        """Update a ShapeElement's color buffer (Arcade 3.3 compatibility)."""
        new_color = Color.from_iterable(color)
        shape.colors = [new_color] * len(shape.points)
        shape.data = array("f", [c for a in zip(shape.points, shape.colors) for b in a for c in b])

    # Boost wall inner edge when power mode is active.
    def _update_wall_edge_colors(self, power_active):
        """Boost wall edge brightness during power mode for mood shift."""
        edge_alpha = WALL_EDGE[3]
        if power_active:
            edge_alpha = min(255, edge_alpha + 40)
        edge_color = (WALL_EDGE[0], WALL_EDGE[1], WALL_EDGE[2], edge_alpha)
        for shape in self.wall_edge_shapes:
            self._set_shape_color(shape, edge_color)
        self.wall_edge_shapes.dirties.update(self.wall_edge_shapes.batches.values())

    # Adjust wall glow alpha for slow neon pulsing.
    def _update_wall_glow(self, intensity):
        """Update wall glow alpha for slow neon pulsing."""
        intensity = clamp(intensity, 0.0, 2.0)
        if abs(intensity - self.glow_intensity) < 0.03:
            return
        self.glow_intensity = intensity
        for shape in self.wall_glow_shapes:
            base_alpha = getattr(shape, "_base_alpha", WALL_GLOW_ALPHA_INNER)
            new_alpha = int(clamp(base_alpha * intensity, 0, 255))
            self._set_shape_color(shape, (WALL_GLOW[0], WALL_GLOW[1], WALL_GLOW[2], new_alpha))
        self.wall_glow_shapes.dirties.update(self.wall_glow_shapes.batches.values())

    # Cache orb pulse values at a fixed step for performance.
    def _update_coin_pulses(self, dt):
        """Cache orb pulse values at a fixed cadence (keeps FPS stable)."""
        self.coin_pulse_timer += dt
        if self.coin_pulse_timer < COIN_PULSE_STEP:
            return
        self.coin_pulse_timer = 0.0
        for coin in self.coins:
            period = ORB_BIG_PULSE_PERIOD if coin.big else ORB_SMALL_PULSE_PERIOD
            coin.pulse_value = 0.5 + 0.5 * math.sin(
                (self.game_time + coin.pulse_offset) * (2 * math.pi / period)
            )

    # Darken floor slightly during power mode (mood shift).
    def _update_floor_colors(self, power_active):
        """Swap floor tints during power mode for subtle mood change."""
        base_color = FLOOR_BASE_POWER if power_active else FLOOR_BASE
        alt_color = FLOOR_ALT_POWER if power_active else FLOOR_ALT
        corridor_color = CORRIDOR_TINT_POWER if power_active else CORRIDOR_TINT
        arcade.set_background_color(base_color)
        for shape in self.floor_shapes:
            self._set_shape_color(shape, alt_color)
        self.floor_shapes.dirties.update(self.floor_shapes.batches.values())
        for shape in self.corridor_shapes:
            self._set_shape_color(shape, corridor_color)
        self.corridor_shapes.dirties.update(self.corridor_shapes.batches.values())

    # Clear all trail segments (death/reset).
    def _clear_trail(self):
        """Clear all trail data (used on death/reset)."""
        self.trail_segments = []
        self.trail_cells = {}
        self.last_trail_cell = None
        self.trail_skip_next = False

    # True while player is off-screen in tunnel wrap.
    def _in_tunnel_transit(self):
        """True while the player is off-screen in a tunnel wrap.
        Trail and collisions are paused during this transit.
        """
        if self.player is None:
            return False
        r = ROWS - 1 - int(self.player.center_y // TILE)
        if r not in self.tunnel_rows:
            return False
        return self.player.center_x < 0 or self.player.center_x > SCREEN_W

    # Trail lifetime scales by wave.
    def _trail_lifetime(self):
        """Trail lifetime scales by wave for difficulty ramp."""
        return TRAIL_LIFETIME * (1.0 + (self.wave - 1) * TRAIL_WAVE_BONUS_PCT)

    # Remove expired trail segments.
    def _update_trail(self):
        """Prune expired trail segments and grid cells."""
        lifetime = self._trail_lifetime()
        cutoff = self.game_time - lifetime
        self.trail_segments = [seg for seg in self.trail_segments if seg["t"] >= cutoff]
        self.trail_cells = {k: t for k, t in self.trail_cells.items() if t >= cutoff}

    # Add a new trail segment at the given grid cell.
    def _add_trail_segment_cell(self, c, r):
        """Record a trail cell and report collision if it's already occupied.
        Uses grid occupancy to avoid pixel-precision false hits.
        """
        if self._in_tunnel_transit():
            return False
        cell = (c, r)
        if cell in self.trail_cells:
            if (self.game_time - self.trail_cells[cell]) >= TRAIL_GRACE:
                return True
        self.trail_cells[cell] = self.game_time
        if self.last_trail_cell == cell:
            return False
        self.last_trail_cell = cell
        cx, cy = grid_to_world(c, r)
        self.trail_segments.append({"x": cx, "y": cy, "t": self.game_time, "c": c, "r": r})
        return False

    # Add a new trail segment at the current grid cell.
    def _add_trail_segment(self, x, y):
        """Add a trail segment based on current pixel position."""
        c, r = world_to_grid(x, y)
        return self._add_trail_segment_cell(c, r)

    # Check player collision against the trail (after grace window).
    def _check_trail_collision(self):
        """Geometry-based trail collision (kept for reference)."""
        if self.power_mode_timer > 0:
            return False
        if self._in_tunnel_transit():
            return False
        if not self.trail_segments:
            return False
        px = self.player.center_x
        py = self.player.center_y
        pc, pr = world_to_grid(px, py)
        pc, pr = wrap_cell_if_tunnel(pc, pr)

        player_r = self.player.width / 2
        trail_r = TILE * TRAIL_RADIUS
        line_w = max(2, trail_r * 2)
        hit_point = player_r + trail_r
        hit_line = player_r + line_w / 2
        if pr <= TRAIL_TOP_ROW_FIX:
            hit_point *= TRAIL_TOP_HIT_BOOST
            hit_line *= TRAIL_TOP_HIT_BOOST

        # Circle test against segment centers
        for seg in self.trail_segments:
            age = self.game_time - seg["t"]
            if age < TRAIL_GRACE:
                continue
            dx = px - seg["x"]
            dy = py - seg["y"]
            if dx * dx + dy * dy <= hit_point * hit_point:
                return True

        # Line test between adjacent segments (only if both are out of grace)
        prev = None
        for seg in self.trail_segments:
            if prev is not None:
                prev_age = self.game_time - prev["t"]
                age = self.game_time - seg["t"]
                prev_new = prev_age < TRAIL_GRACE
                seg_new = age < TRAIL_GRACE
                if not prev_new and not seg_new:
                    adjacent = abs(prev["c"] - seg["c"]) + abs(prev["r"] - seg["r"]) == 1
                    if adjacent:
                        ax, ay = prev["x"], prev["y"]
                        bx, by = seg["x"], seg["y"]
                        abx = bx - ax
                        aby = by - ay
                        apx = px - ax
                        apy = py - ay
                        ab_len2 = abx * abx + aby * aby
                        if ab_len2 > 0:
                            t = (apx * abx + apy * aby) / ab_len2
                            t = clamp(t, 0.0, 1.0)
                            cx = ax + abx * t
                            cy = ay + aby * t
                            dx = px - cx
                            dy = py - cy
                            if dx * dx + dy * dy <= hit_line * hit_line:
                                return True
            prev = seg
        return False

    # Draw trail as connected path with fading alpha.
    def _draw_trail(self):
        """Draw trail visuals only; collision uses grid occupancy elsewhere."""
        if not self.trail_segments:
            return
        radius = TILE * TRAIL_RADIUS
        line_width = max(2, radius * 2)
        lifetime = self._trail_lifetime()
        prev = None
        prev_alpha = None
        for seg in self.trail_segments:
            age = self.game_time - seg["t"]
            if age >= lifetime:
                continue
            alpha = int(TRAIL_ALPHA * (1.0 - age / lifetime))
            if alpha <= 0:
                continue
            color = (TRAIL_COLOR[0], TRAIL_COLOR[1], TRAIL_COLOR[2], alpha)
            if prev is not None:
                adjacent = abs(prev["c"] - seg["c"]) + abs(prev["r"] - seg["r"]) == 1
                if adjacent:
                    line_alpha = alpha if prev_alpha is None else min(alpha, prev_alpha)
                    line_color = (TRAIL_COLOR[0], TRAIL_COLOR[1], TRAIL_COLOR[2], line_alpha)
                    arcade.draw_line(prev["x"], prev["y"], seg["x"], seg["y"], line_color, line_width)
            glow_alpha = int(alpha * 0.25)
            if glow_alpha > 0:
                glow_color = (TRAIL_COLOR[0], TRAIL_COLOR[1], TRAIL_COLOR[2], glow_alpha)
                arcade.draw_circle_filled(seg["x"], seg["y"], radius * 1.35, glow_color)
            arcade.draw_circle_filled(seg["x"], seg["y"], radius, color)
            prev = seg
            prev_alpha = alpha

    # Small Pac-Man icon for menus.
    def _draw_pac_icon(self, x, y, r, facing):
        arcade.draw_circle_filled(x, y, r, (255, 220, 40))

        ang = _dir_angle(facing)

        mouth = 0.55
        reach = r * 1.28

        x1 = x + reach * math.cos(ang + mouth)
        y1 = y + reach * math.sin(ang + mouth)
        x2 = x + reach * math.cos(ang - mouth)
        y2 = y + reach * math.sin(ang - mouth)

        arcade.draw_polygon_filled([(x, y), (x1, y1), (x2, y2)], (0, 0, 0, 190))
        arcade.draw_circle_outline(x, y, r, (255, 245, 170, 120), 2)



    # Start menu screen (title + controls).
    def _draw_start_menu(self):
        self.clear()
        self._draw_floor()
        self.wall_glow_shapes.draw()
        self.wall_base_shapes.draw()
        self.wall_edge_shapes.draw()

        overlay_rect = arcade.XYWH(SCREEN_W / 2, SCREEN_H / 2, SCREEN_W, SCREEN_H)
        arcade.draw_rect_filled(overlay_rect, (0, 0, 0, 190))

        title_y = SCREEN_H / 2 + 96
        title_text = "PacSnake - No Return"
        title_size = 36
        gap = 14
        icon_r = 18
        title_obj = arcade.Text(
            title_text,
            0,
            0,
            arcade.color.WHITE,
            title_size,
            font_name=HUD_FONT,
            anchor_x="left",
        )
        group_w = icon_r * 2 + gap + title_obj.content_width
        group_x = SCREEN_W / 2 - group_w / 2
        icon_y = title_y + title_obj.content_height * 0.29
        self._draw_pac_icon(group_x + icon_r, icon_y, icon_r, "R")
        arcade.draw_text(
            title_text,
            group_x + icon_r * 2 + gap,
            title_y,
            arcade.color.WHITE,
            title_size,
            font_name=HUD_FONT,
            anchor_x="left",
        )
        arcade.draw_text(
            "Your path is the danger",
            SCREEN_W / 2,
            SCREEN_H / 2 + 35,
            HUD_SUBTEXT,
            14,
            font_name=HUD_FONT,
            anchor_x="center",
        )
        arcade.draw_text(
            "[ ENTER ]  START",
            SCREEN_W / 2,
            SCREEN_H / 2 - 5,
            arcade.color.WHITE,
            18,
            font_name=HUD_FONT,
            anchor_x="center",
        )
        arcade.draw_text(
            "[ ESC ]  EXIT",
            SCREEN_W / 2,
            SCREEN_H / 2 - 35,
            HUD_SUBTEXT,
            14,
            font_name=HUD_FONT,
            anchor_x="center",
        )

    # Game over screen (score + restart/exit).
    def _draw_game_over(self):
        self.clear()
        self._draw_floor()
        self.wall_glow_shapes.draw()
        self.wall_base_shapes.draw()
        self.wall_edge_shapes.draw()

        overlay_rect = arcade.XYWH(SCREEN_W / 2, SCREEN_H / 2, SCREEN_W, SCREEN_H)
        arcade.draw_rect_filled(overlay_rect, (0, 0, 0, 190))

        arcade.draw_text(
            "GAME OVER",
            SCREEN_W / 2,
            SCREEN_H / 2 + 50,
            arcade.color.RED,
            34,
            font_name=HUD_FONT,
            anchor_x="center",
        )
        arcade.draw_text(
            "Score: {}".format(self.player.score),
            SCREEN_W / 2,
            SCREEN_H / 2 + 15,
            arcade.color.WHITE,
            18,
            font_name=HUD_FONT,
            anchor_x="center",
        )
        arcade.draw_text(
            "[ ENTER ]  RESTART",
            SCREEN_W / 2,
            SCREEN_H / 2 - 20,
            arcade.color.WHITE,
            16,
            font_name=HUD_FONT,
            anchor_x="center",
        )
        arcade.draw_text(
            "[ ESC ]  EXIT",
            SCREEN_W / 2,
            SCREEN_H / 2 - 45,
            HUD_SUBTEXT,
            14,
            font_name=HUD_FONT,
            anchor_x="center",
        )


    # Rebuild only dots/pellets for a new wave.
    def _rebuild_coins(self):
        # Used for infinite waves:
        # Clears coin list and rebuilds from LEVEL_MAP without touching walls
        self.coins = arcade.SpriteList(use_spatial_hash=True)
        for r in range(ROWS):
            for c in range(COLS):
                ch = LEVEL_MAP[r][c]
                if ch == "." or ch == "o":
                    x, y = grid_to_world(c, r)
                    if ch == ".":
                        self.coins.append(Coin(x, y, value=10, big=False))
                    else:
                        self.coins.append(Coin(x, y, value=50, big=True))

    # Random non-wall world position (ghost respawn helper).
    def _get_random_empty_pos(self):
        # Picks a random non wall cell and returns its world coordinates
        # Used for ghost respawn after being eaten
        while True:
            c = random.randint(1, COLS - 2)
            r = random.randint(1, ROWS - 2)
            if LEVEL_MAP[r][c] != "#":
                return grid_to_world(c, r)

    # Enter a non-playing state and freeze player.
    def _start_end_screen(self, new_state):
        """Switch to menu/game over and stop player movement."""
        # Transition into game over state and stop player movement
        self.state = new_state
        self.end_timer = 0.0
        self.player.dir = "S"
        self.player.want_dir = "S"
        self._clear_trail()

    # Full game reset for a fresh run.
    def _reset_game(self):
        """Hard reset for a fresh run (score, wave, timers, positions)."""
        self.wave = 1
        self.banner_timer = 0.0
        self.power_mode_timer = 0.0
        self.power_mode_active = False
        self._update_wall_edge_colors(False)
        self._update_floor_colors(False)
        self._update_wall_glow(1.0)

        self.mode_index = 0
        self.ghost_mode = CHASE_SCATTER_SCHEDULE[0][0]
        self.mode_timer = CHASE_SCATTER_SCHEDULE[0][1]

        self.player.score = 0
        self.player.lives = 3
        self.game_time = 0.0

        self._rebuild_coins()
        self._update_coin_pulses(COIN_PULSE_STEP)
        self._reset_positions()

    # Start gameplay from menu/game over.
    def _start_game(self):
        """Start gameplay from menu or game over."""
        self._reset_game()
        self.state = STATE_PLAYING

    # Reset player/ghost positions to spawn.
    def _reset_positions(self):
        """Reset player/ghost positions after death or wave clear."""
        self.player.center_x, self.player.center_y = self.spawn_pos
        self.player.dir = "S"
        self.player.want_dir = "S"

        # Snap player to grid center
        self._snap_to_tile_center(self.player)
        self._clear_trail()
        self.ghost_wait_for_move = True
        self.ghost_hold_timer = 0.0

        for g in self.ghosts:
            g.center_x, g.center_y = g.start_x, g.start_y
            g.is_dead = False
            g.respawn_timer = 0.0
            g.dir = random.choice(["U", "D", "L", "R"])
            g.color = g.base_color
            g.exit_timer = 0.0

            # Snap each ghost to grid center (MUST be inside the loop)
            self._snap_to_tile_center(g)


    # Snap a sprite to the exact tile center.
    def _snap_to_tile_center(self, spr):
        """Hard snap to the nearest tile center (used on resets)."""
        c, r = world_to_grid(spr.center_x, spr.center_y)
        spr.center_x, spr.center_y = grid_to_world(c, r)

    # Snap to the turn axis if close enough (prevents "late" feeling turns).
    def _snap_for_turn(self, spr, direction):
        """Small turn-assist: nudge onto axis to accept buffered turns."""
        c, r = world_to_grid(spr.center_x, spr.center_y)
        cx, cy = grid_to_world(c, r)
        if direction in ("U", "D"):
            if abs(spr.center_x - cx) <= TURN_SNAP_PX:
                spr.center_x = cx
                return True
        elif direction in ("L", "R"):
            if abs(spr.center_y - cy) <= TURN_SNAP_PX:
                spr.center_y = cy
                return True
        return False



    # ----------------------------
    # Movement and collision helpers
    # ----------------------------
    # Tunnel wrap for sprites on open rows.
    def _handle_wrap(self, spr):
        """Wrap sprites only on tunnel rows.
        Prevents accidental wrap on normal rows.
        """
        # Wrap when crossing left/right edges, but only if sprite is on a tunnel row.
        # We do NOT require perfect tile-centering, because small drift can accumulate across waves.

        # Determine row from Y only (X can be outside bounds during wrap)
        r = ROWS - 1 - int(spr.center_y // TILE)

        if r not in self.tunnel_rows:
            return

        if spr.center_x < -TILE / 2:
            spr.center_x = SCREEN_W + TILE / 2
            if spr is self.player:
                self.trail_skip_next = True
                self.last_trail_cell = None
        elif spr.center_x > SCREEN_W + TILE / 2:
            spr.center_x = -TILE / 2
            if spr is self.player:
                self.trail_skip_next = True
                self.last_trail_cell = None


    # Move a sprite one step; cancel if colliding with walls.
    def _try_step_sprite(self, spr, direction, speed):
        """Move one step; revert if it would hit a wall."""
        # Attempt to move a sprite one step
        # If it hits a wall, revert and return False
        dx, dy = DIRS[direction]
        old_x, old_y = spr.center_x, spr.center_y
        spr.center_x += dx * speed
        spr.center_y += dy * speed
        if arcade.check_for_collision_with_list(spr, self.walls):
            spr.center_x, spr.center_y = old_x, old_y
            return False
        return True

    # Check if a sprite can move in a direction without collision.
    def _can_move_dir(self, spr, direction):
        """Predictive wall check. Used for smooth buffered turning."""
        # Look ahead one step to see if movement would collide
        dx, dy = DIRS[direction]
        old_x, old_y = spr.center_x, spr.center_y
        spr.center_x += dx * MOVE_SPEED
        spr.center_y += dy * MOVE_SPEED
        blocked = arcade.check_for_collision_with_list(spr, self.walls)
        spr.center_x, spr.center_y = old_x, old_y
        return not blocked

    # Lose a life and reset or trigger game over.
    def _lose_life(self):
        """Lose a life, then reset or go to game over."""
        # Life management and game over trigger
        self.player.lives -= 1
        if self.player.lives <= 0:
            self._start_end_screen(STATE_GAME_OVER)
        else:
            self._reset_positions()



    # Draw static floor + corridor tint layers.
    def _draw_floor(self):
        """Draw the cached floor + corridor tint layers."""
        self.floor_shapes.draw()
        self.corridor_shapes.draw()

    # Draw a dot/pellet with pulse/glow styling.
    def _draw_coin(self, coin):
        """Draw a dot/pellet with its pulse/glow styling."""
        base_r = coin.width / 2
        pulse = coin.pulse_value
        if coin.big:
            scale = ORB_BIG_SCALE_MIN + (ORB_BIG_SCALE_MAX - ORB_BIG_SCALE_MIN) * pulse
            core_r = base_r * scale
            glow_alpha = int(ORB_BIG_GLOW_ALPHA + ORB_BIG_GLOW_PULSE * pulse)
            glow_color = _with_alpha(ORB_BIG_GLOW, glow_alpha)
            arcade.draw_circle_filled(coin.center_x, coin.center_y, core_r * ORB_BIG_GLOW_SCALE, glow_color)
            arcade.draw_circle_filled(coin.center_x, coin.center_y, core_r, ORB_BIG_CORE)

            ring_t = ((self.game_time + coin.pulse_offset) % ORB_RING_PERIOD) / ORB_RING_PERIOD
            ring_r = base_r * 1.2 + ring_t * ORB_RING_SPAN
            ring_alpha = int(ORB_RING_ALPHA * (1.0 - ring_t))
            if ring_alpha > 2:
                ring_color = _with_alpha(ORB_BIG_GLOW, ring_alpha)
                arcade.draw_circle_outline(coin.center_x, coin.center_y, ring_r, ring_color, border_width=2)
        else:
            brightness = ORB_SMALL_MIN_BRIGHT + ORB_SMALL_PULSE_DEPTH * pulse
            core_color = _scale_color(ORB_SMALL_BASE, brightness)
            glow_alpha = int(ORB_SMALL_GLOW_ALPHA * (0.6 + 0.4 * pulse))
            glow_color = _with_alpha(ORB_SMALL_GLOW, glow_alpha)
            arcade.draw_circle_filled(coin.center_x, coin.center_y, base_r * ORB_SMALL_GLOW_SCALE, glow_color)
            arcade.draw_circle_filled(coin.center_x, coin.center_y, base_r, core_color)

    # Draw the player with animated mouth.
    def _draw_pacman(self, p):
        """Draw Pac-Man with a simple mouth animation."""
        r = p.width / 2
        cx = p.center_x
        cy = p.center_y

        d = p.dir
        if d == "S":
            d = p.want_dir
        if d == "S":
            d = "R"

        ang = 0.0
        if d == "R":
            ang = 0.0
        elif d == "U":
            ang = math.pi / 2
        elif d == "L":
            ang = math.pi
        elif d == "D":
            ang = -math.pi / 2

        arcade.draw_circle_filled(cx, cy, r, arcade.color.YELLOW)

        if p.mouth_open:
            x1 = cx + r * math.cos(ang + 0.55)
            y1 = cy + r * math.sin(ang + 0.55)
            x2 = cx + r * math.cos(ang - 0.55)
            y2 = cy + r * math.sin(ang - 0.55)
            arcade.draw_polygon_filled([(cx, cy), (x1, y1), (x2, y2)], arcade.color.BLACK)


    # Draw a ghost with simple body + eyes.
    def _draw_ghost(self, g):
        """Draw a ghost body + eyes based on its current direction."""
        w = g.width
        h = g.height
        cx = g.center_x
        cy = g.center_y
        col = g.color

        top_r = w * 0.5
        top_cy = cy + h * 0.15
        arcade.draw_circle_filled(cx, top_cy, top_r, col)

        rect_w = w
        rect_h = h * 0.55
        rect_cy = cy - h * 0.15
        arcade.draw_rect_filled(arcade.XYWH(cx, rect_cy, rect_w, rect_h), col)


        bump_r = w * 0.18
        bump_y = cy - h * 0.42
        arcade.draw_circle_filled(cx - w * 0.28, bump_y, bump_r, col)
        arcade.draw_circle_filled(cx, bump_y, bump_r, col)
        arcade.draw_circle_filled(cx + w * 0.28, bump_y, bump_r, col)

        eye_r = w * 0.14
        eye_y = cy + h * 0.10
        eye_x1 = cx - w * 0.16
        eye_x2 = cx + w * 0.16

        arcade.draw_circle_filled(eye_x1, eye_y, eye_r, arcade.color.WHITE)
        arcade.draw_circle_filled(eye_x2, eye_y, eye_r, arcade.color.WHITE)

        pdx, pdy = 0.0, 0.0
        if g.dir == "R":
            pdx = eye_r * 0.35
        elif g.dir == "L":
            pdx = -eye_r * 0.35
        elif g.dir == "U":
            pdy = eye_r * 0.35
        elif g.dir == "D":
            pdy = -eye_r * 0.35

        pupil_r = eye_r * 0.45
        arcade.draw_circle_filled(eye_x1 + pdx, eye_y + pdy, pupil_r, arcade.color.BLACK)
        arcade.draw_circle_filled(eye_x2 + pdx, eye_y + pdy, pupil_r, arcade.color.BLACK)





    # Small Pac-Man icon used in HUD lives.
    def _draw_life_icon(self, x, y, r):
        """Tiny Pac-Man icon used for the HUD life counter."""
        arcade.draw_circle_filled(x, y, r, arcade.color.YELLOW)

        p1 = (r * 1.05, 0.0)
        p2 = (r * 0.2, r * 0.65)
        p3 = (r * 0.2, -r * 0.65)

        x1, y1 = _rotate_point(p1[0], p1[1], 0.0)
        x2, y2 = _rotate_point(p2[0], p2[1], 0.0)
        x3, y3 = _rotate_point(p3[0], p3[1], 0.0)

        arcade.draw_polygon_filled(
            [(x, y), (x + x2, y + y2), (x + x1, y + y1), (x + x3, y + y3)],
            arcade.color.BLACK
        )

    # HUD: score, wave, lives, optional FPS.
    def _draw_hud(self):
        """Top HUD: score, wave, lives, and optional FPS."""
        HUD_Y_OFFSET = -2.2 # negative = lower, positive = higher
        hud_center_y = SCREEN_H - HUD_HEIGHT / 2
        hud_rect = arcade.XYWH(SCREEN_W / 2, hud_center_y, SCREEN_W, HUD_HEIGHT)
        arcade.draw_rect_filled(hud_rect, HUD_BG)

        inner_w = SCREEN_W - HUD_PADDING * 2
        inner_h = HUD_HEIGHT - HUD_PADDING * 2
        inner_rect = arcade.XYWH(SCREEN_W / 2, hud_center_y, inner_w, inner_h)
        arcade.draw_rect_filled(inner_rect, HUD_PANEL)
        arcade.draw_rect_outline(inner_rect, HUD_BORDER, border_width=2)

        score_right = SCREEN_W * 0.45
        wave_right = SCREEN_W * 0.65
        line_bottom = SCREEN_H - HUD_HEIGHT + 6
        line_top = SCREEN_H - 6
        arcade.draw_line(score_right, line_bottom, score_right, line_top, HUD_BORDER, 2)
        arcade.draw_line(wave_right, line_bottom, wave_right, line_top, HUD_BORDER, 2)

        label_y = SCREEN_H - 20 + HUD_Y_OFFSET
        value_y = SCREEN_H - HUD_HEIGHT + 10 + HUD_Y_OFFSET


        score_x = HUD_PADDING + 10
        arcade.draw_text("SCORE", score_x, label_y, HUD_LABEL, 12, font_name=HUD_FONT)
        arcade.draw_text("{:06d}".format(self.player.score), score_x, value_y, HUD_VALUE, 20, font_name=HUD_FONT)

        wave_center = (score_right + wave_right) / 2
        arcade.draw_text("WAVE", wave_center, label_y, HUD_LABEL, 12, font_name=HUD_FONT, anchor_x="center")
        arcade.draw_text(str(self.wave), wave_center, value_y, HUD_VALUE, 20, font_name=HUD_FONT, anchor_x="center")

        lives_left = wave_right + 12
        arcade.draw_text("LIVES", lives_left, label_y, HUD_LABEL, 12, font_name=HUD_FONT)

        life_r = 6
        life_y = value_y + 8
        icons_to_draw = min(self.player.lives, 6)
        icon_start_x = lives_left + 8
        for i in range(icons_to_draw):
            self._draw_life_icon(icon_start_x + i * 16, life_y, life_r)

        arcade.draw_text(
            "x{}".format(self.player.lives),
            icon_start_x + icons_to_draw * 16 + 6,
            value_y + 2,
            HUD_SUBTEXT,
            12,
            font_name=HUD_FONT
        )

        if SHOW_FPS:
            fps_text = "{} FPS".format(self.fps_value)
            arcade.draw_text(
                fps_text,
                SCREEN_W - HUD_PADDING - 8,
                label_y,
                HUD_SUBTEXT,
                12,
                font_name=HUD_FONT,
                anchor_x="right"
            )
    # ----------------------------
    # Input handling
    # Player movement uses buffered direction (want_dir) for smoother turns
    # ----------------------------
    # Keyboard input for menu and gameplay.
    def on_key_press(self, symbol: int, modifiers: int):
        """Keyboard input: buffer direction changes and handle menus."""
        if self.state == STATE_MENU:
            if symbol == arcade.key.ENTER:
                self._start_game()
            elif symbol == arcade.key.ESCAPE:
                self.close()
            return
        if self.state == STATE_GAME_OVER:
            if symbol == arcade.key.ENTER:
                self._start_game()
            elif symbol == arcade.key.ESCAPE:
                self.close()
            return
        if symbol == arcade.key.W:
            self.player.want_dir = "U"
        elif symbol == arcade.key.S:
            self.player.want_dir = "D"
        elif symbol == arcade.key.A:
            self.player.want_dir = "L"
        elif symbol == arcade.key.D:
            self.player.want_dir = "R"

    # ----------------------------
    # Main update loop
    # Runs every frame, drives movement, collisions, timers, waves, and AI
    # ----------------------------
    # Main update loop (movement, AI, collisions, timers).
    def on_update(self, delta_time: float):
        """Main game loop: movement, collisions, timers, AI, and waves."""
        # If not playing, pause all game logic (menu/game over screens are static)
        if self.state != STATE_PLAYING:
            return

        if SHOW_FPS:
            self.fps_accum_time += delta_time
            self.fps_accum_frames += 1
            if self.fps_accum_time >= 0.25:
                self.fps_value = int(self.fps_accum_frames / self.fps_accum_time)
                self.fps_accum_time = 0.0
                self.fps_accum_frames = 0

        self.game_time += delta_time
        if self.ghost_hold_timer > 0.0:
            self.ghost_hold_timer = max(0.0, self.ghost_hold_timer - delta_time)
        self._update_coin_pulses(delta_time)

        # Wave banner timing
        if self.banner_timer > 0:
            self.banner_timer -= delta_time

        # Power pellet timer: when it ends, revert ghosts to base colors
        if self.power_mode_timer > 0:
            self.power_mode_timer -= delta_time
            if self.power_mode_timer <= 0:
                self.power_mode_timer = 0
                for g in self.ghosts:
                    g.color = g.base_color

        # Turning logic only at tile centers for clean movement
        # Turn assist: allow buffered turns slightly before the exact center.
        if self.player.want_dir != self.player.dir:
            old_x, old_y = self.player.center_x, self.player.center_y
            snapped = self._snap_for_turn(self.player, self.player.want_dir)
            if snapped and self._can_move_dir(self.player, self.player.want_dir):
                self.player.dir = self.player.want_dir
            elif snapped:
                self.player.center_x, self.player.center_y = old_x, old_y

        if at_tile_center(self.player.center_x, self.player.center_y):
            if self.player.want_dir != self.player.dir and self._can_move_dir(self.player, self.player.want_dir):
                self.player.dir = self.player.want_dir
            if not self._can_move_dir(self.player, self.player.dir):
                self.player.dir = "S"

        # Move the player in the current direction
        moved = self._try_step_sprite(self.player, self.player.dir, MOVE_SPEED)
        player_moved = moved and self.player.dir != "S"
        self.player.update_mouth(delta_time, player_moved)
        if not moved:
            pass

        if self.ghost_wait_for_move and player_moved:
            self.ghost_wait_for_move = False
            self.ghost_hold_timer = GHOST_RELEASE_DELAY

        # Tunnel wrap for player
        self._handle_wrap(self.player)

        # Trail placement and aging (place once per new grid cell)
        if player_moved:
            if self.trail_skip_next:
                self.trail_skip_next = False
            else:
                c, r = world_to_grid(self.player.center_x, self.player.center_y)
                if self.last_trail_cell is None:
                    if self._add_trail_segment_cell(c, r):
                        self._lose_life()
                        return
                elif self.last_trail_cell != (c, r):
                    lc, lr = self.last_trail_cell
                    dc = c - lc
                    dr = r - lr
                    if dc != 0 and dr != 0:
                        # Unexpected diagonal step; just add the target cell.
                        if self._add_trail_segment_cell(c, r):
                            self._lose_life()
                            return
                    elif dc != 0:
                        step = 1 if dc > 0 else -1
                        for nc in range(lc + step, c + step, step):
                            if self._add_trail_segment_cell(nc, lr):
                                self._lose_life()
                                return
                    elif dr != 0:
                        step = 1 if dr > 0 else -1
                        for nr in range(lr + step, r + step, step):
                            if self._add_trail_segment_cell(lc, nr):
                                self._lose_life()
                                return
        # Remove expired trail so the maze clears behind the player.
        self._update_trail()

        # Eat dots and power pellets
        hit_coins = arcade.check_for_collision_with_list(self.player, self.coins)
        for coin in hit_coins:
            self.player.score += coin.value
            if coin.value == 50:
                # Start frightened mode and reverse ghosts immediately
                self.power_mode_timer = 8.0
                for g in self.ghosts:
                    if not g.is_dead:
                        g.dir = opp_dir(g.dir)
                    g.color = arcade.color.BLUE

            coin.remove_from_sprite_lists()

        power_active = self.power_mode_timer > 0
        if power_active != self.power_mode_active:
            self.power_mode_active = power_active
            self._update_wall_edge_colors(power_active)
            self._update_floor_colors(power_active)

        self.glow_update_timer += delta_time
        if self.glow_update_timer >= 1 / 20:
            self.glow_update_timer = 0.0
            pulse = 0.5 + 0.5 * math.sin(self.game_time * (2 * math.pi / WALL_GLOW_PULSE_PERIOD))
            intensity = 1.0 - WALL_GLOW_PULSE_DEPTH / 2 + WALL_GLOW_PULSE_DEPTH * pulse
            if self.power_mode_active:
                intensity *= WALL_GLOW_POWER_BOOST
            self._update_wall_glow(intensity)

        # Wave clear: rebuild dots, reset positions, increase wave counter
        if len(self.coins) == 0:
            self.wave += 1
            self.banner_timer = WAVE_BANNER_SECONDS
            self.power_mode_timer = 0.0
            self.power_mode_active = False
            self._update_wall_edge_colors(False)
            self._update_floor_colors(False)
            self._clear_trail()
            for g in self.ghosts:
                g.color = g.base_color
            self._rebuild_coins()
            self._reset_positions()
            return

        # Update chase/scatter mode based on schedule
        self._update_mode_timer(delta_time)

        # Ghosts stay frozen until you move, then wait a short beat.
        ghosts_frozen = self.ghost_wait_for_move or self.ghost_hold_timer > 0.0

        # Speed tuning: frightened ghosts slightly slower
        ghost_speed = GHOST_SPEED
        frightened_speed = max(2, GHOST_SPEED - 1)

        # Ghost movement and AI
        if not ghosts_frozen:
            for g in self.ghosts:
                if g.is_dead:
                    g.respawn_timer -= delta_time
                    if g.respawn_timer <= 0:
                        g.is_dead = False
                        g.center_x, g.center_y = self.ghost_house_pos
                        self._snap_to_tile_center(g)
                        g.dir = "U"
                        g.exit_timer = 1.2
                        g.color = g.base_color
                    continue

                if g.exit_timer > 0:
                    g.exit_timer -= delta_time
                    g.color = g.base_color
                    self._try_step_sprite(g, "U", ghost_speed)
                    self._handle_wrap(g)
                    continue

                frightened = self.power_mode_timer > 0
                speed = frightened_speed if frightened else ghost_speed

                # Choose direction only at tile centers, based on target tile
                if at_tile_center(g.center_x, g.center_y):
                    target = self._ghost_target_cell(g)
                    g.dir = self._choose_dir_to_target(g, target, frightened)

                # Move ghost, and if blocked, re-pick immediately to avoid freezing
                moved_ghost = self._try_step_sprite(g, g.dir, speed)
                if not moved_ghost:
                    target = self._ghost_target_cell(g)
                    g.dir = self._choose_dir_to_target(g, target, frightened)
                    self._try_step_sprite(g, g.dir, speed)

                # Tunnel wrap for ghosts
                self._handle_wrap(g)

                # Visual color state for frightened mode
                if frightened:
                    g.color = arcade.color.BLUE
                else:
                    g.color = g.base_color

            # Collision between player and ghosts
            # If powered up: eat ghost for points
            # If not powered up: lose a life
            hit_ghosts = arcade.check_for_collision_with_list(self.player, self.ghosts)
            for g in hit_ghosts:
                if (not g.is_dead) and (g.exit_timer <= 0):
                    if self.power_mode_timer > 0:
                        self.player.score += 200
                        g.is_dead = True
                        g.respawn_timer = 5.0
                        g.center_x, g.center_y = -100, -100
                    else:
                        self._lose_life()

    # ----------------------------
    # Rendering
    # Draw all sprites and HUD, plus overlays for wave banner and game over
    # ----------------------------
    # Render the current screen (menu, game over, or gameplay).
    def on_draw(self):
        if self.state == STATE_MENU:
            self._draw_start_menu()
            return
        if self.state == STATE_GAME_OVER:
            self._draw_game_over()
            return

        self.clear()
        self._draw_floor()
        self.wall_glow_shapes.draw()
        self.wall_base_shapes.draw()
        self.wall_edge_shapes.draw()
        self._draw_trail()
        for coin in self.coins:
            self._draw_coin(coin)
        for g in self.ghosts:
            self._draw_ghost(g)

        self._draw_pacman(self.player)

        self._draw_hud()

        overlay_rect = arcade.XYWH(SCREEN_W / 2, SCREEN_H / 2, SCREEN_W, SCREEN_H)

        if self.state == STATE_PLAYING and self.banner_timer > 0:
            arcade.draw_rect_filled(overlay_rect, (0, 0, 0, 180))
            arcade.draw_text("WAVE " + str(self.wave), SCREEN_W / 2, SCREEN_H / 2 + 10, arcade.color.WHITE, 44, anchor_x="center")

# ----------------------------
# Entry point
# ----------------------------
# Program entry point.
def main():
    PacmanGame()
    arcade.run()

if __name__ == "__main__":
    main()
