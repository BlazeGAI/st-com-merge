import streamlit as st
import pandas as pd

# --- Data loaders with encoding fallback ---
@st.cache_data
def load_instructor_report(uploaded_file):
    if not uploaded_file:
        return pd.DataFrame()
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
        return pd.DataFrame()

@st.cache_data
def load_student_comments(uploaded_file):
    if not uploaded_file:
        return pd.DataFrame()
    for enc in ("utf-8", "ISO-8859-1", "latin-1"):
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc)
        except UnicodeDecodeError:
            continue
    st.error("Could not decode CSV. Please check file encoding.")
    return pd.DataFrame()

# --- Merge helper ---
def merge_data(comments_df, instr_df, on_key):
    return pd.merge(comments_df, instr_df, on=on_key, how="left")

# --- Keyword filter ---
def filter_by_keyword(df, column, keyword):
    if keyword and column in df.columns:
        return df[df[column].str.contains(keyword, case=False, na=False)]
    return df

# --- App layout ---
def main():
    st.set_page_config(page_title="Comments Dashboard", layout="wide")
    st.title("Instructor Report & Student Comments")

    # Sidebar uploads with unique keys
    st.sidebar.header("Upload Files")
    instr_file = st.sidebar.file_uploader(
        label="Instructor Report (Excel)",
        type=["xls", "xlsx"],
        key="uploader_instructor"
    )
    comm_file = st.sidebar.file_uploader(
        label="Student Comments (CSV)",
        type=["csv"],
        key="uploader_comments"
    )

    instr_df    = load_instructor_report(instr_file)
    comments_df = load_student_comments(comm_file)

    if comments_df.empty:
        st.info("Upload your Student Comments CSV to begin.")
        return

    # Determine valid merge keys
    common_keys = sorted(set(instr_df.columns) & set(comments_df.columns))
    if common_keys:
        on_key = st.sidebar.selectbox(
            "Select merge key",
            common_keys,
            key="select_merge_key"
        )
    else:
        on_key = st.sidebar.text_input(
            "No common columns found—enter merge key manually",
            value="",
            key="text_merge_key"
        )

    # Validate before merge
    if on_key:
        missing = []
        if on_key not in comments_df.columns:
            missing.append(f"`{on_key}` missing from Student Comments")
        if not instr_df.empty and on_key not in instr_df.columns:
            missing.append(f"`{on_key}` missing from Instructor Report")
        if missing:
            st.error(" • ".join(missing))
            return
        merged_df = merge_data(comments_df, instr_df, on_key)
    else:
        st.warning("Please specify a merge key.")
        return

    # Preview merged data
    st.header("Merged Data Preview")
    st.dataframe(merged_df, use_container_width=True)

    # Keyword search
    keyword = st.sidebar.text_input(
        "Keyword search in comments",
        value="",
        key="keyword_search"
    )
    filtered = filter_by_keyword(merged_df, "Comment", keyword)

    st.header("Filtered Comments")
    st.dataframe(filtered, use_container_width=True)

    # Analytics dashboard
    st.header("Analytics")
    if not filtered.empty:
        if "InstructorName" in filtered.columns:
            st.subheader("Comments per Instructor")
            counts = filtered["InstructorName"].value_counts()
            st.bar_chart(counts, use_container_width=True)

        st.subheader("Top 10 Words in Comments")
        words = (
            filtered["Comment"]
            .dropna()
            .str.split()
            .explode()
            .str.lower()
            .value_counts()
            .head(10)
        )
        st.bar_chart(words, use_container_width=True)
    else:
        st.warning("No comments match your keyword filter.")

if __name__ == "__main__":
    main()
