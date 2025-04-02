import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import streamlit as st
from backend.app.services.core import add_lore_to_db, get_all_lore_from_db, generate_text_from_lore, init_db, update_lore_entry, delete_lore_entry_by_title, get_setting, set_setting

init_db()

# Load from DB
current_title = get_setting("app_title", "Lore Assistant")
current_desc = get_setting("app_description", "")

# Show on page
st.title(current_title)
if current_desc.strip():
    st.markdown(f"_{current_desc}_")

# Editor hidden in an expander
with st.expander("Edit Project Info"):
    new_title = st.text_input("Project title", value=current_title)
    new_desc = st.text_area("Project description", value=current_desc, height=100)
    if st.button("Save Project Info"):
        set_setting("app_title", new_title)
        set_setting("app_description", new_desc)
        st.success("Project info updated!")
        st.rerun()

with st.form("Add Lore"):
    title = st.text_input("Title")
    content = st.text_area("Content")
    tags = st.text_input("Tags (comma-separated)")
    submitted = st.form_submit_button("Add Lore")
    if submitted:
        add_lore_to_db(title, content, [t.strip() for t in tags.split(",")])
        st.success("Lore added.")

st.header("All Lore Entries (Editable)")
lore_entries = get_all_lore_from_db()
for entry in lore_entries:
    with st.expander(entry["title"]):
        new_title = st.text_input(f"Title ({entry['title']})", value=entry["title"], key=f"title_{entry['title']}")
        new_content = st.text_area(f"Content ({entry['title']})", value=entry["content"], key=f"content_{entry['title']}")
        new_tags_raw = st.text_input(f"Tags ({entry['title']})", value=", ".join(entry["tags"]), key=f"tags_{entry['title']}")
        if st.button(f"Save Changes ({entry['title']})"):
            new_tags = [t.strip() for t in new_tags_raw.split(",")]
            update_lore_entry(entry["title"], new_title, new_content, new_tags)
            st.success(f"Updated: {new_title}")
            st.rerun()
        if st.button(f"Delete Entry ({entry['title']})", key=f"delete_{entry['title']}"):
            delete_lore_entry_by_title(entry["title"])
            st.warning(f"Deleted: {entry['title']}")
            st.rerun()

st.header("Generate Text from Lore")
user_prompt = st.text_area("Enter a prompt")
if st.button("Generate"):
    result = generate_text_from_lore(user_prompt, get_all_lore_from_db())
    st.write(result)
