"""
AI Configuration and Performance Tracking System
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger("AIConfig")


@dataclass
class AIConfig:
    """Configuration for AI difficulty levels"""
    name: str
    description: str
    ai_class: str
    
    # Performance parameters
    think_time: float = 1.0  # Seconds to "think" before shooting
    accuracy_boost: float = 0.0  # Artificial accuracy boost (0-1)
    
    # Strategy weights
    hunt_pattern: str = "checkerboard"  # Hunt pattern to use
    target_aggression: float = 0.7  # How aggressively to pursue hits (0-1)
    
    # Monte Carlo parameters (for MCTS AI)
    mcts_simulations: int = 100
    mcts_time_limit: float = 2.0
    
    # Behavioral parameters
    mistake_probability: float = 0.0  # Chance to make suboptimal move
    memory_limit: int = 100  # How many past shots to remember
    
    # Learning parameters (for Adaptive AI)
    learning_rate: float = 0.2
    exploration_rate: float = 0.1


# Default AI configurations
DEFAULT_CONFIGS = {
    "easy": AIConfig(
        name="Easy",
        description="Random shooting with basic targeting",
        ai_class="RandomAI",
        think_time=0.5,
        mistake_probability=0.3,
        memory_limit=10
    ),
    
    "medium": AIConfig(
        name="Medium", 
        description="Hunt and target with pattern recognition",
        ai_class="ImprovedHuntTargetAI",
        think_time=1.0,
        hunt_pattern="checkerboard",
        target_aggression=0.7,
        mistake_probability=0.1
    ),
    
    "hard": AIConfig(
        name="Hard",
        description="Adaptive AI that learns your patterns",
        ai_class="AdaptiveAI", 
        think_time=1.5,
        learning_rate=0.2,
        exploration_rate=0.15,
        accuracy_boost=0.1
    ),
    
    "expert": AIConfig(
        name="Expert",
        description="Advanced AI with Monte Carlo simulations",
        ai_class="MonteCarloTreeSearchAI",
        think_time=2.0,
        mcts_simulations=200,
        mcts_time_limit=3.0,
        accuracy_boost=0.15
    ),
    
    "master": AIConfig(
        name="Master",
        description="Neural network-based AI",
        ai_class="NeuralNetworkAI",
        think_time=2.5,
        accuracy_boost=0.2,
        mistake_probability=0.05
    ),
    
    "nightmare": AIConfig(
        name="Nightmare",
        description="Unbeatable AI with perfect play",
        ai_class="MonteCarloTreeSearchAI",
        think_time=1.0,  # Fast to be intimidating
        mcts_simulations=500,
        mcts_time_limit=5.0,
        accuracy_boost=0.3,
        mistake_probability=0.0
    )
}


@dataclass
class GameStats:
    """Statistics for a single game"""
    game_id: str
    timestamp: datetime
    ai_difficulty: str
    player_won: bool
    total_turns: int
    player_shots: int
    player_hits: int
    player_accuracy: float
    ai_shots: int
    ai_hits: int
    ai_accuracy: float
    game_duration: float  # seconds
    ships_sunk_by_player: int
    ships_sunk_by_ai: int
    first_hit_turn: Optional[int] = None
    first_sink_turn: Optional[int] = None


class AIPerformanceTracker:
    """Track and analyze AI performance over time"""
    
    def __init__(self, stats_file: str = "ai_stats.json"):
        self.stats_file = stats_file
        self.current_game_stats = {}
        self.game_history: List[GameStats] = []
        self.load_stats()
        
    def load_stats(self):
        """Load historical stats from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    self.game_history = [
                        GameStats(**game) for game in data.get('games', [])
                    ]
                logger.info(f"Loaded {len(self.game_history)} historical games")
            except Exception as e:
                logger.error(f"Failed to load stats: {e}")
                self.game_history = []
        
    def save_stats(self):
        """Save stats to file"""
        try:
            data = {
                'games': [asdict(game) for game in self.game_history],
                'summary': self.get_summary_stats()
            }
            
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.info("Stats saved successfully")
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
    
    def start_game(self, game_id: str, ai_difficulty: str):
        """Start tracking a new game"""
        self.current_game_stats = {
            'game_id': game_id,
            'timestamp': datetime.now(),
            'ai_difficulty': ai_difficulty,
            'start_time': datetime.now(),
            'player_shots': 0,
            'player_hits': 0,
            'ai_shots': 0,
            'ai_hits': 0,
            'turn_count': 0,
            'first_hit_turn': None,
            'first_sink_turn': None,
            'ships_sunk_by_player': 0,
            'ships_sunk_by_ai': 0
        }
        
    def record_shot(self, is_player: bool, hit: bool, sunk: bool = False):
        """Record a shot in the current game"""
        if not self.current_game_stats:
            return
            
        self.current_game_stats['turn_count'] += 0.5  # Half turn per shot
        
        if is_player:
            self.current_game_stats['player_shots'] += 1
            if hit:
                self.current_game_stats['player_hits'] += 1
                if self.current_game_stats['first_hit_turn'] is None:
                    self.current_game_stats['first_hit_turn'] = int(self.current_game_stats['turn_count'])
            if sunk:
                self.current_game_stats['ships_sunk_by_player'] += 1
                if self.current_game_stats['first_sink_turn'] is None:
                    self.current_game_stats['first_sink_turn'] = int(self.current_game_stats['turn_count'])
        else:
            self.current_game_stats['ai_shots'] += 1
            if hit:
                self.current_game_stats['ai_hits'] += 1
            if sunk:
                self.current_game_stats['ships_sunk_by_ai'] += 1
    
    def end_game(self, player_won: bool):
        """End the current game and save stats"""
        if not self.current_game_stats:
            return
            
        # Calculate final stats
        duration = (datetime.now() - self.current_game_stats['start_time']).total_seconds()
        
        player_accuracy = (self.current_game_stats['player_hits'] / 
                         self.current_game_stats['player_shots'] 
                         if self.current_game_stats['player_shots'] > 0 else 0)
        
        ai_accuracy = (self.current_game_stats['ai_hits'] / 
                      self.current_game_stats['ai_shots'] 
                      if self.current_game_stats['ai_shots'] > 0 else 0)
        
        # Create game stats
        game_stats = GameStats(
            game_id=self.current_game_stats['game_id'],
            timestamp=self.current_game_stats['timestamp'],
            ai_difficulty=self.current_game_stats['ai_difficulty'],
            player_won=player_won,
            total_turns=int(self.current_game_stats['turn_count']),
            player_shots=self.current_game_stats['player_shots'],
            player_hits=self.current_game_stats['player_hits'],
            player_accuracy=player_accuracy,
            ai_shots=self.current_game_stats['ai_shots'],
            ai_hits=self.current_game_stats['ai_hits'],
            ai_accuracy=ai_accuracy,
            game_duration=duration,
            ships_sunk_by_player=self.current_game_stats['ships_sunk_by_player'],
            ships_sunk_by_ai=self.current_game_stats['ships_sunk_by_ai'],
            first_hit_turn=self.current_game_stats['first_hit_turn'],
            first_sink_turn=self.current_game_stats['first_sink_turn']
        )
        
        self.game_history.append(game_stats)
        self.save_stats()
        
        # Clear current game
        self.current_game_stats = {}
        
        logger.info(f"Game ended - Player {'won' if player_won else 'lost'} "
                   f"(Accuracy: Player {player_accuracy:.1%}, AI {ai_accuracy:.1%})")
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics across all games"""
        if not self.game_history:
            return {}
            
        summary = {
            'total_games': len(self.game_history),
            'by_difficulty': {}
        }
        
        # Group by difficulty
        for difficulty in DEFAULT_CONFIGS.keys():
            games = [g for g in self.game_history if g.ai_difficulty == difficulty]
            
            if games:
                wins = sum(1 for g in games if g.player_won)
                total = len(games)
                
                summary['by_difficulty'][difficulty] = {
                    'games_played': total,
                    'player_wins': wins,
                    'ai_wins': total - wins,
                    'win_rate': wins / total if total > 0 else 0,
                    'avg_player_accuracy': sum(g.player_accuracy for g in games) / total,
                    'avg_ai_accuracy': sum(g.ai_accuracy for g in games) / total,
                    'avg_game_duration': sum(g.game_duration for g in games) / total,
                    'avg_turns': sum(g.total_turns for g in games) / total
                }
        
        return summary
    
    def get_ai_recommendation(self) -> str:
        """Recommend AI difficulty based on player performance"""
        summary = self.get_summary_stats()
        
        if not summary:
            return "medium"  # Default for new players
            
        # Calculate overall win rate
        total_games = summary['total_games']
        if total_games < 5:
            return "medium"  # Not enough data
            
        # Check recent performance
        recent_games = self.game_history[-10:]  # Last 10 games
        recent_wins = sum(1 for g in recent_games if g.player_won)
        recent_win_rate = recent_wins / len(recent_games)
        
        # Recommend based on win rate
        if recent_win_rate > 0.8:
            # Player is dominating, increase difficulty
            current_difficulties = [g.ai_difficulty for g in recent_games]
            if "master" in current_difficulties:
                return "nightmare"
            elif "expert" in current_difficulties:
                return "master"
            elif "hard" in current_difficulties:
                return "expert"
            elif "medium" in current_difficulties:
                return "hard"
            else:
                return "medium"
                
        elif recent_win_rate < 0.2:
            # Player is struggling, decrease difficulty
            current_difficulties = [g.ai_difficulty for g in recent_games]
            if "nightmare" in current_difficulties:
                return "master"
            elif "master" in current_difficulties:
                return "expert"
            elif "expert" in current_difficulties:
                return "hard"
            elif "hard" in current_difficulties:
                return "medium"
            elif "medium" in current_difficulties:
                return "easy"
            else:
                return "easy"
        else:
            # Win rate is balanced, keep current difficulty
            return recent_games[-1].ai_difficulty


class AIConfigManager:
    """Manage AI configurations"""
    
    def __init__(self, config_file: str = "ai_config.json"):
        self.config_file = config_file
        self.configs = DEFAULT_CONFIGS.copy()
        self.load_configs()
        
    def load_configs(self):
        """Load custom AI configurations"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                for name, config_data in data.items():
                    self.configs[name] = AIConfig(**config_data)
                    
                logger.info(f"Loaded {len(data)} AI configurations")
            except Exception as e:
                logger.error(f"Failed to load AI configs: {e}")
        
    def save_configs(self):
        """Save current configurations"""
        try:
            data = {name: asdict(config) for name, config in self.configs.items()}
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info("AI configurations saved")
        except Exception as e:
            logger.error(f"Failed to save AI configs: {e}")
    
    def get_config(self, difficulty: str) -> AIConfig:
        """Get configuration for difficulty level"""
        return self.configs.get(difficulty, self.configs["medium"])
    
    def create_custom_config(self, name: str, base_difficulty: str, **overrides) -> AIConfig:
        """Create a custom AI configuration"""
        base_config = self.configs.get(base_difficulty, self.configs["medium"])
        
        # Create new config with overrides
        config_data = asdict(base_config)
        config_data.update(overrides)
        config_data['name'] = name
        
        new_config = AIConfig(**config_data)
        self.configs[name] = new_config
        
        self.save_configs()
        return new_config


# Global instances
ai_config_manager = AIConfigManager()
ai_performance_tracker = AIPerformanceTracker()