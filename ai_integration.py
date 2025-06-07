"""
AI System Integration - Connects improved AI with the game
"""

import logging
import time
import pygame
from typing import Optional, Tuple
from game_state import game_state
from ai import (
    create_ai, BaseAI, ImprovedHuntTargetAI, AdaptiveAI, 
    MonteCarloTreeSearchAI, NeuralNetworkAI, AIAnalyzer
)
from ai_config import ai_config_manager, ai_performance_tracker, AIConfig

logger = logging.getLogger("AIIntegration")


class AIPlayer:
    """Enhanced AI player wrapper with config and performance tracking"""
    
    def __init__(self, difficulty: str = "medium"):
        self.difficulty = difficulty
        self.config = ai_config_manager.get_config(difficulty)
        
        # Create AI instance
        self.ai_core = self._create_ai_instance()
        
        # State tracking
        self.thinking = False
        self.think_start_time = 0
        self.last_move_time = 0
        self.move_count = 0
        
        # Performance tracking
        self.game_id = f"ai_game_{int(time.time())}"
        ai_performance_tracker.start_game(self.game_id, difficulty)
        
        logger.info(f"AI Player initialized: {self.config.name} ({self.config.ai_class})")
        
    def _create_ai_instance(self) -> BaseAI:
        """Create AI instance based on config"""
        ai_class_map = {
            "RandomAI": lambda: BaseAI(10),
            "ImprovedHuntTargetAI": lambda: ImprovedHuntTargetAI(10),
            "AdaptiveAI": lambda: AdaptiveAI(10),
            "MonteCarloTreeSearchAI": lambda: MonteCarloTreeSearchAI(
                10, 
                self.config.mcts_simulations,
                self.config.mcts_time_limit
            ),
            "NeuralNetworkAI": lambda: NeuralNetworkAI(10)
        }
        
        creator = ai_class_map.get(self.config.ai_class, ai_class_map["ImprovedHuntTargetAI"])
        ai = creator()
        
        # Apply configuration
        if hasattr(ai, 'hunt_pattern'):
            ai.hunt_pattern = self.config.hunt_pattern
            
        return ai
    
    def start_thinking(self):
        """Start AI thinking animation"""
        self.thinking = True
        self.think_start_time = time.time()
        
    def is_thinking_done(self) -> bool:
        """Check if AI has finished thinking"""
        if not self.thinking:
            return True
            
        elapsed = time.time() - self.think_start_time
        return elapsed >= self.config.think_time
    
    def make_move(self) -> Optional[Tuple[int, int]]:
        """Make a move with configured behavior"""
        # Start thinking if not already
        if not self.thinking:
            self.start_thinking()
            return None
            
        # Check if still thinking
        if not self.is_thinking_done():
            return None
            
        # Make the actual move
        self.thinking = False
        self.move_count += 1
        
        # Get AI's choice
        move = self.ai_core.make_guess()
        
        if move:
            # Apply mistake probability
            import random
            if random.random() < self.config.mistake_probability:
                # Make a suboptimal move occasionally
                valid_targets = self.ai_core.possible_targets
                if valid_targets:
                    # Choose a random target instead
                    alternative_moves = [t for t in valid_targets if t != move]
                    if alternative_moves:
                        move = random.choice(alternative_moves)
                        logger.info(f"AI made a 'mistake' - chose suboptimal move")
            
            # Apply accuracy boost (cheat a little for harder difficulties)
            if self.config.accuracy_boost > 0 and random.random() < self.config.accuracy_boost:
                # Try to find a position that's actually a hit
                # This simulates the AI having better "intuition"
                # In a real implementation, this would check against actual ships
                pass  # Placeholder for now
        
        self.last_move_time = time.time()
        return move
    
    def update_after_shot(self, x: int, y: int, hit: bool, sunk: bool = False, 
                         ship_size: Optional[int] = None):
        """Update AI after shot result"""
        # Update core AI
        self.ai_core.update_after_guess(x, y, hit, sunk, ship_size)
        
        # Track performance
        ai_performance_tracker.record_shot(False, hit, sunk)
        
        # Log for debugging
        result = "HIT" if hit else "MISS"
        if sunk:
            result += f" - SUNK (size {ship_size})"
        logger.info(f"AI shot at ({x},{y}): {result}")
        
    def get_debug_info(self) -> dict:
        """Get debug information about AI state"""
        return {
            "difficulty": self.difficulty,
            "ai_class": self.config.ai_class,
            "move_count": self.move_count,
            "thinking": self.thinking,
            "hits": len(self.ai_core.hits),
            "misses": len(self.ai_core.misses),
            "remaining_targets": len(self.ai_core.possible_targets),
            "ships_sunk": len(self.ai_core.ships_sunk),
            "heat_map": AIAnalyzer.visualize_heat_map(self.ai_core)
        }
    
    def end_game(self, player_won: bool):
        """End game and save performance stats"""
        ai_performance_tracker.end_game(player_won)
        
        # If using adaptive AI, let it learn
        if isinstance(self.ai_core, AdaptiveAI) and hasattr(self, 'enemy_ships'):
            self.ai_core.learn_from_game(self.enemy_ships)


