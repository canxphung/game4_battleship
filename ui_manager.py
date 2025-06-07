"""
UI Manager - Quản lý tất cả UI elements, buttons, menus
"""

import pygame
import os
from typing import Callable, Optional, List, Tuple
from game_state import game_state, GamePhase, GameMode
import logging
from ship_manager import ShipManager

logger = logging.getLogger("UIManager")


class Button:
    """Base button class với các tính năng cơ bản"""
    def __init__(self, x: int, y: int, width: int, height: int, 
                 text: str = "", image: Optional[pygame.Surface] = None,
                 callback: Optional[Callable] = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.image = image
        self.callback = callback
        self.hovered = False
        self.pressed = False
        self.enabled = True
        self.visible = True
        
        # Colors
        self.normal_color = (16, 167, 232)  # BLUE
        self.hover_color = (255, 167, 16)   # ORANGE
        self.pressed_color = (200, 126, 2)  # ORANGEDARKER
        self.disabled_color = (107, 99, 99) # GRAY
        self.text_color = (255, 255, 255)  # WHITE
        
    def update(self, mouse_pos: Tuple[int, int], mouse_clicked: bool):
        """Update button state"""
        if not self.enabled or not self.visible:
            return
            
        # Check hover
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        # Check click
        if self.hovered and mouse_clicked and not self.pressed:
            self.pressed = True
            if self.callback:
                self.callback()
        elif not mouse_clicked:
            self.pressed = False
    
    def draw(self, surface: pygame.Surface, font: Optional[pygame.font.Font] = None):
        """Draw button"""
        if not self.visible:
            return
            
        # Determine color
        if not self.enabled:
            color = self.disabled_color
        elif self.pressed:
            color = self.pressed_color
        elif self.hovered:
            color = self.hover_color
        else:
            color = self.normal_color
        
        # Draw button background
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)  # Border
        
        # Draw image or text
        if self.image:
            # Center image in button
            img_rect = self.image.get_rect(center=self.rect.center)
            surface.blit(self.image, img_rect)
        elif self.text and font:
            # Render text
            text_surface = font.render(self.text, True, self.text_color)
            text_rect = text_surface.get_rect(center=self.rect.center)
            surface.blit(text_surface, text_rect)


class ImageButton(Button):
    """Button with image that scales on hover"""
    def __init__(self, x: int, y: int, image: pygame.Surface, 
                 scale: float = 1.0, hover_scale: float = 1.1,
                 callback: Optional[Callable] = None):
        # Scale image
        width = int(image.get_width() * scale)
        height = int(image.get_height() * scale)
        self.original_image = pygame.transform.scale(image, (width, height))
        
        # Create hover image
        hover_width = int(image.get_width() * hover_scale)
        hover_height = int(image.get_height() * hover_scale)
        self.hover_image = pygame.transform.scale(image, (hover_width, hover_height))
        
        super().__init__(x - width//2, y - height//2, width, height, 
                        image=self.original_image, callback=callback)
        
        self.hover_scale = hover_scale
        
    def draw(self, surface: pygame.Surface, font: Optional[pygame.font.Font] = None):
        """Draw image button"""
        if not self.visible:
            return
            
        if self.hovered and self.enabled:
            # Draw larger image centered
            img_rect = self.hover_image.get_rect(center=self.rect.center)
            surface.blit(self.hover_image, img_rect)
        else:
            surface.blit(self.image, self.rect)


