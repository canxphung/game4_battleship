"""
Battle Manager - Quản lý logic trận đánh, turn-based gameplay
"""

import pygame
from typing import Optional, Tuple, List
from game_state import game_state, GamePhase
from ship_manager import ShipManager
import logging
import random

logger = logging.getLogger("BattleManager")


class Shot:
    """Represents a shot in the game"""
    def __init__(self, x: int, y: int, hit: bool, player_shot: bool = True):
        self.x = x
        self.y = y
        self.hit = hit
        self.player_shot = player_shot
        self.timestamp = pygame.time.get_ticks()
        
        # For animation
        self.animation_complete = False
        self.splash_radius = 0
        self.max_splash_radius = 20


class BattleManager:
    """Manages battle phase logic"""
    
    def __init__(self, ship_manager: ShipManager):
        self.ship_manager = ship_manager
        self.shots: List[Shot] = []
        self.pending_shot: Optional[Tuple[int, int]] = None
        self.last_shot_time = 0
        self.shot_delay = 500  # ms between shots
        
        # Sound effects
        self.load_sounds()
        
        # Animation state
        self.animations = []
        
        logger.info("BattleManager initialized")
    
    def load_sounds(self):
        """Load sound effects"""
        try:
            self.hit_sounds = [
                pygame.mixer.Sound("Sounds/boom1.mp3"),
                pygame.mixer.Sound("Sounds/boom2.mp3"),
                pygame.mixer.Sound("Sounds/boom3.mp3")
            ]
            self.miss_sounds = [
                pygame.mixer.Sound("Sounds/splash1.mp3"),
                pygame.mixer.Sound("Sounds/splash2.mp3"),
                pygame.mixer.Sound("Sounds/splash3.mp3")
            ]
            self.sink_sound = pygame.mixer.Sound("Sounds/sink.mp3")
            
            # Set volumes based on game state
            self.update_sound_volumes()
        except Exception as e:
            logger.error(f"Failed to load sounds: {e}")
            self.hit_sounds = []
            self.miss_sounds = []
            self.sink_sound = None
    
    def update_sound_volumes(self):
        """Update sound volumes from game state"""
        volume = game_state.volume_effects / 100.0
        
        for sound in self.hit_sounds + self.miss_sounds:
            sound.set_volume(volume)
            
        if self.sink_sound:
            self.sink_sound.set_volume(volume)
    
    def update(self, mouse_pos: Tuple[int, int], mouse_clicked: bool):
        """Update battle logic"""
        current_time = pygame.time.get_ticks()
        
        # Update animations
        self.update_animations()
        
        # Handle player turn
        if game_state.battle.my_turn and game_state.is_battle_phase():
            # Check if player clicked on enemy grid
            if mouse_clicked and current_time - self.last_shot_time > self.shot_delay:
                grid_pos = self.ship_manager.get_grid_position(mouse_pos, False)
                
                if grid_pos:
                    x, y = grid_pos
                    
                    # Check if position already shot
                    if not self.is_position_shot(x, y, True):
                        self.pending_shot = (x, y)
                        self.last_shot_time = current_time
                        logger.info(f"Player targeting position ({x}, {y})")
        
        # Process pending shot
        if self.pending_shot:
            x, y = self.pending_shot
            self.process_player_shot(x, y)
            self.pending_shot = None
    
    def process_player_shot(self, x: int, y: int):
        """Process player's shot"""
        # Check hit
        hit, sunk, ship_size = self.ship_manager.handle_shot(x, y, True)
        
        # Create shot record
        shot = Shot(x, y, hit, True)
        self.shots.append(shot)
        
        # Update game state
        game_state.add_shot(x, y, hit, True)
        
        # Play sound
        self.play_shot_sound(hit, sunk)
        
        # Add to UI message
        from ui_manager import UIManager
        if hasattr(self, 'ui_manager') and self.ui_manager:
            if sunk:
                self.ui_manager.show_message(f"Enemy ship sunk! (size {ship_size})", 3.0, "success")
            elif hit:
                self.ui_manager.show_message("Hit!", 1.5, "success")
            else:
                self.ui_manager.show_message("Miss!", 1.5, "info")
        
        # Check for game over
        winner = self.ship_manager.check_game_over()
        if winner == "player":
            self.handle_game_over(True)
        else:
            # Switch turns
            game_state.set_turn(False)
            
            # In singleplayer, trigger AI turn
            if game_state.is_singleplayer():
                pygame.time.set_timer(pygame.USEREVENT + 1, 1000)  # AI shoots after 1 second
    
    def process_enemy_shot(self, x: int, y: int):
        """Process enemy/AI shot"""
        # Check hit
        hit, sunk, ship_size = self.ship_manager.handle_shot(x, y, False)
        
        # Create shot record
        shot = Shot(x, y, hit, False)
        self.shots.append(shot)
        
        # Update game state
        game_state.add_shot(x, y, hit, False)
        
        # Play sound
        self.play_shot_sound(hit, sunk)
        
        # Add to UI message
        if hasattr(self, 'ui_manager') and self.ui_manager:
            if sunk:
                self.ui_manager.show_message(f"Your ship was sunk! (size {ship_size})", 3.0, "error")
            elif hit:
                self.ui_manager.show_message("Your ship was hit!", 1.5, "warning")
            else:
                self.ui_manager.show_message("Enemy missed!", 1.5, "info")
        
        # Check for game over
        winner = self.ship_manager.check_game_over()
        if winner == "enemy":
            self.handle_game_over(False)
        else:
            # Switch turns back to player
            game_state.set_turn(True)
    
    def handle_ai_turn(self):
        """Handle AI turn in singleplayer"""
        if not game_state.is_singleplayer() or game_state.battle.my_turn:
            return
            
        # Get AI decision
        if game_state.ai_player:
            # Get valid targets for AI
            valid_targets = []
            for x in range(10):
                for y in range(10):
                    if not self.is_position_shot(x, y, False):
                        valid_targets.append((x, y))
            
            if valid_targets:
                # Update AI's possible targets
                game_state.ai_player.possible_targets = valid_targets
                
                # Get AI's choice
                ai_guess = game_state.ai_player.make_guess()
                
                if ai_guess:
                    x, y = ai_guess
                    logger.info(f"AI shooting at ({x}, {y})")
                    
                    # Process the shot
                    self.process_enemy_shot(x, y)
                    
                    # Update AI with result
                    shot = self.shots[-1]  # Get the shot we just processed
                    game_state.ai_player.update_after_guess(
                        x, y, shot.hit,
                        # Check if ship was sunk
                        any(ship.is_sunk and (x, y) in ship.positions 
                            for ship in self.ship_manager.player_ships),
                        # Get ship size if sunk
                        next((ship.size for ship in self.ship_manager.player_ships 
                             if ship.is_sunk and (x, y) in ship.positions), None)
                    )
    
    def is_position_shot(self, x: int, y: int, by_player: bool) -> bool:
        """Check if position has been shot"""
        for shot in self.shots:
            if shot.x == x and shot.y == y and shot.player_shot == by_player:
                return True
        return False
    
    def play_shot_sound(self, hit: bool, sunk: bool = False):
        """Play appropriate sound effect"""
        try:
            if sunk and self.sink_sound:
                self.sink_sound.play()
            elif hit and self.hit_sounds:
                random.choice(self.hit_sounds).play()
            elif not hit and self.miss_sounds:
                random.choice(self.miss_sounds).play()
        except Exception as e:
            logger.error(f"Error playing sound: {e}")
    
    def handle_game_over(self, player_won: bool):
        """Handle game over"""
        game_state.set_game_phase("game_over")
        
        if player_won:
            game_state.add_win()
            message = "Victory! You destroyed all enemy ships!"
            msg_type = "success"
        else:
            game_state.add_loss()
            message = "Defeat! All your ships were destroyed!"
            msg_type = "error"
            
        # Show message
        if hasattr(self, 'ui_manager') and self.ui_manager:
            self.ui_manager.show_message(message, 5.0, msg_type)
            
        logger.info(f"Game over - Player {'won' if player_won else 'lost'}")
    
    def update_animations(self):
        """Update shot animations"""
        for shot in self.shots:
            if not shot.animation_complete:
                shot.splash_radius += 2
                if shot.splash_radius >= shot.max_splash_radius:
                    shot.animation_complete = True
    
    def draw_shots(self, surface: pygame.Surface):
        """Draw all shots on the board"""
        for shot in self.shots:
            if shot.player_shot:
                # Draw on enemy board
                px = self.ship_manager.enemy_grid_x + shot.x * self.ship_manager.cell_size
                py = self.ship_manager.enemy_grid_y + shot.y * self.ship_manager.cell_size
            else:
                # Draw on player board
                px = self.ship_manager.player_grid_x + shot.x * self.ship_manager.cell_size
                py = self.ship_manager.player_grid_y + shot.y * self.ship_manager.cell_size
            
            # Center of cell
            cx = px + self.ship_manager.cell_size // 2
            cy = py + self.ship_manager.cell_size // 2
            
            if shot.hit:
                # Draw hit marker (X)
                color = (255, 0, 0)  # Red
                pygame.draw.line(surface, color,
                               (px + 5, py + 5),
                               (px + self.ship_manager.cell_size - 5,
                                py + self.ship_manager.cell_size - 5), 3)
                pygame.draw.line(surface, color,
                               (px + self.ship_manager.cell_size - 5, py + 5),
                               (px + 5, py + self.ship_manager.cell_size - 5), 3)
                
                # Draw explosion effect if animating
                if not shot.animation_complete:
                    for i in range(3):
                        radius = shot.splash_radius - i * 5
                        if radius > 0:
                            alpha = 255 - (shot.splash_radius * 10)
                            if alpha > 0:
                                pygame.draw.circle(surface, (255, 100, 0, alpha),
                                                 (cx, cy), radius, 2)
            else:
                # Draw miss marker (O)
                color = (100, 100, 100)  # Gray
                pygame.draw.circle(surface, color, (cx, cy), 10, 2)
                
                # Draw splash effect if animating
                if not shot.animation_complete:
                    alpha = 255 - (shot.splash_radius * 10)
                    if alpha > 0:
                        pygame.draw.circle(surface, (100, 100, 255, alpha),
                                         (cx, cy), shot.splash_radius, 1)
    
    def draw_targeting_cursor(self, surface: pygame.Surface, mouse_pos: Tuple[int, int]):
        """Draw targeting cursor on enemy grid during player turn"""
        if not game_state.battle.my_turn or not game_state.is_battle_phase():
            return
            
        # Check if mouse is over enemy grid
        grid_pos = self.ship_manager.get_grid_position(mouse_pos, False)
        if not grid_pos:
            return
            
        x, y = grid_pos
        
        # Check if position already shot
        if self.is_position_shot(x, y, True):
            return
            
        # Calculate pixel position
        px = self.ship_manager.enemy_grid_x + x * self.ship_manager.cell_size
        py = self.ship_manager.enemy_grid_y + y * self.ship_manager.cell_size
        
        # Draw targeting cursor
        cursor_color = (0, 255, 0, 128)  # Semi-transparent green
        s = pygame.Surface((self.ship_manager.cell_size, self.ship_manager.cell_size))
        s.set_alpha(128)
        s.fill(cursor_color)
        surface.blit(s, (px, py))
        
        # Draw crosshair
        cx = px + self.ship_manager.cell_size // 2
        cy = py + self.ship_manager.cell_size // 2
        
        pygame.draw.line(surface, (0, 255, 0),
                        (cx - 10, cy), (cx + 10, cy), 2)
        pygame.draw.line(surface, (0, 255, 0),
                        (cx, cy - 10), (cx, cy + 10), 2)
        pygame.draw.circle(surface, (0, 255, 0),
                         (cx, cy), 15, 2)
    
    def reset(self):
        """Reset battle manager for new game"""
        self.shots.clear()
        self.pending_shot = None
        self.last_shot_time = 0
        self.animations.clear()
        logger.info("Battle manager reset")
    
    def set_ui_manager(self, ui_manager):
        """Set reference to UI manager for messages"""
        self.ui_manager = ui_manager