class AIInterface:
    """Interface between AI system and game"""
    
    def __init__(self):
        self.ai_player: Optional[AIPlayer] = None
        self.debug_mode = False
        
    def initialize_ai(self, difficulty: str = None):
        """Initialize AI with specified or recommended difficulty"""
        if difficulty is None:
            # Get recommendation based on player performance
            difficulty = ai_performance_tracker.get_ai_recommendation()
            logger.info(f"AI difficulty recommendation: {difficulty}")
            
        self.ai_player = AIPlayer(difficulty)
        game_state.ai_player = self.ai_player.ai_core  # For compatibility
        
        # Set opponent name
        game_state.network.opponent_name = f"AI {self.ai_player.config.name}"
        
    def handle_ai_turn(self) -> Optional[Tuple[int, int]]:
        """Handle AI's turn"""
        if not self.ai_player or game_state.battle.my_turn:
            return None
            
        # Get AI's move
        move = self.ai_player.make_move()
        
        if move and self.ai_player.is_thinking_done():
            logger.info(f"AI decided to shoot at {move}")
            return move
            
        return None
    
    def update_ai_after_shot(self, x: int, y: int, hit: bool, 
                           sunk: bool = False, ship_size: Optional[int] = None):
        """Update AI after its shot"""
        if self.ai_player:
            self.ai_player.update_after_shot(x, y, hit, sunk, ship_size)
            
    def notify_player_shot(self, x: int, y: int, hit: bool, sunk: bool = False):
        """Notify AI of player's shot (for performance tracking)"""
        ai_performance_tracker.record_shot(True, hit, sunk)
        
    def end_game(self, player_won: bool):
        """End the game and save stats"""
        if self.ai_player:
            self.ai_player.end_game(player_won)
            
    def render_thinking_indicator(self, screen: pygame.Surface):
        """Render AI thinking indicator"""
        if not self.ai_player or not self.ai_player.thinking:
            return
            
        # Calculate progress
        elapsed = time.time() - self.ai_player.think_start_time
        progress = min(1.0, elapsed / self.ai_player.config.think_time)
        
        # Position
        x = screen.get_width() // 2
        y = screen.get_height() - 150
        
        # Draw thinking text
        font = pygame.font.SysFont(None, 30)
        text = font.render("AI is thinking...", True, (255, 255, 255))
        text_rect = text.get_rect(center=(x, y - 30))
        screen.blit(text, text_rect)
        
        # Draw progress bar
        bar_width = 200
        bar_height = 10
        bar_x = x - bar_width // 2
        bar_y = y
        
        # Background
        pygame.draw.rect(screen, (50, 50, 50), 
                        (bar_x, bar_y, bar_width, bar_height))
        
        # Progress
        fill_width = int(bar_width * progress)
        pygame.draw.rect(screen, (0, 255, 0),
                        (bar_x, bar_y, fill_width, bar_height))
        
        # Border
        pygame.draw.rect(screen, (255, 255, 255),
                        (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Thinking animation (dots)
        dots = "." * (int(elapsed * 2) % 4)
        dots_text = font.render(dots, True, (255, 255, 255))
        screen.blit(dots_text, (text_rect.right + 5, text_rect.y))
        
    def render_debug_overlay(self, screen: pygame.Surface):
        """Render AI debug information"""
        if not self.debug_mode or not self.ai_player:
            return
            
        debug_info = self.ai_player.get_debug_info()
        
        # Background
        overlay_rect = pygame.Rect(10, 100, 400, 400)
        overlay_surface = pygame.Surface((overlay_rect.width, overlay_rect.height))
        overlay_surface.set_alpha(200)
        overlay_surface.fill((0, 0, 0))
        screen.blit(overlay_surface, overlay_rect)
        
        # Draw debug info
        font = pygame.font.SysFont("monospace", 14)
        y_offset = 110
        line_height = 20
        
        # Title
        title = font.render("=== AI DEBUG INFO ===", True, (0, 255, 0))
        screen.blit(title, (20, y_offset))
        y_offset += line_height * 1.5
        
        # Basic info
        info_lines = [
            f"Difficulty: {debug_info['difficulty']}",
            f"AI Class: {debug_info['ai_class']}",
            f"Moves Made: {debug_info['move_count']}",
            f"Status: {'Thinking...' if debug_info['thinking'] else 'Ready'}",
            f"Hits: {debug_info['hits']}",
            f"Misses: {debug_info['misses']}",
            f"Ships Sunk: {debug_info['ships_sunk']}",
            f"Targets Left: {debug_info['remaining_targets']}",
        ]
        
        for line in info_lines:
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (20, y_offset))
            y_offset += line_height
            
        # Heat map visualization (if it fits)
        if y_offset < overlay_rect.bottom - 150:
            y_offset += 10
            heatmap_title = font.render("Heat Map Preview:", True, (255, 255, 0))
            screen.blit(heatmap_title, (20, y_offset))
            y_offset += line_height
            
            # Show first few rows of heat map
            heat_lines = debug_info['heat_map'].split('\n')[:5]
            for line in heat_lines:
                if line.strip():
                    text = font.render(line[:40], True, (200, 200, 200))
                    screen.blit(text, (20, y_offset))
                    y_offset += line_height
    
    def toggle_debug_mode(self):
        """Toggle AI debug mode"""
        self.debug_mode = not self.debug_mode
        logger.info(f"AI debug mode: {'ON' if self.debug_mode else 'OFF'}")


# Create global AI interface
ai_interface = AIInterface()


# Integration functions for game
def initialize_ai(difficulty: str = None):
    """Initialize AI system"""
    ai_interface.initialize_ai(difficulty)
    

def handle_ai_turn() -> Optional[Tuple[int, int]]:
    """Handle AI turn and return move"""
    return ai_interface.handle_ai_turn()


def update_ai_after_shot(x: int, y: int, hit: bool, sunk: bool = False, 
                        ship_size: Optional[int] = None):
    """Update AI after its shot"""
    ai_interface.update_ai_after_shot(x, y, hit, sunk, ship_size)


def notify_player_shot(x: int, y: int, hit: bool, sunk: bool = False):
    """Notify AI system of player's shot"""
    ai_interface.notify_player_shot(x, y, hit, sunk)


def end_ai_game(player_won: bool):
    """End AI game and save stats"""
    ai_interface.end_game(player_won)


def render_ai_ui(screen: pygame.Surface):
    """Render AI UI elements"""
    ai_interface.render_thinking_indicator(screen)
    if game_state.show_debug:
        ai_interface.render_debug_overlay(screen)


def toggle_ai_debug():
    """Toggle AI debug mode"""
    ai_interface.toggle_debug_mode()