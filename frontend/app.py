import sys
import os
import pdb
from typing import Dict, Any, List, Optional
import streamlit as st
import json
from PIL import Image
import logging
from random import choice

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.core import (
    add_lore_to_db,
    get_all_lore_from_db,
    delete_lore_entry_by_title,
    update_lore_entry,
    generate_text_from_lore,
    embed_text,
    get_filtered_lore,
    get_setting,
    set_setting,
    init_db,
    delete_all_entries,
    delete_settings,
    get_entries_for_export,
    get_entries_for_markdown_export,
    generate_field_content,
    process_template_fields  # Add this import
)

favicon_path = os.path.join(os.path.dirname(__file__), "assets", "favicon.png")
st.set_page_config(page_title="LoreA",
    page_icon=favicon_path,  # You can use an emoji
    layout="wide")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("App started")  # Will appear in logs

if ("initializedDB" not in st.session_state) or (st.session_state.initializedDB == False):
    # Initialize the database
    init_db()
    st.session_state.initializedDB = True



# Initialize all session state variables BEFORE any UI elements
if "project_title" not in st.session_state:
    st.session_state.project_title = get_setting("project_title") or "Name your world..."
if "project_description" not in st.session_state:
    st.session_state.project_description = get_setting("project_description") or ""
if "confirm_delete_all" not in st.session_state:
    st.session_state.confirm_delete_all = False
# Add filter state initialization
if "search_query" not in st.session_state:
    st.session_state.search_query = None
if "template_filter" not in st.session_state:
    st.session_state.template_filter = None
if "selected_tags" not in st.session_state:
    st.session_state.selected_tags = None
if "show_preview" not in st.session_state:
    st.session_state.show_preview = False
if "generated_content" not in st.session_state:
    st.session_state.generated_content = None
# Add to session state initialization
if "dev_mode" not in st.session_state:
    st.session_state.dev_mode = get_setting("dev_mode") == "true"
if "show_editor" not in st.session_state:
    st.session_state.show_editor = False
if "last_created_entry" not in st.session_state:
    st.session_state.last_created_entry = None
if "selected_entry_title" not in st.session_state:
    st.session_state.selected_category = "Character"
if "entries_per_page" not in st.session_state:
    st.session_state.entries_per_page = 2
if "page_numbers" not in st.session_state:
    st.session_state.page_numbers = {}
if "import_status" not in st.session_state:
    st.session_state.import_status = None
if "is_local" not in st.session_state:
    # Check if running locally (not on Streamlit Cloud)
    st.session_state.is_local = os.environ.get('STREAMLIT_BROWSER_GATHER_USAGE_STATS', '') != 'true'

def import_entries_with_progress(entries, update_settings=False, sample_title=None, sample_desc=None):
    """Import entries with progress tracking."""
    total = len(entries)
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        # Update settings if provided
        if update_settings:
            progress_text.text("📝 Updating project settings...")
            progress_bar.progress(0.1)
            st.session_state.project_title = sample_title
            st.session_state.project_description = sample_desc
            set_setting("project_title", sample_title)
            set_setting("project_description", sample_desc)
        
        # Group entries by template
        progress_text.text("🗂️ Organizing entries...")
        progress_bar.progress(0.2)
        entries_by_type = {}
        for entry in entries:
            template = entry["template"]
            if template not in entries_by_type:
                entries_by_type[template] = []
            entries_by_type[template].append(entry)
        
        # Import entries with progress updates
        completed = 0
        for template, template_entries in entries_by_type.items():
            progress_text.text(f"✨ Creating {template}s...")
            for entry in template_entries:
                add_lore_to_db(
                    title=entry["fields"]["Name"],
                    content=entry["fields"],
                    tags=entry["fields"].get("Tags", []),
                    template=entry["template"]
                )
                completed += 1
                progress_bar.progress(0.2 + (0.8 * (completed / total)))
        
        progress_text.text("✅ Import complete!")
        progress_bar.progress(1.0)
        return True
    except Exception as e:
        progress_text.text(f"❌ Import failed: {str(e)}")
        return False

# Now create the layout
col1, col2 = st.columns([6, 1])

with col2:
    # Load and display logo
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.image(logo, width=100)

