import sys
import os
import pdb
from typing import Dict, Any, List, Optional
import streamlit as st
import json

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
    get_entries_for_export,
    get_entries_for_markdown_export,
    generate_field_content
)

init_db()
st.set_page_config(page_title="Lore Assistant", layout="wide")

# Initialize all session state variables
if "project_title" not in st.session_state:
    st.session_state.project_title = get_setting("project_title") or "Untitled Project"
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

st.title(st.session_state["project_title"])
st.caption(f"*{st.session_state['project_description']}*")

with st.expander("⚙️ Project Settings"):
    # Project Info Section
    st.subheader("📋 Project Information")
    new_title = st.text_input("Project Title", value=st.session_state["project_title"])
    if st.button("Save Title"):
        st.session_state["project_title"] = new_title
        set_setting("project_title", new_title)
        st.success("Title updated.")

    new_desc = st.text_area("Project Description", value=st.session_state["project_description"])
    if st.button("Save Description"):
        st.session_state["project_description"] = new_desc
        set_setting("project_description", new_desc)
        st.success("Description updated.")

    # Developer Settings Section
    st.markdown("---")
    st.subheader("🛠️ Developer Settings")
    dev_mode = st.toggle("Dev Mode (disable OpenAI calls)", value=st.session_state.dev_mode)
    if dev_mode != st.session_state.dev_mode:
        st.session_state.dev_mode = dev_mode
        set_setting("dev_mode", "true" if dev_mode else "false")
        st.success("Dev mode " + ("enabled" if dev_mode else "disabled"))

    # Data Management Section
    st.markdown("---")
    st.subheader("📤 Data Management")
    
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

    # Danger Zone Section
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("## ⚠️ Danger Zone")
    st.error("⛔ The following actions can result in permanent data loss!")
    
    if st.session_state.confirm_delete_all:
        st.error("⚠️ Click 'Confirm Delete' to permanently delete all entries")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Cancel"):
                st.session_state.confirm_delete_all = False
                st.rerun()
        with col2:
            if st.button("Confirm Delete", type="primary"):
                delete_all_entries()
                st.session_state.confirm_delete_all = False
                st.success("All entries deleted.")
                st.rerun()
    else:
        if st.button("Delete All Entries"):
            st.session_state.confirm_delete_all = True
            st.rerun()

# --- Template-Based Lore Entry Section ---
LORE_TEMPLATES = {
    "Character": ["Name", "Role", "Motivation", "Relationships", "Tags"],
    "Location": ["Name", "Description", "Mood", "Significance", "Tags"],
    "Faction": ["Name", "Goals", "Beliefs / Code", "Allies / Enemies", "Tags"],
    "Event": ["Name", "Summary", "Who Was Involved", "Why It Matters", "Tags"],
    "Item / Artifact": ["Name", "Description", "Powers / Purpose", "Origin / Lore", "Tags"]
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

with st.expander("📝 Add New Entry"):
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
                content=fields_dict,  # Pass the entire fields dictionary
                tags=tags,
                template=selected_template
            )
            st.success("Lore entry saved!")
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
        st.markdown("---")
        st.markdown("### 🪶 Lore Assistant")
        
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
                
                # Add buttons in columns
                col_gen1, col_gen2, col_gen3 = st.columns([1, 1, 2])
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
    st.markdown("## ✨ Lore Entries")
    
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
        
        # Ensure valid category selection
        if not st.session_state.selected_category or st.session_state.selected_category not in categories:
            st.session_state.selected_category = categories[0]
            st.session_state.selected_entry_title = None
            
        if st.session_state.selected_category:
            category_entries = entries_by_category[st.session_state.selected_category]
            entry_titles = [e['title'] for e in category_entries]
            
            # Display selected entry first
            if st.session_state.selected_entry_title:
                selected_entry = next(e for e in category_entries if e['title'] == st.session_state.selected_entry_title)
                display_entry(selected_entry)
        
        # Add filter controls after entry display
        st.markdown("### 🔍 Filter Entries")
        col1, col2, col3 = st.columns(3)
        with col1:
            query = st.text_input("Search in title/content", key="search_query")
            if query != st.session_state.search_query:
                st.session_state.search_query = query
                st.rerun()
        with col2:
            filter_type = st.selectbox(
                "Filter by type",
                ["All"] + list(LORE_TEMPLATES.keys()),
                key="template_filter"
            )
            if filter_type != st.session_state.template_filter:
                st.session_state.template_filter = filter_type
                st.rerun()
        with col3:
            all_tags = set()
            for entry in entries:
                all_tags.update(entry.get('tags', []))
            tags = st.multiselect("Filter by tags", list(all_tags), key="tag_filter")
            if tags != st.session_state.selected_tags:
                st.session_state.selected_tags = tags
                st.rerun()
                
        # Navigation section after filters
        st.markdown("### 📚 Navigation")
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            selected_category = st.selectbox(
                "Select Category",
                categories,
                index=categories.index(st.session_state.selected_category)
            )
            if selected_category != st.session_state.selected_category:
                st.session_state.selected_category = selected_category
                st.session_state.selected_entry_title = None
                st.rerun()
                
        if selected_category:
            category_entries = entries_by_category[selected_category]
            entry_titles = [e['title'] for e in category_entries]
            with nav_col2:
                selected_title = st.selectbox(
                    "Select Entry",
                    options=entry_titles,
                    index=entry_titles.index(st.session_state.selected_entry_title) if st.session_state.selected_entry_title in entry_titles else 0,
                    key=f"entry_select_{selected_category}"
                )
                if selected_title != st.session_state.selected_entry_title:
                    select_entry(selected_category, selected_title)