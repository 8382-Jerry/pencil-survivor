"""
settings.py —— 所有游戏常量、数值平衡、资源路径集中配置
修改本文件即可调整游戏平衡，无需翻阅主逻辑代码。
"""
import math
import os

# ========================= 路径配置 =========================

# 项目根目录（main.py 所在目录）
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# 素材目录：优先使用项目内的 assets 文件夹，其次使用上级目录的 assets
_internal_assets = os.path.join(PROJECT_DIR, "assets")
_parent_assets = os.path.join(os.path.dirname(PROJECT_DIR), "assets")
ASSETS_DIR = _internal_assets if os.path.isdir(_internal_assets) else _parent_assets

# -------- 素材文件路径（相对于 ASSETS_DIR）--------
ASSET_PATHS = {
    "background": "background/background_swhite_paper_texture.png",
    "player": "player/pencil_person.png",
    "pistol": "weapons/pistol.png",
    "smg": "weapons/smg.png",
    "baseball_bat": "weapons/baseball_bat.png",
    "knife": "weapons/knife.png",
    "pencil_line_enemy": "enemy/pencil_line.png",
    "ink_drop_enemy": "enemy/ink_drop.png",
    "small_pencil": "enemy/small_pencil.png",
    "giant_eraser": "enemy/boss_giant_eraser.png",
}


def get_asset_path(key: str) -> str:
    """根据 key 获取素材的完整路径"""
    filename = ASSET_PATHS.get(key, "")
    return os.path.join(ASSETS_DIR, filename)


# ========================= 窗口 / 渲染 =========================

LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720
FPS = 60

# ========================= 颜色定义 =========================

COLOR_WHITE = (255, 255, 255)
COLOR_PAPER = (250, 246, 236)
COLOR_BLACK = (30, 30, 30)
COLOR_RED = (200, 50, 50)
COLOR_GREEN = (50, 180, 50)
COLOR_BLUE = (50, 80, 200)
COLOR_YELLOW = (220, 180, 30)
COLOR_ORANGE = (230, 130, 20)
COLOR_GRAY = (150, 150, 150)
COLOR_DARK_GRAY = (60, 60, 60)
COLOR_XP_GREEN = (100, 220, 100)
COLOR_HP_RED = (220, 60, 60)
COLOR_BOSS_HP = (180, 20, 20)
COLOR_CARD_BG = (255, 252, 240)
COLOR_CARD_HOVER = (255, 245, 200)
COLOR_CARD_BORDER = (80, 80, 60)
COLOR_DANGER_ZONE = (255, 80, 80, 100)

# ========================= 玩家 =========================

PLAYER_MAX_HP = 100.0
PLAYER_SPEED = 250.0
PLAYER_RADIUS = 20.0
PLAYER_PICKUP_RANGE = 100.0
PLAYER_INVINCIBLE_TIME = 0.5
PLAYER_START_LEVEL = 1
PLAYER_MAX_WEAPONS = 4

# ========================= 经验 / 升级（加速版）=========================

# 升级所需累积经验（比之前降低约 40%，升级更快更爽）
XP_THRESHOLDS = {
    1: 0,
    2: 60,        # Lv1→2: 60
    3: 150,       # +90
    4: 285,       # +135
    5: 490,       # +205
    6: 800,       # +310
    7: 1260,      # +460
    8: 1950,      # +690
    9: 2980,      # +1030
    10: 4520,     # +1540
    11: 6830,     # +2310
    12: 10300,    # +3470
    13: 15500,    # +5200
    14: 23300,    # +7800
    15: 35000,    # +11700
    16: 52600,    # +17600
    17: 79000,    # +26400
    18: 118600,   # +39600
    19: 178000,   # +59400
    20: 267100,   # +89100
}


def get_xp_for_level(level: int) -> float:
    """返回升到指定等级所需的累积经验"""
    if level <= 1:
        return 0
    if level in XP_THRESHOLDS:
        return XP_THRESHOLDS[level]
    return XP_THRESHOLDS[20] * (1.5 ** (level - 20))