with col1:
    # Use markdown for italic title instead of st.title
    st.markdown(f"# *{st.session_state.project_title}*")
    if st.session_state.project_title == "Name your world...":
        st.markdown("🛠 Tip: Give your project a name and description in Project Settings!")
    st.caption(f"*{st.session_state.project_description}*")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Vollkorn:ital,wght@0,400;0,600;1,400;1,600&family=Quicksand:wght@400;500;600&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap');

html, body, [class*="css"]  {
   font-family: 'Spectral', serif;
   background-color: #F1E8D7;
   color: #2B2B2B;
   font-size: 18px;
   line-height: 1.6;
   letter-spacing: 0.01em;
}

/* Improve text readability */
p, li {
    max-width: 70ch;
    margin-bottom: 1.2em;
    font-family: 'Spectral', serif;
    font-weight: 400;
}

h1 {
   font-family: 'Vollkorn', serif;
   color: #B54B27;
   font-size: 2.8rem;
   margin-bottom: 1.5rem;
   letter-spacing: -0.01em;
   font-weight: 600;
   font-style: italic;
}

h2, h3 {
   font-family: 'Vollkorn', serif;
   color: #B54B27;
   line-height: 1.3;
   margin-top: 1.5em;
   margin-bottom: 0.8em;
   font-weight: 600;
}

/* UI elements */
button, select, .stSelectbox, [data-testid="stWidgetLabel"] {
    font-family: 'Quicksand', sans-serif !important;
    font-weight: 500;
}

/* Input field improvements */
[data-testid="stTextInput"] input, 
[data-testid="stTextArea"] textarea {
    font-family: 'Spectral', serif;
    background-color: #F9F4E8;
    border: 1px solid #D4A76A;
    color: #2B2B2B;
    font-size: 1.05rem;
    line-height: 1.6;
    padding: 0.6em;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Target expander containers */
div[data-testid="stExpander"] {
    background-color: #F9F4E8;      /* light parchment */
    border: 1px solid #D97706;      /* warm amber border */
    border-radius: 6px;
    padding: 0.5rem;
    margin-top: 0.5rem;
}

/* Target expander labels */
div[data-testid="stExpander"] > details > summary {
    color: #B54B27;                 /* red-orange title */
    font-weight: bold;
    font-family: 'EB Garamond', serif;
}

/* Optional: hover effect */
div[data-testid="stExpander"]:hover {
    background-color: #F2E3C6;
}

/* Style input fields */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background-color: #F9F4E8;      /* light parchment */
    border: 1px solid #D4A76A;      /* warm brown border */
    color: #2B2B2B;                 /* dark text for readability */
}

/* Hover state */
[data-testid="stTextInput"] input:hover, [data-testid="stTextArea"] textarea:hover {
    background-color: #FDF9F0;      /* slightly lighter parchment */
    border-color: #B54B27;          /* accent color border */
}

