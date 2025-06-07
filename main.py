"""
Battleship Game - Main Entry Point
Fully integrated version with all improvements
"""

import pygame
import sys
import logging
import os
import time
from typing import Optional

# Import game modules
from game_state import game_state, GamePhase, GameMode
from ui_manager import UIManager
from ship_manager import ShipManager
from battle_manager import BattleManager
from renderer import Renderer
from network_manager import NetworkManager
from game_integration import GameIntegration
import ai

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 650
FPS = 60
GAME_TITLE = "Battleship"
VERSION = "2.0"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("battleship.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Battleship")


class BattleshipGame:
    """Main game class - orchestrates all components"""
    
    def __init__(self):
        logger.info(f"Initializing {GAME_TITLE} v{VERSION}")
        
        # Initialize Pygame
        pygame.init()
        pygame.mixer.init()
        
        # Create screen
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        
        # Set icon
        try:
            icon = pygame.image.load(os.path.join("Assets", "logo.png"))
            pygame.display.set_icon(icon)
        except Exception as e:
            logger.warning(f"Failed to load game icon: {e}")
        
        # Game clock and FPS tracking
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0
        
        # Initialize game components
        self.initialize_components()
        
        # Load settings
        game_state.load_settings()
        
        # Initialize sounds
        self.initialize_sounds()
        
        # Show loading complete
        logger.info("Game initialized successfully")
        
    def initialize_components(self):
        """Initialize all game components"""
        logger.info("Initializing game components...")
        
        # Core components
        self.ship_manager = ShipManager()
        self.ui_manager = UIManager(self.screen, self.ship_manager)
        self.battle_manager = BattleManager(self.ship_manager)
        self.renderer = Renderer(self.screen)
        
        # Integration layer
        self.game_integration = GameIntegration(
            self.ui_manager,
            self.ship_manager,
            self.battle_manager
        )
        
        # Set cross-references
        self.battle_manager.set_ui_manager(self.ui_manager)
        
        logger.info("Components initialized")
    
    def initialize_sounds(self):
        """Initialize background music and sound system"""
        try:
            # Set up mixer
            pygame.mixer.set_num_channels(20)
            
            # Load background music
            music_path = os.path.join("Sounds", "valkyries.mp3")
            if os.path.exists(music_path):
                self.music = pygame.mixer.Sound(music_path)
                self.music.set_volume(game_state.volume_music / 100.0)
                
                # Play on loop
                self.music_channel = pygame.mixer.find_channel(True)
                self.music_channel.play(self.music, -1)
                
                logger.info("Background music initialized")
            else:
                logger.warning(f"Music file not found: {music_path}")
                self.music = None
                
        except Exception as e:
            logger.error(f"Failed to initialize music: {e}")
            self.music = None
    
    def handle_events(self):
        """Handle all pygame events"""
        mouse_clicked = False
        mouse_released = False
        keys_pressed = {}
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                keys_pressed[event.key] = True
                
                # Global hotkeys
                if event.key == pygame.K_ESCAPE:
                    self.handle_escape()
                    
                elif event.key == pygame.K_F1:
                    # Show help
                    self.show_help()
                    
                elif event.key == pygame.K_F3:
                    # Toggle FPS display
                    game_state.show_fps = not game_state.show_fps
                    self.ui_manager.show_message(
                        f"FPS display {'ON' if game_state.show_fps else 'OFF'}", 
                        1.0, "info"
                    )
                    
                elif event.key == pygame.K_F4:
                    # Toggle debug mode
                    game_state.show_debug = not game_state.show_debug
                    self.ui_manager.show_message(
                        f"Debug mode {'ON' if game_state.show_debug else 'OFF'}", 
                        1.0, "info"
                    )
                    
                elif event.key == pygame.K_F5 and game_state.is_multiplayer():
                    # Force reconnect
                    self.ui_manager.show_message("Reconnecting...", 2.0, "info")
                    if hasattr(self.game_integration, 'network_manager'):
                        self.game_integration._initialize_network()
                        
                # Ship rotation keys
                elif event.key in [pygame.K_r, pygame.K_SPACE]:
                    if game_state.game_phase == GamePhase.SHIP_PLACEMENT:
                        # Rotate selected ship
                        for ship in self.ship_manager.draggable_ships:
                            if ship.dragging:
                                ship.rotate()
                                
            elif event.type == pygame.KEYUP:
                keys_pressed[event.key] = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_clicked = True
                elif event.button == 2:  # Middle click
                    # Rotate ship if dragging
                    if game_state.game_phase == GamePhase.SHIP_PLACEMENT:
                        for ship in self.ship_manager.draggable_ships:
                            if ship.dragging:
                                ship.rotate()
                                
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mouse_released = True
                    
            elif event.type == pygame.WINDOWFOCUSLOST:
                game_state.window_focused = False
                
            elif event.type == pygame.WINDOWFOCUSGAINED:
                game_state.window_focused = True
                
            # Custom events
            elif event.type == pygame.USEREVENT + 1:
                # AI turn timer
                if game_state.is_singleplayer() and not game_state.battle.my_turn:
                    self.game_integration.handle_ai_turn()
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # Cancel timer
                    
            elif event.type == pygame.USEREVENT + 2:
                # Auto-save timer
                game_state.save_settings()
        
        return mouse_clicked, mouse_released, keys_pressed
    
    def handle_escape(self):
        """Handle escape key press"""
        if game_state.show_settings:
            # Close settings
            game_state.show_settings = False
            game_state.save_settings()
        elif game_state.game_phase == GamePhase.MENU:
            # Exit game
            self.running = False
        elif game_state.game_phase == GamePhase.GAME_OVER:
            # Return to menu
            self.return_to_menu()
        else:
            # Show pause/quit dialog
            self.show_quit_dialog()
    
    def show_help(self):
        """Show help information"""
        help_text = [
            "=== BATTLESHIP HELP ===",
            "",
            "CONTROLS:",
            "Mouse - Select and place ships",
            "R or Space - Rotate ship",
            "Middle Click - Rotate ship (while dragging)",
            "ESC - Menu/Back",
            "F1 - This help",
            "F3 - Toggle FPS",
            "F4 - Toggle Debug",
            "F5 - Reconnect (Multiplayer)",
            "",
            "RULES:",
            "- Place all 5 ships on your board",
            "- Ships cannot overlap or touch",
            "- Take turns firing at enemy board",
            "- First to sink all ships wins!",
        ]
        
        # Show in console for now
        for line in help_text:
            logger.info(line)
            
        self.ui_manager.show_message("Help printed to console/log", 2.0, "info")
    
    def show_quit_dialog(self):
        """Show quit confirmation dialog"""
        # For now, just return to menu
        self.ui_manager.show_message("Returning to menu...", 1.0, "info")
        self.return_to_menu()
    
    def update(self):
        """Update game logic"""
        # Get input state
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked, mouse_released, keys_pressed = self.handle_events()
        
        # Update FPS counter
        self.update_fps()
        
        # Update UI (handles menus, buttons, etc.)
        self.ui_manager.update(mouse_pos, mouse_clicked)
        
        # Update game based on phase
        if game_state.game_phase == GamePhase.MENU:
            # Menu is handled by UI manager
            pass
            
        elif game_state.game_phase == GamePhase.CONNECTING:
            # Connecting is handled by game integration
            pass
            
        elif game_state.game_phase == GamePhase.WAITING_FOR_OPPONENT:
            # Show waiting message
            if not hasattr(self, '_waiting_message_shown'):
                self.ui_manager.show_message("Waiting for opponent...", 10.0, "info")
                self._waiting_message_shown = True
                
        elif game_state.game_phase == GamePhase.SHIP_PLACEMENT:
            # Update ship placement
            self.ship_manager.update_placement(
                mouse_pos, mouse_clicked, mouse_released, keys_pressed
            )
            
        elif game_state.game_phase == GamePhase.WAITING_FOR_OPPONENT_SHIPS:
            # Waiting is passive
            pass
            
        elif game_state.game_phase == GamePhase.BATTLE:
            # Update battle
            self.battle_manager.update(mouse_pos, mouse_clicked)
            
            # Schedule AI turn if needed
            if (game_state.is_singleplayer() and 
                not game_state.battle.my_turn and
                not pygame.time.get_ticks() < getattr(self, '_ai_turn_scheduled', 0)):
                
                # Schedule AI turn after 1 second
                pygame.time.set_timer(pygame.USEREVENT + 1, 1000)
                self._ai_turn_scheduled = pygame.time.get_ticks() + 1000
                
        elif game_state.game_phase == GamePhase.GAME_OVER:
            # Show return to menu after delay
            if not hasattr(self, '_game_over_time'):
                self._game_over_time = time.time()
                
            if time.time() - self._game_over_time > 3.0:
                # Show click to continue message
                if not hasattr(self, '_continue_message_shown'):
                    self.ui_manager.show_message(
                        "Click to return to menu", 10.0, "info"
                    )
                    self._continue_message_shown = True
                    
                # Return to menu on click
                if mouse_clicked:
                    self.return_to_menu()
        
        # Update game integration (handles network, etc.)
        self.game_integration.update()
        
        # Update sound volumes
        self.update_sound_volumes()
        
        # Auto-save periodically (every 30 seconds)
        if not hasattr(self, '_last_save_time'):
            self._last_save_time = time.time()
            
        if time.time() - self._last_save_time > 30:
            game_state.save_settings()
            self._last_save_time = time.time()
    
    def update_fps(self):
        """Update FPS counter"""
        self.fps_counter += 1
        
        if time.time() - self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = time.time()
    
    def render(self):
        """Render everything"""
        # Main rendering
        self.renderer.render(
            self.ship_manager,
            self.battle_manager,
            self.ui_manager
        )
        
        # Render FPS if enabled
        if game_state.show_fps:
            self.render_fps()
            
        # Update display
        pygame.display.flip()
    
    def render_fps(self):
        """Render FPS counter"""
        font = pygame.font.SysFont(None, 30)
        fps_text = f"FPS: {self.current_fps}"
        
        # Create text surface
        text_surface = font.render(fps_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect()
        text_rect.bottomleft = (10, SCREEN_HEIGHT - 10)
        
        # Draw background
        bg_rect = text_rect.inflate(10, 5)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), bg_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 1)
        
        # Draw text
        self.screen.blit(text_surface, text_rect)
    
    def update_sound_volumes(self):
        """Update sound volumes from game state"""
        if hasattr(self, 'music') and self.music:
            self.music.set_volume(game_state.volume_music / 100.0)
            
        self.battle_manager.update_sound_volumes()
    
    def return_to_menu(self):
        """Return to main menu and clean up game state"""
        logger.info("Returning to main menu")
        
        # Clean up network connection if exists
        if hasattr(self.game_integration, 'network_manager'):
            if self.game_integration.network_manager:
                self.game_integration.network_manager.disconnect()
                self.game_integration.network_manager = None
        
        # Reset game state
        game_state.reset()
        
        # Reset component states
        self.ship_manager = ShipManager()
        self.battle_manager = BattleManager(self.ship_manager)
        self.battle_manager.set_ui_manager(self.ui_manager)
        
        # Update game integration
        self.game_integration.ship_manager = self.ship_manager
        self.game_integration.battle_manager = self.battle_manager
        
        # Clear any temporary attributes
        for attr in ['_waiting_message_shown', '_game_over_time', 
                    '_continue_message_shown', '_ai_turn_scheduled']:
            if hasattr(self, attr):
                delattr(self, attr)
        
        # Show menu message
        self.ui_manager.show_message("Welcome back!", 1.0, "info")
    
    def run(self):
        """Main game loop"""
        logger.info(f"Starting {GAME_TITLE} v{VERSION}")
        logger.info(f"Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT} @ {FPS} FPS")
        
        # Show initial message
        self.ui_manager.show_message(f"Welcome to {GAME_TITLE}!", 3.0, "info")
        
        # Main loop
        while self.running:
            # Cap framerate
            self.clock.tick(FPS)
            
            # Update game logic
            self.update()
            
            # Render frame
            self.render()
        
        # Clean up before exit
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources before exit"""
        logger.info("Shutting down...")
        
        # Save settings
        game_state.save_settings()
        logger.info("Settings saved")
        
        # Disconnect from network if connected
        if hasattr(self.game_integration, 'network_manager'):
            if self.game_integration.network_manager:
                self.game_integration.network_manager.disconnect()
                logger.info("Network disconnected")
        
        # Stop music
        if hasattr(self, 'music_channel') and self.music_channel:
            self.music_channel.stop()
            
        # Quit pygame
        pygame.quit()
        
        logger.info(f"{GAME_TITLE} closed successfully")
        sys.exit(0)


def main():
    """Entry point"""
    try:
        # Create and run game
        game = BattleshipGame()
        game.run()
        
    except Exception as e:
        # Log any unhandled exceptions
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        
        # Show error dialog if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Battleship Error",
                f"An error occurred:\n\n{str(e)}\n\nCheck battleship.log for details."
            )
            root.destroy()
        except:
            pass
            
        # Exit with error code
        sys.exit(1)


if __name__ == "__main__":
    main()