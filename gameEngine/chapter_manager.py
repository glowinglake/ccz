import json

def load_chapters_config(config_path):
    """Load the chapter definitions from JSON."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_chapter_by_id(chapters_data, chapter_id):
    """Utility to find a chapter dict by ID."""
    for c in chapters_data["chapters"]:
        if c["chapterId"] == chapter_id:
            return c
    return None

