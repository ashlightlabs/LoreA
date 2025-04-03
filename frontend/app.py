import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import streamlit as st
from backend.app.services.core import add_lore_to_db, get_all_lore_from_db, generate_text_from_lore, init_db, update_lore_entry, delete_lore_entry_by_title, get_setting, set_setting

init_db()

# Load from DB
current_title = get_setting("app_title", "Lore Assistant")
current_desc = get_setting("app_description", "")

st.markdown(
    """
    ### 💬 [Give Feedback](https://docs.google.com/forms/d/e/1FAIpQLSfHAVzQDC0JXzz-aIxWum93DopQ7DHIlSUmMRuIA17HD6V5eA/viewform?usp=header)
    Let us know what’s working and what could be better.
    """,
    unsafe_allow_html=True
)

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

# Initialize form state only once
for key in ["new_title", "new_content", "new_tags", "form_status", "form_submitted"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# Clear fields BEFORE widgets render if last form was submitted
if st.session_state["form_submitted"]:
    st.session_state["new_title"] = ""
    st.session_state["new_content"] = ""
    st.session_state["new_tags"] = ""
    st.session_state["form_submitted"] = False

with st.form("Add Lore"):
    title = st.text_input("Title", key="new_title")
    content = st.text_area("Content", key="new_content")
    tags = st.text_input("Tags (comma-separated)", key="new_tags")

    submitted = st.form_submit_button("Add Lore")

    if submitted:
        add_lore_to_db(title, content, [t.strip() for t in tags.split(",")])
        st.session_state["form_status"] = "Lore added!"
        st.session_state["form_submitted"] = True
        st.rerun()

# Show success message
if st.session_state["form_status"]:
    st.success(st.session_state["form_status"])
    st.session_state["form_status"] = ""

with st.expander("📥 Import Lore"):
    st.markdown("Upload a `.json` file or paste JSON to bulk-import lore entries.")

    uploaded_file = st.file_uploader("Upload JSON File", type=["json"])
    raw_json = st.text_area("Or paste raw JSON")

    if st.button("Import Lore"):
        try:
            if uploaded_file:
                import_data = json.load(uploaded_file)
            elif raw_json.strip():
                import_data = json.loads(raw_json)
            else:
                st.warning("Please upload a file or paste valid JSON.")
                import_data = None

            if import_data:
                if isinstance(import_data, dict):
                    import_data = [import_data]

                # Get existing titles
                existing_titles = {entry["title"] for entry in get_all_lore_from_db()}

                imported_count = 0
                skipped_titles = []

                for entry in import_data:
                    if all(k in entry for k in ["title", "content", "tags"]):
                        if entry["title"] in existing_titles:
                            skipped_titles.append(entry["title"])
                        else:
                            add_lore_to_db(entry["title"], entry["content"], entry["tags"])
                            imported_count += 1

                st.success(f"Imported {imported_count} new entries.")
                if skipped_titles:
                    st.warning(f"Skipped {len(skipped_titles)} duplicate titles: {', '.join(skipped_titles)}")
                st.rerun()

        except Exception as e:
            st.error(f"Failed to import JSON: {e}")


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
