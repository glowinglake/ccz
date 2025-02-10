import json
import os

def load_chapters_config(chapters_dir):
    """
    Load chapter definitions from individual JSON files in the chapters directory.
    Each file should be named chapter_<id>.json
    """ 
    chapters = {}
    # Load each chapter_<id>.json file
    for filename in sorted(os.listdir(chapters_dir)):
        if filename.startswith("chapter_") and filename.endswith(".json"):
            filepath = os.path.join(chapters_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                chapters[chapter_data["chapterId"]] = chapter_data
    
    return chapters

def get_chapter_by_id(chapters_data, chapter_id):
    """Get a specific chapter's data."""
    return chapters_data.get(chapter_id)

