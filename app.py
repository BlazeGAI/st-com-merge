import streamlit as st
import pandas as pd
from io import StringIO

# — Helpers to load files with fallback encodings —
@st.cache_data
def load_excel(uploader):
    if not uploader:
        return pd.DataFrame()
    try:
        return pd.read_excel(uploader)
    except Exception as e:
        st.error(f"Failed to read Instructor Report: {e}")
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
    st.error("Failed to decode Student Comments CSV. Check its encoding.")
    return pd.DataFrame()

# — Format “Term” from Instructor Report into YYYY_01_TTn —
def format_term(raw):
    s = str(raw).strip()
    # Already in YYYY_SS_TTn?
    if s.count("_") == 2:
        return s
    # Expecting “YYYY TTn” (e.g. “2025 SP2”)
    parts = s.split()
    if len(parts) == 2:
        year, code = parts
        return f"{year}_01_{code}"
    # Otherwise, return as-is
    return s

def main():
    st.set_page_config(page_title="Append Instructor → Comments", layout="wide")
    st.title("Append Instructor Report to Student Comments")

    # Upload widgets
    instr_u = st.sidebar.file_uploader("Instructor Report (Excel)", ["xls","xlsx"], key="instr")
    comm_u  = st.sidebar.file_uploader("Student Comments (CSV)",       ["csv"],      key="comm")

    instr_df = load_excel(instr_u)
    comm_df  = load_csv(comm_u)

    if comm_df.empty:
        st.info("Step 1: Upload your Student Comments CSV.")
        return
    if instr_df.empty:
        st.info("Step 2: Upload your Instructor Report Excel.")
        return

    # — Build new rows from Instructor Report —
    # Map columns A–G exactly:
    # A: Term        ← format_term(instr_df['Term'])
    # B: Course_Code ← first 6 chars of instr_df['Course_Code']
    # C: Course_Name ← instr_df['Course_Name']
    # D: Inst_FName  ← instr_df['Inst_FName']
    # E: Inst_LName  ← instr_df['Inst_LName']
    # F: Question    ← instr_df['QuestionKey']
    # G: Response    ← instr_df['Comments']
    new_rows = pd.DataFrame({
        "Term":       instr_df.get("Term",       instr_df.get("Project", ""))\
                         .apply(format_term),
        "Course_Code": instr_df["Course_Code"].astype(str).str[:6],
        "Course_Name": instr_df["Course_Name"].astype(str),
        "Inst_FName":  instr_df["Inst_FName"].astype(str),
        "Inst_LName":  instr_df["Inst_LName"].astype(str),
        "Question":    instr_df["QuestionKey"].astype(str),
        "Response":    instr_df["Comments"].astype(str),
    })

    # — Ensure new_rows has all other columns (blank) so concat keeps sheet format —
    for col in comm_df.columns:
        if col not in new_rows.columns:
            new_rows[col] = ""

    # — Append to the end, preserving all original rows —
    updated = pd.concat([comm_df, new_rows[comm_df.columns]], ignore_index=True)

    st.header("Full Comments Sheet (original + appended)")
    st.dataframe(updated, use_container_width=True)

    # — Download button for updated CSV —
    buf = StringIO()
    updated.to_csv(buf, index=False)
    st.download_button(
        "📥 Download updated Student Comments CSV",
        data=buf.getvalue(),
        file_name="Student_Comments_appended.csv",
        mime="text/csv",
        key="download"
    )

if __name__ == "__main__":
    main()