/* Focus state */
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    background-color: #FDF9F0;
    border-color: #B54B27;
    box-shadow: 0 0 0 1px #B54B27;
}
</style>
""", unsafe_allow_html=True)

with st.expander("⚙️ Project Settings"):
    # Project Info Section
    st.subheader("📋 Project Information")
    new_title = st.text_input("Project Title", value=st.session_state["project_title"])
    if st.button("Save Title"):
        st.session_state["project_title"] = new_title
        set_setting("project_title", new_title)
        st.success("Title updated.")
        st.rerun()

    new_desc = st.text_area("Project Description", value=st.session_state["project_description"])
    if st.button("Save Description"):
        st.session_state["project_description"] = new_desc
        set_setting("project_description", new_desc)
        st.success("Description updated.")
        st.rerun()

# --- Template-Based Lore Entry Section ---
LORE_TEMPLATES = {
    "Character": ["Name", "Role", "Motivation", "Relationships", "Tags"],
    "Location": ["Name", "Description", "Mood", "Significance", "Tags"],
    "Faction": ["Name", "Goals", "Beliefs / Code", "Allies / Enemies", "Tags"],
    "Event": ["Name", "Summary", "Who Was Involved", "Why It Matters", "Tags"],
    "Item / Artifact": ["Name", "Description", "Powers / Purpose", "Origin / Lore", "Tags"]
}

# Add template emoji mapping after LORE_TEMPLATES
TEMPLATE_EMOJIS = {
    "Character": "👤",
    "Location": "🗺️",
    "Faction": "⚔️",
    "Event": "📅",
    "Item / Artifact": "🏺"
}

# Generation style mappings
FIELD_TO_STYLES = {
    "Role": ["Default", "Flavor Text", "Narrative Hook"],
    "Motivation": ["Default", "Flavor Text", "Character Dialogue", "Narrative Hook"],
    "Relationships": ["Default", "Flavor Text", "Character Dialogue"],
    "Description": ["Default", "Flavor Text", "World-Building Detail", "Narrative Hook"],
    "Mood": ["Default", "Flavor Text"],
    "Significance": ["Default", "World-Building Detail", "Narrative Hook"],
    "Goals": ["Default", "World-Building Detail", "Narrative Hook"],
    "Beliefs / Code": ["Default", "World-Building Detail", "Narrative Hook"],
    "Allies / Enemies": ["Default", "Flavor Text", "World-Building Detail"],
    "Summary": ["Default", "World-Building Detail", "Narrative Hook"],
    "Who Was Involved": ["Default", "Flavor Text"],
    "Why It Matters": ["Default", "World-Building Detail", "Narrative Hook"],
    "Powers / Purpose": ["Default", "World-Building Detail"],
    "Origin / Lore": ["Default", "World-Building Detail", "Narrative Hook"],
}

LOADING_PHRASES = [
    "🌱 Growing wild tales...",
    "📚 Consulting ancient tomes...",
    "🧙‍♀️ Stirring the cauldron of creativity...",
    "🌿 Brewing narrative tea...",
    "🎪 Juggling plot threads...",
    "🔮 Peering through time's window...",
    "🗝️ Unlocking forgotten chambers...",
    "🎭 Donning the mask of mystery...",
    "🌟 Catching falling stories...",
    "🎪 Spinning tall tales...",
    "🪄 Channeling narrative magic...",
    "👁️ 👁️ Consulting the narrative gods...",
    "🌊 Diving into narrative depths...",
    "🧭 Following whispered legends...",
    "🎭 Gathering tales from old...",
    "📜 Unraveling ancient scrolls...",
]

entries = get_all_lore_from_db()
expanded = False
if(entries == []):
    st.markdown("""
        ### 🗺️ Welcome to LoreA

        **Your journey begins here.**  
        Every world needs a name, a map, a cast of legends — yours is waiting to be written.

        Start by forging a **character**, uncovering a **location**, or discovering a forgotten **artifact** using the **Lore Entry** below.  
        Each entry is a step deeper into the world you're creating.

        Once you've begun, **LoreA** can you help you expand your story — suggesting details, establishing connections, and unlocking new possibilities.
                
        **LoreA uses your existing lore entries to generate new content, so the more you add, the richer your world becomes.**

        ---

        **Not sure where to begin?**  
        Use the button below to populate your world with a few starting entries and dive straight into the adventure.

    """)
    
    # Add FTUE data import button
    ftue_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "lore_json", "lorea_ftue_50_entries.json")
    if os.path.exists(ftue_path):
        if st.button("🪄 Load Sample World"):
            with st.spinner("📚 Loading sample world..."):
                try:
                    with open(ftue_path, 'r', encoding='utf-8') as f:
                        sample_entries = json.load(f)
                    
                    success = import_entries_with_progress(
                        sample_entries,
                        update_settings=True,
                        sample_title="Chroma",
                        sample_desc="""In the year 2187, the city of New Carthage hangs on the edge of memory and malfunction. Synthetics drift through identity loops, rogue AIs whisper beneath flooded servers, and fractured collectives fight to reclaim agency from decaying infrastructure."""
                    )
                    
                    if success:
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to load sample world: {e}")
    expanded = True

with st.expander("📝 Add New Entry", expanded):
    st.subheader("Lore Entry")
    selected_template = st.selectbox("Select a lore template", list(LORE_TEMPLATES.keys()), key="template_select")
    
    template_fields = {}
    for field in LORE_TEMPLATES[selected_template]:
        if field == "Tags":
            tags_input = st.text_input(f"**{field}** (comma-separated)", key=f"template_{field}")
            template_fields[field] = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        elif field.lower() in ["description", "summary", "relationships", "allies / enemies", "origin / lore"]:
            template_fields[field] = st.text_area(f"**{field}**", key=f"template_{field}")
        else:
            template_fields[field] = st.text_input(f"**{field}**", key=f"template_{field}")

    if st.button("Save Lore Entry from Template"):
        if not template_fields.get("Name"):
            st.error("Name is required.")
        else:
            fields_dict, tags = process_template_fields(template_fields)
            add_lore_to_db(
                title=fields_dict["Name"],
                content=fields_dict,
                tags=tags,
                template=selected_template
            )
            # Show simple success message and open editor
            st.success(f"Saved {fields_dict['Name']}")
            st.session_state.selected_category = selected_template
            st.session_state.selected_entry_title = fields_dict["Name"]
            st.session_state.show_editor = True
            st.rerun()

# Existing lore listing and features
entries = get_all_lore_from_db()

# Initialize navigation state
if "selected_category" not in st.session_state:
    st.session_state.selected_category = None
if "selected_entry_title" not in st.session_state:
    st.session_state.selected_entry_title = None

def change_entry(idx: int) -> None:
    """Handle entry selection changes."""
    st.session_state.selected_entry_idx = idx

def select_entry(category: str, title: str) -> None:
    """Helper function to handle entry selection."""
    st.session_state.selected_category = category
    st.session_state.selected_entry_title = title
    st.rerun()

def display_entry(entry: Dict[str, Any]) -> None:
    """Display a single lore entry."""
    # Start with a copy of all existing fields
    new_values = {**entry['fields']}
    
    # Parse current content
    current_values = {}
    content_lines = entry['content'].split('\n')
    for line in content_lines:
        if ':' in line:
            field, value = line.split(':', 1)
            current_values[field.strip()] = value.strip()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        template_fields = LORE_TEMPLATES.get(entry['template'], [])
        
        # Display fields first to collect all values
        for field in template_fields:
            current_value = current_values.get(field, "")
            field_key = f"edit_{entry['title']}_{field}"
            
            if field == "Tags":
                new_value = st.text_input(
                    label=f"**{field}** (comma-separated)",
                    value=", ".join(entry['tags']),
                    key=field_key
                )
                new_values[field] = [tag.strip() for tag in new_value.split(",") if tag.strip()]
            elif field.lower() in ["description", "summary", "relationships", "allies / enemies", "origin / lore"]:
                new_value = st.text_area(
                    label=f"**{field}**",
                    value=current_value,
                    key=field_key
                )
                new_values[field] = new_value
            else:
                new_value = st.text_input(
                    label=f"**{field}**",
                    value=current_value,
                    key=field_key
                )
                new_values[field] = new_value
        
        # Entry actions after collecting all values
        col_actions1, col_actions2, col_actions3 = st.columns([1, 1, 2])
        with col_actions1:
            if st.button("💾 Save Changes", key=f"save_{entry['title']}"):
                update_lore_entry(
                    original_title=entry['title'],
                    new_title=new_values.get('Name', entry['title']),
                    new_content="\n".join(f"{k}: {v}" for k, v in new_values.items()),
                    new_tags=new_values.get('Tags', []),
                    new_template=entry['template'],
                    new_fields=new_values
                )
                st.success("Changes saved!")
                st.rerun()
        with col_actions2:
            if st.button("🗑️ Delete Entry", key=f"del_{entry['title']}"):
                delete_lore_entry_by_title(entry['title'])
                st.rerun()
        
        # Lore Assistant section
        st.markdown("### 🧝‍♀️  LoreA")
        
        with st.expander("About LoreA", expanded=True):
            st.markdown("""
            ### Meet Your Lorekeeper Companion

            Welcome to **LoreA**, your tireless companion in the grand art of world-weaving. Whether you're sketching the bones of a fledgling kingdom or breathing life into forgotten lands, LoreA is here to gently guide your hand and spark your imagination.

            ### How to Begin Your Journey:

            1. **Open a chapter** - Select the chapter of your lore you'd like to work on. Roles? Motivations? Allies or Enemies?

            2. **Set the tone:**

                * **Default** - Clear, steady guidance. A compass when you're unsure.
                * **Flavor Text** - A dash of charm and color.
                * **World-Building Detail** - Rich threads of history, culture, and depth.
                * **Narrative Hook** - A spark to draw readers in.

            3. **Guide LoreA** - Add an optional prompt to shape the voice of LoreA.

            4. **Ask LoreA to “Tell Me a Tale”** - And watch your world unfold.
            """)
        
        # Get available fields for current template (excluding Name and Tags)
        available_fields = [
            field for field in LORE_TEMPLATES[entry['template']]
            if field not in ["Name", "Tags"]
        ]
        
        # Field selection dropdown
        selected_field = st.selectbox(
            "Select a chapter to work with",
            ["Open a chapter..."] + available_fields,  # Add default option
            key=f"field_select_{entry['title']}"
        )
        
        # Only show additional controls if a valid field is selected
        if selected_field and selected_field != "Select a field...":
            # Add Generation Style dropdown with dynamic options
            available_styles = FIELD_TO_STYLES.get(selected_field, ["Default"])
            generation_style = st.selectbox(
                "Set the tone",
                available_styles,
                key=f"style_{entry['title']}_{selected_field}"
            )
            
            current_content = entry['fields'].get(selected_field, "")
            prompt = st.text_input(
                "Guide LoreA (optional)",
                key=f"prompt_{entry['title']}_{selected_field}",
                help="Help guide LoreA's voice and tone. Want something specific? Here is where you can shape it."
            )
            
            # Add Inspire Me button and preview
            if st.button("✨ Tell Me a Tale", key=f"inspire_{entry['title']}_{selected_field}"):
                with st.spinner(choice(LOADING_PHRASES)):
                    generated = generate_field_content(
                        entry_title=entry['title'],
                        field_name=selected_field,
                        template_type=entry['template'],
                        current_content=current_content,
                        user_prompt=prompt,
                        tags=entry['tags'],
                        generation_style=generation_style  # Pass the selected style
                    )
                    st.session_state.generated_content = generated
                    st.rerun()
                
            if st.session_state.generated_content:
                st.markdown("#### 🪄 LoreA's Suggestion:")
                st.markdown(st.session_state.generated_content)
                
                # Create a container with smaller columns for the buttons
                with st.container():
                    col_gen1, col_gap, col_gen2, col_spacer = st.columns([0.4, 0.1, 0.4, 2.1])
                    with col_gen1:
                        if st.button("✅ Use This"):
                            new_values = {**entry['fields']}
                            new_values[selected_field] = st.session_state.generated_content
                            st.session_state.generated_content = None
                            update_lore_entry(
                                original_title=entry['title'],
                                new_title=entry['title'],
                                new_content="\n".join(f"{k}: {v}" for k, v in new_values.items()),
                                new_tags=entry['tags'],
                                new_template=entry['template'],
                                new_fields=new_values
                            )
                            st.rerun()
                    with col_gen2:
                        if st.button("❌ Discard"):
                            st.session_state.generated_content = None
                            st.rerun()

    with col2:
        # Linked Entries section
        if entry.get('linked_entries'):
            st.markdown("### 🔗 Linked Entries")
            for idx, linked_title in enumerate(entry['linked_entries']):
                col_link1, col_link2 = st.columns([3, 1])
                with col_link1:
                    st.text(linked_title)
                with col_link2:
                    if st.button("View", key=f"view_{entry['title']}_{linked_title}_{idx}"):
                        # Find target entry's category
                        for cat, entries in entries_by_category.items():
                            if any(e['title'] == linked_title for e in entries):
                                select_entry(cat, linked_title)  # Use select_entry helper



# Update the entries display section
if entries:
    # Add visual separator
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## 📜 Lore Entries")
    
    # Add simple filter bar
    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        search = st.text_input("🔎", 
            placeholder="Search entries...",
            value=st.session_state.search_query or "",
            label_visibility="collapsed")
        if search != st.session_state.search_query:
            st.session_state.search_query = search
            st.session_state.page_numbers = {}  # Reset pagination
            st.rerun()
            
    with filter_col2:
        # Collect all tags
        all_tags = set()
        for entry in entries:
            all_tags.update(entry.get('tags', []))
        if all_tags:  # Only show if there are tags
            selected_tags = st.multiselect("🏷️",
                options=sorted(list(all_tags)),
                default=st.session_state.selected_tags,
                placeholder="Filter by tags...",
                label_visibility="collapsed")
            if selected_tags != st.session_state.selected_tags:
                st.session_state.selected_tags = selected_tags
                st.session_state.page_numbers = {}  # Reset pagination
                st.rerun()
    
    filtered_entries = get_filtered_lore(
        tags=st.session_state.selected_tags if st.session_state.selected_tags else None,
        entry_type=st.session_state.template_filter if st.session_state.template_filter != "All" else None,
        query=st.session_state.search_query if st.session_state.search_query else None
    )
    
    if not filtered_entries:
        st.info("No entries match your filters.")
    else:
        # Group entries by template type
        entries_by_category = {}
        for entry in filtered_entries:
            category = entry['template']
            if category not in entries_by_category:
                entries_by_category[category] = []
            entries_by_category[category].append(entry)
        
        categories = list(entries_by_category.keys())
        
        # Create tabs for each category with entry counts
        category_tabs = st.tabs([
            f"{TEMPLATE_EMOJIS[cat]} {cat}s ({len(entries_by_category[cat])})" 
            for cat in categories
        ])
        
        # Display entries in respective tabs
        for idx, (category, tab) in enumerate(zip(categories, category_tabs)):
            with tab:
                category_entries = entries_by_category[category]
                
                # Initialize page number for this category if not exists
                if category not in st.session_state.page_numbers:
                    st.session_state.page_numbers[category] = 0
                
                # Calculate pagination
                start_idx = st.session_state.page_numbers[category] * st.session_state.entries_per_page
                end_idx = start_idx + st.session_state.entries_per_page
                page_entries = category_entries[start_idx:end_idx]
                total_pages = (len(category_entries) + st.session_state.entries_per_page - 1) // st.session_state.entries_per_page
                
                # Display only the entries for current page
                for entry in page_entries:
                    # Get appropriate summary field based on template type
                    summary_field = {
                        "Character": "Role",
                        "Location": "Description",
                        "Faction": "Goals",
                        "Event": "Summary",
                        "Item / Artifact": "Description"
                    }.get(entry['template'], "Description")
                    
                    summary = entry['fields'].get(summary_field, "No description available.")
                    first_sentence = summary.split('.')[0] + '.' if '.' in summary else summary
                    
                    is_selected = entry['title'] == st.session_state.selected_entry_title
                    
                    # Create card layout
                    st.markdown(f"#### {TEMPLATE_EMOJIS[entry['template']]} {entry['title']} ({entry['template']}) {'✅' if is_selected else ''}")
                    st.markdown(f"{summary_field}: *{first_sentence}*")
                    if entry['tags']:
                        st.markdown(f"🏷️ {', '.join(entry['tags'])}")
                    
                    # Add view button in the cards list with unique key including category
                    if st.button("Edit Details", key=f"card_edit_{category}_{entry['title']}", type="primary"):
                        st.session_state.selected_entry_title = entry['title']
                        st.session_state.selected_category = category
                        st.session_state.show_editor = True
                        st.rerun()
 
                
                if not category_entries:
                    st.info(f"No {category} entries found.")
                
                # Add pagination controls after entries but before editor
                if category_entries:  # Only show if there are entries
                    # Calculate total pages
                    total_pages = (len(category_entries) + st.session_state.entries_per_page - 1) // st.session_state.entries_per_page
                    
                    # Add custom CSS for compact buttons
                    st.markdown("""
                        <style>
                            .stHorizontalBlock {
                                gap: 0rem !important;
                                padding: 0 !important;
                                margin: 0 !important;
                            }
                            div[data-testid="column"] {
                                padding: 0 !important;
                                margin: 0 !important;
                            }
                            div[data-testid="stVerticalBlock"] > div {
                                padding: 0 !important;
                                margin: 0 !important;
                            }
                            .pagination-text {
                                text-align: center;
                                margin: 0;
                                padding: 0;
                            }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    # Create compact button columns with page number display
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        prev_disabled = st.session_state.page_numbers[category] == 0
                        if st.button("⬅️", key=f"prev_{category}", disabled=prev_disabled, use_container_width=True):
                            st.session_state.page_numbers[category] = max(0, st.session_state.page_numbers[category] - 1)
                            st.rerun()
                    with col2:
                        current_page = st.session_state.page_numbers[category] + 1
                        st.markdown(f"<p class='pagination-text'>{current_page} of {total_pages}</p>", unsafe_allow_html=True)
                    with col3:
                        next_disabled = st.session_state.page_numbers[category] >= total_pages - 1
                        if st.button("➡️", key=f"next_{category}", disabled=next_disabled, use_container_width=True):
                            st.session_state.page_numbers[category] = min(total_pages - 1, st.session_state.page_numbers[category] + 1)
                            st.rerun()
            
            # If this is the category of the selected entry, make this tab active
            if st.session_state.selected_category == category:
                st.session_state.active_tab = idx
        
        # Display selected entry details if one is selected (moved outside the tab loop)
        if st.session_state.selected_entry_title and st.session_state.show_editor:
            st.markdown("## 🪶 Editor")
            try:
                selected_entry = next(e for e in entries if e['title'] == st.session_state.selected_entry_title)
                
                # Create anchor point for scrolling
                details_anchor = st.empty()
                st.markdown("""
                    <div id="entry-details"></div>
                """, unsafe_allow_html=True)
                
                # Add header with close button in columns with unique key
                col1, col2 = st.columns([6, 1])
                with col1:
                    emoji = TEMPLATE_EMOJIS.get(selected_entry['template'], "📝")
                    st.markdown(f"### {emoji} Editing: {selected_entry['title']} ({selected_entry['template']})")
                with col2:
                    if st.button("❌ Close", key=f"close_editor_{selected_entry['title']}", use_container_width=True):
                        st.session_state.show_editor = False
                        st.rerun()
                
                display_entry(selected_entry)
            except StopIteration:
                st.error("Selected entry not found")
                st.session_state.show_editor = False
                st.session_state.selected_entry_title = None
                st.rerun()

        # Add filter and navigation controls in an expander
        # with st.expander("🔍 Filter/Search"):
        #     # Filter controls
        #     st.markdown("### 🎛️ Filter Entries")
        #     col1, col2, col3 = st.columns(3)
        #     with col1:
        #         query = st.text_input("Search in title/content", key="search_query")
        #         if query != st.session_state.search_query:
        #             st.session_state.search_query = query
        #             st.rerun()
        #     with col2:
        #         filter_type = st.selectbox(
        #             "Filter by type",
        #             ["All"] + list(LORE_TEMPLATES.keys()),
        #             key="template_filter"
        #         )
        #         if filter_type != st.session_state.template_filter:
        #             st.session_state.template_filter = filter_type
        #             st.rerun()
        #     with col3:
        #         all_tags = set()
        #         for entry in entries:
        #             all_tags.update(entry.get('tags', []))
        #         tags = st.multiselect("Filter by tags", list(all_tags), key="tag_filter")
        #         if tags != st.session_state.selected_tags:
        #             st.session_state.selected_tags = tags
        #             st.rerun()

        #     # Navigation section
        #     st.markdown("### 📚 Navigation")
        #     nav_col1, nav_col2 = st.columns(2)
        #     with nav_col1:
        #         selected_category = st.selectbox(
        #             "Select Category",
        #             categories,
        #             index=categories.index(st.session_state.selected_category)
        #         )
        #         if selected_category != st.session_state.selected_category:
        #             st.session_state.selected_category = selected_category
        #             st.session_state.selected_entry_title = None
        #             st.rerun()
                
        #     if selected_category:
        #         category_entries = entries_by_category[selected_category]
        #         entry_titles = [e['title'] for e in category_entries]
        #         with nav_col2:
        #             selected_title = st.selectbox(
        #                 "Select Entry",
        #                 options=entry_titles,
        #                 index=entry_titles.index(st.session_state.selected_entry_title) if st.session_state.selected_entry_title in entry_titles else 0,
        #                 key=f"entry_select_{selected_category}"
        #             )
        #             if selected_title != st.session_state.selected_entry_title:
        #                 select_entry(selected_category, selected_title)
            
            # Remove the duplicated editor display code from here
            # The section starting with "Display selected entry details if one is selected"
            # and ending with display_entry(selected_entry) should be removed from inside the expander

