"""
Ship Manager - Quản lý ships, ship placement và validation
"""

import pygame
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass
from game_state import game_state
import logging

logger = logging.getLogger("ShipManager")


@dataclass
class Ship:
    """Ship data structure"""
    size: int
    positions: List[Tuple[int, int]]
    vertical: bool
    image: pygame.Surface
    rect: pygame.Rect
    is_sunk: bool = False
    hits: List[Tuple[int, int]] = None
    
    def __post_init__(self):
        if self.hits is None:
            self.hits = []
    
    def is_hit_at(self, x: int, y: int) -> bool:
        """Check if ship is hit at position"""
        return (x, y) in self.positions
    
    def add_hit(self, x: int, y: int):
        """Add a hit to the ship"""
        if (x, y) in self.positions and (x, y) not in self.hits:
            self.hits.append((x, y))
            if len(self.hits) == self.size:
                self.is_sunk = True
                logger.info(f"Ship of size {self.size} has been sunk!")
    
    def get_damage_percentage(self) -> float:
        """Get ship damage percentage"""
        return len(self.hits) / self.size * 100


class DraggableShip:
    """Ship that can be dragged during placement phase"""
    def __init__(self, image_path: str, size: int, initial_pos: Tuple[int, int]):
        self.size = size
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(center=initial_pos)
        self.vertical = False
        self.dragging = False
        self.valid_placement = True
        
        # Create rotated version
        self.horizontal_image = self.image
        self.vertical_image = pygame.transform.rotate(self.image, 90)
        
    def update(self, mouse_pos: Tuple[int, int], mouse_clicked: bool,
               mouse_released: bool, keys_pressed: dict):
        """Update ship state"""
        # Check for dragging
        if self.rect.collidepoint(mouse_pos) and mouse_clicked and not self.dragging:
            self.dragging = True
            
        if self.dragging:
            self.rect.center = mouse_pos
            
            # Check for rotation
            if (keys_pressed.get(pygame.K_UP) or keys_pressed.get(pygame.K_DOWN) or
                keys_pressed.get(pygame.K_LEFT) or keys_pressed.get(pygame.K_RIGHT) or
                keys_pressed.get(pygame.K_r)):
                self.rotate()
                
        if mouse_released:
            self.dragging = False
    
    def rotate(self):
        """Rotate the ship"""
        self.vertical = not self.vertical
        
        # Swap image
        if self.vertical:
            self.image = self.vertical_image
        else:
            self.image = self.horizontal_image
            
        # Update rect keeping center position
        center = self.rect.center
        self.rect = self.image.get_rect(center=center)
        
        logger.info(f"Ship rotated - vertical: {self.vertical}")
    
    def draw(self, surface: pygame.Surface):
        """Draw the ship"""
        # Tint based on valid placement
        if self.dragging:
            if self.valid_placement:
                # Green tint for valid placement
                tinted = self.image.copy()
                tinted.fill((0, 255, 0, 50), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(tinted, self.rect)
            else:
                # Red tint for invalid placement
                tinted = self.image.copy()
                tinted.fill((255, 0, 0, 50), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(tinted, self.rect)
        else:
            surface.blit(self.image, self.rect)
    
    def snap_to_grid(self, grid_x: int, grid_y: int, cell_size: int = 35):
        """Snap ship position to grid"""
        if self.vertical:
            self.rect.x = grid_x + cell_size // 2 - self.rect.width // 2
            self.rect.y = grid_y
        else:
            self.rect.x = grid_x
            self.rect.y = grid_y + cell_size // 2 - self.rect.height // 2


class ShipManager:
    """Manages all ship-related operations"""
    
    # Standard ship sizes
    SHIP_SIZES = [5, 4, 3, 3, 2]  # Carrier, Battleship, Cruiser, Submarine, Destroyer
    SHIP_NAMES = ["Carrier", "Battleship", "Cruiser", "Submarine", "Destroyer"]
    
    def __init__(self):
        self.board_size = 10
        self.cell_size = 35
        
        # Grid positions for player board
        self.player_grid_x = 92 + 35  # Adjusted from original
        self.player_grid_y = 155
        
        # Grid positions for enemy board  
        self.enemy_grid_x = 757
        self.enemy_grid_y = 155
        
        # Ships for placement
        self.draggable_ships: List[DraggableShip] = []
        
        # Placed ships
        self.player_ships: List[Ship] = []
        self.enemy_ships: List[Ship] = []
        
        # Load ship images
        self.load_ship_images()
        
        logger.info("ShipManager initialized")
    
    def load_ship_images(self):
        """Load ship images and create draggable ships"""
        ship_files = [
            "Assets/Battleship5.png",
            "Assets/Cruiser4.png", 
            "Assets/Submarine3.png",
            "Assets/RescueShip3.png",
            "Assets/Destroyer2.png"
        ]
        
        # Create draggable ships for placement
        for i, (file, size) in enumerate(zip(ship_files, self.SHIP_SIZES)):
            try:
                ship = DraggableShip(
                    os.path.join(file),
                    size,
                    (600, 135 + 35 * i)  # Initial positions on right side
                )
                self.draggable_ships.append(ship)
            except Exception as e:
                logger.error(f"Failed to load ship image {file}: {e}")
    
    def update_placement(self, mouse_pos: Tuple[int, int], mouse_clicked: bool,
                        mouse_released: bool, keys_pressed: dict):
        """Update ship placement"""
        for ship in self.draggable_ships:
            ship.update(mouse_pos, mouse_clicked, mouse_released, keys_pressed)
            
            # Check if ship is over the grid
            if ship.dragging:
                grid_pos = self.get_grid_position(mouse_pos, True)
                if grid_pos:
                    ship.valid_placement = self.is_valid_placement(ship, grid_pos)
                else:
                    ship.valid_placement = False
    
    def draw_draggable_ships(self, surface: pygame.Surface):
        """Draw ships during placement phase"""
        for ship in self.draggable_ships:
            ship.draw(surface)
    
    def draw_placed_ships(self, surface: pygame.Surface, draw_enemy: bool = False):
        """Draw placed ships on the board"""
        # Draw player ships
        for ship in self.player_ships:
            for x, y in ship.positions:
                # Calculate pixel position
                px = self.player_grid_x + x * self.cell_size
                py = self.player_grid_y + y * self.cell_size
                
                # Draw ship part
                if (x, y) in ship.hits:
                    # Draw damaged part
                    pygame.draw.rect(surface, (139, 0, 0), 
                                   (px, py, self.cell_size, self.cell_size))
                else:
                    # Draw healthy part
                    pygame.draw.rect(surface, (100, 100, 100),
                                   (px, py, self.cell_size, self.cell_size))
                    
                # Draw ship outline
                pygame.draw.rect(surface, (0, 0, 0),
                               (px, py, self.cell_size, self.cell_size), 2)
        
        # Draw enemy ships (only if game is over or in debug mode)
        if draw_enemy or game_state.show_debug:
            for ship in self.enemy_ships:
                for x, y in ship.positions:
                    px = self.enemy_grid_x + x * self.cell_size
                    py = self.enemy_grid_y + y * self.cell_size
                    
                    # Draw with transparency
                    s = pygame.Surface((self.cell_size, self.cell_size))
                    s.set_alpha(128)
                    
                    if (x, y) in ship.hits:
                        s.fill((139, 0, 0))
                    else:
                        s.fill((100, 100, 100))
                        
                    surface.blit(s, (px, py))
                    pygame.draw.rect(surface, (0, 0, 0, 128),
                                   (px, py, self.cell_size, self.cell_size), 1)
    
    def get_grid_position(self, pixel_pos: Tuple[int, int], 
                         player_board: bool = True) -> Optional[Tuple[int, int]]:
        """Convert pixel position to grid coordinates"""
        if player_board:
            grid_x = self.player_grid_x
            grid_y = self.player_grid_y
        else:
            grid_x = self.enemy_grid_x
            grid_y = self.enemy_grid_y
            
        # Calculate grid position
        x = (pixel_pos[0] - grid_x) // self.cell_size
        y = (pixel_pos[1] - grid_y) // self.cell_size
        
        # Check if within bounds
        if 0 <= x < self.board_size and 0 <= y < self.board_size:
            return (x, y)
        return None
    
    def is_valid_placement(self, ship: DraggableShip, 
                          grid_pos: Tuple[int, int]) -> bool:
        """Check if ship placement is valid"""
        x, y = grid_pos
        positions = []
        
        # Calculate ship positions
        if ship.vertical:
            if y + ship.size > self.board_size:
                return False
            positions = [(x, y + i) for i in range(ship.size)]
        else:
            if x + ship.size > self.board_size:
                return False
            positions = [(x + i, y) for i in range(ship.size)]
        
        # Check for overlaps with existing ships
        existing_positions = set()
        for placed_ship in self.player_ships:
            existing_positions.update(placed_ship.positions)
            
        for pos in positions:
            if pos in existing_positions:
                return False
        
        # Check adjacent cells (ships can't touch)
        for pos in positions:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    check_pos = (pos[0] + dx, pos[1] + dy)
                    if check_pos in existing_positions:
                        return False
        
        return True
    
    def place_all_ships(self) -> bool:
        """Try to place all draggable ships on the board"""
        self.player_ships.clear()
        all_valid = True
        
        for i, drag_ship in enumerate(self.draggable_ships):
            # Get grid position from ship center
            grid_pos = self.get_grid_position(drag_ship.rect.center, True)
            
            if not grid_pos:
                logger.warning(f"Ship {i} is not on the grid")
                all_valid = False
                continue
                
            # Adjust grid position based on ship orientation
            x, y = grid_pos
            if drag_ship.vertical:
                # Adjust y position
                y = (drag_ship.rect.y - self.player_grid_y) // self.cell_size
            else:
                # Adjust x position  
                x = (drag_ship.rect.x - self.player_grid_x) // self.cell_size
                
            grid_pos = (x, y)
            
            if not self.is_valid_placement(drag_ship, grid_pos):
                logger.warning(f"Ship {i} has invalid placement at {grid_pos}")
                all_valid = False
                continue
            
            # Create ship positions
            positions = []
            if drag_ship.vertical:
                positions = [(x, y + j) for j in range(drag_ship.size)]
            else:
                positions = [(x + j, y) for j in range(drag_ship.size)]
            
            # Create Ship object
            ship = Ship(
                size=drag_ship.size,
                positions=positions,
                vertical=drag_ship.vertical,
                image=drag_ship.image,
                rect=drag_ship.rect.copy()
            )
            
            self.player_ships.append(ship)
            
            # Snap ship to exact grid position
            drag_ship.snap_to_grid(
                self.player_grid_x + x * self.cell_size,
                self.player_grid_y + y * self.cell_size
            )
            
            logger.info(f"Placed ship {i} at positions {positions}")
        
        if all_valid and len(self.player_ships) == len(self.SHIP_SIZES):
            # Save ship positions to game state
            game_state.player.ships = [ship.positions for ship in self.player_ships]
            game_state.player.ships_ready = True
            logger.info("All ships placed successfully")
            return True
        else:
            logger.warning("Ship placement failed")
            return False
    
    def generate_random_enemy_ships(self):
        """Generate random ship positions for AI/enemy"""
        import random
        
        self.enemy_ships.clear()
        ships_to_place = self.SHIP_SIZES.copy()
        
        max_attempts = 1000
        attempts = 0
        
        while ships_to_place and attempts < max_attempts:
            attempts += 1
            
            size = ships_to_place[0]
            vertical = random.choice([True, False])
            
            if vertical:
                x = random.randint(0, self.board_size - 1)
                y = random.randint(0, self.board_size - size)
                positions = [(x, y + i) for i in range(size)]
            else:
                x = random.randint(0, self.board_size - size)
                y = random.randint(0, self.board_size - 1)
                positions = [(x + i, y) for i in range(size)]
            
            # Check validity
            valid = True
            existing_positions = set()
            
            for ship in self.enemy_ships:
                existing_positions.update(ship.positions)
                
            # Check overlap
            for pos in positions:
                if pos in existing_positions:
                    valid = False
                    break
                    
            # Check adjacent cells
            if valid:
                for pos in positions:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            check_pos = (pos[0] + dx, pos[1] + dy)
                            if check_pos in existing_positions:
                                valid = False
                                break
                    if not valid:
                        break
            
            if valid:
                # Create ship
                ship = Ship(
                    size=size,
                    positions=positions,
                    vertical=vertical,
                    image=None,  # Enemy ships don't need images
                    rect=pygame.Rect(0, 0, 0, 0)
                )
                self.enemy_ships.append(ship)
                ships_to_place.pop(0)
                logger.info(f"Placed enemy ship of size {size} at {positions}")
        
        if ships_to_place:
            logger.error("Failed to place all enemy ships!")
            return False
            
        # Save to game state
        game_state.opponent.ships = [ship.positions for ship in self.enemy_ships]
        game_state.opponent.ships_ready = True
        
        return True
    
    def handle_shot(self, x: int, y: int, is_player_shot: bool) -> Tuple[bool, bool, int]:
        """
        Handle a shot at position (x, y)
        Returns: (hit, sunk, ship_size)
        """
        if is_player_shot:
            # Player shooting at enemy
            ships = self.enemy_ships
        else:
            # Enemy shooting at player
            ships = self.player_ships
            
        for ship in ships:
            if ship.is_hit_at(x, y):
                ship.add_hit(x, y)
                
                if ship.is_sunk:
                    logger.info(f"Ship sunk! Size: {ship.size}")
                    return True, True, ship.size
                else:
                    return True, False, 0
                    
        return False, False, 0
    
    def check_game_over(self) -> Optional[str]:
        """
        Check if game is over
        Returns: "player" if player wins, "enemy" if enemy wins, None if game continues
        """
        # Check if all enemy ships are sunk
        enemy_sunk = bool(self.enemy_ships) and all(ship.is_sunk for ship in self.enemy_ships)
        if enemy_sunk:
            return "player"
            
        # Check if all player ships are sunk
        player_sunk = bool(self.player_ships) and all(ship.is_sunk for ship in self.player_ships)
        if player_sunk:
            return "enemy"
            
        return None
    
    def get_ship_at_position(self, x: int, y: int, 
                           check_player: bool = True) -> Optional[Ship]:
        """Get ship at given position"""
        ships = self.player_ships if check_player else self.enemy_ships
        
        for ship in ships:
            if (x, y) in ship.positions:
                return ship
        return None