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

# — Convert “Project” (e.g. “2025 Summer Term I”) → “2025_01_SU1” etc. —
def format_term(proj):
    parts = str(proj).split()               # ["2025","Summer","Term","I"]
    if len(parts) == 4:
        year, season, _, roman = parts
        # map roman numerals I, II, III → 1,2,3
        roman_map = {"I":"1","II":"2","III":"3","IV":"4"}
        num = roman_map.get(roman, roman)
        season_map = {"Spring":"SP","Summer":"SU","Fall":"FA","Winter":"WI"}
        code = season_map.get(season, season[:2].upper()) + num
        return f"{year}_01_{code}"
    return str(proj)

def main():
    st.set_page_config(page_title="Append Instructor → Comments", layout="wide")
    st.title("Append Instructor Report to Student Comments")

    instr_u = st.sidebar.file_uploader("Instructor Report (Excel)", ["xls","xlsx"], key="instr")
    comm_u  = st.sidebar.file_uploader("Student Comments (CSV)",       ["csv"],      key="comm")

    instr_df = load_excel(instr_u)
    comm_df  = load_csv(comm_u)

    if comm_df.empty:
        st.info("1) Upload your Student Comments CSV first.")
        return
    if instr_df.empty:
        st.info("2) Then upload your Instructor Report Excel.")
        return

    # — Build new rows from Instructor Report —
    # A: Term        ← format_term(instr_df['Project'])
    # B: Course_Code ← first 6 chars of instr_df['Course Code']
    # C: Course_Name ← f"{Code}_{UniqueID} {Title}"
    # D: Inst_FName  ← instr_df['Instructor Firstname']
    # E: Inst_LName  ← instr_df['Instructor Lastname']
    # F: Question    ← instr_df['QuestionKey']
    # G: Response    ← instr_df['Comments']
    new = pd.DataFrame({
        "Term":        instr_df["Project"].map(format_term),
        "Course_Code": instr_df["Course Code"].astype(str).str[:6],
        "Course_Name": instr_df["Course Code"].astype(str)
                         + "_"
                         + instr_df["Course UniqueID"].astype(str)
                         + " "
                         + instr_df["Course Title"].astype(str),
        "Inst_FName":  instr_df["Instructor Firstname"].astype(str),
        "Inst_LName":  instr_df["Instructor Lastname"].astype(str),
        "Question":    instr_df["QuestionKey"].astype(str),
        "Response":    instr_df["Comments"].astype(str),
    })

    # — Preserve every other column (blank for new rows) —
    for col in comm_df.columns:
        if col not in new.columns:
            new[col] = ""

    # — Append (no in-place edits of original rows) —
    appended = pd.concat([comm_df, new[comm_df.columns]], ignore_index=True)

    st.header("Full Comments Sheet (original + appended)")
    st.dataframe(appended, use_container_width=True)

    # — Download updated CSV —
    buf = StringIO()
    appended.to_csv(buf, index=False)
    st.download_button(
        "📥 Download updated Student Comments CSV",
        buf.getvalue(),
        file_name="Student_Comments_appended.csv",
        mime="text/csv",
        key="download"
    )

if __name__ == "__main__":
    main()
