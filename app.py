import streamlit as st
import pandas as pd
from io import StringIO

# — Helpers to load files with encoding fallback —
@st.cache_data
def load_excel(uploader):
    if not uploader:
        return pd.DataFrame()
    try:
        return pd.read_excel(uploader)
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
        return pd.DataFrame()

@st.cache_data
def load_csv(uploader):
    if not uploader:
        return pd.DataFrame()
    for enc in ("utf-8", "ISO-8859-1", "latin-1"):
        try:
            uploader.seek(0)
            return pd.read_csv(uploader, encoding=enc)
        except UnicodeDecodeError:
            continue
    st.error("Could not decode CSV. Please check file encoding.")
    return pd.DataFrame()

def main():
    st.set_page_config(page_title="Merge Instructor → Comments", layout="wide")
    st.title("Merge Instructor Report into Student Comments")

    # — Upload widgets (unique keys) —
    instr_u = st.sidebar.file_uploader(
        "Instructor Report (Excel)", ["xls", "xlsx"], key="instr"
    )
    comm_u  = st.sidebar.file_uploader(
        "Student Comments (CSV)", ["csv"], key="comm"
    )

    instr_df = load_excel(instr_u)
    comm_df  = load_csv(comm_u)

    if comm_df.empty:
        st.info("Upload your Student Comments CSV first.")
        return
    if instr_df.empty:
        st.info("Then upload your Instructor Report Excel.")
        return

    # — 1) Normalize Instructor Report columns to match the Comments file —
    instr_clean = instr_df.rename(columns={
        # report → comments-file names
        "Term":                  "Term",
        "Course_Co":             "Course_Code",
        "Course_Code":           "Course_Code",   # in case your file uses this
        "Course_Na":             "Course_Name",
        "Course_Title":          "Course_Name",   # or this
        "Inst_FNam":             "Inst_FName",
        "Inst_FName":            "Inst_FName",    # or this
        "Inst_Lnam":             "Inst_LName",
        "Inst_LName":            "Inst_LName",    # or this
        "Question":              "Question",
        "QuestionKey":           "Question",      # if it’s named that
        "Response":              "Response",      # only if you actually want to override student Response
        "Comments":              "Response",      # if your report “Comments” maps to student “Response”
        "Comment_Resolved?":     "Resolved?",
        "Resolved?":             "Resolved?",
        "Notes":                 "Notes"
    })[
        [
            "Term",
            "Course_Code",
            "Course_Name",
            "Inst_FName",
            "Inst_LName",
            "Question",
            # only import these two extra columns:
            "Resolved?",
            "Notes"
        ]
    ].copy()

    # — 2) Truncate Course_Code to first 6 chars (ACC210 etc.) —
    instr_clean["Course_Code"] = instr_clean["Course_Code"].astype(str).str[:6]

    # — 3) Merge INTO the original comments DataFrame —
    merge_on = [
        "Term",
        "Course_Code",
        "Course_Name",
        "Inst_FName",
        "Inst_LName",
        "Question",
    ]
    # validate
    missing = [c for c in merge_on if c not in comm_df.columns] \
            + [c for c in merge_on if c not in instr_clean.columns]
    if missing:
        st.error("Missing columns for merge: " + ", ".join(missing))
        return

    merged = comm_df.merge(
        instr_clean,
        on=merge_on,
        how="left",
        suffixes=("", "_instr")
    )

    # — 4) Overwrite only the two import columns in the original layout —
    comm_df["Resolved?"] = merged["Resolved?"]
    comm_df["Notes"]    = merged["Notes"]

    # — 5) Show a preview & download button —
    st.header("Updated Student Comments Preview")
    st.dataframe(comm_df, use_container_width=True)

    buf = StringIO()
    comm_df.to_csv(buf, index=False)
    st.download_button(
        "📥 Download merged Comments CSV",
        buf.getvalue(),
        file_name="Student_Comments_merged.csv",
        mime="text/csv",
        key="download"
    )

if __name__ == "__main__":
    main()
