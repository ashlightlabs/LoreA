from typing import Dict, List

LORE_TEMPLATES: Dict[str, List[str]] = {
    "Character": ["Name", "Role", "Motivation", "Relationships", "Tags"],
    "Location": ["Name", "Description", "Mood", "Significance", "Tags"],
    "Faction": ["Name", "Goals", "Beliefs / Code", "Allies / Enemies", "Tags"],
    "Event": ["Name", "Summary", "Who Was Involved", "Why It Matters", "Tags"],
    "Item / Artifact": ["Name", "Description", "Powers / Purpose", "Origin / Lore", "Tags"]
}

DEFAULT_PROJECT_TITLE = "Untitled Project"
DEFAULT_PROJECT_DESCRIPTION = ""