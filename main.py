"""
main.py —— Pencil Survivor 游戏主程序
2D 生存类游戏 Demo，类似 Vampire Survivors 的玩法。
在无限延伸的白纸上，铅笔线稿玩家 vs 彩色文具敌人。
"""
import pygame
import sys
import math
import random
import os
import asyncio
from settings import *

# ============================================================
# 0. 初始化 Pygame
# ============================================================
pygame.init()
pygame.display.set_caption("Pencil Survivor")
_real_screen = pygame.display.set_mode((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.RESIZABLE)
LOGICAL_SURFACE = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
CLOCK = pygame.time.Clock()

# 尝试加载系统中文字体
FONT_SMALL = None
FONT_MEDIUM = None
FONT_LARGE = None
FONT_HUGE = None
_font_candidates = [
    "SimHei", "Microsoft YaHei", "SimSun", "FangSong",
    "KaiTi", "Noto Sans CJK SC", "WenQuanYi Micro Hei",
    "Arial", "DejaVu Sans",
]
for _fn in _font_candidates:
    try:
        FONT_SMALL = pygame.font.SysFont(_fn, 16)
        FONT_MEDIUM = pygame.font.SysFont(_fn, 22)
        FONT_LARGE = pygame.font.SysFont(_fn, 36)
        FONT_HUGE = pygame.font.SysFont(_fn, 56)
        break
    except Exception:
        continue
if FONT_SMALL is None:
    FONT_SMALL = pygame.font.Font(None, 16)
    FONT_MEDIUM = pygame.font.Font(None, 22)
    FONT_LARGE = pygame.font.Font(None, 36)
    FONT_HUGE = pygame.font.Font(None, 56)


# ============================================================
# 1. 资源加载
# ============================================================

# 图片缓存：避免每帧从磁盘重复加载
_image_cache = {}

def load_image(key: str, scale_to: tuple = None) -> pygame.Surface:
    """安全加载图片（带缓存），失败时返回程序绘制的占位图"""
    cache_key = (key, scale_to)
    if cache_key in _image_cache:
        return _image_cache[cache_key]

    full_path = get_asset_path(key)
    try:
        img = pygame.image.load(full_path).convert_alpha()
        if scale_to:
            img = pygame.transform.scale(img, scale_to)
        _image_cache[cache_key] = img
        return img
    except Exception:
        print(f"[WARN] 素材缺失: {full_path}，使用占位图。")
        surf = pygame.Surface(scale_to if scale_to else (32, 32), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        pygame.draw.rect(surf, (200, 200, 200), surf.get_rect(), 2)
        pygame.draw.line(surf, (200, 0, 0), (0, 0), surf.get_size(), 2)
        pygame.draw.line(surf, (200, 0, 0), (0, surf.get_height()), (surf.get_width(), 0), 2)
        _image_cache[cache_key] = surf
        return surf


def draw_text(surface, text, x, y, font, color=COLOR_BLACK, center=True):
    """绘制文字，可指定居中或左上角"""
    rendered = font.render(str(text), True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(rendered, rect)
    return rect


# ============================================================
# 2. 世界 ↔ 屏幕坐标转换
# ============================================================

class Camera:
    """摄像机，始终跟随玩家，玩家位于屏幕中心"""
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self, player_x, player_y):
        self.x = player_x
        self.y = player_y

    def world_to_screen(self, wx, wy):
        return (wx - self.x + LOGICAL_WIDTH / 2,
                wy - self.y + LOGICAL_HEIGHT / 2)

    def screen_to_world(self, sx, sy):
        return (sx - LOGICAL_WIDTH / 2 + self.x,
                sy - LOGICAL_HEIGHT / 2 + self.y)


# ============================================================
# 3. 子弹 / 投射物
# ============================================================

class Bullet:
    """通用子弹类"""
    def __init__(self, x, y, vx, vy, damage, pierce=0, radius=5):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.pierce = pierce          # 穿透次数（0 = 命中即消失）
        self.radius = radius
        self.alive = True
        self.distance_traveled = 0.0
        self.max_distance = 1200.0
        self.hit_enemies = set()      # 已命中的敌人 id（穿透时避免重复命中）

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.distance_traveled += math.hypot(self.vx * dt, self.vy * dt)
        if self.distance_traveled > self.max_distance:
            self.alive = False

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if 0 <= sx <= LOGICAL_WIDTH and 0 <= sy <= LOGICAL_HEIGHT:
            pygame.draw.circle(surf, COLOR_BLACK, (int(sx), int(sy)), max(3, self.radius))
            # 简单拖尾
            tail_dir = math.atan2(self.vy, self.vx)
            tx = self.x - math.cos(tail_dir) * self.radius * 2
            ty = self.y - math.sin(tail_dir) * self.radius * 2
            tsx, tsy = camera.world_to_screen(tx, ty)
            pygame.draw.line(surf, COLOR_DARK_GRAY, (int(tsx), int(tsy)),
                             (int(sx), int(sy)), max(1, self.radius // 2))


# ============================================================
# 4. 经验物品
# ============================================================

class ExperienceOrb:
    """经验值物品，由敌人死亡掉落"""
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value
        self.radius = 6.0
        self.alive = True
        self.birth_time = 0.0
        self.magnet_speed = 350.0

    def update(self, dt, game_time):
        self.birth_time += dt
        # 出生 0.3 秒后才能被拾取（给一点视觉效果时间）
        pass

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if 0 <= sx <= LOGICAL_WIDTH + 20 and 0 <= sy <= LOGICAL_HEIGHT + 20:
            # 程序绘制绿色菱形经验宝石
            pts = [
                (int(sx), int(sy - 7)),
                (int(sx + 5), int(sy)),
                (int(sx), int(sy + 7)),
                (int(sx - 5), int(sy)),
            ]
            pygame.draw.polygon(surf, COLOR_XP_GREEN, pts)
            pygame.draw.polygon(surf, (50, 180, 50), pts, 1)


# ============================================================
# 5. 近战效果
# ============================================================

class MeleeEffect:
    """近战攻击的视觉效果"""
    def __init__(self, x, y, angle, weapon_range, arc_angle, duration=0.15):
        self.x = x
        self.y = y
        self.angle = angle        # 攻击方向（弧度）
        self.weapon_range = weapon_range
        self.arc_angle = arc_angle
        self.duration = duration
        self.timer = 0.0
        self.alive = True

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.duration:
            self.alive = False

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if 0 <= sx <= LOGICAL_WIDTH and 0 <= sy <= LOGICAL_HEIGHT:
            progress = self.timer / self.duration
            alpha = int(180 * (1 - progress))
            # 绘制扇形攻击范围
            arc_surf = pygame.Surface((self.weapon_range * 2, self.weapon_range * 2), pygame.SRCALPHA)
            rect = pygame.Rect(0, 0, self.weapon_range * 2, self.weapon_range * 2)
            start_angle = math.degrees(self.angle - self.arc_angle / 2)
            end_angle = math.degrees(self.angle + self.arc_angle / 2)
            pygame.draw.arc(arc_surf, (100, 100, 100, alpha), rect, start_angle, end_angle, 8)
            # 两条边线
            cx, cy = self.weapon_range, self.weapon_range
            lx = cx + math.cos(self.angle - self.arc_angle / 2) * self.weapon_range
            ly = cy - math.sin(self.angle - self.arc_angle / 2) * self.weapon_range
            rx = cx + math.cos(self.angle + self.arc_angle / 2) * self.weapon_range
            ry = cy - math.sin(self.angle + self.arc_angle / 2) * self.weapon_range
            pygame.draw.line(arc_surf, (80, 80, 80, alpha), (cx, cy), (lx, ly), 4)
            pygame.draw.line(arc_surf, (80, 80, 80, alpha), (cx, cy), (rx, ry), 4)
            surf.blit(arc_surf, (sx - self.weapon_range, sy - self.weapon_range))


# ============================================================
# 6. 伤害数字
# ============================================================

class DamageNumber:
    """浮动伤害数字"""
    def __init__(self, x, y, value, color=COLOR_RED):
        self.x = x
        self.y = y
        self.value = value
        self.color = color
        self.timer = 0.0
        self.duration = 0.8
        self.alive = True

    def update(self, dt):
        self.timer += dt
        self.y -= 40 * dt  # 向上浮动
        if self.timer >= self.duration:
            self.alive = False

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        if 0 <= sx <= LOGICAL_WIDTH and 0 <= sy <= LOGICAL_HEIGHT:
            progress = self.timer / self.duration
            alpha = int(255 * (1 - progress))
            text = FONT_SMALL.render(str(self.value), True, self.color)
            text.set_alpha(alpha)
            surf.blit(text, text.get_rect(center=(sx, sy)))


# ============================================================
# 7. 武器系统
# ============================================================

class Weapon:
    """单个武器实例"""
    def __init__(self, weapon_type, level=1):
        self.weapon_type = weapon_type
        self.level = level
        self.cooldown_remaining = 0.0
        self.knife_angle = random.uniform(0, math.pi * 2)  # 小刀初始角度
        self._stats = WEAPON_STATS[weapon_type][level]

    @property
    def stats(self):
        return WEAPON_STATS[self.weapon_type][self.level]

    @property
    def max_level(self):
        return 5

    def get_cooldown(self):
        return self.stats["cooldown"]

    def update(self, dt, player, enemies, bullets, effects, dmg_numbers, speed_mult=1.0):
        """武器冷却计时与攻击触发。speed_mult 来自玩家的攻击速度加成"""
        self.cooldown_remaining -= dt * speed_mult
        # 小刀持续旋转（独立于攻击冷却）
        if self.weapon_type == "knife":
            s = self.stats
            self.knife_angle += s.get("rotation_speed", 2.5) * dt
            self.knife_angle %= (math.pi * 2)
        if self.cooldown_remaining <= 0:
            self.cooldown_remaining = 0
            # 寻找最近的有效敌人
            nearest = None
            nearest_dist = float("inf")
            for e in enemies:
                if not e.alive:
                    continue
                d = math.hypot(player.world_x - e.world_x, player.world_y - e.world_y)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = e
            if nearest is not None:
                self._attack(player, nearest, enemies, bullets, effects, dmg_numbers)

    def _attack(self, player, target, enemies, bullets, effects, dmg_numbers):
        """执行攻击"""
        s = self.stats
        dmg_mult = getattr(player, 'damage_mult', 1.0)
        if self.weapon_type == "pistol":
            self._fire_bullet(player, target, bullets, s, dmg_mult)
            self.cooldown_remaining = s["cooldown"]
        elif self.weapon_type == "smg":
            self._fire_bullet(player, target, bullets, s, dmg_mult, spread=s.get("spread", 0))
            self.cooldown_remaining = s["cooldown"]
        elif self.weapon_type == "baseball_bat":
            self._swing_bat(player, target, enemies, effects, dmg_numbers, s, dmg_mult)
            self.cooldown_remaining = s["cooldown"]
        elif self.weapon_type == "knife":
            self._update_knives(player, enemies, dmg_numbers, s, dmg_mult)
            self.cooldown_remaining = s["cooldown"]

    def _fire_bullet(self, player, target, bullets, stats, dmg_mult=1.0, spread=0):
        """发射子弹"""
        damage = stats["damage"] * dmg_mult
        count = stats.get("count", 1)
        speed = stats.get("projectile_speed", 650)
        radius = stats.get("radius", 5)
        pierce = stats.get("pierce", 0)

        dx = target.world_x - player.world_x
        dy = target.world_y - player.world_y
        base_angle = math.atan2(dy, dx)

        for i in range(count):
            angle = base_angle
            if spread > 0 and count > 1:
                angle += spread * (i - (count - 1) / 2)
            elif spread > 0:
                angle += random.uniform(-spread, spread)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            bullets.append(Bullet(player.world_x, player.world_y, vx, vy, damage, pierce, radius))

    def _swing_bat(self, player, target, enemies, effects, dmg_numbers, stats, dmg_mult=1.0):
        """棒球棍挥击：扇形 AoE + 击退"""
        damage = stats["damage"] * dmg_mult
        weapon_range = stats["range"]
        arc_angle = stats["arc_angle"]
        knockback = stats["knockback"]

        dx = target.world_x - player.world_x
        dy = target.world_y - player.world_y
        angle = math.atan2(dy, dx)

        # 命中检测
        for e in enemies:
            if not e.alive:
                continue
            edx = e.world_x - player.world_x
            edy = e.world_y - player.world_y
            dist = math.hypot(edx, edy)
            if dist > weapon_range + e.radius:
                continue
            e_angle = math.atan2(edy, edx)
            angle_diff = abs((e_angle - angle + math.pi) % (2 * math.pi) - math.pi)
            if angle_diff <= arc_angle / 2:
                e.take_damage(damage, dmg_numbers)
                # 击退
                kbx = math.cos(e_angle) * knockback
                kby = math.sin(e_angle) * knockback
                e.knockback_x += kbx
                e.knockback_y += kby

        effects.append(MeleeEffect(player.world_x, player.world_y, angle, weapon_range, arc_angle))

    def _update_knives(self, player, enemies, dmg_numbers, stats, dmg_mult=1.0):
        """小刀环绕攻击的伤害判定（旋转在 update 中持续进行）"""
        damage = stats["damage"] * dmg_mult
        knife_count = stats.get("knife_count", 1)
        orbit_radius = stats.get("orbit_radius", 55)
        hit_range = stats.get("range", 70)

        for i in range(knife_count):
            angle = self.knife_angle + (2 * math.pi / knife_count) * i
            kx = player.world_x + math.cos(angle) * orbit_radius
            ky = player.world_y + math.sin(angle) * orbit_radius
            for e in enemies:
                if not e.alive:
                    continue
                if math.hypot(e.world_x - kx, e.world_y - ky) < hit_range:
                    e.take_damage(damage, dmg_numbers)

    def draw(self, surf, camera, player_x, player_y, offset_x, offset_y):
        """绘制武器图标（跟随玩家）"""
        sx, sy = camera.world_to_screen(player_x, player_y)
        draw_x = int(sx + offset_x)
        draw_y = int(sy + offset_y)
        if 0 <= draw_x <= LOGICAL_WIDTH and 0 <= draw_y <= LOGICAL_HEIGHT:
            icon = load_image(self.weapon_type, (28, 28))
            icon = pygame.transform.scale(icon, (28, 28))
            # 轻微浮动
            float_offset = int(math.sin(pygame.time.get_ticks() * 0.005 + offset_x) * 3)
            surf.blit(icon, (draw_x - 14, draw_y - 14 + float_offset))
            # 等级指示
            lvl_text = FONT_SMALL.render(f"Lv.{self.level}", True, COLOR_DARK_GRAY)
            surf.blit(lvl_text, lvl_text.get_rect(center=(draw_x, draw_y + 18)))

    def draw_knives(self, surf, camera, player_x, player_y):
        """绘制环绕小刀"""
        if self.weapon_type != "knife":
            return
        s = self.stats
        knife_count = s.get("knife_count", 1)
        orbit_radius = s.get("orbit_radius", 55)
        for i in range(knife_count):
            angle = self.knife_angle + (2 * math.pi / knife_count) * i
            kx = player_x + math.cos(angle) * orbit_radius
            ky = player_y + math.sin(angle) * orbit_radius
            sx, sy = camera.world_to_screen(kx, ky)
            if 0 <= sx <= LOGICAL_WIDTH and 0 <= sy <= LOGICAL_HEIGHT:
                knife_img = load_image("knife", (20, 20))
                rotated = pygame.transform.rotate(knife_img, math.degrees(-angle))
                surf.blit(rotated, rotated.get_rect(center=(sx, sy)))


# ============================================================
# 8. 玩家
# ============================================================

class Player:
    def __init__(self):
        self.world_x = 0.0
        self.world_y = 0.0
        self.max_hp = PLAYER_MAX_HP
        self.hp = PLAYER_MAX_HP
        self.speed = PLAYER_SPEED
        self.level = PLAYER_START_LEVEL
        self.xp = 0
        self.pickup_range = PLAYER_PICKUP_RANGE
        self.damage_reduction = 0.0        # 伤害减免比例（0~1）
        self.attack_speed_mult = 1.0       # 攻击速度倍率
        self.damage_mult = 1.0             # 伤害倍率
        self.weapons = []                  # Weapon 列表
        self.alive = True
        self.invincible_timer = 0.0        # 无敌计时器
        self.flip_x = False                # 是否水平翻转

        # 动画
        self.bob_offset = 0.0
        self.idle_wobble = 0.0
        self.flash_timer = 0.0

        # 被动升级计数
        self.passive_counts = {k: 0 for k in PASSIVE_UPGRADES}

    @property
    def weapon_types(self):
        return [w.weapon_type for w in self.weapons]

    def can_add_weapon(self):
        return len(self.weapons) < PLAYER_MAX_WEAPONS

    def add_weapon(self, weapon_type, level=1):
        """添加新武器"""
        if not self.can_add_weapon() and weapon_type not in self.weapon_types:
            return False
        # 检查是否重复
        for w in self.weapons:
            if w.weapon_type == weapon_type:
                if w.level < w.max_level:
                    w.level += 1
                return True
        self.weapons.append(Weapon(weapon_type, level))
        return True

    def upgrade_weapon(self, weapon_type):
        """升级已有武器"""
        for w in self.weapons:
            if w.weapon_type == weapon_type and w.level < w.max_level:
                w.level += 1
                return True
        return False

    def apply_passive(self, passive_key):
        """应用被动升级"""
        if passive_key not in PASSIVE_UPGRADES:
            return
        p = PASSIVE_UPGRADES[passive_key]
        self.passive_counts[passive_key] = self.passive_counts.get(passive_key, 0) + 1
        if "hp_bonus" in p:
            self.max_hp += p["hp_bonus"]
            self.hp = min(self.hp + p["hp_bonus"], self.max_hp)
        if "speed_mult" in p:
            self.speed += PLAYER_SPEED * p["speed_mult"]
        if "pickup_mult" in p:
            self.pickup_range += PLAYER_PICKUP_RANGE * p["pickup_mult"]
        if "dmg_reduce" in p:
            self.damage_reduction = min(0.75, self.damage_reduction + p["dmg_reduce"])
        if "atk_speed_mult" in p:
            self.attack_speed_mult += p["atk_speed_mult"]
        if "dmg_mult" in p:
            self.damage_mult += p["dmg_mult"]

    def take_damage(self, raw_damage, dmg_numbers):
        """受到伤害，考虑无敌和减伤"""
        if self.invincible_timer > 0 or not self.alive:
            return
        actual = raw_damage * (1.0 - self.damage_reduction)
        self.hp -= actual
        self.invincible_timer = PLAYER_INVINCIBLE_TIME
        dmg_numbers.append(DamageNumber(self.world_x, self.world_y - 30, int(actual), COLOR_RED))
        # 记录承受伤害
        if "dmg_taken" in game_ref:
            game_ref["dmg_taken"] += actual
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def update(self, dt, keys, enemies, experience_orbs, dmg_numbers):
        """玩家每帧更新"""
        # --- 移动输入 ---
        dx, dy = 0.0, 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        # 向量标准化
        mag = math.hypot(dx, dy)
        if mag > 0:
            dx /= mag
            dy /= mag
        self.world_x += dx * self.speed * dt
        self.world_y += dy * self.speed * dt

        # --- 朝向 ---
        if dx > 0:
            self.flip_x = False
        elif dx < 0:
            self.flip_x = True

        # --- 无敌计时 ---
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            self.flash_timer += dt

        # --- 动画 ---
        if mag > 0.01:
            self.bob_offset = math.sin(pygame.time.get_ticks() * 0.01) * 4
        else:
            self.idle_wobble = math.sin(pygame.time.get_ticks() * 0.003) * 2

        # --- 拾取经验 ---
        for orb in experience_orbs:
            if not orb.alive:
                continue
            if math.hypot(self.world_x - orb.x, self.world_y - orb.y) < self.pickup_range:
                orb.alive = False
                self.xp += orb.value

        # --- 更新武器 ---
        for w in self.weapons:
            w.update(dt, self, enemies, game_ref["bullets"], game_ref["effects"], dmg_numbers, self.attack_speed_mult)

    def draw(self, surf, camera):
        """绘制玩家"""
        sx, sy = camera.world_to_screen(self.world_x, self.world_y)
        if self.invincible_timer > 0 and int(self.flash_timer * 20) % 2 == 0:
            return  # 受伤闪烁（隔帧不绘制）
        if not self.alive:
            # 死亡淡出
            return

        # 运动浮动
        bobbing = self.bob_offset if abs(self.bob_offset) > 0.1 else self.idle_wobble

        img = load_image("player", (48, 48))
        if self.flip_x:
            img = pygame.transform.flip(img, True, False)

        draw_y = int(sy + bobbing - 24)
        draw_x = int(sx - 24)
        surf.blit(img, (draw_x, draw_y))

        # 绘制武器跟随
        for i, w in enumerate(self.weapons):
            ox, oy = WEAPON_OFFSETS[i % len(WEAPON_OFFSETS)]
            if self.flip_x:
                ox = -ox
            w.draw(surf, camera, self.world_x, self.world_y, ox, oy)
        # 绘制小刀环绕
        for w in self.weapons:
            w.draw_knives(surf, camera, self.world_x, self.world_y)


# ============================================================
# 9. 敌人基类与具体敌人
# ============================================================

class EnemyBase:
    """敌人基类"""
    def __init__(self, config_key, world_x, world_y, game_time):
        cfg = ENEMY_CONFIGS[config_key]
        self.config_key = config_key
        self.world_x = world_x
        self.world_y = world_y
        self.hp = cfg["hp"] * enemy_hp_mult(game_time)
        self.max_hp = self.hp
        self.speed = cfg["speed"] * enemy_speed_mult(game_time)
        self.damage = cfg["damage"] * enemy_damage_mult(game_time)
        self.xp_value = cfg["xp"]
        self.radius = cfg["radius"]
        self.alive = True
        self.knockback_x = 0.0
        self.knockback_y = 0.0
        self.asset_key = cfg.get("asset_key", config_key)
        self._id = id(self)

    def take_damage(self, amount, dmg_numbers):
        self.hp -= amount
        dmg_numbers.append(DamageNumber(self.world_x, self.world_y - self.radius, int(amount)))
        # 全局伤害统计
        if "dmg_dealt" in game_ref:
            game_ref["dmg_dealt"] += amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def update_knockback(self, dt):
        if abs(self.knockback_x) > 0.5 or abs(self.knockback_y) > 0.5:
            self.world_x += self.knockback_x * dt
            self.world_y += self.knockback_y * dt
            self.knockback_x *= 0.85
            self.knockback_y *= 0.85
        else:
            self.knockback_x = 0.0
            self.knockback_y = 0.0

    def move_toward(self, target_x, target_y, dt):
        dx = target_x - self.world_x
        dy = target_y - self.world_y
        dist = math.hypot(dx, dy)
        if dist > 1:
            self.world_x += (dx / dist) * self.speed * dt
            self.world_y += (dy / dist) * self.speed * dt

    def update(self, dt, player, dmg_numbers):
        """基类更新：追踪 + 击退"""
        self.update_knockback(dt)
        self.move_toward(player.world_x, player.world_y, dt)

    def check_player_collision(self, player, dmg_numbers):
        """接触伤害"""
        dist = math.hypot(self.world_x - player.world_x, self.world_y - player.world_y)
        if dist < self.radius + PLAYER_RADIUS:
            player.take_damage(self.damage, dmg_numbers)

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.world_x, self.world_y)
        if 0 <= sx <= LOGICAL_WIDTH + 50 and 0 <= sy <= LOGICAL_HEIGHT + 50:
            size = int(self.radius * 2)
            img = load_image(self.asset_key, (max(size, 20), max(size, 20)))
            surf.blit(img, img.get_rect(center=(int(sx), int(sy))))
            # 血条
            if self.hp < self.max_hp:
                bar_w = size + 10
                bar_h = 4
                bar_x = int(sx - bar_w / 2)
                bar_y = int(sy - self.radius - 8)
                ratio = self.hp / self.max_hp
                pygame.draw.rect(surf, COLOR_DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surf, COLOR_HP_RED, (bar_x, bar_y, int(bar_w * ratio), bar_h))


class PencilLineEnemy(EnemyBase):
    """铅笔线条怪：快速、低血量"""
    def __init__(self, world_x, world_y, game_time):
        super().__init__("pencil_line", world_x, world_y, game_time)


class InkDropEnemy(EnemyBase):
    """墨水滴怪：慢速、高血量"""
    def __init__(self, world_x, world_y, game_time):
        super().__init__("ink_drop", world_x, world_y, game_time)


class SmallPencilElite(EnemyBase):
    """精英小铅笔：冲刺 AI"""
    def __init__(self, world_x, world_y, game_time):
        super().__init__("small_pencil", world_x, world_y, game_time)
        cfg = ENEMY_CONFIGS["small_pencil"]
        self.dash_speed = cfg["dash_speed"]
        self.dash_damage = cfg["dash_damage"]
        self.dash_duration = cfg["dash_duration"]
        self.dash_prepare = cfg["dash_prepare"]
        self.dash_recover = cfg["dash_recover"]
        self.dash_range = cfg["dash_range"]
        self.dash_cooldown = cfg["dash_cooldown"]
        self.dash_cooldown_remaining = cfg["dash_cooldown"] * 0.5  # 首次更快
        self.state = "CHASE"        # CHASE, PREPARE_DASH, DASH, RECOVER
        self.state_timer = 0.0
        self.dash_angle = 0.0

    def update(self, dt, player, dmg_numbers):
        self.update_knockback(dt)

        dist_to_player = math.hypot(self.world_x - player.world_x,
                                     self.world_y - player.world_y)

        if self.state == "CHASE":
            self.move_toward(player.world_x, player.world_y, dt)
            self.dash_cooldown_remaining -= dt
            if dist_to_player < self.dash_range and self.dash_cooldown_remaining <= 0:
                self.state = "PREPARE_DASH"
                self.state_timer = self.dash_prepare
                self.dash_angle = math.atan2(player.world_y - self.world_y,
                                              player.world_x - self.world_x)

        elif self.state == "PREPARE_DASH":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "DASH"
                self.state_timer = self.dash_duration

        elif self.state == "DASH":
            self.world_x += math.cos(self.dash_angle) * self.dash_speed * dt
            self.world_y += math.sin(self.dash_angle) * self.dash_speed * dt
            # 冲刺期间接触伤害更高
            if dist_to_player < self.radius + PLAYER_RADIUS:
                player.take_damage(self.dash_damage, dmg_numbers)
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "RECOVER"
                self.state_timer = self.dash_recover
                self.dash_cooldown_remaining = self.dash_cooldown

        elif self.state == "RECOVER":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "CHASE"

        # 非冲刺状态检查接触伤害
        if self.state != "DASH":
            self.check_player_collision(player, dmg_numbers)

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.world_x, self.world_y)
        if 0 <= sx <= LOGICAL_WIDTH + 50 and 0 <= sy <= LOGICAL_HEIGHT + 50:
            size = int(self.radius * 2)
            img = load_image(self.asset_key, (max(size, 24), max(size, 24)))
            # 蓄力时旋转/缩放提示
            if self.state == "PREPARE_DASH":
                img = pygame.transform.scale(img, (int(size * 1.3), int(size * 1.3)))
            surf.blit(img, img.get_rect(center=(int(sx), int(sy))))
            # 冲刺方向指示
            if self.state == "PREPARE_DASH":
                tip_x = sx + math.cos(self.dash_angle) * (size + 10)
                tip_y = sy + math.sin(self.dash_angle) * (size + 10)
                pygame.draw.line(surf, COLOR_RED, (int(sx), int(sy)),
                                 (int(tip_x), int(tip_y)), 2)
            # 血条
            if self.hp < self.max_hp:
                bar_w = size + 10
                bar_h = 4
                bar_x = int(sx - bar_w / 2)
                bar_y = int(sy - self.radius - 8)
                ratio = self.hp / self.max_hp
                pygame.draw.rect(surf, COLOR_DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surf, COLOR_ORANGE, (bar_x, bar_y, int(bar_w * ratio), bar_h))


class GiantEraserBoss(EnemyBase):
    """Boss：巨型橡皮擦"""
    def __init__(self, world_x, world_y, game_time):
        super().__init__("giant_eraser", world_x, world_y, game_time)
        self.state = "CHASE"
        self.state_timer = 0.0
        self.attack_cooldowns = {
            "charge": 2.0,       # 首次更快
            "erase_zone": 4.0,
            "summon": 6.0,
        }
        self.current_attack = None
        self.last_attack = None
        self.charge_angle = 0.0
        self.charge_target_x = 0.0
        self.charge_target_y = 0.0
        self.erase_zones = []      # 当前活跃的危险区域（正在造成伤害）
        self.warning_zones = []    # 预警中的红圈（仅视觉+倒计时，不造成伤害）
        self.enraged = False

    @property
    def is_enraged(self):
        return self.hp <= self.max_hp * ENEMY_CONFIGS["giant_eraser"]["enrage_hp_threshold"]

    def _get_attack_stats(self, attack_name):
        """获取攻击在狂暴前后的参数"""
        base = BOSS_ATTACKS[attack_name]
        if self.is_enraged and attack_name in BOSS_ENRAGE_MODIFIERS:
            merged = dict(base)
            merged.update(BOSS_ENRAGE_MODIFIERS[attack_name])
            return merged
        return dict(base)

    def update(self, dt, player, dmg_numbers):
        self.update_knockback(dt)
        dist = math.hypot(self.world_x - player.world_x, self.world_y - player.world_y)

        # 减少冷却
        for key in self.attack_cooldowns:
            self.attack_cooldowns[key] -= dt

        if self.state == "CHASE":
            self.move_toward(player.world_x, player.world_y, dt)
            # 选择攻击
            available = [k for k, cd in self.attack_cooldowns.items()
                         if cd <= 0 and k != self.last_attack]
            if not available and any(cd <= 0 for cd in self.attack_cooldowns.values()):
                available = [k for k, cd in self.attack_cooldowns.items() if cd <= 0]
            if available:
                chosen = random.choice(available)
                self.last_attack = chosen
                self.current_attack = chosen
                if chosen == "charge":
                    stats = self._get_attack_stats("charge")
                    self.state = "ATTACK_PREPARE"
                    self.state_timer = stats["telegraph"]
                    self.charge_target_x = player.world_x
                    self.charge_target_y = player.world_y
                    self.charge_angle = math.atan2(player.world_y - self.world_y,
                                                    player.world_x - self.world_x)
                elif chosen == "erase_zone":
                    stats = self._get_attack_stats("erase_zone")
                    # 立即在玩家位置创建预警红圈（仅视觉，不造成伤害）
                    self.warning_zones.append({
                        "x": player.world_x,
                        "y": player.world_y,
                        "radius": stats["radius"],
                        "timer": stats["warning"],
                        "max_timer": stats["warning"],
                    })
                    self.state = "ATTACK_PREPARE"
                    self.state_timer = stats["warning"]
                elif chosen == "summon":
                    stats = self._get_attack_stats("summon")
                    count = random.randint(stats["count_min"], stats["count_max"])
                    for _ in range(count):
                        angle = random.uniform(0, math.pi * 2)
                        r = random.uniform(150, 350)
                        ex = self.world_x + math.cos(angle) * r
                        ey = self.world_y + math.sin(angle) * r
                        game_ref["pending_spawns"].append(("pencil_line", ex, ey, 0))
                    self.attack_cooldowns["summon"] = stats["cooldown"]
                    self.current_attack = None
                    self.state = "CHASE"

        elif self.state == "ATTACK_PREPARE":
            self.state_timer -= dt
            if self.state_timer <= 0:
                if self.current_attack == "charge":
                    stats = self._get_attack_stats("charge")
                    self.state = "ATTACK"
                    self.state_timer = stats["duration"]
                elif self.current_attack == "erase_zone":
                    stats = self._get_attack_stats("erase_zone")
                    # 将最近到期的预警区转为活跃危险区域
                    if self.warning_zones:
                        wz = self.warning_zones.pop(0)
                        self.erase_zones.append({
                            "x": wz["x"],
                            "y": wz["y"],
                            "radius": stats["radius"],
                            "timer": stats["duration"],
                        })
                    self.attack_cooldowns["erase_zone"] = stats["cooldown"]
                    self.current_attack = None
                    self.state = "CHASE"

        elif self.state == "ATTACK":  # 冲撞执行
            stats = self._get_attack_stats("charge")
            self.world_x += math.cos(self.charge_angle) * stats["speed"] * dt
            self.world_y += math.sin(self.charge_angle) * stats["speed"] * dt
            if math.hypot(self.world_x - player.world_x, self.world_y - player.world_y) < self.radius + PLAYER_RADIUS:
                player.take_damage(stats["damage"], dmg_numbers)
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "RECOVERY"
                self.state_timer = 0.5
                self.attack_cooldowns["charge"] = stats["cooldown"]

        elif self.state == "RECOVERY":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "CHASE"

        # 更新预警红圈（仅视觉，不造成伤害）
        for wz in self.warning_zones[:]:
            wz["timer"] -= dt
            if wz["timer"] <= 0:
                self.warning_zones.remove(wz)

        # 更新活跃危险区域（造成伤害）
        for zone in self.erase_zones[:]:
            zone["timer"] -= dt
            if math.hypot(player.world_x - zone["x"], player.world_y - zone["y"]) < zone["radius"]:
                stats = self._get_attack_stats("erase_zone")
                player.take_damage(stats["damage_per_sec"] * dt, dmg_numbers)
            if zone["timer"] <= 0:
                self.erase_zones.remove(zone)

        # 非冲撞状态检查接触伤害
        if self.state != "ATTACK" or self.current_attack != "charge":
            self.check_player_collision(player, dmg_numbers)

        # 检查狂暴
        was_enraged = self.enraged
        self.enraged = self.is_enraged
        if self.enraged and not was_enraged:
            game_ref["messages"].append(("THE GIANT ERASER IS ENRAGED!", 2.0))

    def draw(self, surf, camera):
        sx, sy = camera.world_to_screen(self.world_x, self.world_y)
        if 0 <= sx <= LOGICAL_WIDTH + 100 and 0 <= sy <= LOGICAL_HEIGHT + 100:
            size = int(self.radius * 2)
            img = load_image(self.asset_key, (max(size, 60), max(size, 60)))
            surf.blit(img, img.get_rect(center=(int(sx), int(sy))))

        # 预警红圈（脉动动画：圈从小到大再收缩，透明度变化）
        for wz in self.warning_zones:
            zx, zy = camera.world_to_screen(wz["x"], wz["y"])
            progress = 1.0 - (wz["timer"] / max(wz["max_timer"], 0.01))
            # 脉动效果：半径在 0.3x ~ 1.0x 之间循环
            pulse = 0.3 + 0.7 * abs(math.sin(progress * math.pi * 3))
            display_radius = int(wz["radius"] * pulse)
            # 透明度从浅到深渐变
            alpha = int(60 + 140 * progress)
            danger_surf = pygame.Surface((display_radius * 2, display_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(danger_surf, (255, 40, 40, alpha), (display_radius, display_radius), display_radius)
            pygame.draw.circle(danger_surf, (255, 80, 80, min(255, alpha + 40)), (display_radius, display_radius), display_radius, 3)
            surf.blit(danger_surf, (int(zx - display_radius), int(zy - display_radius)))

        # 活跃危险区域（持续红圈，伤害阶段）
        for zone in self.erase_zones:
            zx, zy = camera.world_to_screen(zone["x"], zone["y"])
            radius = int(zone["radius"])
            alpha = int(100 + 50 * math.sin(zone["timer"] * 5))
            danger_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(danger_surf, (255, 40, 40, alpha), (radius, radius), radius)
            pygame.draw.circle(danger_surf, (255, 20, 20, 220), (radius, radius), radius, 4)
            surf.blit(danger_surf, (int(zx - radius), int(zy - radius)))

        # 冲撞预警指示
        if self.state == "ATTACK_PREPARE" and self.current_attack == "charge":
            tip_len = self.radius + 40
            tip_x = sx + math.cos(self.charge_angle) * tip_len
            tip_y = sy + math.sin(self.charge_angle) * tip_len
            pygame.draw.line(surf, COLOR_RED, (int(sx), int(sy)), (int(tip_x), int(tip_y)), 4)


# ============================================================
# 10. 升级卡片系统
# ============================================================

class UpgradeCard:
    """升级选择卡片"""
    def __init__(self, rect, upgrade_type, data):
        """
        upgrade_type: "new_weapon" | "weapon_upgrade" | "passive"
        data: 具体升级数据
        """
        self.rect = rect
        self.upgrade_type = upgrade_type
        self.data = data
        self.hovered = False

    def contains(self, mx, my):
        return self.rect.collidepoint(mx, my)

    def draw(self, surf):
        color = COLOR_CARD_HOVER if self.hovered else COLOR_CARD_BG
        # 卡片阴影
        shadow_rect = self.rect.move(3, 3)
        pygame.draw.rect(surf, (0, 0, 0, 40), shadow_rect, border_radius=8)
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, COLOR_CARD_BORDER, self.rect, 2, border_radius=8)

        cx, cy = self.rect.center
        if self.upgrade_type == "new_weapon":
            info = WEAPON_INFO.get(self.data, {"name": self.data})
            draw_text(surf, f"[New Weapon]", cx, cy - 30, FONT_MEDIUM, COLOR_ORANGE)
            draw_text(surf, info["name"], cx, cy + 5, FONT_LARGE, COLOR_BLACK)
        elif self.upgrade_type == "weapon_upgrade":
            wtype, new_level = self.data
            info = WEAPON_INFO.get(wtype, {"name": wtype})
            draw_text(surf, f"[Upgrade]", cx, cy - 30, FONT_MEDIUM, COLOR_GREEN)
            draw_text(surf, f"{info['name']} → Lv.{new_level}", cx, cy + 5, FONT_LARGE, COLOR_BLACK)
        elif self.upgrade_type == "passive":
            p = PASSIVE_UPGRADES.get(self.data, {"name": self.data, "desc": ""})
            draw_text(surf, f"[Passive]", cx, cy - 30, FONT_MEDIUM, COLOR_BLUE)
            draw_text(surf, p["name"], cx, cy + 5, FONT_LARGE, COLOR_BLACK)
            draw_text(surf, p["desc"], cx, cy + 35, FONT_SMALL, COLOR_DARK_GRAY)


def generate_upgrade_cards(player):
    """
    根据权重随机生成 3 张升级卡片
    返回 UpgradeCard 列表
    """
    pool_new_weapon = []
    pool_weapon_upgrade = []
    pool_passive = []

    # 新武器池：未拥有的武器
    all_weapons = list(WEAPON_STATS.keys())
    for wtype in all_weapons:
        if wtype not in player.weapon_types and player.can_add_weapon():
            pool_new_weapon.append(("new_weapon", wtype))

    # 武器升级池：已拥有且未满级的武器
    for w in player.weapons:
        if w.level < w.max_level:
            pool_weapon_upgrade.append(("weapon_upgrade", (w.weapon_type, w.level + 1)))

    # 被动池
    for key in PASSIVE_UPGRADES:
        pool_passive.append(("passive", key))

    # 动态调整权重
    candidates = []
    if pool_new_weapon:
        candidates.extend(pool_new_weapon * 3)   # 权重 30%
    if pool_weapon_upgrade:
        candidates.extend(pool_weapon_upgrade * 4)  # 权重 40%
    if pool_passive:
        candidates.extend(pool_passive * 3)      # 权重 30%

    if not candidates:
        # 如果没有任何合法选项，生成占位升级
        return [UpgradeCard(pygame.Rect(0, 0, 200, 120), "passive", "max_hp")]

    # 去重：采样 3 个不同的选项
    chosen = []
    seen = set()
    shuffled = list(candidates)
    random.shuffle(shuffled)
    for c in shuffled:
        key = str(c)
        if key not in seen:
            seen.add(key)
            chosen.append(c)
        if len(chosen) >= 3:
            break

    # 如果不足 3 个，允许重复类型但不要完全相同
    while len(chosen) < 3:
        extra = random.choice(candidates)
        if str(extra) not in seen:
            seen.add(str(extra))
            chosen.append(extra)
        elif len(chosen) < len(candidates):
            continue
        else:
            chosen.append(extra)

    # 创建卡片 UI
    card_w, card_h = 200, 140
    total_w = card_w * 3 + 40 * 2
    start_x = (LOGICAL_WIDTH - total_w) / 2
    center_y = LOGICAL_HEIGHT / 2

    cards = []
    for i, (up_type, data) in enumerate(chosen[:3]):
        rect = pygame.Rect(start_x + i * (card_w + 40), center_y - card_h / 2, card_w, card_h)
        cards.append(UpgradeCard(rect, up_type, data))
    return cards


# ============================================================
# 11. 敌人生成
# ============================================================

def get_spawn_position(player_x, player_y, camera):
    """在屏幕外侧生成敌人位置，距玩家至少 SPAWN_DISTANCE_MIN"""
    side = random.choice(["top", "bottom", "left", "right"])
    margin = SPAWN_MARGIN
    if side == "top":
        wx, wy = camera.screen_to_world(random.randint(0, LOGICAL_WIDTH), -margin)
    elif side == "bottom":
        wx, wy = camera.screen_to_world(random.randint(0, LOGICAL_WIDTH), LOGICAL_HEIGHT + margin)
    elif side == "left":
        wx, wy = camera.screen_to_world(-margin, random.randint(0, LOGICAL_HEIGHT))
    else:
        wx, wy = camera.screen_to_world(LOGICAL_WIDTH + margin, random.randint(0, LOGICAL_HEIGHT))
    # 保证距玩家距离 >= SPAWN_DISTANCE_MIN
    if math.hypot(wx - player_x, wy - player_y) < SPAWN_DISTANCE_MIN:
        return get_spawn_position(player_x, player_y, camera)
    return wx, wy


def create_enemy(enemy_type, world_x, world_y, game_time):
    """工厂函数：根据类型创建敌人实例"""
    if enemy_type == "pencil_line":
        return PencilLineEnemy(world_x, world_y, game_time)
    elif enemy_type == "ink_drop":
        return InkDropEnemy(world_x, world_y, game_time)
    elif enemy_type == "small_pencil":
        return SmallPencilElite(world_x, world_y, game_time)
    return None


# ============================================================
# 12. 游戏主类
# ============================================================

class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        """重置游戏状态"""
        self.state = "PLAYING"     # PLAYING, LEVEL_UP, GAME_OVER, VICTORY
        self.game_time = 0.0
        self.player = Player()
        # 给玩家初始武器（手枪 Lv.1），确保开局就能攻击
        self.player.add_weapon("pistol", 1)
        self.camera = Camera()
        self.enemies = []
        self.bullets = []
        self.experience_orbs = []
        self.effects = []
        self.dmg_numbers = []
        self.messages = []          # (文本, 持续时间)
        self.pending_spawns = []    # Boss 召唤等延迟生成的敌人
        self.boss = None
        self.boss_spawned = False
        self.boss_defeated = False
        self.boss_warning_timer = 0.0
        self.spawn_timer = 0.0
        self.spawn_interval = 1.5
        self.current_spawn_types = ["pencil_line"]
        self.max_enemies = 30
        self.event_triggers = {
            60: False,    # 1:00 墨水入侵
            120: False,   # 2:00 铅笔突袭 + 精英
        }
        self.upgrade_cards = []
        self.victory_checked = False

        # ---- 战斗统计数据 ----
        self.stats_kills = 0           # 总击杀数
        self.stats_damage_dealt = 0.0  # 累计造成伤害
        self.stats_damage_taken = 0.0  # 累计受到伤害

        # 初始化全局引用（供武器和敌人访问）
        global game_ref
        game_ref["bullets"] = self.bullets
        game_ref["effects"] = self.effects
        game_ref["pending_spawns"] = self.pending_spawns
        game_ref["messages"] = self.messages
        game_ref["dmg_dealt"] = 0.0
        game_ref["dmg_taken"] = 0.0

    def update(self, dt):
        """主更新"""
        # --- 处理消息计时 ---
        for i in range(len(self.messages) - 1, -1, -1):
            text, timer = self.messages[i]
            timer -= dt
            if timer <= 0:
                self.messages.pop(i)
            else:
                self.messages[i] = (text, timer)

        if self.state == "PLAYING":
            self._update_playing(dt)
        elif self.state == "LEVEL_UP":
            self._update_level_up(dt)
        elif self.state == "GAME_OVER" or self.state == "VICTORY":
            pass  # 等待鼠标点击

    def _update_playing(self, dt):
        """PLAYING 状态下的逻辑更新"""
        self.game_time += dt
        player = self.player
        keys = pygame.key.get_pressed()

        # --- 更新玩家 ---
        player.update(dt, keys, self.enemies, self.experience_orbs, self.dmg_numbers)

        # 死亡检查
        if not player.alive:
            self.state = "GAME_OVER"
            return

        # --- 更新摄像机 ---
        self.camera.update(player.world_x, player.world_y)

        # --- 检查经验升级 ---
        xp_needed = get_xp_for_level(player.level + 1)
        if player.xp >= xp_needed:
            self._trigger_level_up()
            return

        # --- 更新子弹 ---
        for b in self.bullets[:]:
            b.update(dt)
            if not b.alive:
                self.bullets.remove(b)
                continue
            # 子弹与敌人碰撞
            for e in self.enemies:
                if not e.alive:
                    continue
                if math.hypot(b.x - e.world_x, b.y - e.world_y) < b.radius + e.radius:
                    if id(e) not in b.hit_enemies:
                        b.hit_enemies.add(id(e))
                        e.take_damage(b.damage, self.dmg_numbers)
                        if b.pierce <= 0:
                            b.alive = False
                            break
                        else:
                            b.pierce -= 1
                            if b.pierce < 0:
                                b.alive = False
                                break

        # --- 更新敌人 ---
        for e in self.enemies[:]:
            if e.alive:
                e.update(dt, player, self.dmg_numbers)
            else:
                # 敌人死亡：掉落经验
                self.experience_orbs.append(ExperienceOrb(e.world_x, e.world_y, e.xp_value))
                self.stats_kills += 1
                if e is self.boss:
                    self.boss = None
                    self.boss_defeated = True
                self.enemies.remove(e)

        # --- 更新经验球 ---
        for orb in self.experience_orbs[:]:
            orb.update(dt, self.game_time)
            if not orb.alive:
                self.experience_orbs.remove(orb)

        # --- 更新近战效果 ---
        for fx in self.effects[:]:
            fx.update(dt)
            if not fx.alive:
                self.effects.remove(fx)

        # --- 更新伤害数字 ---
        for dn in self.dmg_numbers[:]:
            dn.update(dt)
            if not dn.alive:
                self.dmg_numbers.remove(dn)

        # --- 精英生成 ---
        elite_count = sum(1 for e in self.enemies if isinstance(e, SmallPencilElite))
        normal_count = sum(1 for e in self.enemies if isinstance(e, (PencilLineEnemy, InkDropEnemy)))
        if self.game_time >= 120 and elite_count < ELITE_CAP and random.random() < 0.008 and self.boss is None:
            wx, wy = get_spawn_position(player.world_x, player.world_y, self.camera)
            self.enemies.append(SmallPencilElite(wx, wy, self.game_time))

        # --- 事件触发 ---
        if self.game_time >= 60 and not self.event_triggers[60]:
            self.event_triggers[60] = True
            self.messages.append(("INK INVASION! Ink drops are appearing!", 2.5))
        if self.game_time >= 120 and not self.event_triggers[120]:
            self.event_triggers[120] = True
            self.messages.append(("PENCIL ASSAULT! Elite pencils spotted!", 2.5))

        # --- Boss 生成 ---
        if self.game_time >= BOSS_SPAWN_TIME and not self.boss_spawned:
            self._spawn_boss()

        # --- 更新生成计划 ---
        for time_pt, interval, max_en, types in SPAWN_SCHEDULE:
            if self.game_time >= time_pt:
                self.spawn_interval = interval
                self.max_enemies = max_en
                self.current_spawn_types = types

        # --- 普通敌人生成（Boss 出现后完全停止）---
        if self.boss is None:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_interval and normal_count < ENEMY_CAP:
                self.spawn_timer = 0.0
                if self.current_spawn_types:
                    etype = random.choice(self.current_spawn_types)
                    if etype != "small_pencil":  # 精英不通过普通生成
                        wx, wy = get_spawn_position(player.world_x, player.world_y, self.camera)
                        enemy = create_enemy(etype, wx, wy, self.game_time)
                        if enemy:
                            self.enemies.append(enemy)

        # --- 处理延迟生成（Boss 召唤等） ---
        for spawn in self.pending_spawns[:]:
            etype, ex, ey, _ = spawn
            enemy = create_enemy(etype, ex, ey, self.game_time)
            if enemy:
                self.enemies.append(enemy)
            self.pending_spawns.remove(spawn)

        # --- 胜利检查 ---
        if self.game_time >= VICTORY_CHECK_TIME and self.boss_defeated and not self.victory_checked:
            self.state = "VICTORY"
            self.victory_checked = True

        # --- 如果 Boss 已在战斗中被击杀 ---
        if self.boss_defeated and self.boss is None and not self.victory_checked and self.game_time >= VICTORY_CHECK_TIME:
            self.state = "VICTORY"
            self.victory_checked = True

    def _trigger_level_up(self):
        """触发升级"""
        self.upgrade_cards = generate_upgrade_cards(self.player)
        self.state = "LEVEL_UP"

    def _window_to_logical(self, mx, my):
        """将窗口鼠标坐标映射回逻辑坐标"""
        win_w, win_h = _real_screen.get_size()
        if win_w == 0 or win_h == 0:
            return mx, my
        scale = min(win_w / LOGICAL_WIDTH, win_h / LOGICAL_HEIGHT)
        offset_x = (win_w - LOGICAL_WIDTH * scale) / 2
        offset_y = (win_h - LOGICAL_HEIGHT * scale) / 2
        return (mx - offset_x) / scale, (my - offset_y) / scale

    def _update_level_up(self, dt):
        """升级选择界面更新（由事件驱动，此处仅处理悬停）"""
        mx, my = pygame.mouse.get_pos()
        logical_mx, logical_my = self._window_to_logical(mx, my)
        for card in self.upgrade_cards:
            card.hovered = card.contains(logical_mx, logical_my)

    def handle_level_up_click(self, mx, my):
        """处理升级卡片点击"""
        for card in self.upgrade_cards:
            if card.contains(mx, my):
                self._apply_upgrade(card)
                self.upgrade_cards = []
                self.state = "PLAYING"
                return

    def _apply_upgrade(self, card):
        """应用升级选择"""
        player = self.player
        if card.upgrade_type == "new_weapon":
            player.add_weapon(card.data, 1)
        elif card.upgrade_type == "weapon_upgrade":
            wtype, _ = card.data
            player.upgrade_weapon(wtype)
        elif card.upgrade_type == "passive":
            player.apply_passive(card.data)
        # 升级：等级 +1，HP 回满
        player.level += 1
        player.hp = player.max_hp

    def _spawn_boss(self):
        """生成 Boss"""
        self.boss_warning_timer = 1.5
        self.messages.append(("!!! BOSS WARNING !!!", 3.0))
        # Boss 在屏幕外生成
        wx, wy = get_spawn_position(self.player.world_x, self.player.world_y, self.camera)
        self.boss = GiantEraserBoss(wx, wy, self.game_time)
        self.enemies.append(self.boss)
        self.boss_spawned = True

    def draw(self, surf):
        """绘制整个游戏画面"""
        surf.fill(COLOR_PAPER)

        # --- 绘制纸张背景纹理（程序生成网格线） ---
        self._draw_paper_background(surf)

        # --- 绘制经验球 ---
        for orb in self.experience_orbs:
            orb.draw(surf, self.camera)

        # --- 绘制敌人 ---
        for e in self.enemies:
            if e.alive:
                e.draw(surf, self.camera)

        # --- 绘制子弹 ---
        for b in self.bullets:
            b.draw(surf, self.camera)

        # --- 绘制近战效果 ---
        for fx in self.effects:
            fx.draw(surf, self.camera)

        # --- 绘制玩家 ---
        self.player.draw(surf, self.camera)

        # --- 绘制伤害数字 ---
        for dn in self.dmg_numbers:
            dn.draw(surf, self.camera)

        # --- 绘制 UI ---
        self._draw_hud(surf)

        # --- Boss 血条 ---
        if self.boss is not None and self.boss.alive:
            self._draw_boss_hp(surf)

        # --- 消息 ---
        self._draw_messages(surf)

        # --- 升级界面 ---
        if self.state == "LEVEL_UP":
            self._draw_level_up(surf)

        # --- Game Over ---
        if self.state == "GAME_OVER":
            self._draw_game_over(surf)

        # --- Victory ---
        if self.state == "VICTORY":
            self._draw_victory(surf)

    def _draw_paper_background(self, surf):
        """绘制纸张背景（网格线 + 尝试加载纹理）"""
        try:
            bg_img = load_image("background", (LOGICAL_WIDTH, LOGICAL_HEIGHT))
            # 计算平铺偏移
            cam_x = self.camera.x % LOGICAL_WIDTH
            cam_y = self.camera.y % LOGICAL_HEIGHT
            for dx in [-LOGICAL_WIDTH, 0, LOGICAL_WIDTH]:
                for dy in [-LOGICAL_HEIGHT, 0, LOGICAL_HEIGHT]:
                    surf.blit(bg_img, (dx - cam_x, dy - cam_y))
        except Exception:
            pass
        # 程序绘制浅色网格线（模拟纸张）
        grid_size = 80
        cam_x = self.camera.x % grid_size
        cam_y = self.camera.y % grid_size
        for x in range(-grid_size, LOGICAL_WIDTH + grid_size, grid_size):
            px = x - cam_x
            pygame.draw.line(surf, (220, 215, 205), (px, 0), (px, LOGICAL_HEIGHT), 1)
        for y in range(-grid_size, LOGICAL_HEIGHT + grid_size, grid_size):
            py = y - cam_y
            pygame.draw.line(surf, (220, 215, 205), (0, py), (LOGICAL_WIDTH, py), 1)

    def _draw_hud(self, surf):
        """绘制顶部 HUD"""
        player = self.player
        # HP 条
        hp_bar_w, hp_bar_h = 200, 16
        hp_x, hp_y = 20, 15
        pygame.draw.rect(surf, COLOR_DARK_GRAY, (hp_x, hp_y, hp_bar_w, hp_bar_h), border_radius=4)
        hp_ratio = player.hp / player.max_hp
        hp_color = COLOR_HP_RED if hp_ratio > 0.3 else COLOR_RED
        pygame.draw.rect(surf, hp_color, (hp_x, hp_y, int(hp_bar_w * hp_ratio), hp_bar_h), border_radius=4)
        draw_text(surf, f"HP: {int(player.hp)}/{int(player.max_hp)}", hp_x + hp_bar_w / 2, hp_y + hp_bar_h / 2, FONT_SMALL, COLOR_WHITE)

        # 等级
        draw_text(surf, f"LV.{player.level}", hp_x + hp_bar_w + 30, hp_y + hp_bar_h / 2, FONT_MEDIUM, COLOR_BLACK, center=False)

        # XP 条
        xp_bar_w, xp_bar_h = 150, 10
        xp_x, xp_y = hp_x, hp_y + hp_bar_h + 6
        current_xp = player.xp - get_xp_for_level(player.level)
        needed_xp = get_xp_for_level(player.level + 1) - get_xp_for_level(player.level)
        xp_ratio = min(1.0, current_xp / max(1, needed_xp))
        pygame.draw.rect(surf, COLOR_DARK_GRAY, (xp_x, xp_y, xp_bar_w, xp_bar_h), border_radius=3)
        pygame.draw.rect(surf, COLOR_XP_GREEN, (xp_x, xp_y, int(xp_bar_w * xp_ratio), xp_bar_h), border_radius=3)
        draw_text(surf, f"XP: {int(current_xp)}/{int(needed_xp)}", xp_x + xp_bar_w + 10, xp_y + xp_bar_h / 2, FONT_SMALL, COLOR_DARK_GRAY, center=False)

        # 生存时间
        mins = int(self.game_time // 60)
        secs = int(self.game_time % 60)
        draw_text(surf, f"Time: {mins:02d}:{secs:02d}", LOGICAL_WIDTH - 120, 25, FONT_MEDIUM, COLOR_BLACK)

        # 武器图标
        wx_start = hp_x
        wy = xp_y + xp_bar_h + 10
        for i, w in enumerate(player.weapons):
            icon = load_image(w.weapon_type, (22, 22))
            ix = wx_start + i * 28
            surf.blit(icon, (ix, wy))
            lvl_text = FONT_SMALL.render(f"{w.level}", True, COLOR_DARK_GRAY)
            surf.blit(lvl_text, (ix + 18, wy + 6))

    def _draw_boss_hp(self, surf):
        """Boss 血条（屏幕顶部中央）"""
        if self.boss is None or not self.boss.alive:
            return
        bar_w, bar_h = 400, 20
        bar_x = (LOGICAL_WIDTH - bar_w) / 2
        bar_y = 55
        ratio = self.boss.hp / self.boss.max_hp
        pygame.draw.rect(surf, (40, 40, 40), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=6)
        pygame.draw.rect(surf, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        boss_color = (255, 60, 60) if self.boss.enraged else COLOR_BOSS_HP
        pygame.draw.rect(surf, boss_color, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=4)
        enraged_text = " [ENRAGED]" if self.boss.enraged else ""
        draw_text(surf, f"GIANT ERASER{enraged_text}", bar_x + bar_w / 2, bar_y + bar_h / 2, FONT_SMALL, COLOR_WHITE)

    def _draw_messages(self, surf):
        """绘制事件消息"""
        for i, (text, _) in enumerate(self.messages):
            alpha = min(255, int(200 * (self.messages[i][1] / 2.0))) if self.messages[i][1] < 2.0 else 255
            txt = FONT_LARGE.render(text, True, COLOR_RED)
            if alpha < 255:
                txt.set_alpha(alpha)
            surf.blit(txt, txt.get_rect(center=(LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2 - 80 + i * 50)))

    def _draw_level_up(self, surf):
        """升级选择界面"""
        # 半透明遮罩
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surf.blit(overlay, (0, 0))

        draw_text(surf, "LEVEL UP! Choose an upgrade:", LOGICAL_WIDTH / 2, LOGICAL_HEIGHT / 2 - 130, FONT_LARGE, COLOR_WHITE)
        for card in self.upgrade_cards:
            card.draw(surf)

    def _get_battle_stats(self):
        """收集战斗统计数据"""
        mins = int(self.game_time // 60)
        secs = int(self.game_time % 60)
        return [
            f"Survival Time: {mins:02d}:{secs:02d}",
            f"Final Level: {self.player.level}",
            f"Weapons: {len(self.player.weapons)}",
            f"Enemies Killed: {self.stats_kills}",
            f"Damage Dealt: {int(game_ref['dmg_dealt'])}",
            f"Damage Taken: {int(game_ref['dmg_taken'])}",
        ]

    def _draw_game_over(self, surf):
        """失败界面"""
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surf.blit(overlay, (0, 0))

        base_y = LOGICAL_HEIGHT / 2 - 160
        draw_text(surf, "GAME OVER", LOGICAL_WIDTH / 2, base_y, FONT_HUGE, COLOR_RED)

        stats = self._get_battle_stats()
        for i, line in enumerate(stats):
            draw_text(surf, line, LOGICAL_WIDTH / 2, base_y + 55 + i * 32, FONT_MEDIUM, COLOR_WHITE)

        # RESTART 按钮
        btn_w, btn_h = 160, 45
        btn_spacing = 40
        restart_x = LOGICAL_WIDTH / 2 - btn_w - btn_spacing / 2
        btn_y = base_y + 55 + len(stats) * 32 + 30
        self._game_over_restart_btn = pygame.Rect(restart_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, COLOR_RED, self._game_over_restart_btn, border_radius=8)
        draw_text(surf, "RESTART", self._game_over_restart_btn.centerx, self._game_over_restart_btn.centery, FONT_MEDIUM, COLOR_WHITE)

        # EXIT 按钮
        exit_x = LOGICAL_WIDTH / 2 + btn_spacing / 2
        self._game_over_exit_btn = pygame.Rect(exit_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, COLOR_DARK_GRAY, self._game_over_exit_btn, border_radius=8)
        draw_text(surf, "EXIT", self._game_over_exit_btn.centerx, self._game_over_exit_btn.centery, FONT_MEDIUM, COLOR_WHITE)

    def _draw_victory(self, surf):
        """胜利界面"""
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surf.blit(overlay, (0, 0))

        base_y = LOGICAL_HEIGHT / 2 - 170
        draw_text(surf, "VICTORY!", LOGICAL_WIDTH / 2, base_y, FONT_HUGE, COLOR_GREEN)
        draw_text(surf, "THE GIANT ERASER HAS BEEN DEFEATED", LOGICAL_WIDTH / 2, base_y + 45, FONT_LARGE, COLOR_WHITE)

        stats = self._get_battle_stats()
        for i, line in enumerate(stats):
            draw_text(surf, line, LOGICAL_WIDTH / 2, base_y + 90 + i * 32, FONT_MEDIUM, COLOR_WHITE)

        # PLAY AGAIN 按钮
        btn_w, btn_h = 180, 45
        btn_spacing = 40
        play_x = LOGICAL_WIDTH / 2 - btn_w - btn_spacing / 2
        btn_y = base_y + 90 + len(stats) * 32 + 30
        self._victory_play_btn = pygame.Rect(play_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, COLOR_GREEN, self._victory_play_btn, border_radius=8)
        draw_text(surf, "PLAY AGAIN", self._victory_play_btn.centerx, self._victory_play_btn.centery, FONT_MEDIUM, COLOR_WHITE)

        # EXIT 按钮
        exit_x = LOGICAL_WIDTH / 2 + btn_spacing / 2
        self._victory_exit_btn = pygame.Rect(exit_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(surf, COLOR_DARK_GRAY, self._victory_exit_btn, border_radius=8)
        draw_text(surf, "EXIT", self._victory_exit_btn.centerx, self._victory_exit_btn.centery, FONT_MEDIUM, COLOR_WHITE)

    def handle_click(self, mx, my):
        """处理鼠标点击"""
        logical_mx, logical_my = self._window_to_logical(mx, my)

        if self.state == "LEVEL_UP":
            self.handle_level_up_click(logical_mx, logical_my)
        elif self.state == "GAME_OVER":
            if hasattr(self, '_game_over_restart_btn') and self._game_over_restart_btn.collidepoint(logical_mx, logical_my):
                self.reset()
            elif hasattr(self, '_game_over_exit_btn') and self._game_over_exit_btn.collidepoint(logical_mx, logical_my):
                pygame.quit()
                sys.exit()
        elif self.state == "VICTORY":
            if hasattr(self, '_victory_play_btn') and self._victory_play_btn.collidepoint(logical_mx, logical_my):
                self.reset()
            elif hasattr(self, '_victory_exit_btn') and self._victory_exit_btn.collidepoint(logical_mx, logical_my):
                pygame.quit()
                sys.exit()


# ============================================================
# 13. 全局引用（供回调访问）
# ============================================================

game_ref = {
    "bullets": [],
    "effects": [],
    "pending_spawns": [],
    "messages": [],
    "dmg_dealt": 0.0,
    "dmg_taken": 0.0,
}


# ============================================================
# 14. 主循环
# ============================================================

async def main():
    game = Game()
    running = True

    while running:
        dt = min(CLOCK.tick(FPS) / 1000.0, 0.1)  # 限制最大 dt 防止跳帧异常

        # --- 事件处理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                game.handle_click(mx, my)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # --- 更新 ---
        game.update(dt)

        # --- 渲染到逻辑表面 ---
        game.draw(LOGICAL_SURFACE)

        # --- 缩放到实际窗口 ---
        win_w, win_h = _real_screen.get_size()
        scale = min(win_w / LOGICAL_WIDTH, win_h / LOGICAL_HEIGHT)
        scaled_w = int(LOGICAL_WIDTH * scale)
        scaled_h = int(LOGICAL_HEIGHT * scale)
        scaled_surf = pygame.transform.scale(LOGICAL_SURFACE, (scaled_w, scaled_h))

        _real_screen.fill((30, 30, 30))  # 黑边
        offset_x = (win_w - scaled_w) // 2
        offset_y = (win_h - scaled_h) // 2
        _real_screen.blit(scaled_surf, (offset_x, offset_y))

        pygame.display.flip()
        await asyncio.sleep(0)  # pygbag 需要：让出控制权给浏览器

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    asyncio.run(main())
