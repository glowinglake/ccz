import os
import pygame
from gameEngine.chapter_manager import load_chapters_config
from gameEngine.state_manager import load_game_state, save_game_state, GameState
from gameEngine.game_manager import GameManager
from gameEngine.constants import *

# Possible "modes" of the game
MODE_MENU = "MENU"   # Choose a save or start new
MODE_PLAY = "PLAY"   # Normal gameplay (lobby/overworld style)
MODE_SAVE = "SAVE"   # Typing a save filename
MODE_GRID = "GRID"   # The grid-based campaign view

def list_save_files(folder="savedStates"):
    """Return a list of all JSON files in savedStates/."""
    if not os.path.exists(folder):
        os.makedirs(folder)
    files = [f for f in os.listdir(folder) if f.endswith(".json")]
    return files

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("War Chess in Python - In-Game Menu + Grid")

    # Store the default window size
    default_size = (SCREEN_WIDTH, SCREEN_HEIGHT)

    # We'll load the chapters config once (the chapters themselves don't change).
    chapters_data = load_chapters_config("chapters")  # Now points to a directory

    # We'll keep a reference to our GameManager, but create it only after user chooses a save.
    manager = None

    # UI state
    font = pygame.font.SysFont(None, FONT_SIZE)
    clock = pygame.time.Clock()

    # Start in MENU mode
    mode = MODE_MENU

    # For the MENU mode
    menu_saves = list_save_files("savedStates")
    menu_options = menu_saves + ["New Game"]
    selected_index = 0

    # For the SAVE mode, we store typed text in typed_save_name
    typed_save_name = ""

    # We'll keep a temporary GameState reference so that once we pick a save/new game, we create manager
    game_state_obj = None
    

    running = True
    while running:
        clock.tick(300)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # --- MENU Mode: pick a save or new game ---
            if mode == MODE_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_index = max(0, selected_index - 1)
                    elif event.key == pygame.K_DOWN:
                        selected_index = min(len(menu_options) - 1, selected_index + 1)
                    elif event.key == pygame.K_RETURN:
                        chosen = menu_options[selected_index]
                        if chosen == "New Game":
                            # Create a brand new state
                            game_state_obj = GameState()
                        else:
                            # Load an existing save
                            path = os.path.join("savedStates", chosen)
                            loaded_dict = load_game_state(path)
                            if loaded_dict is None:
                                # If we fail to load, fallback to new game
                                game_state_obj = GameState()
                            else:
                                game_state_obj = GameState(loaded_dict)

                        # Now we have a valid GameState, let's create our GameManager
                        manager = GameManager(chapters_data, game_state_obj)
                        manager.start_chapter()
                        mode = MODE_PLAY

            # --- PLAY Mode: normal gameplay (overworld) ---
            elif mode == MODE_PLAY and manager is not None:
                if event.type == pygame.KEYDOWN:
                    # Press 's' to switch to SAVE mode
                    if event.key == pygame.K_s:
                        typed_save_name = ""
                        mode = MODE_SAVE

                    # Press 'g' to switch to GRID mode (the map campaign)
                    elif event.key == pygame.K_g:
                        manager.start_grid_mode()  # prepare the grid data
                        # Get window size from grid config, default to 800x600 if not specified
                        grid_width = min(800, manager.current_grid_data.get("width")*TILE_SIZE)
                        grid_height = min(600, manager.current_grid_data.get("height")*TILE_SIZE + STATUS_BAR_HEIGHT)
                        screen = pygame.display.set_mode((grid_width, grid_height))
                        mode = MODE_GRID

            # --- SAVE Mode: type a filename for your save ---
            elif mode == MODE_SAVE and manager is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Finalize saving
                        save_path = os.path.join("savedStates", typed_save_name)
                        if not save_path.endswith(".json"):
                            save_path += ".json"
                        save_game_state(manager.game_state.to_dict(), save_path)
                        mode = MODE_PLAY
                    elif event.key == pygame.K_BACKSPACE:
                        typed_save_name = typed_save_name[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        mode = MODE_PLAY
                    else:
                        if event.unicode.isprintable():
                            typed_save_name += event.unicode

            # --- GRID Mode: show the 15x15 grid + units ---
            elif mode == MODE_GRID and manager is not None:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Return to PLAY mode and restore default window size
                        screen = pygame.display.set_mode(default_size)
                        mode = MODE_PLAY
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mouse_x, mouse_y = event.pos
                        # Check if click is in the status bar
                        if mouse_y <= STATUS_BAR_HEIGHT:
                            handle_status_bar_click(mouse_x, mouse_y, manager)
                        else:
                            # Check if we clicked the popup menu
                            if manager.context_menu["visible"]:
                                if clicked_popup_menu(screen, manager, mouse_x, mouse_y):
                                    # If we handled a popup click, do nothing else
                                    continue

                            # Otherwise it's a grid click
                            manager.handle_grid_click((mouse_x, mouse_y))
                        # check game victory or defeat condition
                        if manager.check_chapter_completion():
                            manager.on_chapter_victory()
                            mode = MODE_PLAY  # Return to play mode
                            continue
                    if event.button == 3:
                        # right click cancels menu and resets selected unit
                        if manager:
                            if manager.selected_unit:
                                manager.selected_unit.clear()
                                manager.selected_unit.update(manager.selected_unit_before_action)
                                manager.selected_unit_before_action = None
                                manager.selected_unit = None
                            manager.attackable_tiles = []
                            manager.attackable_tiles_drawing = []
                            manager.reachable_tiles = []
                            manager.context_menu["visible"] = False
                            manager.message = "Pop-up menu or attack status cancelled by right-click."
                        continue
                elif event.type == pygame.MOUSEMOTION:
                    # Handle mouse hover
                    mouse_x, mouse_y = event.pos
                    if mouse_y > STATUS_BAR_HEIGHT:
                        # Convert pixel coordinates to grid coordinates
                        grid_x = mouse_x // TILE_SIZE
                        grid_y = (mouse_y - STATUS_BAR_HEIGHT) // TILE_SIZE
                        # Get unit at hovered position
                        hovered_unit = manager.get_unit_at(grid_x, grid_y)
                        if hovered_unit:
                            # Show unit info in message
                            manager.message = (
                                f"Unit: {hovered_unit['unitId']} | "
                                f"HP: {hovered_unit['HP']} | "
                                f"Attack: {hovered_unit['attack']} | "
                                f"Defense: {hovered_unit['defense']} | "
                                f"MP: {hovered_unit['MP']}"
                            )
                        else:
                            manager.message = ""

        # --- RENDER / DRAW ---
        screen.fill(BLACK)

        if mode == MODE_MENU:
            draw_menu(screen, font, menu_options, selected_index)
        elif mode == MODE_PLAY:
            if manager:
                manager.draw_status(screen)
        elif mode == MODE_SAVE:
            draw_save_prompt(screen, font, typed_save_name)
        elif mode == MODE_GRID:
            draw_grid_mode(screen, manager, font)
            draw_popup_menu(screen, manager, font)

        # 2) Draw the status bar (always on top)
        draw_status_bar(screen, font, manager, mode)
        pygame.display.flip()

    pygame.quit()

def draw_menu(screen, font, options, selected_index):
    """Draw a simple vertical menu (saves + 'New Game')."""
    title_surf = font.render("Select a Save or Start New Game", True, WHITE)
    screen.blit(title_surf, (MENU_TITLE_X, MENU_START_Y))

    y_offset = MENU_OPTION_Y
    for i, opt in enumerate(options):
        color = YELLOW if i == selected_index else LIGHT_GRAY
        text_surf = font.render(opt, True, color)
        screen.blit(text_surf, (MENU_OPTION_X, y_offset))
        y_offset += MENU_OPTION_SPACING

def draw_save_prompt(screen, font, typed_name):
    """Draw the UI for typing a save filename."""
    instructions = [
        "Type a name for your save (no spaces recommended).",
        "Press ENTER to confirm, ESC to cancel."
    ]
    y_offset = 50
    for line in instructions:
        surf = font.render(line, True, WHITE)
        screen.blit(surf, (50, y_offset))
        y_offset += 40

    # Show the typed filename
    typed_surf = font.render("Filename: " + typed_name, True, YELLOW)
    screen.blit(typed_surf, (50, y_offset))

def draw_grid_mode(screen, manager, font):
    """
    Renders the grid campaign.
    - Draw the background image if loaded
    - Draw each unit at its (x,y) position
    """
    # The manager has a .grid_background (a loaded pygame.Surface or None)
    # The manager also has .grid_data for the current chapter
    grid_data = manager.current_grid_data
    if not grid_data:
        # fallback message if no grid data
        text_surf = font.render("No grid data available!", True, RED)
        screen.blit(text_surf, (50, 50))
        return

    # Draw background
    if manager.grid_background:
        # Scale background to fill screen
        screen_width, screen_height = screen.get_size()
        scaled_bg = pygame.transform.scale(manager.grid_background, (screen_width, screen_height))
        screen.blit(scaled_bg, (0, 0))
    else:
        # fallback, fill with dark green
        screen.fill((34, 139, 34))

    tile_size = 32  # each cell is 32x32
    # You can scale or position the grid as needed in your design
    

    # 1. Draw each unit
    for unit in manager.grid_units:  
        # unit = {"unitId":..., "x":..., "y":..., "side": "player" or "enemy"}
        x_px = unit["x"] * tile_size
        y_px = unit["y"] * tile_size + STATUS_BAR_HEIGHT
        if unit["side"] == "player":
            if unit["hasMoved"] == manager.ACTION_STATE_NOT_YET:
                color = (0, 255, 0)
            else:
                color = (1, 150, 32)            
        else:
            if unit["hasMoved"] == manager.ACTION_STATE_NOT_YET:
                color = (255, 0, 0)
            else:
                color = (139, 0, 0)
        pygame.draw.rect(screen, color, (x_px, y_px, tile_size, tile_size))

    # 2. Highlight reachable tiles and attackable tiles
    highlight_color = (0, 0, 255, 80)  # RGBA with some alpha
    attack_highlight_color = (150, 0, 0, 80)  # RGBA with some alpha
    highlight_surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    highlight_surf.fill(highlight_color)
    for (rx, ry) in manager.reachable_tiles:
        screen.blit(highlight_surf, (rx * tile_size, ry * tile_size + STATUS_BAR_HEIGHT))

    attack_highlight_surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    attack_highlight_surf.fill(attack_highlight_color)
    for (rx, ry) in manager.attackable_tiles_drawing:
        screen.blit(attack_highlight_surf, (rx * tile_size, ry * tile_size + STATUS_BAR_HEIGHT))

    # Overlay some textual info: e.g. "Press ESC to exit"
    msg = f"Chapter {manager.game_state.currentChapterId} Grid - Max Turns {grid_data.get('maxTurns', 0)}"
    text_surf = font.render(msg, True, WHITE)
    screen.blit(text_surf, (10, 10))

    help_surf = font.render("Press ESC to exit grid mode", True, WHITE)
    screen.blit(help_surf, (10, 40))


def draw_status_bar(screen, font, manager, mode):
    """
    Always visible bar at the top (0,0) -> (width=640, height=70).
    Shows:
      - current game mode
      - manager.message (if any)
      - if grid mode: "Turn X / Y", "all units done" if applicable
      - an "End Turn" button if in grid mode
    """
    bar_rect = (0, 0, SCREEN_WIDTH, STATUS_BAR_HEIGHT)
    pygame.draw.rect(screen, DARK_GRAY, bar_rect)

    if manager is None:
        text = f"Game Mode: {mode}"
        surf = font.render(text, True, WHITE)
        screen.blit(surf, (10, 10))
        return

    # Left side: Game Mode
    mode_text = f"Game Mode: {mode}"
    surf_mode = font.render(mode_text, True, WHITE)
    screen.blit(surf_mode, (10, 10))

    # Middle: manager.message
    msg = manager.message
    surf_msg = font.render(msg, True, YELLOW)
    screen.blit(surf_msg, (10, 40))

    if mode == MODE_GRID:
        turn_text = f"Turn {manager.grid_currentTurn}/{manager.grid_maxTurns}"
        if not manager.isPlayerTurn:
            turn_text += " (Enemy Turn)"
        else:
            turn_text += " (Player Turn)"
        surf_turn = font.render(turn_text, True, WHITE)
        screen.blit(surf_turn, (250, 10))

        if manager.isPlayerTurn and manager.all_player_units_done():
            done_text = "All player's units are done with actions!"
            surf_done = font.render(done_text, True, YELLOW)
            screen.blit(surf_done, (250, 40))

        pygame.draw.rect(screen, MEDIUM_GRAY, END_TURN_BUTTON)
        btn_label = font.render("End Turn", True, WHITE)
        screen.blit(btn_label, (END_TURN_BUTTON[0]+10, END_TURN_BUTTON[1]+5))

def handle_status_bar_click(mouse_x, mouse_y, manager):
    """
    Check if user clicked on the "End Turn" button in the status bar.
    If so, call manager.end_turn().
    """
    bx, by, bw, bh = END_TURN_BUTTON
    if bx <= mouse_x <= bx + bw and by <= mouse_y <= by + bh:
        manager.end_turn()

def clicked_popup_menu(screen, manager, mx, my):
    if not manager.context_menu["visible"]:
        return False

    px, py = manager.context_menu["x"], manager.context_menu["y"]

    # Adjust position if too close to screen edges
    screen_w, screen_h = screen.get_size()
    if px + POPUP_MENU_WIDTH > screen_w:
        px = screen_w - POPUP_MENU_WIDTH
    if py + POPUP_MENU_HEIGHT > screen_h:
        py = screen_h - POPUP_MENU_HEIGHT

    if not (px <= mx <= px + POPUP_MENU_WIDTH and py <= my <= py + POPUP_MENU_HEIGHT):
        return False

    if py <= my < py + POPUP_OPTION_HEIGHT:
        # Attack area
        if manager.context_menu["attackEnabled"]:
            manager.start_attack_mode()
        else:
            manager.message = "Attack is disabled."
    elif py + POPUP_OPTION_HEIGHT <= my < py + (POPUP_OPTION_HEIGHT * 2):
        # Cast area
        manager.message = "Cast action not implemented."
    else:
        manager.handle_stay_action()

    manager.context_menu["visible"] = False
    return True

def draw_popup_menu(screen, manager, font):
    if not manager.context_menu["visible"]:
        return

    px = manager.context_menu["x"]
    py = manager.context_menu["y"]
    
    # Adjust position if too close to screen edges
    screen_w, screen_h = screen.get_size()
    if px + POPUP_MENU_WIDTH > screen_w:
        px = screen_w - POPUP_MENU_WIDTH
    if py + POPUP_MENU_HEIGHT > screen_h:
        py = screen_h - POPUP_MENU_HEIGHT
    
    # Draw background
    pygame.draw.rect(screen, POPUP_BG_COLOR, (px, py, POPUP_MENU_WIDTH, POPUP_MENU_HEIGHT))

    # Attack option
    attack_color = LIGHT_GRAY if manager.context_menu["attackEnabled"] else MEDIUM_GRAY
    attack_text = font.render("Attack", True, attack_color)
    screen.blit(attack_text, (px + POPUP_TEXT_PADDING_X, py + POPUP_TEXT_PADDING_Y))

    # Cast option
    cast_text = font.render("Cast", True, LIGHT_GRAY)
    screen.blit(cast_text, (px + POPUP_TEXT_PADDING_X, py + POPUP_CAST_Y_OFFSET))

    # Stay option
    stay_text = font.render("Stay", True, LIGHT_GRAY)
    screen.blit(stay_text, (px + POPUP_TEXT_PADDING_X, py + POPUP_STAY_Y_OFFSET))

if __name__ == "__main__":
    main()
