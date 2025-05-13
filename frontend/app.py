import sys
import os
import pdb
from typing import Dict, Any, List, Optional
import streamlit as st
import json
from PIL import Image

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

init_db()
st.set_page_config(page_title="Lore Assistant", layout="wide")

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
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond&family=Lora&display=swap');

html, body, [class*="css"]  {
   font-family: 'EB Garamond', 'Lora', serif;
   background-color: #F1E8D7;
   color: #2B2B2B;
}

h1 {
   font-family: 'Lora', italic;
   color: #B54B27;
}
h2, h3 {
   font-family: 'Lora', serif;
   color: #B54B27;
}

/* Logo styles */
.logo-container {
    position: absolute;
    top: 1rem;
    right: 2rem;
    z-index: 1000;
    width: 80px;
    height: 80px;
    opacity: 0.85;
    transition: opacity 0.2s;
}

.logo-container:hover {
    opacity: 1;
}

/* Ensure logo doesn't overlap with content */
.main {
    margin-right: 100px;
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

entries = get_all_lore_from_db()
expanded = False
if(entries == []):
    st.markdown("🗺️ **Welcome to LoreA!**")
    st.markdown("Let’s start building your world.")
    st.markdown("Create a **character**, **location**, or **artifact** using the entry form below.")
    
    st.markdown("Once you have some entries, you can use the Lore Assistant to generate content and manage your lore.")
    expanded = True
with st.expander("📝 Add New Entry", expanded):
    st.subheader("Template-Based Entry")
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
                #### Your AI Writing Assistant
                LoreA helps you develop and enrich your world by providing creative suggestions 
                for your lore entries.
                
                #### How to Use:
                1. Select any field you want to work on
                2. Choose a generation style:
                        
                   • **Default** - Balanced, straightforward content
                        
                   • **Flavor Text** - Adds narrative flair
                        
                   • **World-Building Detail** - Focuses on deeper lore
                        
                   • **Narrative Hook** - Creates intriguing story hooks
                3. Optionally add a prompt to guide the AI
                4. Click "Inspire Me" to generate suggestions
            """)
        
        # Get available fields for current template (excluding Name and Tags)
        available_fields = [
            field for field in LORE_TEMPLATES[entry['template']]
            if field not in ["Name", "Tags"]
        ]
        
        # Field selection dropdown
        selected_field = st.selectbox(
            "Select field to work with",
            ["Select a field..."] + available_fields,  # Add default option
            key=f"field_select_{entry['title']}"
        )
        
        # Only show additional controls if a valid field is selected
        if selected_field and selected_field != "Select a field...":
            # Add Generation Style dropdown with dynamic options
            available_styles = FIELD_TO_STYLES.get(selected_field, ["Default"])
            generation_style = st.selectbox(
                "Generation Style",
                available_styles,
                key=f"style_{entry['title']}_{selected_field}"
            )
            
            current_content = entry['fields'].get(selected_field, "")
            prompt = st.text_input(
                "Enter a prompt (optional)",
                key=f"prompt_{entry['title']}_{selected_field}",
                help="Enter a prompt for the AI assistant to help with this field"
            )
            
            # Add Inspire Me button and preview
            if st.button("✨ Inspire Me", key=f"inspire_{entry['title']}_{selected_field}"):
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
                st.markdown("#### ✨ Generated Content")
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
                entry_titles = [e['title'] for e in category_entries]
                
                # Display cards for all entries in the category
                for entry in category_entries:
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
                    st.markdown("---")
                
                if not category_entries:
                    st.info(f"No {category} entries found.")
            
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
    
    # Developer Settings with a toggle
    st.markdown("### 🔧 Development Options")
    dev_mode = st.toggle("Dev Mode (disable OpenAI calls)", value=st.session_state.dev_mode)
    if dev_mode != st.session_state.dev_mode:
        st.session_state.dev_mode = dev_mode
        set_setting("dev_mode", "true" if dev_mode else "false")
        st.success("Dev mode " + ("enabled" if dev_mode else "disabled"))
    
    # Add separator
    st.markdown("---")
    
    # Data Management Section
    st.markdown("### 📤 Data Management")
    
    tab1, tab2 = st.tabs(["Import", "Export"])
    
    with tab1:
        st.markdown("#### 📥 Import Lore Entries")
        uploaded_json = st.file_uploader("Upload JSON File", type="json")
        if uploaded_json:
            try:
                entries = json.load(uploaded_json)
                for entry in entries:
                    add_lore_to_db(
                        title=entry["fields"]["Name"],
                        content=entry["fields"],
                        tags=entry["fields"].get("Tags", []),
                        template=entry["template"],
                        linked_entries=entry.get("linked_entries", [])
                    )
                st.success(f"Imported {len(entries)} entries.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to import: {e}")

        st.markdown("**Or paste JSON directly below:**")
        json_input = st.text_area("Paste JSON array of entries", height=200)
        if st.button("Import Pasted JSON"):
            try:
                entries = json.loads(json_input)
                for entry in entries:
                    add_lore_to_db(
                        title=entry["fields"]["Name"],
                        content=entry["fields"],
                        tags=entry["fields"].get("Tags", []),
                        template=entry["template"],
                        linked_entries=entry.get("linked_entries", [])
                    )
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

