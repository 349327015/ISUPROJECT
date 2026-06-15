import pygame
import json
import os
import math


# ---------------- SETUP ----------------
pygame.init()
pygame.display.set_caption("Metroidvania Game")

screen = pygame.display.set_mode((640, 480))
clock = pygame.time.Clock()

small_font = pygame.font.Font(None, 32)
splash_font = pygame.font.Font(None, 48)
sign_font = pygame.font.Font(None, 24)
tutorial_font = pygame.font.Font(None, 28)
menu_font = pygame.font.Font(None, 36)
pause_font = pygame.font.Font(None, 28)



# ---------------- MUSIC ----------------
pygame.mixer.init()

try:
    pygame.mixer.music.load("menuMusic.mp3")
    pygame.mixer.music.set_volume(0.5)
except:
    pass



# ---------------- IMAGES ----------------
try:
    title_img = pygame.image.load("titleScreen.png")
    title_img = pygame.transform.scale(title_img, (640, 480))
except:
    title_img = pygame.Surface((640, 480))
    title_img.fill((20, 20, 40))

try:
    settings_img = pygame.image.load("settingsScreen.png")
    settings_img = pygame.transform.scale(settings_img, (640, 480))
except:
    settings_img = pygame.Surface((640, 480))
    settings_img.fill((30, 30, 50))

try:
    save_img = pygame.image.load("saveScreen.png")
    save_img = pygame.transform.scale(save_img, (640, 480))
except:
    save_img = pygame.Surface((640, 480))
    save_img.fill((25, 25, 45))



# ---------------- STATES ----------------
splash_screen = True
title_screen = False
settings_menu = False
save_menu = False
delete_menu = False
game_active = False
paused = False
transitioning = False
transition_alpha = 0
transition_target_room = None
transition_spawn_x = 0
transition_spawn_y = 0

running = True



# ---------------- MAIN MENU ----------------
menu_options = ["Start Game", "Settings", "Quit"]
selected_option = 0

# Pause menu options
pause_options = ["Resume", "Title Screen"]
pause_selected = 0



# ---------------- SETTINGS ----------------
settings_options = ["Volume", "Back"]
settings_selected = 0
volume = 50
pygame.mixer.music.set_volume(volume / 100)



# ---------------- SAVE SYSTEM ----------------
save_options = ["Save Slot 1", "Save Slot 2", "Save Slot 3", "Delete Save", "Back"]
save_selected = 0

delete_options = ["Save Slot 1", "Save Slot 2", "Save Slot 3", "Back"]
delete_selected = 0
delete_confirmation = False
delete_target_slot = None
ignore_next_enter = False

current_progress = 0
current_skill_points = 0
current_abilities = {
    "dash": False,
    "double_jump": False,
    "wall_jump": False,
    "time_stop": False,
    "knife_throw": False
}

# Map system
explored_rooms = set()

# Define room connections for map
room_connections = {
    "tutorial_1": {"x": 0, "y": 0, "right": "tutorial_2", "name": "Entrance"},
    "tutorial_2": {"x": 1, "y": 0, "left": "tutorial_1", "right": "tutorial_3", "name": "Climb"},
    "tutorial_3": {"x": 2, "y": 0, "left": "tutorial_2", "right": "tutorial_4", "name": "Lava Cavern"},
    "tutorial_4": {"x": 3, "y": 0, "left": "tutorial_3", "right": "hub", "name": "Combat Arena"},
    "hub": {"x": 4, "y": 0, "left": "tutorial_4", "name": "Hub"}
}

# Room transition zones (x position to trigger transition)
room_transitions = {
    "tutorial_1": {"right": "tutorial_2"},
    "tutorial_2": {"left": "tutorial_1", "right": "tutorial_3"},
    "tutorial_3": {"left": "tutorial_2", "right": "tutorial_4"},
    "tutorial_4": {"left": "tutorial_3", "right": "hub"},
    "hub": {"left": "tutorial_4"}
}



def save_game(slot):
    data = {
        "progress": current_progress,
        "skill_points": current_skill_points,
        "abilities": current_abilities,
        "player_x": player.x if 'player' in globals() else 100,
        "player_y": player.y if 'player' in globals() else 300,
        "current_room": current_room_name if 'current_room_name' in globals() else "tutorial_1",
        "explored_rooms": list(explored_rooms) if 'explored_rooms' in globals() else ["tutorial_1"]
    }
    with open(f"save{slot}.json", "w") as file:
        json.dump(data, file)

def load_game(slot):
    if os.path.exists(f"save{slot}.json"):
        with open(f"save{slot}.json", "r") as file:
            return json.load(file)
    return None

def delete_save(slot):
    if os.path.exists(f"save{slot}.json"):
        os.remove(f"save{slot}.json")
        return True
    return False



# ---------------- SPLASH ----------------
fade_alpha = 0
fade_speed = 3
splash_timer = 0
fading_out = False

fade_surface = pygame.Surface((640,480))
fade_alpha_global = 0
fading = False
fade_direction = 0
next_state = None

def start_fade(target):
    global fading, fade_direction, next_state, fade_alpha_global
    fading = True
    fade_direction = 1
    next_state = target
    fade_alpha_global = 0



