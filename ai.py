"""
Enhanced AI System for Battleship
Includes improved algorithms, pattern recognition, and adaptive strategies
"""

import random
import math
import numpy as np
from collections import defaultdict, deque
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass
from enum import Enum
import logging

# Try to import game_state if available
try:
    from game_state import game_state
except ImportError:
    game_state = None

logger = logging.getLogger("AI")


class ShotPattern(Enum):
    """Common shot patterns for analysis"""
    RANDOM = "random"
    DIAGONAL = "diagonal"
    CHECKERBOARD = "checkerboard"
    SPIRAL = "spiral"
    EDGES_FIRST = "edges_first"
    CENTER_FIRST = "center_first"


@dataclass
class ShipInfo:
    """Information about a ship"""
    size: int
    hits: List[Tuple[int, int]]
    orientation: Optional[str] = None  # 'horizontal' or 'vertical'
    sunk: bool = False
    
    def is_fully_hit(self) -> bool:
        return len(self.hits) >= self.size


class BaseAI:
    """Enhanced base class for all AI implementations"""
    
    def __init__(self, board_size=10):
        self.board_size = board_size
        self.shots_fired: List[Tuple[int, int]] = []
        self.hits: List[Tuple[int, int]] = []
        self.misses: List[Tuple[int, int]] = []
        self.ships_sunk: List[ShipInfo] = []
        self.possible_targets = [(x, y) for x in range(board_size) 
                               for y in range(board_size)]
        self.ship_sizes = [5, 4, 3, 3, 2]
        self.remaining_ship_sizes = self.ship_sizes.copy()
        
        # Enhanced tracking
        self.current_targets: List[Tuple[int, int]] = []
        self.ship_segments: List[List[Tuple[int, int]]] = []
        self.heat_map = np.zeros((board_size, board_size))
        self.last_shot_result = None
        
    def update_after_guess(self, x: int, y: int, is_hit: bool, 
                          is_sunk: bool = False, sunk_ship_size: Optional[int] = None):
        """Update AI state after a guess"""
        self.shots_fired.append((x, y))
        
        if is_hit:
            self.hits.append((x, y))
            self.last_shot_result = "hit"
            
            if is_sunk and sunk_ship_size:
                # Find which ship was sunk
                ship_hits = self._find_ship_from_last_hit(x, y, sunk_ship_size)
                if ship_hits:
                    ship_info = ShipInfo(
                        size=sunk_ship_size,
                        hits=ship_hits,
                        sunk=True
                    )
                    self.ships_sunk.append(ship_info)
                    
                    # Remove ship size from remaining
                    if sunk_ship_size in self.remaining_ship_sizes:
                        self.remaining_ship_sizes.remove(sunk_ship_size)
                    
                    # Clear targets around sunk ship
                    self._clear_adjacent_targets(ship_hits)
        else:
            self.misses.append((x, y))
            self.last_shot_result = "miss"
        
        # Remove from possible targets
        if (x, y) in self.possible_targets:
            self.possible_targets.remove((x, y))
        
        # Update heat map
        self._update_heat_map()
    
    def make_guess(self) -> Optional[Tuple[int, int]]:
        """Make a guess - should be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement make_guess")
    
    def _find_ship_from_last_hit(self, x: int, y: int, size: int) -> List[Tuple[int, int]]:
        """Find ship positions from the last hit"""
        # Use BFS to find connected hits
        visited = set()
        queue = deque([(x, y)])
        ship_hits = []
        
        while queue and len(ship_hits) < size:
            cx, cy = queue.popleft()
            if (cx, cy) in visited:
                continue
                
            visited.add((cx, cy))
            
            if (cx, cy) in self.hits:
                ship_hits.append((cx, cy))
                
                # Add adjacent positions
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < self.board_size and 0 <= ny < self.board_size 
                        and (nx, ny) not in visited):
                        queue.append((nx, ny))
        
        return ship_hits if len(ship_hits) == size else []
    
    def _clear_adjacent_targets(self, ship_positions: List[Tuple[int, int]]):
        """Remove positions adjacent to ship from targets"""
        for x, y in ship_positions:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < self.board_size and 0 <= ny < self.board_size
                        and (nx, ny) in self.possible_targets):
                        self.possible_targets.remove((nx, ny))
    
    def _update_heat_map(self):
        """Update probability heat map"""
        self.heat_map.fill(0)
        
        # Add probabilities for each remaining ship
        for ship_size in self.remaining_ship_sizes:
            # Horizontal placements
            for y in range(self.board_size):
                for x in range(self.board_size - ship_size + 1):
                    if self._can_place_ship(x, y, ship_size, horizontal=True):
                        for i in range(ship_size):
                            self.heat_map[y][x + i] += 1
            
            # Vertical placements
            for y in range(self.board_size - ship_size + 1):
                for x in range(self.board_size):
                    if self._can_place_ship(x, y, ship_size, horizontal=False):
                        for i in range(ship_size):
                            self.heat_map[y + i][x] += 1
    
    def _can_place_ship(self, x: int, y: int, size: int, horizontal: bool) -> bool:
        """Check if ship can be placed at position"""
        positions = []
        if horizontal:
            positions = [(x + i, y) for i in range(size)]
        else:
            positions = [(x, y + i) for i in range(size)]
        
        # Check if any position is a miss or out of bounds
        for px, py in positions:
            if px >= self.board_size or py >= self.board_size:
                return False
            if (px, py) in self.misses:
                return False
        
        # Check if placement is consistent with hits
        hit_count = sum(1 for px, py in positions if (px, py) in self.hits)
        
        # If we have hits, the ship must include them
        if hit_count > 0:
            # Check if all hits in this line are part of the same ship
            line_hits = [(px, py) for px, py in positions if (px, py) in self.hits]
            if len(line_hits) > 1:
                # Check continuity
                if horizontal:
                    xs = sorted([px for px, py in line_hits])
                    if xs[-1] - xs[0] != len(xs) - 1:
                        return False
                else:
                    ys = sorted([py for px, py in line_hits])
                    if ys[-1] - ys[0] != len(ys) - 1:
                        return False
        
        return True
    
    def _get_adjacent_positions(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid adjacent positions"""
        adjacent = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < self.board_size and 0 <= ny < self.board_size
                and (nx, ny) in self.possible_targets):
                adjacent.append((nx, ny))
        return adjacent


