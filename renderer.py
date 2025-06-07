"""
Game Renderer - Handles all game rendering
"""

import pygame
import os
from typing import Optional
from game_state import game_state, GamePhase
from ship_manager import ShipManager
from battle_manager import BattleManager
from ui_manager import UIManager
import logging

logger = logging.getLogger("Renderer")


class Renderer:
    """Main renderer class"""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        # Colors
        self.BLUE = (16, 167, 232)
        self.RED = (206, 10, 10)
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.GRAY = (107, 99, 99)
        self.DARK_GREY = (41, 41, 46)
        self.ORANGE = (255, 167, 16)
        self.ORANGEDARKER = (200, 126, 2)
        self.LIGHT_GRAY = (237, 223, 223)
        self.GREEN = (0, 255, 0)
        
        # Load images
        self.load_images()
        
        # Fonts
        self.load_fonts()
        
        # Grid settings
        self.cell_size = 35
        self.grid_size = 10
        
        logger.info("Renderer initialized")
    
    def load_images(self):
        """Load game images"""
        try:
            self.background_image = pygame.image.load(
                os.path.join("Assets", "Background2.png")
            ).convert_alpha()
            
            self.hit_image = pygame.image.load(
                os.path.join("Assets", "hit.png")
            ).convert_alpha()
            
            self.miss_image = pygame.image.load(
                os.path.join("Assets", "miss.png")
            ).convert_alpha()
            
            logger.info("Images loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load images: {e}")
            # Create placeholder images
            self.background_image = None
            self.hit_image = None
            self.miss_image = None
    
    def load_fonts(self):
        """Load fonts"""
        try:
            font_path = os.path.join("Fonts", "INVASION2000.TTF")
            self.font_title = pygame.font.Font(font_path, 50)
            self.font_grid = pygame.font.Font(font_path, 35)
        except:
            self.font_title = pygame.font.SysFont(None, 50)
            self.font_grid = pygame.font.SysFont(None, 35)
            
        self.font_numbers = pygame.font.SysFont(None, 45)
    
    def render(self, ship_manager: Optional[ShipManager] = None,
              battle_manager: Optional[BattleManager] = None,
              ui_manager: Optional[UIManager] = None):
        """Main render method"""
        # Clear screen
        self.screen.fill(self.GRAY)
        
        # Render based on game phase
        if game_state.game_phase == GamePhase.MENU:
            self.render_menu_background()
        elif game_state.game_phase in [GamePhase.SHIP_PLACEMENT, 
                                      GamePhase.WAITING_FOR_OPPONENT_SHIPS,
                                      GamePhase.BATTLE]:
            self.render_game_background()
            self.render_game_board()
            
            if ship_manager:
                # Draw placed ships
                ship_manager.draw_placed_ships(self.screen)
                
                # Draw draggable ships in placement phase
                if game_state.game_phase == GamePhase.SHIP_PLACEMENT:
                    ship_manager.draw_draggable_ships(self.screen)
            
            if battle_manager and game_state.game_phase == GamePhase.BATTLE:
                # Draw shots
                battle_manager.draw_shots(self.screen)
                
                # Draw targeting cursor
                mouse_pos = pygame.mouse.get_pos()
                battle_manager.draw_targeting_cursor(self.screen, mouse_pos)
        
        # Always render UI on top
        if ui_manager:
            ui_manager.draw()
        
        # Render debug info if enabled
        if game_state.show_debug:
            self.render_debug_info()
        
        # Render FPS if enabled
        if game_state.show_fps:
            self.render_fps()
    
    def render_menu_background(self):
        """Render menu background"""
        if self.background_image:
            self.screen.blit(self.background_image, (0, 0))
        else:
            # Fallback gradient
            for y in range(self.screen_height):
                color_value = int(50 + (y / self.screen_height) * 50)
                pygame.draw.line(self.screen, (0, color_value, color_value * 2),
                               (0, y), (self.screen_width, y))
    
    def render_game_background(self):
        """Render game background with borders"""
        # Main border
        pygame.draw.line(self.screen, self.DARK_GREY, (10, 10), (1190, 10))
        pygame.draw.line(self.screen, self.DARK_GREY, (1190, 10), (1190, 630))
        pygame.draw.line(self.screen, self.DARK_GREY, (1190, 560), (10, 560))
        pygame.draw.line(self.screen, self.DARK_GREY, (10, 10), (10, 630))
        pygame.draw.line(self.screen, self.DARK_GREY, (10, 630), (1190, 630))
        
        # Title
        title_text = self.font_title.render("BATTLESHIP", True, self.BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 38))
        self.screen.blit(title_text, title_rect)
    
    def render_game_board(self):
        """Render game boards"""
        # Player board title
        player_text = self.font_grid.render("Your Fleet", True, self.BLACK)
        player_rect = player_text.get_rect(center=(287, 90))
        self.screen.blit(player_text, player_rect)
        
        # Enemy board title
        enemy_name = game_state.network.opponent_name
        if game_state.is_singleplayer():
            enemy_name = f"AI ({game_state.ai_difficulty})"
        enemy_text = self.font_grid.render(f"{enemy_name}'s Fleet", True, self.BLACK)
        enemy_rect = enemy_text.get_rect(center=(920, 90))
        self.screen.blit(enemy_text, enemy_rect)
        
        # Draw both grids
        self.draw_grid(92, 120, True)   # Player grid
        self.draw_grid(720, 120, False) # Enemy grid
    
    def draw_grid(self, x: int, y: int, is_player_grid: bool):
        """Draw a single grid"""
        # Grid background
        grid_width = self.cell_size * self.grid_size + self.cell_size
        grid_height = self.cell_size * self.grid_size + self.cell_size
        
        # Water background
        pygame.draw.rect(self.screen, self.BLUE,
                        pygame.Rect(x + self.cell_size, y + self.cell_size,
                                  grid_width - self.cell_size, grid_height - self.cell_size))
        
        # Header row and column (orange)
        pygame.draw.rect(self.screen, self.ORANGE,
                        pygame.Rect(x + self.cell_size, y,
                                  grid_width - self.cell_size, self.cell_size))
        pygame.draw.rect(self.screen, self.ORANGE,
                        pygame.Rect(x, y + self.cell_size,
                                  self.cell_size, grid_height - self.cell_size))
        
        # Draw grid lines
        for i in range(self.grid_size + 2):
            # Vertical lines
            pygame.draw.line(self.screen, self.BLACK,
                           (x + i * self.cell_size, y),
                           (x + i * self.cell_size, y + grid_height), 3)
            # Horizontal lines
            pygame.draw.line(self.screen, self.BLACK,
                           (x, y + i * self.cell_size),
                           (x + grid_width, y + i * self.cell_size), 3)
        
        # Draw coordinates
        for i in range(self.grid_size):
            # Numbers (0-9) on top
            num_text = self.font_numbers.render(str(i), True, self.LIGHT_GRAY)
            num_rect = num_text.get_rect(
                center=(x + self.cell_size + i * self.cell_size + self.cell_size // 2,
                       y + self.cell_size // 2)
            )
            self.screen.blit(num_text, num_rect)
            
            # Letters (A-J) on left
            letter = chr(65 + i)  # A-J
            letter_text = self.font_numbers.render(letter, True, self.LIGHT_GRAY)
            letter_rect = letter_text.get_rect(
                center=(x + self.cell_size // 2,
                       y + self.cell_size + i * self.cell_size + self.cell_size // 2)
            )
            self.screen.blit(letter_text, letter_rect)
    
    def render_debug_info(self):
        """Render debug information"""
        debug_info = [
            f"Phase: {game_state.game_phase.value}",
            f"Mode: {game_state.game_mode.value}",
            f"Turn: {'Player' if game_state.battle.my_turn else 'AI/Enemy'}",
            f"Connected: {game_state.is_connected()}",
            f"Ships Ready - Player: {game_state.player.ships_ready}, Enemy: {game_state.opponent.ships_ready}",
        ]
        
        # Background
        bg_height = len(debug_info) * 25 + 20
        debug_bg = pygame.Surface((300, bg_height))
        debug_bg.set_alpha(200)
        debug_bg.fill((0, 0, 0))
        self.screen.blit(debug_bg, (self.screen_width - 310, 10))
        
        # Text
        font = pygame.font.SysFont(None, 20)
        for i, info in enumerate(debug_info):
            text = font.render(info, True, self.WHITE)
            self.screen.blit(text, (self.screen_width - 300, 20 + i * 25))
    
    def render_fps(self):
        """Render FPS counter"""
        clock = pygame.time.Clock()
        fps = int(clock.get_fps())
        
        font = pygame.font.SysFont(None, 30)
        fps_text = font.render(f"FPS: {fps}", True, self.WHITE)
        
        # Background
        bg_rect = fps_text.get_rect()
        bg_rect.inflate_ip(10, 5)
        bg_rect.bottomleft = (10, self.screen_height - 10)
        
        pygame.draw.rect(self.screen, (0, 0, 0, 128), bg_rect)
        
        # Text
        fps_rect = fps_text.get_rect(center=bg_rect.center)
        self.screen.blit(fps_text, fps_rect)
    
    def render_connection_status(self):
        """Render connection status indicator"""
        if not game_state.is_multiplayer():
            return
            
        # Status colors
        colors = {
            "disconnected": self.RED,
            "connecting": self.ORANGE,
            "connected": self.GREEN
        }
        
        status = game_state.network.connection_status.value
        color = colors.get(status, self.GRAY)
        
        # Draw indicator
        pygame.draw.circle(self.screen, self.BLACK,
                         (self.screen_width - 20, 20), 10)
        pygame.draw.circle(self.screen, color,
                         (self.screen_width - 20, 20), 8)
        
        # Ping display if connected
        if game_state.is_connected() and game_state.network.ping > 0:
            font = pygame.font.SysFont(None, 20)
            ping_text = font.render(f"{game_state.network.ping}ms", True, self.WHITE)
            self.screen.blit(ping_text, (self.screen_width - 60, 10))