# ---------------- GAME CLASSES ----------------
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 24
        self.height = 28
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5
        self.jump_power = -11
        self.gravity = 0.55
        self.on_ground = False
        self.on_ceiling = False
        self.facing_right = True
        self.color = (255, 200, 100)
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        self.jump_buffer = 0
        self.coyote_time = 0
        self.jump_buffer_duration = 8
        self.coyote_time_duration = 6
        
        self.can_dash = False
        self.is_dashing = False
        self.dash_cooldown = 0
        self.dash_duration = 0
        self.dash_speed = 24
        self.dash_time = 6
        
        self.can_double_jump = False
        self.has_double_jump = False
        self.can_time_stop = False
        
        self.health = 100
        self.max_health = 100
        self.invincible_frames = 0
        
        # Attack system
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_combo = 0
        self.attack_combo_timer = 0
        self.attack_cooldown = 0
        self.attack_duration = 6
        self.attack_range = 45
        self.attack_width = 25
        self.attack_damage = 1
        
    def update(self, platforms, items, signs, room_width, ground_rects, hazards, enemies):
        if self.is_dashing:
            self.dash_duration -= 1
            if self.dash_duration <= 0:
                self.is_dashing = False
                self.vel_x = self.dash_speed * 0.3 if self.facing_right else -self.dash_speed * 0.3
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        
        if self.invincible_frames > 0:
            self.invincible_frames -= 1
        
        # Attack system updates
        if self.is_attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.attack_combo_timer = 20
        
        if self.attack_combo_timer > 0:
            self.attack_combo_timer -= 1
            if self.attack_combo_timer <= 0 and not self.is_attacking:
                self.attack_combo = 0
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.attack_combo = 0
        
        if not self.is_dashing:
            self.vel_y += self.gravity
        
        if self.vel_y > 14:
            self.vel_y = 14
            
        self.x += self.vel_x
        self.y += self.vel_y
        
        self.rect.x = self.x
        self.rect.y = self.y
        
        self.on_ground = False
        self.on_ceiling = False
        
        # Collision with floating platforms
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0 and self.rect.bottom > platform.rect.top and self.rect.top < platform.rect.top:
                    self.rect.bottom = platform.rect.top
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.on_ground = True
                    self.has_double_jump = False
                    self.coyote_time = self.coyote_time_duration
                    if self.is_dashing:
                        self.is_dashing = False
                elif self.vel_y < 0 and self.rect.top < platform.rect.bottom and self.rect.bottom > platform.rect.bottom:
                    self.rect.top = platform.rect.bottom
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.on_ceiling = True
                elif self.vel_x > 0 and self.rect.right > platform.rect.left and self.rect.left < platform.rect.left:
                    self.rect.right = platform.rect.left
                    self.x = self.rect.x
                elif self.vel_x < 0 and self.rect.left < platform.rect.right and self.rect.right > platform.rect.right:
                    self.rect.left = platform.rect.right
                    self.x = self.rect.x
        
        # Collision with ground
        for ground in ground_rects:
            if self.rect.colliderect(ground):
                if self.vel_y > 0 and self.rect.bottom > ground.top and self.rect.top < ground.top:
                    self.rect.bottom = ground.top
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.on_ground = True
                    self.has_double_jump = False
                    self.coyote_time = self.coyote_time_duration
                    if self.is_dashing:
                        self.is_dashing = False
                elif self.vel_y < 0 and self.rect.top < ground.bottom and self.rect.bottom > ground.bottom:
                    self.rect.top = ground.bottom
                    self.y = self.rect.y
                    self.vel_y = 0
                    self.on_ceiling = True
                elif self.vel_x > 0 and self.rect.right > ground.left and self.rect.left < ground.left:
                    self.rect.right = ground.left
                    self.x = self.rect.x
                elif self.vel_x < 0 and self.rect.left < ground.right and self.rect.right > ground.right:
                    self.rect.left = ground.right
                    self.x = self.rect.x
        
        # Hazard collision (lava)
        for hazard in hazards:
            if self.rect.colliderect(hazard.rect) and self.invincible_frames == 0:
                self.health -= 20
                self.invincible_frames = 30
                if self.health <= 0:
                    return "dead"
        
        # Enemy collision (damage)
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect) and self.invincible_frames == 0 and not self.is_attacking:
                self.health -= 10
                self.invincible_frames = 30
                if self.health <= 0:
                    return "dead"
        
        if not self.on_ground:
            if self.coyote_time > 0:
                self.coyote_time -= 1
        else:
            self.coyote_time = self.coyote_time_duration
        
        if self.jump_buffer > 0:
            self.jump_buffer -= 1
        
        if self.jump_buffer > 0 and (self.on_ground or self.coyote_time > 0) and not self.is_dashing:
            self._perform_jump()
            self.jump_buffer = 0
        
        self.x = max(0, min(room_width - self.width, self.x))
        self.rect.x = self.x
        
        if self.y < 0:
            self.y = 0
            self.vel_y = 0
        if self.y > 600 - self.height:
            self.y = 600 - self.height
            self.vel_y = 0
            self.on_ground = True
        
        collected_item = None
        for item in items[:]:
            if self.rect.colliderect(item.rect):
                collected_item = item
                items.remove(item)
                break
        
        nearby_sign = None
        for sign in signs:
            sign_trigger = sign.rect.inflate(60, 60)
            if self.rect.colliderect(sign_trigger):
                nearby_sign = sign
                break
        
        return None, collected_item, nearby_sign
    
    def attack(self):
        if not self.is_attacking and self.attack_cooldown == 0 and not self.is_dashing:
            self.is_attacking = True
            self.attack_timer = self.attack_duration
            
            if self.attack_combo < 3:
                self.attack_combo += 1
            else:
                self.attack_combo = 1
            
            self.attack_combo_timer = 0
            
            if self.attack_combo == 3:
                self.attack_cooldown = 20
            
            # Create attack hitbox
            attack_rect = self.get_attack_rect()
            return attack_rect
        return None
    
    def get_attack_rect(self):
        if self.facing_right:
            return pygame.Rect(self.x + self.width, self.y + 8, self.attack_range, self.attack_width)
        else:
            return pygame.Rect(self.x - self.attack_range, self.y + 8, self.attack_range, self.attack_width)
    
    def _perform_jump(self):
        self.vel_y = self.jump_power
        self.on_ground = False
        self.coyote_time = 0
        
    def jump(self):
        if not self.is_dashing:
            self.jump_buffer = self.jump_buffer_duration
        
    def double_jump(self):
        if self.can_double_jump and not self.has_double_jump and not self.on_ground and self.coyote_time == 0 and not self.is_dashing:
            self.vel_y = self.jump_power
            self.has_double_jump = True
            return True
        return False
        
    def dash(self):
        if self.can_dash and self.dash_cooldown <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_duration = self.dash_time
            if self.facing_right:
                self.vel_x = self.dash_speed
            else:
                self.vel_x = -self.dash_speed
            self.dash_cooldown = 40
            return True
        return False
        
    def handle_input(self):
        keys = pygame.key.get_pressed()
        if not self.is_dashing and not self.is_attacking:
            self.vel_x = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vel_x = -self.speed
                self.facing_right = False
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vel_x = self.speed
                self.facing_right = True
            
    def draw(self, screen, camera_x):
        if self.x + self.width > camera_x and self.x < camera_x + 640:
            player_rect = pygame.Rect(self.x - camera_x, self.y, self.width, self.height)
            
            # Draw sword slash effect
            if self.is_attacking:
                attack_rect = self.get_attack_rect()
                attack_rect.x -= camera_x
                
                if self.attack_combo == 1:
                    slash_color = (200, 200, 255)
                elif self.attack_combo == 2:
                    slash_color = (255, 200, 100)
                else:
                    slash_color = (255, 100, 100)
                
                pygame.draw.rect(screen, slash_color, attack_rect)
                
                if self.facing_right:
                    for i in range(3):
                        line_x = attack_rect.x + i * 15
                        pygame.draw.line(screen, (255, 255, 255), (line_x, attack_rect.y), (line_x + 10, attack_rect.y + attack_rect.height), 2)
                    pygame.draw.arc(screen, (255, 255, 255), attack_rect, 0, math.pi, 2)
                else:
                    for i in range(3):
                        line_x = attack_rect.x + attack_rect.width - i * 15
                        pygame.draw.line(screen, (255, 255, 255), (line_x, attack_rect.y), (line_x - 10, attack_rect.y + attack_rect.height), 2)
                    pygame.draw.arc(screen, (255, 255, 255), attack_rect, math.pi, math.pi * 2, 2)
                
                pygame.draw.rect(screen, (255, 255, 255), attack_rect, 2)
            
            if self.invincible_frames > 0 and (self.invincible_frames // 5) % 2 == 0:
                pygame.draw.rect(screen, (255, 255, 255), player_rect)
            elif self.is_dashing:
                for i in range(4):
                    trail_rect = pygame.Rect(self.x - camera_x - (i+1)*8, self.y, self.width, self.height)
                    trail_color = (200, 150, 100)
                    pygame.draw.rect(screen, trail_color, trail_rect)
                pygame.draw.rect(screen, (255, 220, 150), player_rect)
            else:
                pygame.draw.rect(screen, self.color, player_rect)
            
            eye_x = self.x - camera_x + (18 if self.facing_right else 6)
            eye_y = self.y + 8
            pygame.draw.circle(screen, (0, 0, 0), (eye_x, eye_y), 3)
            
            # Draw sword when not attacking
            if not self.is_attacking and self.attack_cooldown == 0:
                sword_x = self.x - camera_x + (22 if self.facing_right else -6)
                sword_y = self.y + 12
                sword_length = 20
                if self.facing_right:
                    pygame.draw.line(screen, (192, 192, 192), (sword_x, sword_y), (sword_x + sword_length, sword_y), 3)
                    pygame.draw.line(screen, (255, 255, 255), (sword_x + sword_length, sword_y - 2), (sword_x + sword_length + 4, sword_y), 2)
                else:
                    pygame.draw.line(screen, (192, 192, 192), (sword_x, sword_y), (sword_x - sword_length, sword_y), 3)
                    pygame.draw.line(screen, (255, 255, 255), (sword_x - sword_length, sword_y - 2), (sword_x - sword_length - 4, sword_y), 2)
            elif self.attack_cooldown > 0:
                sword_x = self.x - camera_x + (22 if self.facing_right else -6)
                sword_y = self.y + 16
                sword_length = 15
                if self.facing_right:
                    pygame.draw.line(screen, (100, 100, 100), (sword_x, sword_y), (sword_x + sword_length, sword_y), 3)
                else:
                    pygame.draw.line(screen, (100, 100, 100), (sword_x, sword_y), (sword_x - sword_length, sword_y), 3)
            
            ribbon_color = (200, 100, 100)
            pygame.draw.rect(screen, ribbon_color, (self.x - camera_x + 8, self.y - 4, 8, 6))
            
            bar_width = 50
            bar_height = 6
            bar_x = self.x - camera_x + (self.width // 2) - (bar_width // 2)
            bar_y = self.y - 12
            health_percent = self.health / self.max_health
            pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(screen, (200, 50, 50), (bar_x, bar_y, bar_width * health_percent, bar_height))
            
            if self.can_dash and self.dash_cooldown > 0:
                cooldown_percent = self.dash_cooldown / 40
                dash_bar_width = 30
                dash_bar_x = self.x - camera_x + (self.width // 2) - (dash_bar_width // 2)
                dash_bar_y = self.y - 20
                pygame.draw.rect(screen, (80, 80, 80), (dash_bar_x, dash_bar_y, dash_bar_width, 4))
                pygame.draw.rect(screen, (255, 165, 0), (dash_bar_x, dash_bar_y, dash_bar_width * (1 - cooldown_percent), 4))

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 24
        self.height = 24
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.health = 2
        self.max_health = 2
        self.animation_frame = 0
        self.patrol_left = x - 80
        self.patrol_right = x + 80
        self.direction = 1
        self.speed = 1.5
        
    def update(self):
        self.animation_frame += 0.1
        # Simple patrol movement
        self.x += self.speed * self.direction
        if self.x <= self.patrol_left:
            self.x = self.patrol_left
            self.direction = 1
        elif self.x >= self.patrol_right:
            self.x = self.patrol_right
            self.direction = -1
        self.rect.x = self.x
        
    def take_damage(self, damage):
        self.health -= damage
        return self.health <= 0
    
    def draw(self, screen, camera_x):
        rect = pygame.Rect(self.x - camera_x, self.y, self.width, self.height)
        # Animated enemy
        pulse = abs(math.sin(self.animation_frame * 2)) * 30
        body_color = (150 + pulse//3, 50, 50)
        
        # Draw enemy body
        pygame.draw.rect(screen, body_color, rect)
        pygame.draw.rect(screen, (200, 50, 50), rect, 2)
        
        # Draw angry eyes
        eye_y = rect.y + 8
        left_eye = rect.x + 6
        right_eye = rect.x + 18
        pygame.draw.circle(screen, (255, 255, 255), (left_eye, eye_y), 3)
        pygame.draw.circle(screen, (255, 255, 255), (right_eye, eye_y), 3)
        pygame.draw.circle(screen, (0, 0, 0), (left_eye + 1, eye_y), 2)
        pygame.draw.circle(screen, (0, 0, 0), (right_eye + 1, eye_y), 2)
        
        # Draw health bar
        bar_width = 24
        bar_height = 4
        bar_x = rect.x + (self.width - bar_width) // 2
        bar_y = rect.y - 6
        health_percent = self.health / self.max_health
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, bar_width * health_percent, bar_height))

class Platform:
    def __init__(self, x, y, width, height, color=(100, 100, 120)):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
    def draw(self, screen, camera_x):
        if self.rect.x + self.rect.width > camera_x and self.rect.x < camera_x + 640:
            rect = pygame.Rect(self.rect.x - camera_x, self.rect.y, self.rect.width, self.rect.height)
            shadow_rect = pygame.Rect(rect.x, rect.y + 3, rect.width, 5)
            pygame.draw.rect(screen, (20, 20, 30), shadow_rect)
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, (150, 150, 170), rect, 2)

class Ground:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.top_color = (80, 80, 100)
        self.body_color = (40, 40, 60)
    def draw(self, screen, camera_x):
        if self.rect.x + self.rect.width > camera_x and self.rect.x < camera_x + 640:
            rect = pygame.Rect(self.rect.x - camera_x, self.rect.y, self.rect.width, self.rect.height)
            body_rect = pygame.Rect(rect.x, rect.y + 15, rect.width, 600 - (rect.y + 15))
            pygame.draw.rect(screen, self.body_color, body_rect)
            top_surface = pygame.Rect(rect.x, rect.y, rect.width, 15)
            pygame.draw.rect(screen, self.top_color, top_surface)
            pygame.draw.rect(screen, (120, 120, 140), top_surface, 2)

class Lava:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.animation_frame = 0
    def draw(self, screen, camera_x):
        if self.rect.x + self.rect.width > camera_x and self.rect.x < camera_x + 640:
            rect = pygame.Rect(self.rect.x - camera_x, self.rect.y, self.rect.width, self.rect.height)
            self.animation_frame += 0.05
            
            r = 255
            g = 100 + int(math.sin(self.animation_frame * 3) * 30)
            b = 50 + int(math.sin(self.animation_frame * 5) * 20)
            
            lava_color = (r, g, b)
            pygame.draw.rect(screen, lava_color, rect)
            
            for i in range(5):
                bubble_x = rect.x + (i * 20 + self.animation_frame * 10) % rect.width
                bubble_y = rect.y + 3
                bubble_size = 3 + math.sin(self.animation_frame * 10 + i) * 2
                pygame.draw.circle(screen, (255, 200, 100), (int(bubble_x), int(bubble_y)), int(bubble_size))
            
            wave_height = 5 + math.sin(self.animation_frame * 8) * 2
            for x in range(rect.x, rect.x + rect.width, 8):
                wave_y = rect.y + math.sin(x * 0.1 + self.animation_frame * 10) * 3
                pygame.draw.circle(screen, (255, 150, 50), (x, int(wave_y)), 2)
            
            pygame.draw.line(screen, (255, 200, 100), (rect.x, rect.y), (rect.x + rect.width, rect.y), 3)
            pygame.draw.line(screen, (150, 50, 0), (rect.x, rect.y + rect.height), (rect.x + rect.width, rect.y + rect.height), 2)

class Collectable:
    def __init__(self, x, y, collect_type):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.collect_type = collect_type
        self.animation_frame = 0
    def draw(self, screen, camera_x):
        rect = pygame.Rect(self.rect.x - camera_x, self.rect.y, 20, 20)
        self.animation_frame += 0.1
        
        if self.collect_type == "health":
            color = (255, 50, 50)
            symbol = "♥"
        elif self.collect_type == "skill_point":
            color = (147, 0, 211)
            symbol = "★"
        else:
            color = (50, 150, 255)
            symbol = "✦"
        
        for i in range(3):
            glow_rect = pygame.Rect(rect.x - i*2, rect.y - i*2, 20 + i*4, 20 + i*4)
            glow_color = (color[0]//(i+2), color[1]//(i+2), color[2]//(i+2))
            pygame.draw.rect(screen, glow_color, glow_rect, 2)
        
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)
        
        font = pygame.font.Font(None, 16)
        text = font.render(symbol, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=rect.center))

