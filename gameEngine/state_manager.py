import json
import os

class GameState:
    def __init__(self, state_dict=None):
        if state_dict:
            self.currentChapterId = state_dict.get("currentChapterId", 1)
            self.visitedChapters = state_dict.get("visitedChapters", [])
            self.heroes = state_dict.get("heroes", [])
            self.coins = state_dict.get("coins", 0)
            self.currentChapterState = state_dict.get("currentChapterState", {})
        else:
            # Default (new game) values if no save exists
            self.currentChapterId = 1
            self.visitedChapters = []
            self.heroes = []
            self.coins = 0
            self.currentChapterState = {}

    def to_dict(self):
        """Convert this GameState into a serializable dictionary."""
        return {
            "currentChapterId": self.currentChapterId,
            "visitedChapters": self.visitedChapters,
            "heroes": self.heroes,
            "coins": self.coins,
            "currentChapterState": self.currentChapterState
        }

def load_game_state(path):
    """Load game state JSON from disk."""
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_game_state(state_dict, path):
    """Save game state dictionary to disk as JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state_dict, f, indent=2)