# ========================= 被动升级定义（加强版）=========================

PASSIVE_UPGRADES = {
    "max_hp":          {"name": "Max HP +30",       "hp_bonus": 30,                    "desc": "最大生命值 +30"},
    "move_speed":      {"name": "Move Speed +12%",  "speed_mult": 0.12,                "desc": "移动速度 +12%"},
    "pickup_range":    {"name": "Pickup Range +25%","pickup_mult": 0.25,               "desc": "拾取范围 +25%"},
    "damage_reduction": {"name": "Damage -12%",     "dmg_reduce": 0.12,                "desc": "受到的伤害 -12%"},
    "attack_speed":    {"name": "Attack Speed +12%","atk_speed_mult": 0.12,            "desc": "全武器攻击速度 +12%"},
    "all_damage":      {"name": "Damage +15%",      "dmg_mult": 0.15,                  "desc": "全武器伤害 +15%"},
}

# ========================= 武器配置（全部加强）=========================

WEAPON_INFO = {
    "pistol":       {"name": "Pistol",       "icon": "pistol"},
    "smg":          {"name": "SMG",           "icon": "smg"},
    "baseball_bat": {"name": "Baseball Bat",  "icon": "baseball_bat"},
    "knife":        {"name": "Knife",         "icon": "knife"},
}

WEAPON_STATS = {
    "pistol": {
        1: {"damage": 35, "cooldown": 0.75, "projectile_speed": 650, "pierce": 0, "count": 1, "radius": 5},
        2: {"damage": 50, "cooldown": 0.75, "projectile_speed": 680, "pierce": 0, "count": 1, "radius": 5},
        3: {"damage": 50, "cooldown": 0.50, "projectile_speed": 680, "pierce": 0, "count": 1, "radius": 6},
        4: {"damage": 55, "cooldown": 0.50, "projectile_speed": 700, "pierce": 0, "count": 2, "radius": 6},
        5: {"damage": 70, "cooldown": 0.45, "projectile_speed": 720, "pierce": 1, "count": 2, "radius": 7},
    },
    "smg": {
        1: {"damage": 14, "cooldown": 0.16, "projectile_speed": 700, "pierce": 0, "count": 1, "radius": 4, "spread": 0.12},
        2: {"damage": 14, "cooldown": 0.12, "projectile_speed": 720, "pierce": 0, "count": 1, "radius": 4, "spread": 0.12},
        3: {"damage": 16, "cooldown": 0.12, "projectile_speed": 720, "pierce": 0, "count": 2, "radius": 4, "spread": 0.10},
        4: {"damage": 16, "cooldown": 0.12, "projectile_speed": 750, "pierce": 0, "count": 2, "radius": 5, "spread": 0.06},
        5: {"damage": 22, "cooldown": 0.08, "projectile_speed": 750, "pierce": 1, "count": 3, "radius": 5, "spread": 0.05},
    },
    "baseball_bat": {
        1: {"damage": 50,  "cooldown": 1.1, "range": 95,  "arc_angle": math.radians(115), "knockback": 200},
        2: {"damage": 70,  "cooldown": 1.1, "range": 100, "arc_angle": math.radians(115), "knockback": 220},
        3: {"damage": 70,  "cooldown": 1.0, "range": 120, "arc_angle": math.radians(120), "knockback": 240},
        4: {"damage": 80,  "cooldown": 0.9, "range": 130, "arc_angle": math.radians(120), "knockback": 300},
        5: {"damage": 110, "cooldown": 0.8, "range": 155, "arc_angle": math.radians(140), "knockback": 320},
    },
    "knife": {
        1: {"damage": 25, "cooldown": 0.65, "range": 70, "knife_count": 1, "rotation_speed": 2.8, "orbit_radius": 55},
        2: {"damage": 36, "cooldown": 0.60, "range": 70, "knife_count": 1, "rotation_speed": 3.0, "orbit_radius": 55},
        3: {"damage": 36, "cooldown": 0.55, "range": 75, "knife_count": 2, "rotation_speed": 3.2, "orbit_radius": 55},
        4: {"damage": 42, "cooldown": 0.50, "range": 75, "knife_count": 2, "rotation_speed": 4.0, "orbit_radius": 55},
        5: {"damage": 55, "cooldown": 0.45, "range": 80, "knife_count": 3, "rotation_speed": 4.5, "orbit_radius": 60},
    },
}