class Sign:
    def __init__(self, x, y, title, messages):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.title = title
        self.messages = messages
        self.show_popup = False
        self.popup_timer = 0
    def update(self):
        if self.show_popup:
            self.popup_timer += 1
            if self.popup_timer > 300:
                self.show_popup = False
                self.popup_timer = 0
    def draw(self, screen, camera_x):
        if self.rect.x + self.rect.width > camera_x and self.rect.x < camera_x + 640:
            rect = pygame.Rect(self.rect.x - camera_x, self.rect.y, self.rect.width, self.rect.height)
            # Draw sign on the ground
            pygame.draw.rect(screen, (139, 69, 19), (rect.centerx - 3, rect.y + rect.height, 6, 10))
            pygame.draw.rect(screen, (218, 165, 32), rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)
            text = small_font.render("!", True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=rect.center))
    def draw_popup(self, screen, camera_x):
        if self.show_popup:
            sign_screen_x = self.rect.x - camera_x
            sign_screen_y = self.rect.y
            popup_width = 300
            popup_height = 40 + len(self.messages) * 22
            popup_x = sign_screen_x + 16 - (popup_width // 2)
            popup_y = sign_screen_y - popup_height - 5
            popup_x = max(5, min(popup_x, 640 - popup_width - 5))
            popup_y = max(5, popup_y)
            popup_surface = pygame.Surface((popup_width, popup_height))
            popup_surface.set_alpha(200)
            popup_surface.fill((0, 0, 0))
            screen.blit(popup_surface, (popup_x, popup_y))
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
            pygame.draw.rect(screen, (218, 165, 32), popup_rect, 3)
            title_text = sign_font.render(self.title, True, (255, 255, 0))
            screen.blit(title_text, (popup_x + 10, popup_y + 5))
            for i, message in enumerate(self.messages):
                msg_text = sign_font.render(message, True, (255, 255, 255))
                screen.blit(msg_text, (popup_x + 10, popup_y + 28 + i * 20))
            triangle_points = [
                (sign_screen_x + 16, sign_screen_y - 2),
                (sign_screen_x + 8, sign_screen_y - 10),
                (sign_screen_x + 24, sign_screen_y - 10)
            ]
            pygame.draw.polygon(screen, (218, 165, 32), triangle_points)

def draw_background(screen, camera_x):
    """Draw a scenic background with mountains and sky"""
    # Sky gradient
    for y in range(480):
        color_value = 20 + y // 8
        pygame.draw.line(screen, (20, color_value // 2, color_value), (0, y), (640, y))
    
    # Far mountains
    mountain_color_far = (40, 35, 55)
    points_far = []
    for x in range(-100, 800, 60):
        height = 120 + math.sin(x * 0.02) * 30
        points_far.append((x, 480 - height))
    points_far.append((800, 480))
    points_far.append((-100, 480))
    pygame.draw.polygon(screen, mountain_color_far, points_far)
    
    # Near mountains
    mountain_color_near = (50, 45, 65)
    points_near = []
    for x in range(-100, 800, 50):
        height = 180 + math.sin(x * 0.03 + 2) * 40
        points_near.append((x, 480 - height))
    points_near.append((800, 480))
    points_near.append((-100, 480))
    pygame.draw.polygon(screen, mountain_color_near, points_near)
    
    # Snow caps
    for x in range(-100, 800, 50):
        height = 180 + math.sin(x * 0.03 + 2) * 40
        if height > 200:
            snow_height = height - 15
            snow_width = 15
            pygame.draw.polygon(screen, (100, 100, 120), [
                (x, 480 - height),
                (x - snow_width, 480 - snow_height),
                (x + snow_width, 480 - snow_height)
            ])
    
    # Clouds
    cloud_color = (70, 70, 90)
    for cloud_x in range(-200 + int(camera_x * 0.3), 900, 200):
        cloud_y = 60 + math.sin(cloud_x * 0.01) * 10
        pygame.draw.ellipse(screen, cloud_color, (cloud_x, cloud_y, 60, 30))
        pygame.draw.ellipse(screen, cloud_color, (cloud_x + 20, cloud_y - 10, 50, 30))
        pygame.draw.ellipse(screen, cloud_color, (cloud_x + 40, cloud_y - 5, 40, 25))

def draw_minimap(screen, current_room, explored_rooms, room_connections):
    """Draw the minimap UI in the top right corner"""
    map_radius = 90
    map_center_x = 560
    map_center_y = 70
    
    map_surface = pygame.Surface((map_radius * 2, map_radius * 2), pygame.SRCALPHA)
    
    pygame.draw.circle(map_surface, (175, 238, 238, 80), (map_radius, map_radius), map_radius)
    pygame.draw.circle(map_surface, (100, 200, 200, 150), (map_radius, map_radius), map_radius, 2)
    
    font_small = pygame.font.Font(None, 14)
    map_title = font_small.render("MAP", True, (255, 255, 255, 200))
    title_rect = map_title.get_rect(center=(map_radius, 12))
    map_surface.blit(map_title, title_rect)
    
    room_width = 20
    room_height = 16
    
    current_x_pos = room_connections[current_room]["x"]
    current_y_pos = room_connections[current_room]["y"]
    
    offset_x = map_radius - room_width // 2
    offset_y = map_radius - room_height // 2
    
    room_positions = {}
    
    for room_id, connections in room_connections.items():
        if room_id in explored_rooms:
            rel_x = connections["x"] - current_x_pos
            rel_y = connections["y"] - current_y_pos
            x = offset_x + rel_x * (room_width + 4)
            y = offset_y + rel_y * (room_height + 4)
            room_positions[room_id] = (x, y)
    
    for room_id, connections in room_connections.items():
        if room_id in explored_rooms and room_id in room_positions:
            x, y = room_positions[room_id]
            
            if "right" in connections and connections["right"] in explored_rooms and connections["right"] in room_positions:
                right_x, right_y = room_positions[connections["right"]]
                pygame.draw.line(map_surface, (100, 200, 200), 
                               (x + room_width, y + room_height//2),
                               (right_x, y + room_height//2), 2)
            
            if "left" in connections and connections["left"] in explored_rooms and connections["left"] in room_positions:
                left_x, left_y = room_positions[connections["left"]]
                pygame.draw.line(map_surface, (100, 200, 200),
                               (x, y + room_height//2),
                               (left_x + room_width, y + room_height//2), 2)
    
    for room_id, connections in room_connections.items():
        if room_id in explored_rooms and room_id in room_positions:
            x, y = room_positions[room_id]
            
            if room_id == current_room:
                color = (255, 200, 100)
                pygame.draw.rect(map_surface, color, (x, y, room_width, room_height))
                pygame.draw.rect(map_surface, (255, 255, 255), (x, y, room_width, room_height), 1)
                
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 50
                pygame.draw.rect(map_surface, (255, 200 + pulse, 100), (x, y, room_width, room_height), 2)
            else:
                color = (50, 100, 100)
                pygame.draw.rect(map_surface, color, (x, y, room_width, room_height))
                pygame.draw.rect(map_surface, (80, 150, 150), (x, y, room_width, room_height), 1)
    
    player_x = offset_x + room_width // 2
    player_y = offset_y + room_height // 2
    pygame.draw.circle(map_surface, (255, 255, 255), (player_x, player_y), 3)
    pygame.draw.circle(map_surface, (0, 0, 0), (player_x - 1, player_y - 1), 1)
    
    pygame.draw.circle(map_surface, (100, 200, 200, 100), (map_radius, map_radius), map_radius - 5, 1)
    
    font_tiny = pygame.font.Font(None, 10)
    n_text = font_tiny.render("N", True, (150, 220, 220))
    s_text = font_tiny.render("S", True, (150, 220, 220))
    e_text = font_tiny.render("E", True, (150, 220, 220))
    w_text = font_tiny.render("W", True, (150, 220, 220))
    
    n_rect = n_text.get_rect(center=(map_radius, 8))
    s_rect = s_text.get_rect(center=(map_radius, map_radius * 2 - 8))
    e_rect = e_text.get_rect(center=(map_radius * 2 - 8, map_radius))
    w_rect = w_text.get_rect(center=(8, map_radius))
    
    map_surface.blit(n_text, n_rect)
    map_surface.blit(s_text, s_rect)
    map_surface.blit(e_text, e_rect)
    map_surface.blit(w_text, w_rect)
    
    screen.blit(map_surface, (map_center_x - map_radius, map_center_y - map_radius))

def draw_pause_menu(screen, current_room, explored_rooms, room_connections, pause_selected):
    """Draw the pause menu with map directly on the pause screen background"""
    overlay = pygame.Surface((640, 480))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    pause_title = menu_font.render("PAUSED", True, (255, 255, 255))
    title_rect = pause_title.get_rect(center=(320, 35))
    screen.blit(pause_title, title_rect)
    
    map_display_size = 280
    map_display_x = (640 - map_display_size) // 2
    map_display_y = 60
    
    room_width = 22
    room_height = 18
    
    if explored_rooms:
        min_x = min(room_connections[r]["x"] for r in explored_rooms if r in room_connections)
        max_x = max(room_connections[r]["x"] for r in explored_rooms if r in room_connections)
        min_y = min(room_connections[r]["y"] for r in explored_rooms if r in room_connections)
        max_y = max(room_connections[r]["y"] for r in explored_rooms if r in room_connections)
        
        grid_width = (max_x - min_x + 1) * (room_width + 6)
        grid_height = (max_y - min_y + 1) * (room_height + 6)
        
        offset_x = map_display_x + (map_display_size - grid_width) // 2
        offset_y = map_display_y + (map_display_size - grid_height) // 2
        
        full_room_positions = {}
        for room_id, connections in room_connections.items():
            if room_id in explored_rooms:
                x = offset_x + (connections["x"] - min_x) * (room_width + 6)
                y = offset_y + (connections["y"] - min_y) * (room_height + 6)
                full_room_positions[room_id] = (x, y)
        
        for room_id, connections in room_connections.items():
            if room_id in explored_rooms and room_id in full_room_positions:
                x, y = full_room_positions[room_id]
                
                if "right" in connections and connections["right"] in explored_rooms:
                    right_x, right_y = full_room_positions[connections["right"]]
                    pygame.draw.line(screen, (100, 200, 200), 
                                   (x + room_width, y + room_height//2),
                                   (right_x, y + room_height//2), 2)
                
                if "left" in connections and connections["left"] in explored_rooms:
                    left_x, left_y = full_room_positions[connections["left"]]
                    pygame.draw.line(screen, (100, 200, 200),
                                   (x, y + room_height//2),
                                   (left_x + room_width, y + room_height//2), 2)
        
        for room_id, connections in room_connections.items():
            if room_id in explored_rooms and room_id in full_room_positions:
                x, y = full_room_positions[room_id]
                
                if room_id == current_room:
                    color = (255, 200, 100)
                    pygame.draw.rect(screen, color, (x, y, room_width, room_height))
                    pygame.draw.rect(screen, (255, 255, 255), (x, y, room_width, room_height), 1)
                    
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 50
                    pygame.draw.rect(screen, (255, 200 + pulse, 100), (x, y, room_width, room_height), 1)
                else:
                    color = (50, 100, 100)
                    pygame.draw.rect(screen, color, (x, y, room_width, room_height))
                    pygame.draw.rect(screen, (80, 150, 150), (x, y, room_width, room_height), 1)
        
        if current_room in full_room_positions:
            current_x, current_y = full_room_positions[current_room]
            player_x = current_x + room_width // 2
            player_y = current_y + room_height // 2
            pygame.draw.circle(screen, (255, 255, 255), (player_x, player_y), 3)
            pygame.draw.circle(screen, (0, 0, 0), (player_x - 1, player_y - 1), 1)
    
    pygame.draw.rect(screen, (100, 200, 200), (map_display_x - 3, map_display_y - 3, map_display_size + 6, map_display_size + 6), 1)
    
    button_width = 180
    button_height = 35
    button_y = map_display_y + map_display_size + 25
    resume_x = (640 - button_width) // 2
    title_x = (640 - button_width) // 2
    
    if pause_selected == 0:
        pygame.draw.rect(screen, (100, 200, 100), (resume_x, button_y, button_width, button_height))
        pygame.draw.rect(screen, (255, 255, 255), (resume_x, button_y, button_width, button_height), 2)
        resume_text = pause_font.render("RESUME", True, (255, 255, 255))
    else:
        pygame.draw.rect(screen, (60, 60, 80), (resume_x, button_y, button_width, button_height))
        pygame.draw.rect(screen, (100, 200, 200), (resume_x, button_y, button_width, button_height), 2)
        resume_text = pause_font.render("RESUME", True, (200, 200, 200))
    
    resume_rect = resume_text.get_rect(center=(resume_x + button_width // 2, button_y + button_height // 2))
    screen.blit(resume_text, resume_rect)
    
    title_y = button_y + button_height + 10
    if pause_selected == 1:
        pygame.draw.rect(screen, (200, 100, 100), (title_x, title_y, button_width, button_height))
        pygame.draw.rect(screen, (255, 255, 255), (title_x, title_y, button_width, button_height), 2)
        title_text = pause_font.render("TITLE SCREEN", True, (255, 255, 255))
    else:
        pygame.draw.rect(screen, (60, 60, 80), (title_x, title_y, button_width, button_height))
        pygame.draw.rect(screen, (100, 200, 200), (title_x, title_y, button_width, button_height), 2)
        title_text = pause_font.render("TITLE SCREEN", True, (200, 200, 200))
    
    title_rect = title_text.get_rect(center=(title_x + button_width // 2, title_y + button_height // 2))
    screen.blit(title_text, title_rect)
    
    inst_text = small_font.render("WASD/Arrows to select  |  Enter to confirm  |  ESC to close", True, (150, 150, 150))
    inst_rect = inst_text.get_rect(center=(320, title_y + button_height + 20))
    screen.blit(inst_text, inst_rect)

def start_room_transition(target_room, spawn_x, spawn_y):
    global transitioning, transition_alpha, transition_target_room, transition_spawn_x, transition_spawn_y
    transitioning = True
    transition_alpha = 0
    transition_target_room = target_room
    transition_spawn_x = spawn_x
    transition_spawn_y = spawn_y

def update_transition():
    global transitioning, transition_alpha, current_room_name, current_room, player, camera_x, explored_rooms
    if transitioning:
        transition_alpha += 15
        if transition_alpha >= 255:
            # Change room
            current_room_name = transition_target_room
            current_room = rooms[current_room_name]
            player.x = transition_spawn_x
            player.y = transition_spawn_y
            player.vel_x = 0
            player.vel_y = 0
            explored_rooms.add(current_room_name)
            camera_x = player.x + player.width // 2 - 320
            camera_x = max(0, min(camera_x, current_room.width - 640))
            # Start fade out
            transition_alpha = 255
            transitioning = False
        return True
    return False

def draw_transition(screen):
    global transition_alpha, transitioning
    if transitioning or (not transitioning and transition_alpha > 0):
        fade_surface = pygame.Surface((640, 480))
        fade_surface.set_alpha(transition_alpha)
        fade_surface.fill((0, 0, 0))
        screen.blit(fade_surface, (0, 0))
        if not transitioning and transition_alpha > 0:
            transition_alpha -= 15
            if transition_alpha < 0:
                transition_alpha = 0

def create_tutorial_room_1():
    """Room 1: Basic movement and staircase"""
    tutorial = Room("tutorial_1", width=1600)
    tutorial.background_color = None
    
    tutorial.add_ground(0, 450, 1600, 150)
    tutorial.add_ground(1350, 150, 250, 300)
    
    tutorial.add_sign(100, 450, "MOVEMENT CONTROLS", [
        "Welcome to the tutorial!",
        "Use A/← and D/→ to move",
        "Walk to the right to continue"
    ])
    
    tutorial.add_platform(450, 350, 100, 100, (80, 80, 100))
    
    tutorial.add_sign(650, 450, "JUMPING", [
        "Press SPACE, ↑, or Z to jump!",
        "Jump onto the platform above"
    ])
    
    tutorial.add_platform(700, 390, 100, 20, (100, 150, 100))
    tutorial.add_platform(850, 350, 80, 100, (80, 80, 100))
    
    tutorial.add_sign(1000, 450, "PLATFORMING", [
        "Great! Now jump across these 3 platforms",
        "Each platform gets you higher"
    ])
    
    tutorial.add_platform(1050, 380, 80, 20, (100, 100, 150))
    tutorial.add_platform(1150, 300, 80, 20, (100, 100, 150))
    tutorial.add_platform(1250, 220, 80, 20, (100, 100, 150))
    
    tutorial.add_sign(1400, 150, "ROOM 1 COMPLETE!", [
        "Walk to the right wall to continue!"
    ])
    
    return tutorial

def create_tutorial_room_2():
    """Room 2: Up and down staircases"""
    tutorial = Room("tutorial_2", width=1600)
    tutorial.background_color = None
    
    tutorial.add_ground(0, 450, 1600, 150)
    tutorial.add_ground(1350, 250, 250, 200)
    
    tutorial.add_sign(100, 450, "UP AND DOWN", [
        "First climb UP, then go DOWN to the higher ground"
    ])
    
    tutorial.add_platform(450, 350, 100, 100, (80, 80, 100))
    
    tutorial.add_sign(600, 450, "CLIMB UP", [
        "Use these 3 platforms to climb higher"
    ])
    
    tutorial.add_platform(700, 380, 80, 20, (100, 120, 150))
    tutorial.add_platform(800, 320, 80, 20, (100, 120, 150))
    tutorial.add_platform(900, 260, 80, 20, (100, 120, 150))
    tutorial.add_platform(1000, 260, 100, 20, (100, 150, 100))
    
    tutorial.add_sign(1050, 260, "GO DOWN", [
        "Now carefully go down to the higher ground"
    ])
    
    tutorial.add_platform(1150, 320, 80, 20, (100, 120, 150))
    
    tutorial.add_sign(1250, 250, "ROOM 2 COMPLETE!", [
        "Walk to left wall to go back",
        "Walk to right wall to continue"
    ])
    
    tutorial.add_collectable(1420, 220, "skill_point")
    
    return tutorial

def create_tutorial_room_3():
    """Room 3: Lava platforming challenge"""
    tutorial = Room("tutorial_3", width=1600)
    tutorial.background_color = None
    
    tutorial.add_ground(0, 450, 1600, 150)
    
    # Add lava covering the floor under the platforms
    tutorial.add_lava(550, 440, 800, 15)
    
    tutorial.add_ground(1350, 350, 250, 100)
    
    tutorial.add_sign(100, 420, "LAVA CHALLENGE", [
        "Now you need to make longer jumps!",
        "Watch out for LAVA on the floor!",
        "The entire floor is covered in lava - don't fall!"
    ])
    
    tutorial.add_platform(450, 350, 100, 100, (80, 80, 100))
    tutorial.add_platform(600, 380, 80, 20, (100, 120, 150))
    tutorial.add_platform(700, 320, 80, 20, (100, 120, 150))
    tutorial.add_platform(800, 260, 80, 20, (100, 120, 150))
    tutorial.add_platform(900, 320, 80, 20, (100, 120, 150))
    tutorial.add_platform(1000, 380, 80, 20, (100, 120, 150))
    tutorial.add_platform(1200, 380, 80, 20, (100, 100, 150))
    
    tutorial.add_sign(1380, 350, "ROOM 3 COMPLETE!", [
        "Walk to left wall to go back",
        "Walk to right wall to continue"
    ])
    
    tutorial.add_collectable(1450, 320, "health")
    
    return tutorial

def create_tutorial_room_4():
    """Room 4: Combat tutorial with enemies"""
    tutorial = Room("tutorial_4", width=1600)
    tutorial.background_color = None
    
    tutorial.add_ground(0, 450, 1600, 150)
    tutorial.add_ground(1350, 300, 250, 150)
    
    tutorial.add_sign(100, 420, "COMBAT TUTORIAL", [
        "Now you need to fight enemies!",
        "Press X or C to attack",
        "Each enemy takes 2 hits to defeat"
    ])
    
    tutorial.add_platform(450, 350, 100, 100, (80, 80, 100))
    
    # Add enemies on the ground
    tutorial.enemies.append(Enemy(700, 426))
    tutorial.enemies.append(Enemy(900, 426))
    tutorial.enemies.append(Enemy(1100, 426))
    
    tutorial.add_sign(1200, 420, "ENEMY WAVE", [
        "Defeat all enemies to continue!",
        "Use your sword - 3 hit combo!"
    ])
    
    tutorial.add_platform(1300, 350, 100, 20, (100, 100, 150))
    
    tutorial.add_sign(1380, 300, "ROOM 4 COMPLETE!", [
        "Walk to left wall to go back",
        "Walk to right wall to continue to Hub"
    ])
    
    tutorial.add_collectable(1450, 270, "skill_point")
    
    return tutorial

def create_hub_room():
    """Hub room - starting point for the real game"""
    hub = Room("hub", width=1000)
    hub.background_color = None
    
    hub.add_ground(0, 450, 1000, 150)
    
    hub.add_sign(400, 450, "ADVENTURE AWAITS!", [
        "You've completed the tutorial!",
        "More content coming soon...",
        "For now, enjoy exploring!"
    ])
    
    hub.add_platform(500, 350, 100, 20, (100, 100, 150))
    
    return hub

class Room:
    def __init__(self, name, width=2000):
        self.name = name
        self.platforms = []
        self.grounds = []
        self.lavas = []
        self.signs = []
        self.collectables = []
        self.enemies = []
        self.width = width
        self.height = 600
        self.background_color = (30, 30, 50)
        
    def add_platform(self, x, y, width, height, color=(100, 100, 120)):
        self.platforms.append(Platform(x, y, width, height, color))
    
    def add_ground(self, x, y, width, height):
        self.grounds.append(Ground(x, y, width, height))
    
    def add_lava(self, x, y, width, height):
        self.lavas.append(Lava(x, y, width, height))
    
    def add_collectable(self, x, y, collect_type):
        self.collectables.append(Collectable(x, y, collect_type))
    
    def add_sign(self, x, y, title, messages):
        self.signs.append(Sign(x, y, title, messages))
    
    def get_ground_rects(self):
        return [ground.rect for ground in self.grounds]
    
    def draw_background(self, screen):
        if self.background_color:
            screen.fill(self.background_color)

# Create all rooms
rooms = {
    "tutorial_1": create_tutorial_room_1(),
    "tutorial_2": create_tutorial_room_2(),
    "tutorial_3": create_tutorial_room_3(),
    "tutorial_4": create_tutorial_room_4(),
    "hub": create_hub_room()
}

current_room_name = "tutorial_1"
current_room = rooms[current_room_name]
player = Player(50, 420)
camera_x = 0
message_timer = 0
message_text = ""

def init_game():
    global current_room_name, current_room, player, camera_x, current_progress, current_abilities, current_skill_points, message_timer, message_text, explored_rooms, paused, transition_alpha, transitioning
    try:
        pygame.mixer.music.stop()
    except:
        pass
    current_room_name = "tutorial_1"
    current_room = rooms[current_room_name]
    player = Player(100, 420)  # Start at x=100, not at the edge
    camera_x = 0
    message_timer = 0
    message_text = ""
    current_abilities = {"dash": False, "double_jump": False, "wall_jump": False, "time_stop": False, "knife_throw": False}
    current_skill_points = 0
    current_progress = 0
    explored_rooms = {"tutorial_1"}
    paused = False
    transition_alpha = 0
    transitioning = False



# ---------------- MAIN LOOP ----------------
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_active and not fading and not transitioning:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if paused:
                        paused = False
                    else:
                        paused = True
                        pause_selected = 0
                elif not paused:
                    if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_z:
                        if player.on_ground or player.coyote_time > 0:
                            player.jump()
                    elif event.key == pygame.K_x or event.key == pygame.K_c:
                        attack_rect = player.attack()
                        if attack_rect:
                            # Check for enemy hits
                            for enemy in current_room.enemies[:]:
                                if attack_rect.colliderect(enemy.rect):
                                    if enemy.take_damage(player.attack_damage):
                                        current_room.enemies.remove(enemy)
                                    break
            
            if paused and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w or event.key == pygame.K_UP:
                    pause_selected = (pause_selected - 1) % len(pause_options)
                elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
                    pause_selected = (pause_selected + 1) % len(pause_options)
                elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
                    pause_selected = (pause_selected - 1) % len(pause_options)
                elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                    pause_selected = (pause_selected + 1) % len(pause_options)
                elif event.key == pygame.K_RETURN:
                    if pause_selected == 0:
                        paused = False
                    elif pause_selected == 1:
                        game_active = False
                        paused = False
                        start_fade("title")
                        try:
                            pygame.mixer.music.load("menuMusic.mp3")
                            pygame.mixer.music.play(-1)
                        except:
                            pass

        if title_screen and not fading and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                selected_option -= 1
            if event.key == pygame.K_s:
                selected_option += 1
            selected_option %= len(menu_options)
            if event.key == pygame.K_RETURN:
                if selected_option == 0:
                    start_fade("save")
                elif selected_option == 1:
                    start_fade("settings")
                elif selected_option == 2:
                    running = False

        if settings_menu and not fading and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                settings_selected -= 1
            if event.key == pygame.K_s:
                settings_selected += 1
            settings_selected %= len(settings_options)
            if settings_selected == 0:
                if event.key == pygame.K_a:
                    volume -= 5
                    volume = max(0, min(100, volume))
                    pygame.mixer.music.set_volume(volume / 100)
                if event.key == pygame.K_d:
                    volume += 5
                    volume = max(0, min(100, volume))
                    pygame.mixer.music.set_volume(volume / 100)
            if event.key == pygame.K_RETURN:
                if settings_selected == 1:
                    start_fade("title")
            if event.key == pygame.K_ESCAPE:
                start_fade("title")

        if save_menu and not fading and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                save_selected -= 1
            if event.key == pygame.K_s:
                save_selected += 1
            save_selected %= len(save_options)
            if event.key == pygame.K_RETURN:
                if save_selected < 3:
                    slot = save_selected + 1
                    data = load_game(slot)
                    if data:
                        current_progress = data["progress"]
                        current_skill_points = data.get("skill_points", 0)
                        current_abilities = data.get("abilities", current_abilities)
                        current_room_name = data.get("current_room", "tutorial_1")
                        explored_rooms = set(data.get("explored_rooms", ["tutorial_1"]))
                    else:
                        current_progress = 0
                        current_skill_points = 0
                        current_abilities = {"dash": False, "double_jump": False, "wall_jump": False, "time_stop": False, "knife_throw": False}
                        current_room_name = "tutorial_1"
                        explored_rooms = {"tutorial_1"}
                        save_game(slot)
                    start_fade("game")
                elif save_selected == 3:
                    save_menu = False
                    delete_menu = True
                    delete_confirmation = False
                    delete_target_slot = None
                    delete_selected = 0
                    ignore_next_enter = True
                elif save_selected == 4:
                    start_fade("title")
            if event.key == pygame.K_ESCAPE:
                start_fade("title")

        if delete_menu and not fading and event.type == pygame.KEYDOWN:
            if ignore_next_enter and event.key == pygame.K_RETURN:
                ignore_next_enter = False
                continue
            if not delete_confirmation:
                if event.key == pygame.K_w:
                    delete_selected -= 1
                if event.key == pygame.K_s:
                    delete_selected += 1
                delete_selected %= len(delete_options)
                if event.key == pygame.K_RETURN:
                    if delete_selected < 3:
                        delete_target_slot = delete_selected + 1
                        delete_confirmation = True
                    elif delete_selected == 3:
                        delete_menu = False
                        save_menu = True
                        delete_confirmation = False
                        delete_target_slot = None
                if event.key == pygame.K_ESCAPE:
                    delete_menu = False
                    save_menu = True
                    delete_confirmation = False
                    delete_target_slot = None
            else:
                if event.key == pygame.K_y:
                    delete_save(delete_target_slot)
                    delete_confirmation = False
                    delete_target_slot = None
                    delete_selected = 0
                elif event.key == pygame.K_n:
                    delete_confirmation = False
                    delete_target_slot = None

    # --------------- SPLASH SCREEN ---------------
    if splash_screen:
        screen.fill((0,0,0))
        text = splash_font.render("Made by Draco", True, (255,255,255))
        text.set_alpha(fade_alpha)
        screen.blit(text, text.get_rect(center=(320,240)))
        if not fading_out:
            fade_alpha += fade_speed
            if fade_alpha >= 255:
                fade_alpha = 255
                splash_timer += 1
                if splash_timer > 120:
                    fading_out = True
        else:
            fade_alpha -= fade_speed
            if fade_alpha <= 0:
                splash_screen = False
                try:
                    pygame.mixer.music.play(-1)
                except:
                    pass
                start_fade("title")

    # --------------- TITLE SCREEN ---------------
    elif title_screen and not game_active:
        screen.blit(title_img, (0,0))
        for i, option in enumerate(menu_options):
            color = (255,255,0) if i == selected_option else (255,255,255)
            text = small_font.render(option, True, color)
            screen.blit(text, (220, 350 + i * 35))

    # --------------- SETTINGS MENU ---------------
    elif settings_menu and not game_active:
        screen.blit(settings_img, (0,0))
        if settings_selected == 0:
            volume_color = (255,255,0)
        else:
            volume_color = (255,255,255)
        volume_text = small_font.render(f"< Volume: {volume} >", True, volume_color)
        screen.blit(volume_text, (200,300))
        back_color = (255,255,0) if settings_selected == 1 else (255,255,255)
        back_text = small_font.render("Back", True, back_color)
        screen.blit(back_text, (250,350))

    # --------------- SAVE MENU ---------------
    elif save_menu and not game_active:
        screen.blit(save_img, (0,0))
        title = small_font.render("SAVE DATA", True, (255,255,255))
        screen.blit(title, (250,70))
        for i in range(3):
            slot = i + 1
            data = load_game(slot)
            if data:
                info = f"Progress: {data['progress']}% | Points: {data.get('skill_points', 0)}"
            else:
                info = "Empty"
            box_x = 160
            box_y = 150 + i * 75
            if save_selected == i:
                box_color = (255,255,0)
            else:
                box_color = (255,255,255)
            pygame.draw.rect(screen, box_color, (box_x, box_y, 320, 60), 3)
            slot_text = small_font.render(f"Save Slot {slot}", True, (255,255,255))
            screen.blit(slot_text, (box_x+20, box_y+8))
            progress_text = small_font.render(info, True, (200,200,200))
            screen.blit(progress_text, (box_x+20, box_y+32))
        delete_color = (255,255,0) if save_selected == 3 else (255,255,255)
        delete_text = small_font.render("Delete Save", True, delete_color)
        screen.blit(delete_text, (240,390))
        back_color = (255,255,0) if save_selected == 4 else (255,255,255)
        back_text = small_font.render("Back", True, back_color)
        screen.blit(back_text, (250,440))

    # --------------- DELETE SUB-MENU ---------------
    elif delete_menu and not game_active:
        screen.blit(save_img, (0, 0))
        if not delete_confirmation:
            title = small_font.render("SELECT SAVE TO DELETE", True, (255, 255, 255))
            screen.blit(title, (180, 70))
            for i, option in enumerate(delete_options):
                box_x = 120
                box_y = 150 + i * 65
                box_width = 400
                box_height = 55
                if delete_selected == i:
                    box_color = (255, 0, 0)
                    text_color = (255, 255, 0)
                else:
                    box_color = (255, 255, 255)
                    text_color = (255, 255, 255)
                pygame.draw.rect(screen, box_color, (box_x, box_y, box_width, box_height), 3)
                if i < 3:
                    slot = i + 1
                    data = load_game(slot)
                    if data:
                        status = f"{option} (Has data)"
                    else:
                        status = f"{option} (Empty)"
                else:
                    status = option
                option_text = small_font.render(status, True, text_color)
                text_x = box_x + (box_width - option_text.get_width()) // 2
                text_y = box_y + (box_height - option_text.get_height()) // 2
                screen.blit(option_text, (text_x, text_y))
            inst_text = small_font.render("Select a save to delete | ESC to go back", True, (200, 200, 200))
            screen.blit(inst_text, (120, 430))
        else:
            overlay = pygame.Surface((640, 480))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            confirm_rect = pygame.Rect(100, 180, 440, 150)
            pygame.draw.rect(screen, (50, 50, 50), confirm_rect)
            pygame.draw.rect(screen, (255, 255, 255), confirm_rect, 3)
            confirm_text = small_font.render(f"Delete Save Slot {delete_target_slot}?", True, (255, 255, 255))
            screen.blit(confirm_text, confirm_text.get_rect(center=(320, 220)))
            warning_text = small_font.render("This action cannot be undone!", True, (255, 100, 100))
            screen.blit(warning_text, warning_text.get_rect(center=(320, 260)))
            yes_text = small_font.render("YES (Y)", True, (100, 255, 100))
            no_text = small_font.render("NO (N)", True, (255, 100, 100))
            screen.blit(yes_text, (220, 300))
            screen.blit(no_text, (340, 300))

    # --------------- GAME ---------------
    elif game_active:
        
        if not paused and not transitioning:
            player.handle_input()
            
            # Check for room transitions based on player position
            if current_room_name in room_transitions:
                transitions = room_transitions[current_room_name]
                if "right" in transitions and player.x >= 1550:
                    target = transitions["right"]
                    if target == "tutorial_2":
                        start_room_transition("tutorial_2", 100, 420)
                    elif target == "tutorial_3":
                        start_room_transition("tutorial_3", 100, 420)
                    elif target == "tutorial_4":
                        start_room_transition("tutorial_4", 100, 420)
                    elif target == "hub":
                        start_room_transition("hub", 100, 420)
                elif "left" in transitions and player.x <= 50:
                    target = transitions["left"]
                    if target == "tutorial_1":
                        start_room_transition("tutorial_1", 1480, 120)
                    elif target == "tutorial_2":
                        start_room_transition("tutorial_2", 1480, 220)
                    elif target == "tutorial_3":
                        start_room_transition("tutorial_3", 1480, 320)
                    elif target == "tutorial_4":
                        start_room_transition("tutorial_4", 1480, 270)
            
            # Update enemies
            for enemy in current_room.enemies:
                enemy.update()
            
            result, collected_item, nearby_sign = player.update(
                current_room.platforms, current_room.collectables, current_room.signs, 
                current_room.width, current_room.get_ground_rects(), current_room.lavas, current_room.enemies
            )
            
            if result == "dead":
                player.health = player.max_health
                player.x = 100
                player.y = 420
                player.vel_x = 0
                player.vel_y = 0
                message_text = "You died! Respawning..."
                message_timer = 60
            
            for sign in current_room.signs:
                sign.update()
            
            if nearby_sign and not nearby_sign.show_popup:
                for sign in current_room.signs:
                    if sign != nearby_sign:
                        sign.show_popup = False
                        sign.popup_timer = 0
                nearby_sign.show_popup = True
                nearby_sign.popup_timer = 0
            elif not nearby_sign:
                for sign in current_room.signs:
                    sign.show_popup = False
                    sign.popup_timer = 0
            
            if collected_item:
                if collected_item.collect_type == "health":
                    player.health = min(player.max_health, player.health + 30)
                    message_text = "Health restored!"
                    message_timer = 30
                elif collected_item.collect_type == "skill_point":
                    current_skill_points += 1
                    message_text = f"Skill Point obtained! Total: {current_skill_points}"
                    message_timer = 120
            
            camera_x = player.x + player.width // 2 - 320
            camera_x = max(0, min(camera_x, current_room.width - 640))
            
            if current_room_name == "tutorial_1":
                current_progress = 20
            elif current_room_name == "tutorial_2":
                current_progress = 40
            elif current_room_name == "tutorial_3":
                current_progress = 60
            elif current_room_name == "tutorial_4":
                if len(current_room.enemies) == 3:
                    current_progress = 70
                elif len(current_room.enemies) == 2:
                    current_progress = 80
                elif len(current_room.enemies) == 1:
                    current_progress = 90
                else:
                    current_progress = 95
            elif current_room_name == "hub":
                current_progress = 100
            
            if message_timer > 0:
                message_timer -= 1
        
        # Update transition
        if transitioning:
            update_transition()
        
        # Draw background first
        draw_background(screen, camera_x)
        
        # Then draw room objects
        for ground in current_room.grounds:
            ground.draw(screen, camera_x)
        
        for lava in current_room.lavas:
            lava.draw(screen, camera_x)
        
        for platform in current_room.platforms:
            platform.draw(screen, camera_x)
        
        for enemy in current_room.enemies:
            enemy.draw(screen, camera_x)
        
        for collectable in current_room.collectables:
            collectable.draw(screen, camera_x)
        
        for sign in current_room.signs:
            sign.draw(screen, camera_x)
            if sign.show_popup:
                sign.draw_popup(screen, camera_x)
        
        player.draw(screen, camera_x)
        
        draw_minimap(screen, current_room_name, explored_rooms, room_connections)
        
        # Draw transition overlay
        draw_transition(screen)
        
        if paused and not transitioning:
            draw_pause_menu(screen, current_room_name, explored_rooms, room_connections, pause_selected)
        
        if not paused and not transitioning:
            room_text = small_font.render(f"Area: {room_connections[current_room_name]['name']}", True, (255, 255, 255))
            screen.blit(room_text, (10, 10))
            
            progress_text = small_font.render(f"Tutorial Progress: {current_progress}%", True, (255, 255, 255))
            screen.blit(progress_text, (10, 40))
            
            points_text = small_font.render(f"Skill Points: {current_skill_points}", True, (147, 0, 211))
            screen.blit(points_text, (10, 70))
            
            health_text = small_font.render(f"HP: {player.health}/{player.max_health}", True, (255, 100, 100))
            screen.blit(health_text, (10, 100))
            
            if player.attack_cooldown > 0:
                cooldown_x = 320
                cooldown_y = 130
                pygame.draw.rect(screen, (80, 80, 80), (cooldown_x - 50, cooldown_y, 100, 8))
                cooldown_percent = player.attack_cooldown / 20
                pygame.draw.rect(screen, (255, 100, 100), (cooldown_x - 50, cooldown_y, 100 * cooldown_percent, 8))
            
            if message_timer > 0 and message_text:
                msg_surface = pygame.Surface((640, 50))
                msg_surface.set_alpha(200)
                msg_surface.fill((0, 0, 0))
                screen.blit(msg_surface, (0, 200))
                message_display = tutorial_font.render(message_text, True, (255, 255, 0))
                screen.blit(message_display, message_display.get_rect(center=(320, 225)))

    # --------------- FADE TRANSITIONS ---------------
    if fading:
        fade_surface.fill((0,0,0))
        if fade_direction == 1:
            fade_alpha_global += 10
            if fade_alpha_global >= 255:
                fade_alpha_global = 255
                fade_direction = 2
                if next_state == "title":
                    title_screen = True
                    settings_menu = False
                    save_menu = False
                    delete_menu = False
                    game_active = False
                elif next_state == "settings":
                    settings_menu = True
                    title_screen = False
                    save_menu = False
                    delete_menu = False
                    game_active = False
                elif next_state == "save":
                    save_menu = True
                    title_screen = False
                    settings_menu = False
                    delete_menu = False
                    game_active = False
                elif next_state == "game":
                    title_screen = False
                    settings_menu = False
                    save_menu = False
                    delete_menu = False
                    game_active = True
                    init_game()
        else:
            fade_alpha_global -= 10
            if fade_alpha_global <= 0:
                fade_alpha_global = 0
                fading = False
        fade_surface.set_alpha(fade_alpha_global)
        screen.blit(fade_surface, (0,0))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
