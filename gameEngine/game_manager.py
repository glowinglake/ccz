import pygame
import os
from collections import deque
from .chapter_manager import get_chapter_by_id

class GameManager:
    def __init__(self, chapters_data, game_state):
        self.chapters_data = chapters_data
        self.game_state = game_state

        self.font = pygame.font.SysFont(None, 30)
        self.message = ""

        # GRID MODE attributes
        self.current_grid_data = None      # Stores {width, height, bgImage, ...}
        self.grid_background = None        # Pygame.Surface or None
        self.grid_units = []              # List of dicts for all units (player + enemy)
        self.selected_unit = None         # The currently selected player unit
        self.reachable_tiles = []         # List of (x,y) tiles the selected unit can move to
        self.tile_size = 32               # Each grid cell is 32x32 pixels

        # Turn Tracking
        self.isPlayerTurn = True          # True = player turn, False = enemy turn
        self.grid_currentTurn = 1         # Increments each time enemy turn ends
        self.grid_maxTurns = 10           # Fetched from chapter config

        # pop-up menu
        self.context_menu = {      # A simple dict to track the tiny popup menu
            "visible": False,       # Whether the menu is shown
            "x": 0,                 # Pixel position on screen
            "y": 0,
            "attackEnabled": False  # If Attack is greyed out or not
        }

        self.isAttacking = False       # True if we're currently selecting an enemy tile to attack
        self.attackable_tiles = []       # The coordinates of adjacent enemies for the selected unit**

    def start_chapter(self):
        """Load the current chapter and trigger any 'onStart' events."""
        chapter_id = self.game_state.currentChapterId
        chapter = get_chapter_by_id(self.chapters_data, chapter_id)
        if not chapter:
            self.message = f"No chapter found with ID {chapter_id}"
            return
        # Trigger "onStart" events if any
        self.trigger_events(chapter, "onStart")
        self.message = f"Chapter {chapter_id} started: {chapter.get('title')}"

    def start_grid_mode(self):
        """
        Prepare the data for the grid-based campaign:
        - load background image
        - read positions for player/enemy units
        - reset any 'turn/movement' flags
        """
        chapter_id = self.game_state.currentChapterId
        chapter = get_chapter_by_id(self.chapters_data, chapter_id)
        if not chapter:
            self.message = f"No chapter found with ID {chapter_id}"
            return

        grid_info = chapter.get("grid", {})
        self.current_grid_data = grid_info

        # Attempt to load bgImage
        bg_path = grid_info.get("bgImage")
        self.grid_background = None
        if bg_path and os.path.exists(bg_path):
            try:
                img = pygame.image.load(bg_path).convert()
                # Scale to (width * tileSize, height * tileSize)
                desired_w = grid_info["width"] * self.tile_size
                desired_h = grid_info["height"] * self.tile_size
                self.grid_background = pygame.transform.scale(img, (desired_w, desired_h))
            except Exception as e:
                print(f"Failed to load background image: {e}")

        # Combine playerUnits & enemyUnits into a single list
        self.grid_units = []
        player_units = grid_info.get("playerUnits", [])
        for pu in player_units:
            unit_copy = dict(pu)
            unit_copy["side"] = "player"
            # Add HP, attack, etc. if missing
            unit_copy.setdefault("HP", 20)
            unit_copy.setdefault("attack", 5)
            # Track if unit has moved this turn
            unit_copy["hasMoved"] = False  
            self.grid_units.append(unit_copy)

        enemy_units = grid_info.get("enemyUnits", [])
        for eu in enemy_units:
            unit_copy = dict(eu)
            unit_copy["side"] = "enemy"
            unit_copy.setdefault("HP", 15)
            unit_copy.setdefault("attack", 3)
            self.grid_units.append(unit_copy)

        self.selected_unit = None
        self.reachable_tiles = []
        self.message = f"Entered Grid Mode for Chapter {chapter_id}"
    
    def end_turn(self):
        """
        Switch between Player Turn and Enemy Turn.
        If we are on Enemy Turn -> end enemy turn, move to next player turn, 
        increment turn counter.
        If we are on Player Turn -> end player turn, switch to enemy turn.
        Reset 'hasMoved' flags for whichever side is active next.
        """
        if self.isPlayerTurn:
            # We end Player Turn -> go to Enemy Turn
            self.isPlayerTurn = False
            self.message = "Switched to Enemy Turn"
            # Reset enemy hasMoved flags
            for u in self.grid_units:
                if u["side"] == "enemy":
                    u["hasMoved"] = False
        else:
            # We end Enemy Turn -> go to next Player Turn
            self.isPlayerTurn = True
            self.grid_currentTurn += 1
            self.message = f"New Player Turn (Turn {self.grid_currentTurn})"
            # Reset player hasMoved flags
            for u in self.grid_units:
                if u["side"] == "player":
                    u["hasMoved"] = False

    def show_context_menu(self, pixel_x, pixel_y, can_attack):
        """
        Opens the small menu at (pixel_x, pixel_y).
        'can_attack' = True if there's an adjacent enemy, else False.
        """
        self.context_menu["visible"] = True
        self.context_menu["x"] = pixel_x
        self.context_menu["y"] = pixel_y
        self.context_menu["attackEnabled"] = can_attack
        self.isAttacking = False
        self.attackable_tiles = []

    def handle_grid_click(self, mouse_pos):
        # Convert pixel to grid coords
        grid_x = mouse_pos[0] // self.tile_size
        grid_y = mouse_pos[1] // self.tile_size
        
        if self.isAttacking:
            # Check if the click is on an attackable tile
            if (grid_x, grid_y) in self.attackable_tiles:
                # Perform the attack
                defender = self.get_unit_at(grid_x, grid_y)
                if defender:
                    self.attack_unit(self.selected_unit, defender)
                    if defender["HP"] > 0:
                        self.attack_unit(defender, self.selected_unit)
                self.message = f"{self.selected_unit['unitId']} finished attack."
            else:
                self.message = "Attack cancelled."
            # End attack mode, close popup
            self.isAttacking = False
            self.context_menu["visible"] = False
            self.attackable_tiles = []
            return  # Stop processing further

        # If the popup menu was open, close it (unless user clicked inside it - see main.py)
        if self.context_menu["visible"]:
            self.context_menu["visible"] = False
            self.message = "Menu closed."

        if not self.selected_unit:
            # Attempt to select a unit belonging to the side whose turn it is
            clicked_unit = self.get_unit_at(grid_x, grid_y)
            if clicked_unit and not clicked_unit["hasMoved"]:
                if (self.isPlayerTurn and clicked_unit["side"] == "player") \
                   or (not self.isPlayerTurn and clicked_unit["side"] == "enemy"):
                    self.selected_unit = clicked_unit
                    move_range = 5
                    self.reachable_tiles = self.calculate_reachable_tiles((clicked_unit["x"], clicked_unit["y"]), move_range)
                    self.message = f"Selected unit {clicked_unit['unitId']}"
                else:
                    self.message = "Not your unit or unit already moved."
            else:
                self.message = "No valid unit selected."
        else:
            # A unit is selected; show menu if the same cell is clicked, or attempt to move
            if self.selected_unit["x"] == grid_x and self.selected_unit["y"] == grid_y:
                can_attack = self.has_adjacent_enemy(self.selected_unit)
                # Show menu near the mouse click
                self.show_context_menu(mouse_pos[0], mouse_pos[1], can_attack)
                self.message = f"Showing menu for unit {self.selected_unit['unitId']}"
            elif (grid_x, grid_y) in self.reachable_tiles:
                self.selected_unit["x"] = grid_x
                self.selected_unit["y"] = grid_y
                self.selected_unit["hasMoved"] = True
                self.message = f"{self.selected_unit['unitId']} moved to ({grid_x},{grid_y})"
                # Attack adjacent enemy
                self.check_for_adjacent_attack(self.selected_unit)
                
                # Deselect
                self.selected_unit = None
                self.reachable_tiles = []
            else:
                # If user clicked a non-reachable tile, deselect
                self.selected_unit = None
                self.reachable_tiles = []
                self.message = "Invalid move or cancelled selection."

    def has_adjacent_enemy(self, unit):
        x, y = unit["x"], unit["y"]
        # Check if there's an enemy in (x±1, y) or (x, y±1)
        adjacent = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        for ax, ay in adjacent:
            target = self.get_unit_at(ax, ay)
            if target and target["side"] != unit["side"]:
                return True
        return False

    def start_attack_mode(self):
        """
        Called when user clicks "Attack" in the popup.
        We highlight the adjacent enemy tiles.
        """
        if not self.selected_unit:
            return
        self.isAttacking = True
        self.attackable_tiles = []
        x, y = self.selected_unit["x"], self.selected_unit["y"]
        # find adjacent enemy
        adjacent = [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]
        for (ex, ey) in adjacent:
            enemy = self.get_unit_at(ex, ey)
            if enemy and enemy["side"] != self.selected_unit["side"]:
                self.attackable_tiles.append((ex, ey))
        self.message = "Choose an adjacent enemy to attack."

    def calculate_reachable_tiles(self, start_xy, move_range):
        """
        Simple BFS ignoring obstacles or blocked tiles:
        Returns a list of (x,y) within 'move_range' steps from start_xy.
        """
        w = self.current_grid_data.get("width", 15)
        h = self.current_grid_data.get("height", 15)
        visited = set()
        queue = deque()
        queue.append((start_xy[0], start_xy[1], 0))  # (x, y, distance)
        visited.add((start_xy[0], start_xy[1]))

        reachable = []
        while queue:
            x, y, dist = queue.popleft()
            # Any tile within move_range is "reachable"
            if dist <= move_range:
                if (not (x == start_xy[0] and y == start_xy[1])) and self.get_unit_at(x, y):
                    continue
                reachable.append((x, y))
                # Explore neighbors
                for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                    if 0 <= nx < w and 0 <= ny < h:
                        if (nx, ny) not in visited:
                            # Optionally, also skip if there's an obstacle or a unit occupying that tile?
                            # For now, ignoring collisions:
                            visited.add((nx, ny))
                            queue.append((nx, ny, dist+1))
        return reachable

    # -- NEW: if there's an adjacent enemy, do a simple attack
    def check_for_adjacent_attack(self, player_unit):
        px, py = player_unit["x"], player_unit["y"]
        # find any enemy units in the 4 adjacent tiles
        adjacent_coords = [(px+1, py), (px-1, py), (px, py+1), (px, py-1)]
        for ex, ey in adjacent_coords:
            enemy = self.get_unit_at(ex, ey)
            if enemy and enemy["side"] == "enemy":
                # Attack sequence (very simple)
                self.attack_unit(player_unit, enemy)
                # If the enemy is still alive, they might retaliate
                if enemy["HP"] > 0:
                    self.attack_unit(enemy, player_unit)

    def attack_unit(self, attacker, defender):
        """Simple damage formula: defender.HP -= attacker.attack. If HP <= 0, remove them."""
        defender["HP"] -= attacker["attack"]
        self.message = f"{attacker['unitId']} attacked {defender['unitId']}!"
        if defender["HP"] <= 0:
            self.message += f" {defender['unitId']} is defeated!"
            # Remove from grid_units
            if defender in self.grid_units:
                self.grid_units.remove(defender)

    def get_unit_at(self, gx, gy):
        """Return the unit dict at grid coords (gx, gy), or None if empty."""
        for u in self.grid_units:
            if u["x"] == gx and u["y"] == gy:
                return u
        return None

    def all_player_units_done(self):
        """
        Returns True if all units belonging to the side 'player' have 'hasMoved=True'
        for the current turn.
        """
        for u in self.grid_units:
            if u["side"] == "player" and u["hasMoved"] == False:
                return False
        return True

    def on_chapter_victory(self):
        """Simulates beating the current chapter."""
        chapter_id = self.game_state.currentChapterId
        chapter = get_chapter_by_id(self.chapters_data, chapter_id)
        if not chapter:
            self.message = "Error: current chapter not found!"
            return
        
        # Trigger "onVictory" events
        self.trigger_events(chapter, "onVictory")

        # Check if we changed chapters via jumpToChapter
        if not self.is_chapter_changed(chapter_id):
            next_id = chapter.get("defaultNextChapterId", None)
            if next_id:
                self.game_state.currentChapterId = next_id

        # Mark the old chapter as visited
        if chapter_id not in self.game_state.visitedChapters:
            self.game_state.visitedChapters.append(chapter_id)

        self.message = f"Victory in Chapter {chapter_id}!"

    def is_chapter_changed(self, old_chapter_id):
        return self.game_state.currentChapterId != old_chapter_id

    def trigger_events(self, chapter, trigger_point):
        events = chapter.get("events", [])
        for event in events:
            if event.get("triggerPoint") == trigger_point:
                actions = event.get("actions", [])
                self.handle_event_actions(actions)

    def handle_event_actions(self, actions):
        for action in actions:
            action_type = action.get("type")
            if action_type == "addCoins":
                amt = action.get("amount", 0)
                self.game_state.coins += amt
                self.message = f"You earned {amt} coins!"
            elif action_type == "unlockChapter":
                cid = action.get("chapterId")
                if cid not in self.game_state.visitedChapters:
                    self.game_state.visitedChapters.append(cid)
                self.message = f"Chapter {cid} unlocked!"
            elif action_type == "jumpToChapter":
                cid = action.get("chapterId")
                self.game_state.currentChapterId = cid
                self.message = f"Jumped to Chapter {cid}"
            elif action_type == "skipNextChapter":
                pass

    # Existing debug info in PLAY mode
    def draw_status(self, screen):
        chapter_id = self.game_state.currentChapterId
        lines = [
            f"Current Chapter: {chapter_id}",
            f"Coins: {self.game_state.coins}",
            f"Heroes: {len(self.game_state.heroes)}",
            f"Message: {self.message}",
            "Press 'v' = Victory, 'g' = Grid Mode, 's' = Save"
        ]

        y = 50
        for line in lines:
            surf = self.font.render(line, True, (255, 255, 255))
            screen.blit(surf, (50, y))
            y += 30