# ========================= 敌人配置 =========================

ENEMY_CONFIGS = {
    "pencil_line": {
        "name": "Pencil Line", "asset_key": "pencil_line_enemy",
        "hp": 40.0, "speed": 100.0, "damage": 10.0, "xp": 12, "radius": 18.0,
    },
    "ink_drop": {
        "name": "Ink Drop", "asset_key": "ink_drop_enemy",
        "hp": 100.0, "speed": 55.0, "damage": 18.0, "xp": 25, "radius": 25.0,
    },
    "small_pencil": {
        "name": "Small Pencil", "asset_key": "small_pencil",
        "hp": 180.0, "speed": 85.0, "damage": 20.0, "xp": 45, "radius": 26.0,
        "dash_speed": 420.0, "dash_damage": 35.0, "dash_duration": 0.45,
        "dash_prepare": 0.6, "dash_recover": 0.5, "dash_range": 350.0, "dash_cooldown": 2.5,
    },
    "giant_eraser": {
        "name": "Giant Eraser", "asset_key": "giant_eraser",
        "hp": 5000.0, "speed": 38.0, "damage": 35.0, "xp": 500, "radius": 75.0,
        "enrage_speed": 52.0, "enrage_hp_threshold": 0.5,
    },
}

# ========================= 难度成长 =========================

def difficulty_multiplier(game_time: float) -> float:
    return 1.0 + game_time / 120.0

def enemy_hp_mult(game_time: float) -> float:
    return min(1.0 + game_time / 200.0, 3.5)

def enemy_speed_mult(game_time: float) -> float:
    return min(1.0 + game_time / 600.0, 1.8)

def enemy_damage_mult(game_time: float) -> float:
    return min(1.0 + game_time / 350.0, 2.8)

# ========================= 敌人生成 =========================

SPAWN_DISTANCE_MIN = 600.0
SPAWN_MARGIN = 80.0

SPAWN_SCHEDULE = [
    (0,   1.3,  35, ["pencil_line"]),
    (60,  1.0,  50, ["pencil_line", "ink_drop"]),
    (120, 0.85, 60, ["pencil_line", "ink_drop", "small_pencil"]),
    (180, 0.7,  70, ["pencil_line", "ink_drop", "small_pencil"]),
    (240, 0.6,  80, ["pencil_line", "ink_drop", "small_pencil"]),
    # Boss 生成后由代码控制停止普通/精英生成
]

ENEMY_CAP = 80
ELITE_CAP = 8

# ========================= Boss 攻击配置 =========================

BOSS_ATTACKS = {
    "charge": {
        "telegraph": 1.0, "speed": 360.0, "duration": 0.8,
        "damage": 60.0, "cooldown": 6.0,
    },
    "erase_zone": {
        "warning": 2.0,          # 2 秒红圈预警后攻击
        "radius": 140.0,
        "duration": 2.5,
        "damage_per_sec": 25.0,
        "cooldown": 7.0,
    },
    "summon": {
        "count_min": 5, "count_max": 8, "cooldown": 10.0,
    },
}

BOSS_ENRAGE_MODIFIERS = {
    "charge":      {"cooldown": 4.0},
    "erase_zone":  {"radius": 190.0, "duration": 3.0, "cooldown": 5.5},
    "summon":      {"count_min": 8, "count_max": 12, "cooldown": 7.0},
}

# ========================= Boss 时间线 =========================

BOSS_SPAWN_TIME = 270.0      # 4:30
VICTORY_CHECK_TIME = 300.0   # 5:00

# ========================= 武器环绕位置 =========================

WEAPON_OFFSETS = [
    (35, -20), (-35, -20), (30, 25), (-30, 25),
]