class ImprovedHuntTargetAI(BaseAI):
    """Enhanced Hunt-Target AI with pattern recognition"""
    
    def __init__(self, board_size=10):
        super().__init__(board_size)
        self.hunt_pattern = ShotPattern.CHECKERBOARD
        self.target_mode = False
        self.current_ship_hits: List[Tuple[int, int]] = []
        self.priority_targets: List[Tuple[int, int]] = []
        
    def make_guess(self) -> Optional[Tuple[int, int]]:
        if not self.possible_targets:
            return None
        
        # If we have priority targets from a hit ship
        if self.priority_targets:
            while self.priority_targets:
                target = self.priority_targets.pop(0)
                if target in self.possible_targets:
                    return target
        
        # If we have unsunk hits, target around them
        unsunk_hits = [hit for hit in self.hits 
                      if not any(hit in ship.hits for ship in self.ships_sunk)]
        
        if unsunk_hits:
            return self._target_mode(unsunk_hits)
        
        # Otherwise, hunt mode
        return self._hunt_mode()
    
    def _hunt_mode(self) -> Tuple[int, int]:
        """Hunt for ships using patterns"""
        if self.hunt_pattern == ShotPattern.CHECKERBOARD:
            # Checkerboard pattern
            candidates = [(x, y) for x, y in self.possible_targets 
                         if (x + y) % 2 == 0]
            
            if not candidates:
                candidates = self.possible_targets
        
        elif self.hunt_pattern == ShotPattern.DIAGONAL:
            # Diagonal pattern
            candidates = []
            for d in range(self.board_size * 2):
                for x in range(self.board_size):
                    y = d - x
                    if 0 <= y < self.board_size and (x, y) in self.possible_targets:
                        candidates.append((x, y))
                if candidates:
                    break
        
        elif self.hunt_pattern == ShotPattern.SPIRAL:
            # Spiral from center
            center = self.board_size // 2
            candidates = sorted(self.possible_targets,
                              key=lambda p: abs(p[0] - center) + abs(p[1] - center))
        
        else:
            candidates = self.possible_targets
        
        # Use heat map to choose best candidate
        if candidates:
            return max(candidates, key=lambda p: self.heat_map[p[1]][p[0]])
        
        return random.choice(self.possible_targets)
    
    def _target_mode(self, unsunk_hits: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Target mode - focus on sinking ships"""
        # Group hits into potential ships
        ship_groups = self._group_hits(unsunk_hits)
        
        for group in ship_groups:
            if len(group) >= 2:
                # Determine orientation
                if all(y == group[0][1] for x, y in group):
                    # Horizontal ship
                    xs = [x for x, y in group]
                    min_x, max_x = min(xs), max(xs)
                    y = group[0][1]
                    
                    # Try ends
                    if min_x > 0 and (min_x - 1, y) in self.possible_targets:
                        return (min_x - 1, y)
                    if max_x < self.board_size - 1 and (max_x + 1, y) in self.possible_targets:
                        return (max_x + 1, y)
                
                elif all(x == group[0][0] for x, y in group):
                    # Vertical ship
                    ys = [y for x, y in group]
                    min_y, max_y = min(ys), max(ys)
                    x = group[0][0]
                    
                    # Try ends
                    if min_y > 0 and (x, min_y - 1) in self.possible_targets:
                        return (x, min_y - 1)
                    if max_y < self.board_size - 1 and (x, max_y + 1) in self.possible_targets:
                        return (x, max_y + 1)
        
        # For single hits, try all adjacent
        for hit in unsunk_hits:
            adjacents = self._get_adjacent_positions(hit[0], hit[1])
            if adjacents:
                # Prioritize based on heat map
                return max(adjacents, key=lambda p: self.heat_map[p[1]][p[0]])
        
        # Fallback to hunt mode
        return self._hunt_mode()
    
    def _group_hits(self, hits: List[Tuple[int, int]]) -> List[List[Tuple[int, int]]]:
        """Group hits into potential ships"""
        if not hits:
            return []
        
        groups = []
        used = set()
        
        for hit in hits:
            if hit in used:
                continue
            
            # Start new group
            group = [hit]
            used.add(hit)
            
            # Find connected hits
            changed = True
            while changed:
                changed = False
                for other in hits:
                    if other in used:
                        continue
                    
                    # Check if connected to group
                    for member in group:
                        if (abs(other[0] - member[0]) == 1 and other[1] == member[1]) or \
                           (abs(other[1] - member[1]) == 1 and other[0] == member[0]):
                            group.append(other)
                            used.add(other)
                            changed = True
                            break
            
            groups.append(sorted(group))
        
        return groups


class AdaptiveAI(BaseAI):
    """AI that adapts to opponent's placement patterns"""
    
    def __init__(self, board_size=10):
        super().__init__(board_size)
        self.opponent_patterns = defaultdict(float)
        self.games_played = 0
        self.pattern_weights = {
            'edge_preference': 0.5,
            'center_preference': 0.5,
            'cluster_ships': 0.5,
            'spread_ships': 0.5,
            'diagonal_placement': 0.5
        }
        
    def make_guess(self) -> Optional[Tuple[int, int]]:
        if not self.possible_targets:
            return None
        
        # Calculate weighted probabilities
        probabilities = {}
        
        for x, y in self.possible_targets:
            prob = self.heat_map[y][x]
            
            # Adjust based on learned patterns
            if self._is_edge(x, y):
                prob *= self.pattern_weights['edge_preference']
            else:
                prob *= self.pattern_weights['center_preference']
            
            # Boost corners slightly if edge preference is high
            if self._is_corner(x, y) and self.pattern_weights['edge_preference'] > 0.7:
                prob *= 1.2
            
            probabilities[(x, y)] = prob
        
        # Add randomness to avoid being predictable
        if random.random() < 0.1:  # 10% random shots
            return random.choice(self.possible_targets)
        
        # Choose highest probability
        best_targets = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        
        # Select from top candidates with some randomness
        top_count = min(5, len(best_targets))
        weights = [1.0 / (i + 1) for i in range(top_count)]
        
        selected_idx = random.choices(range(top_count), weights=weights)[0]
        return best_targets[selected_idx][0]
    
    def learn_from_game(self, enemy_ship_positions: List[List[Tuple[int, int]]]):
        """Learn from opponent's ship placement after game"""
        self.games_played += 1
        
        # Analyze patterns
        edge_ships = 0
        clustered_ships = 0
        
        all_positions = []
        for ship in enemy_ship_positions:
            all_positions.extend(ship)
            
            # Check if ship is on edge
            if any(self._is_edge(x, y) for x, y in ship):
                edge_ships += 1
        
        # Update pattern weights with exponential moving average
        alpha = 0.2  # Learning rate
        
        edge_ratio = edge_ships / len(enemy_ship_positions)
        self.pattern_weights['edge_preference'] = (
            alpha * edge_ratio + (1 - alpha) * self.pattern_weights['edge_preference']
        )
        self.pattern_weights['center_preference'] = 1.0 - self.pattern_weights['edge_preference']
        
        # Check clustering
        for ship1 in enemy_ship_positions:
            for ship2 in enemy_ship_positions:
                if ship1 != ship2:
                    if self._ships_are_close(ship1, ship2):
                        clustered_ships += 1
                        break
        
        cluster_ratio = clustered_ships / len(enemy_ship_positions)
        self.pattern_weights['cluster_ships'] = (
            alpha * cluster_ratio + (1 - alpha) * self.pattern_weights['cluster_ships']
        )
        self.pattern_weights['spread_ships'] = 1.0 - self.pattern_weights['cluster_ships']
        
        logger.info(f"Updated pattern weights after game {self.games_played}: {self.pattern_weights}")
    
    def _is_edge(self, x: int, y: int) -> bool:
        """Check if position is on edge"""
        return x == 0 or x == self.board_size - 1 or y == 0 or y == self.board_size - 1
    
    def _is_corner(self, x: int, y: int) -> bool:
        """Check if position is corner"""
        return (x == 0 or x == self.board_size - 1) and (y == 0 or y == self.board_size - 1)
    
    def _ships_are_close(self, ship1: List[Tuple[int, int]], 
                        ship2: List[Tuple[int, int]]) -> bool:
        """Check if two ships are close to each other"""
        for x1, y1 in ship1:
            for x2, y2 in ship2:
                if abs(x1 - x2) <= 2 and abs(y1 - y2) <= 2:
                    return True
        return False


class MonteCarloTreeSearchAI(BaseAI):
    """Enhanced MCTS AI with better simulation"""
    
    def __init__(self, board_size=10, simulations=100, time_limit=2.0):
        super().__init__(board_size)
        self.simulations = simulations
        self.time_limit = time_limit
        
    def make_guess(self) -> Optional[Tuple[int, int]]:
        if not self.possible_targets:
            return None
        
        # For early game or when few targets remain, use simple strategy
        if len(self.shots_fired) < 5 or len(self.possible_targets) < 10:
            return self._simple_guess()
        
        # MCTS for complex situations
        import time
        start_time = time.time()
        
        # Initialize visit counts and wins
        visit_counts = defaultdict(int)
        win_scores = defaultdict(float)
        
        simulations_run = 0
        
        while (simulations_run < self.simulations and 
               time.time() - start_time < self.time_limit):
            
            # Select a position to simulate
            position = self._select_position(visit_counts, win_scores)
            
            # Simulate game from this position
            score = self._simulate_from_position(position)
            
            # Update statistics
            visit_counts[position] += 1
            win_scores[position] += score
            
            simulations_run += 1
        
        # Choose position with best average score
        best_position = None
        best_avg_score = -1
        
        for pos in visit_counts:
            if visit_counts[pos] > 0:
                avg_score = win_scores[pos] / visit_counts[pos]
                if avg_score > best_avg_score:
                    best_avg_score = avg_score
                    best_position = pos
        
        return best_position if best_position else random.choice(self.possible_targets)
    
    def _simple_guess(self) -> Tuple[int, int]:
        """Simple guess for early game"""
        # If we have hits, target around them
        unsunk_hits = [hit for hit in self.hits 
                      if not any(hit in ship.hits for ship in self.ships_sunk)]
        
        if unsunk_hits:
            for hit in unsunk_hits:
                adjacents = self._get_adjacent_positions(hit[0], hit[1])
                if adjacents:
                    return random.choice(adjacents)
        
        # Otherwise use heat map
        best_positions = []
        best_heat = -1
        
        for x, y in self.possible_targets:
            heat = self.heat_map[y][x]
            if heat > best_heat:
                best_heat = heat
                best_positions = [(x, y)]
            elif heat == best_heat:
                best_positions.append((x, y))
        
        return random.choice(best_positions) if best_positions else random.choice(self.possible_targets)
    
    def _select_position(self, visit_counts: Dict, win_scores: Dict) -> Tuple[int, int]:
        """Select position using UCB1"""
        total_visits = sum(visit_counts.values())
        
        if total_visits == 0:
            return random.choice(self.possible_targets)
        
        c = math.sqrt(2)  # Exploration constant
        best_score = -1
        best_positions = []
        
        for pos in self.possible_targets:
            if visit_counts[pos] == 0:
                # Unvisited positions get high priority
                score = float('inf')
            else:
                # UCB1 formula
                avg_score = win_scores[pos] / visit_counts[pos]
                exploration = c * math.sqrt(math.log(total_visits) / visit_counts[pos])
                score = avg_score + exploration
            
            if score > best_score:
                best_score = score
                best_positions = [pos]
            elif score == best_score:
                best_positions.append(pos)
        
        return random.choice(best_positions)
    
    def _simulate_from_position(self, position: Tuple[int, int]) -> float:
        """Simulate game from position and return score"""
        # Create simulation state
        sim_hits = self.hits.copy()
        sim_misses = self.misses.copy()
        sim_remaining_ships = self.remaining_ship_sizes.copy()
        sim_targets = self.possible_targets.copy()
        
        # Simulate this shot
        x, y = position
        hit_probability = self._calculate_hit_probability(x, y)
        is_hit = random.random() < hit_probability
        
        if is_hit:
            sim_hits.append((x, y))
        else:
            sim_misses.append((x, y))
        
        sim_targets.remove((x, y))
        
        # Continue simulation with random play
        shots_taken = 1
        ships_sunk = 0
        
        while sim_targets and sim_remaining_ships and shots_taken < 50:
            # Simple random targeting
            if sim_hits:
                # Target around hits
                target = None
                for hit in sim_hits:
                    adjacents = [(hit[0] + dx, hit[1] + dy) 
                               for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]
                               if (hit[0] + dx, hit[1] + dy) in sim_targets]
                    if adjacents:
                        target = random.choice(adjacents)
                        break
                
                if not target:
                    target = random.choice(sim_targets)
            else:
                target = random.choice(sim_targets)
            
            sim_targets.remove(target)
            shots_taken += 1
            
            # Simulate hit (simplified)
            if random.random() < 0.3:  # 30% hit rate
                sim_hits.append(target)
                
                # Check if ship sunk (simplified)
                if random.random() < 0.2:  # 20% chance to sink
                    ships_sunk += 1
                    if sim_remaining_ships:
                        sim_remaining_ships.pop()
        
        # Calculate score
        # Lower shots is better, more ships sunk is better
        if not sim_remaining_ships:
            score = 100 / shots_taken
        else:
            score = (ships_sunk * 10) / shots_taken
        
        return score
    
    def _calculate_hit_probability(self, x: int, y: int) -> float:
        """Calculate probability of hit at position"""
        # Use heat map as base probability
        base_prob = self.heat_map[y][x] / (max(self.heat_map.flatten()) + 0.1)
        
        # Boost if near existing hits
        near_hit_bonus = 0
        for hx, hy in self.hits:
            distance = abs(x - hx) + abs(y - hy)
            if distance == 1:
                near_hit_bonus += 0.3
            elif distance == 2:
                near_hit_bonus += 0.1
        
        return min(0.9, base_prob + near_hit_bonus)