class Slider:
    """Slider for volume control"""
    def __init__(self, x: int, y: int, width: int, height: int,
                 min_value: int = 0, max_value: int = 100,
                 initial_value: int = 50):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.dragging = False
        
        # Colors
        self.bg_color = (255, 255, 255)
        self.fill_color = (177, 177, 177)
        self.outline_color = (0, 0, 0)
        
    def update(self, mouse_pos: Tuple[int, int], mouse_clicked: bool):
        """Update slider"""
        if self.rect.collidepoint(mouse_pos) and mouse_clicked:
            self.dragging = True
        elif not mouse_clicked:
            self.dragging = False
            
        if self.dragging:
            # Calculate value based on mouse position
            relative_x = mouse_pos[0] - self.rect.x
            relative_x = max(0, min(self.rect.width, relative_x))
            self.value = int((relative_x / self.rect.width) * 
                           (self.max_value - self.min_value) + self.min_value)
    
    def draw(self, surface: pygame.Surface, font: Optional[pygame.font.Font] = None):
        """Draw slider"""
        # Background
        pygame.draw.rect(surface, self.bg_color, self.rect, 0, 8)
        
        # Fill
        fill_width = int((self.value - self.min_value) / 
                        (self.max_value - self.min_value) * self.rect.width)
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, 
                                  fill_width, self.rect.height)
            pygame.draw.rect(surface, self.fill_color, fill_rect, 0, 8)
        
        # Outline
        pygame.draw.rect(surface, self.outline_color, self.rect, 2, 10)
        
        # Value text
        if font:
            text = font.render(f"{self.value}%", True, self.bg_color)
            surface.blit(text, (self.rect.x + self.rect.width + 10, 
                              self.rect.y - 5))


