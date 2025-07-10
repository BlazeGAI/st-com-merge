import streamlit as st
import pandas as pd

# Functions to load data
@st.cache_data
def load_instructor_report(uploaded_file):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    return pd.DataFrame()

@st.cache_data
def load_student_comments(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    for enc in ("utf-8", "ISO-8859-1", "latin-1"):
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc)
        except UnicodeDecodeError:
            continue
    st.error("Failed to decode CSV. Please check file encoding.")
    return pd.DataFrame()

# Merge instructor data into comments based on a common key

def merge_data(instructor_df, comments_df, on_key):
    if not instructor_df.empty and not comments_df.empty:
        return pd.merge(comments_df, instructor_df, on=on_key, how='left')
    return comments_df

# Filter comments by keyword

def keyword_search(df, keyword, column):
    if keyword:
        return df[df[column].str.contains(keyword, case=False, na=False)]
    return df

# Streamlit app

def main():
    st.set_page_config(page_title="Comments Dashboard", layout="wide")
    st.title("Instructor Report & Student Comments Dashboard")

    st.sidebar.header("Upload Files")
    instr_file = st.sidebar.file_uploader(
        "Upload Instructor Report (Excel)", type=["xlsx", "xls"]
    )
    comments_file = st.sidebar.file_uploader(
        "Upload Student Comments (CSV)", type=["csv"]
    )

    instr_df = load_instructor_report(instr_file)
    comments_df = load_student_comments(comments_file)

    if comments_df.empty:
        st.info("Please upload the Student Comments CSV to get started.")
        return

    # Allow user to specify the merge key
    on_key = st.sidebar.text_input(
        "Merge on column", value="StudentID"
    )

    merged_df = merge_data(instr_df, comments_df, on_key)

    # Display merged data
    st.header("Merged Data Preview")
    st.dataframe(merged_df)

    # Keyword search
    keyword = st.sidebar.text_input("Keyword Search in Comments")
    filtered_df = keyword_search(merged_df, keyword, column="Comment")

    st.header("Filtered Comments")
    st.dataframe(filtered_df)

    # Dashboard analytics
    st.header("Analytics Dashboard")
    if not filtered_df.empty:
        # Example chart: comment count per instructor
        if 'InstructorName' in filtered_df.columns:
            chart_data = filtered_df['InstructorName'].value_counts()
            st.subheader("Comments per Instructor")
            st.bar_chart(chart_data)
        # Example chart: word frequency
        st.subheader("Top Commented Keywords")
        # Basic word count (split by whitespace)
        words = filtered_df['Comment'].dropna().str.split().explode()
        top_words = words.value_counts().head(10)
        st.bar_chart(top_words)
    else:
        st.warning("No comments match the keyword search.")

if __name__ == "__main__":
    main()