class NeuralNetworkAI(BaseAI):
    """AI using simple neural network for position evaluation"""
    
    def __init__(self, board_size=10):
        super().__init__(board_size)
        # Simple 3-layer network
        self.input_size = board_size * board_size * 3  # 3 channels
        self.hidden_size = 128
        self.output_size = board_size * board_size
        
        # Initialize weights (simplified, no training)
        self._initialize_network()
        
    def _initialize_network(self):
        """Initialize network weights"""
        # Random initialization
        self.w1 = np.random.randn(self.input_size, self.hidden_size) * 0.1
        self.b1 = np.zeros(self.hidden_size)
        self.w2 = np.random.randn(self.hidden_size, self.output_size) * 0.1
        self.b2 = np.zeros(self.output_size)
    
    def make_guess(self) -> Optional[Tuple[int, int]]:
        if not self.possible_targets:
            return None
        
        # Create input features
        features = self._create_features()
        
        # Forward pass
        scores = self._forward(features)
        
        # Mask invalid positions
        for y in range(self.board_size):
            for x in range(self.board_size):
                if (x, y) not in self.possible_targets:
                    scores[y * self.board_size + x] = -float('inf')
        
        # Choose best position
        best_idx = np.argmax(scores)
        x = best_idx % self.board_size
        y = best_idx // self.board_size
        
        return (x, y)
    
    def _create_features(self) -> np.ndarray:
        """Create feature vector from game state"""
        features = np.zeros((self.board_size, self.board_size, 3))
        
        # Channel 0: Hits
        for x, y in self.hits:
            features[y, x, 0] = 1.0
        
        # Channel 1: Misses
        for x, y in self.misses:
            features[y, x, 1] = 1.0
        
        # Channel 2: Heat map (normalized)
        max_heat = np.max(self.heat_map)
        if max_heat > 0:
            features[:, :, 2] = self.heat_map / max_heat
        
        # Flatten
        return features.flatten()
    
    def _forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through network"""
        # Layer 1
        z1 = np.dot(x, self.w1) + self.b1
        a1 = np.maximum(0, z1)  # ReLU
        
        # Layer 2
        z2 = np.dot(a1, self.w2) + self.b2
        
        # Softmax
        exp_z = np.exp(z2 - np.max(z2))
        return exp_z / np.sum(exp_z)


# Factory function to create AI instances
def create_ai(difficulty: str, board_size: int = 10) -> BaseAI:
    """Create AI instance based on difficulty"""
    ai_map = {
        "easy": lambda: BaseAI(board_size),  # Random
        "medium": lambda: ImprovedHuntTargetAI(board_size),
        "hard": lambda: AdaptiveAI(board_size),
        "expert": lambda: MonteCarloTreeSearchAI(board_size, simulations=200),
        "master": lambda: NeuralNetworkAI(board_size),
        "nightmare": lambda: MonteCarloTreeSearchAI(board_size, simulations=500, time_limit=5.0)
    }
    
    ai_class = ai_map.get(difficulty, ai_map["medium"])
    return ai_class()


# Analysis tools for debugging
class AIAnalyzer:
    """Tools for analyzing AI performance"""
    
    @staticmethod
    def visualize_heat_map(ai: BaseAI) -> str:
        """Create ASCII visualization of heat map"""
        if not hasattr(ai, 'heat_map'):
            return "No heat map available"
        
        output = "Heat Map:\n"
        output += "  0 1 2 3 4 5 6 7 8 9\n"
        
        max_heat = np.max(ai.heat_map)
        
        for y in range(ai.board_size):
            output += f"{chr(65 + y)} "
            for x in range(ai.board_size):
                heat = ai.heat_map[y][x]
                
                if (x, y) in ai.hits:
                    output += "X "
                elif (x, y) in ai.misses:
                    output += "- "
                elif (x, y) not in ai.possible_targets:
                    output += ". "
                else:
                    # Show heat level
                    if max_heat > 0:
                        level = int((heat / max_heat) * 9)
                        output += f"{level} "
                    else:
                        output += "0 "
            output += "\n"
        
        return output
    
    @staticmethod
    def get_ai_stats(ai: BaseAI) -> Dict[str, any]:
        """Get AI statistics"""
        total_shots = len(ai.shots_fired)
        hits = len(ai.hits)
        misses = len(ai.misses)
        
        return {
            "total_shots": total_shots,
            "hits": hits,
            "misses": misses,
            "accuracy": hits / total_shots if total_shots > 0 else 0,
            "ships_sunk": len(ai.ships_sunk),
            "remaining_targets": len(ai.possible_targets),
            "remaining_ships": ai.remaining_ship_sizes
        }