# Add visual separator
# st.markdown("<br>", unsafe_allow_html=True)
# st.markdown("---")
# st.markdown("<br>", unsafe_allow_html=True)

# Advanced Tools Section
with st.expander("🛠️ Advanced Tools"):
    st.subheader("Advanced World Building Tools")
    
    # Only show Development Options in local environment
    if st.session_state.is_local:
        st.markdown("### 🔧 Development Options")
        dev_mode = st.toggle("Dev Mode (disable OpenAI calls)", value=st.session_state.dev_mode)
        if dev_mode != st.session_state.dev_mode:
            st.session_state.dev_mode = dev_mode
            set_setting("dev_mode", "true" if dev_mode else "false")
            st.success("Dev mode " + ("enabled" if dev_mode else "disabled"))
        st.markdown("---")
    
    # Data Management Section
    st.markdown("### 📤 Data Management")
    
    tab1, tab2 = st.tabs(["Import", "Export"])
    
    with tab1:
        st.markdown("#### 📥 Import Lore Entries")
        uploaded_json = st.file_uploader("Upload JSON File", type="json")

        if uploaded_json:
            with st.spinner("📚 Processing uploaded file..."):
                try:
                    entries = json.load(uploaded_json)
                    success = import_entries_with_progress(entries)
                    if success:
                        st.success(f"✅ Successfully imported {len(entries)} entries!")
                except Exception as e:
                    st.error(f"Failed to import: {e}")

        st.markdown("**Or paste JSON directly below:**")
        json_input = st.text_area("Paste JSON array of entries", height=200)
        if st.button("Import Pasted JSON"):
            try:
                entries = json.loads(json_input)
                success = import_entries_with_progress(entries)
                if success:
                    st.success(f"Imported {len(entries)} entries.")
            except Exception as e:
                st.error(f"Failed to import pasted JSON: {e}")
    
    with tab2:
        st.markdown("#### 📤 Export Lore Entries")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Get entries in JSON format
            entries = get_entries_for_export()
            export_json = json.dumps(entries, indent=2, ensure_ascii=False)
            
            # Create JSON download button
            st.download_button(
                label="Download as JSON",
                data=export_json,
                file_name="lore_entries.json",
                mime="application/json"
            )
            
        with col2:
            # Get entries in Markdown format
            markdown_content = get_entries_for_markdown_export()
            
            # Create Markdown download button
            st.download_button(
                label="Download as Markdown",
                data=markdown_content,
                file_name="lore_entries.md",
                mime="text/markdown"
            )
        
        # Show preview 
        st.markdown("##### Preview Export Data")
        preview_tab1, preview_tab2 = st.tabs(["JSON", "Markdown"])
        with preview_tab1:
            st.code(export_json, language="json")
        with preview_tab2:
            st.code(markdown_content, language="markdown")

    # Add separator
    st.markdown("---")
    
    # Danger Zone Section
    st.markdown("### ⚠️ Danger Zone")
    st.error("⛔ The following actions can result in permanent data loss!")
    
    if st.session_state.confirm_delete_all:
        st.error("⚠️ Click 'Confirm Delete' to permanently delete the project")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Cancel"):
                st.session_state.confirm_delete_all = False
                st.rerun()
        with col2:
            if st.button("Confirm Delete", type="primary"):
                delete_all_entries()
                delete_settings()
                st.session_state.confirm_delete_all = False
                st.success("All entries deleted.")
                st.rerun()
    else:
        if st.button("Delete Project", type="primary"):
            st.session_state.confirm_delete_all = True
            st.rerun()
    
    # Add separator before future tools info
    st.markdown("---")
    st.info("Additional world building tools coming soon...")

# After favicon configuration, add sidebar content
st.sidebar.markdown("### 🌟 Help Shape LoreA")
st.sidebar.markdown("""
    Your feedback directly influences which features we develop next!
    
    [📝 Share Your Feedback](https://docs.google.com/forms/d/e/1FAIpQLSfzb38_l6UOpwIr_5xpv3Sfw5u6zdlcV9Nvb3zpU5Mh_z9sxQ/viewform?usp=header)
    
    Every suggestion helps make LoreA a better world-building companion.
""")
st.sidebar.markdown("---")

st.sidebar.markdown("""
    **Interested in following our journey?**
    
    [🌍 Follow us on Bluesky](https://bsky.app/profile/ashlightlabs.bsky.social)
    
    [✖️ Follow us on X](https://x.com/ashlightlabs)
    """)
st.sidebar.markdown("---")

st.sidebar.markdown("""### 🗺️ Roadmap
    * MVP: LoreA Assistant <-- Current 
    * Engine Integration (Unreal, eventual Unity and custom)
    * Branching Narratives
    * Lore Generation based on player actions
    * Lore Timelines
    * World Relationships Visualization
    * ... more to come!
    """)
st.sidebar.markdown("---")