class MessageOverlay:
    """Display temporary messages to player"""
    def __init__(self):
        self.messages: List[Tuple[str, float, float, str]] = []  # (text, duration, start_time, type)
        self.font = None
        
    def add_message(self, text: str, duration: float = 3.0, msg_type: str = "info"):
        """Add a message to display"""
        import time
        self.messages.append((text, duration, time.time(), msg_type))
        logger.info(f"Message added: {text}")
        
    def update(self):
        """Update messages and remove expired ones"""
        import time
        current_time = time.time()
        self.messages = [(text, dur, start, typ) for text, dur, start, typ in self.messages
                        if current_time - start < dur]
    
    def draw(self, surface: pygame.Surface):
        """Draw messages"""
        if not self.messages or not self.font:
            return
            
        import time
        current_time = time.time()
        
        # Message type colors
        colors = {
            "info": (255, 255, 255),      # White
            "warning": (255, 165, 0),     # Orange  
            "error": (255, 0, 0),         # Red
            "success": (0, 255, 0)        # Green
        }
        
        y_offset = surface.get_height() - 100
        
        for text, duration, start_time, msg_type in reversed(self.messages):
            # Calculate fade
            elapsed = current_time - start_time
            alpha = 255
            
            if elapsed < 0.5:  # Fade in
                alpha = int(255 * (elapsed / 0.5))
            elif elapsed > duration - 0.5:  # Fade out
                alpha = int(255 * ((duration - elapsed) / 0.5))
            
            if alpha <= 0:
                continue
                
            # Get color
            color = colors.get(msg_type, colors["info"])
            
            # Render text
            text_surface = self.font.render(text, True, color)
            text_rect = text_surface.get_rect(center=(surface.get_width() // 2, y_offset))
            
            # Background
            bg_rect = text_rect.inflate(20, 10)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surface, (0, 0, 0, alpha // 2), bg_surface.get_rect(), border_radius=5)
            
            # Draw
            surface.blit(bg_surface, bg_rect)
            surface.blit(text_surface, text_rect)
            
            y_offset -= bg_rect.height + 5


class UIManager:
    """Main UI Manager class"""
    def __init__(self, screen: pygame.Surface, ship_manager):
        self.screen = screen
        self.ship_manager = ship_manager
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        # Fonts
        self.load_fonts()
        
        # UI Elements
        self.buttons: dict[str, Button] = {}
        self.sliders: dict[str, Slider] = {}
        self.message_overlay = MessageOverlay()
        self.message_overlay.font = self.font_body
        
        # Initialize UI elements
        self.create_ui_elements()
        
        logger.info("UIManager initialized")
    
    def load_fonts(self):
        """Load game fonts"""
        try:
            font_path = os.path.join("Fonts", "INVASION2000.TTF")
            self.font_title = pygame.font.Font(font_path, 50)
            self.font_body = pygame.font.Font(font_path, 35)
            self.font_small = pygame.font.Font(font_path, 20)
        except:
            # Fallback to system fonts
            self.font_title = pygame.font.SysFont(None, 50)
            self.font_body = pygame.font.SysFont(None, 35)
            self.font_small = pygame.font.SysFont(None, 20)
            logger.warning("Custom fonts not found, using system fonts")
        
        self.font_grid = pygame.font.SysFont(None, 45)
        self.font_instruction = pygame.font.SysFont(None, 42)
    
    def create_ui_elements(self):
        """Create all UI elements"""
        # Main menu buttons
        self.buttons["start_game"] = Button(
            self.screen_width//2 - 100, self.screen_height//2 + 250, 200, 50,
            "Start Game", callback=self.on_start_game
        )
        
        self.buttons["singleplayer"] = Button(
            self.screen_width//2 - 150, self.screen_height//2, 300, 50,
            "Single Player", callback=lambda: self.set_game_mode("singleplayer")
        )
        
        self.buttons["multiplayer"] = Button(
            self.screen_width//2 - 150, self.screen_height//2 + 70, 300, 50,
            "Multiplayer", callback=lambda: self.set_game_mode("multiplayer")
        )
        
        # Difficulty buttons
        difficulties = ["easy", "medium", "hard", "expert", "master"]
        for i, diff in enumerate(difficulties):
            self.buttons[f"diff_{diff}"] = Button(
                self.screen_width//2 - 150 + i*62, self.screen_height//2 + 180, 60, 35,
                diff.capitalize(), callback=lambda d=diff: self.set_difficulty(d)
            )
        
        # Settings button
        try:
            settings_img = pygame.image.load(os.path.join("Assets", "SettingsIcon.png"))
            self.buttons["settings"] = ImageButton(
                self.screen_width - 30, self.screen_height - 45,
                settings_img, 1.0, 1.2, callback=self.toggle_settings
            )
        except:
            self.buttons["settings"] = Button(
                self.screen_width - 100, self.screen_height - 50, 90, 40,
                "Settings", callback=self.toggle_settings
            )
        
        # Ship placement done button
        try:
            done_img = pygame.image.load(os.path.join("Assets", "Done_button.png"))
            self.buttons["ships_done"] = ImageButton(
                600, 400, done_img, 1.0, 1.1, 
                callback=self.on_ships_done
            )
        except:
            self.buttons["ships_done"] = Button(
                550, 380, 100, 40, "Done", callback=self.on_ships_done
            )
        
        # Volume sliders
        self.sliders["music_volume"] = Slider(
            100, 150, 400, 20, 0, 100, game_state.volume_music
        )
        
        self.sliders["effects_volume"] = Slider(
            100, 200, 400, 20, 0, 100, game_state.volume_effects
        )
    
    def update(self, mouse_pos: Tuple[int, int], mouse_clicked: bool):
        """Update all UI elements"""
        # Update message overlay
        self.message_overlay.update()
        
        # Update buttons based on game phase
        self.update_button_visibility()
        
        # Update visible buttons
        for button in self.buttons.values():
            if button.visible:
                button.update(mouse_pos, mouse_clicked)
        
        # Update sliders in settings menu
        if game_state.show_settings:
            for slider in self.sliders.values():
                slider.update(mouse_pos, mouse_clicked)
            
            # Update game state with slider values
            game_state.volume_music = self.sliders["music_volume"].value
            game_state.volume_effects = self.sliders["effects_volume"].value
    
    def draw(self):
        """Draw UI elements based on game phase"""
        # Always draw message overlay
        self.message_overlay.draw(self.screen)
        
        # Draw UI based on game phase
        if game_state.game_phase == GamePhase.MENU:
            self.draw_main_menu()
        elif game_state.show_settings:
            self.draw_settings_menu()
        elif game_state.game_phase == GamePhase.SHIP_PLACEMENT:
            self.draw_ship_placement_ui()
        elif game_state.game_phase == GamePhase.BATTLE:
            self.draw_battle_ui()
    
    def draw_main_menu(self):
        """Draw main menu UI"""
        # Title
        title_text = "BATTLESHIP"
        title_surface = self.font_title.render(title_text, True, (255, 167, 16))
        title_rect = title_surface.get_rect(center=(self.screen_width//2, 50))
        self.screen.blit(title_surface, title_rect)
        
        # Player name
        name_text = game_state.player.name
        name_surface = self.font_body.render(name_text, True, (200, 126, 2))
        name_rect = name_surface.get_rect(center=(self.screen_width//2, 105))
        self.screen.blit(name_surface, name_rect)
        
        # Win/Loss record
        wins_text = f"Wins: {game_state.player.wins}"
        losses_text = f"Losses: {game_state.player.losses}"
        wins_surface = self.font_body.render(wins_text, True, (200, 126, 2))
        losses_surface = self.font_body.render(losses_text, True, (200, 126, 2))
        self.screen.blit(wins_surface, (10, 10))
        self.screen.blit(losses_surface, (10, 50))
        
        # Draw buttons
        for key, button in self.buttons.items():
            if button.visible and key.startswith(("singleplayer", "multiplayer", "start_game", "settings")):
                button.draw(self.screen, self.font_body)
        
        # Draw difficulty buttons if singleplayer
        if game_state.game_mode == GameMode.SINGLEPLAYER:
            diff_label = self.font_body.render("AI Difficulty:", True, (255, 255, 255))
            self.screen.blit(diff_label, (self.screen_width//2 - 150, self.screen_height//2 + 140))
            
            for key, button in self.buttons.items():
                if key.startswith("diff_"):
                    button.draw(self.screen, self.font_small)
    
    def draw_settings_menu(self):
        """Draw settings menu"""
        # Background overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Settings panel
        panel_rect = pygame.Rect(100, 50, self.screen_width - 200, self.screen_height - 100)
        pygame.draw.rect(self.screen, (16, 167, 232), panel_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, 3)
        
        # Title
        title = self.font_title.render("Settings", True, (255, 255, 255))
        title_rect = title.get_rect(center=(self.screen_width//2, 100))
        self.screen.blit(title, title_rect)
        
        # Volume section
        volume_title = self.font_body.render("Volume", True, (255, 167, 16))
        self.screen.blit(volume_title, (150, 200))
        
        music_label = self.font_small.render("Music", True, (255, 255, 255))
        self.screen.blit(music_label, (150, 250))
        self.sliders["music_volume"].draw(self.screen, self.font_small)
        
        effects_label = self.font_small.render("Effects", True, (255, 255, 255))
        self.screen.blit(effects_label, (150, 300))
        self.sliders["effects_volume"].draw(self.screen, self.font_small)
        
        # Close button
        close_text = self.font_body.render("X", True, (255, 255, 255))
        close_rect = pygame.Rect(panel_rect.right - 50, panel_rect.top + 10, 40, 40)
        pygame.draw.rect(self.screen, (255, 0, 0), close_rect)
        close_text_rect = close_text.get_rect(center=close_rect.center)
        self.screen.blit(close_text, close_text_rect)
        
        # Check close button click
        mouse_pos = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0] and close_rect.collidepoint(mouse_pos):
            game_state.show_settings = False
            game_state.save_settings()
    
    def draw_ship_placement_ui(self):
        """Draw ship placement UI"""
        # Instructions
        instruction = "Place your ships on the board"
        inst_surface = self.font_instruction.render(instruction, True, (255, 255, 255))
        inst_rect = inst_surface.get_rect(center=(self.screen_width//2, 590))
        self.screen.blit(inst_surface, inst_rect)
        
        # Done button
        self.buttons["ships_done"].draw(self.screen)
    
    def draw_battle_ui(self):
        """Draw battle UI"""
        # Turn indicator
        turn_text = "Your turn" if game_state.battle.my_turn else f"{game_state.network.opponent_name}'s turn"
        turn_color = (0, 255, 0) if game_state.battle.my_turn else (255, 165, 0)
        turn_surface = self.font_instruction.render(turn_text, True, turn_color)
        turn_rect = turn_surface.get_rect(center=(self.screen_width//2, 590))
        self.screen.blit(turn_surface, turn_rect)
    
    def update_button_visibility(self):
        """Update button visibility based on game state"""
        # Hide all buttons first
        for button in self.buttons.values():
            button.visible = False
        
        # Show buttons based on game phase
        if game_state.game_phase == GamePhase.MENU:
            self.buttons["start_game"].visible = True
            self.buttons["singleplayer"].visible = True
            self.buttons["multiplayer"].visible = True
            self.buttons["settings"].visible = True
            
            # Update button states based on game mode
            if game_state.game_mode == GameMode.SINGLEPLAYER:
                self.buttons["singleplayer"].normal_color = (200, 126, 2)
                self.buttons["multiplayer"].normal_color = (16, 167, 232)
                # Show difficulty buttons
                for key in self.buttons:
                    if key.startswith("diff_"):
                        self.buttons[key].visible = True
                        # Highlight selected difficulty
                        if key == f"diff_{game_state.ai_difficulty}":
                            self.buttons[key].normal_color = (200, 126, 2)
                        else:
                            self.buttons[key].normal_color = (16, 167, 232)
            else:
                self.buttons["multiplayer"].normal_color = (200, 126, 2)
                self.buttons["singleplayer"].normal_color = (16, 167, 232)
                
        elif game_state.game_phase == GamePhase.SHIP_PLACEMENT:
            self.buttons["ships_done"].visible = True
            
        # Settings button always visible except in settings menu
        if not game_state.show_settings:
            self.buttons["settings"].visible = True
    
    # Callbacks
    def on_start_game(self):
        """Start game callback"""
        logger.info(f"Starting game in {game_state.game_mode.value} mode")
        
        if game_state.game_mode == GameMode.SINGLEPLAYER:
            # Initialize AI
            from ai_integration import initialize_ai
            initialize_ai()
            game_state.set_game_phase("ship_placement")
            self.message_overlay.add_message("Place your ships", 3.0, "info")
        else:
            # Start multiplayer connection
            game_state.set_game_phase("connecting")
            self.message_overlay.add_message("Connecting to server...", 3.0, "info")
    
    def set_game_mode(self, mode: str):
        """Set game mode callback"""
        game_state.set_game_mode(mode)
        self.message_overlay.add_message(f"Game mode: {mode}", 2.0, "info")
    
    def set_difficulty(self, difficulty: str):
        """Set AI difficulty callback"""
        game_state.ai_difficulty = difficulty
        self.message_overlay.add_message(f"AI difficulty: {difficulty}", 2.0, "info")
    
    def toggle_settings(self):
        """Toggle settings menu"""
        game_state.show_settings = not game_state.show_settings
    
    def on_ships_done(self):
        """Ships placement done callback"""
        logger.info("Ships placement done requested")

        if self.ship_manager.place_all_ships():
            logger.info("All ships placed. Transitioning to battle phase.")
            self.ship_manager.generate_random_enemy_ships()
            game_state.set_game_phase("battle")
            self.message_overlay.add_message("Battle started!", 3.0, "success")
        else:
            logger.warning("Invalid ship placement")
            self.message_overlay.add_message("Please place all ships correctly.", 3.0, "error")
    
    def show_message(self, text: str, duration: float = 3.0, msg_type: str = "info"):
        """Show a message to the player"""
        self.message_overlay.add_message(text, duration, msg_type)