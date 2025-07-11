import streamlit as st
import pandas as pd
from io import StringIO

# — Load Excel with fallback —
@st.cache_data
def load_excel(uploader):
    if not uploader:
        return pd.DataFrame()
    try:
        return pd.read_excel(uploader)
    except Exception as e:
        st.error(f"Failed to read Instructor Report: {e}")
        return pd.DataFrame()

# — Build Term = YYYY_SS_TTn —
def format_term(project, uniqueid):
    parts = str(project).split()
    if len(parts) == 4:
        year, season, _, roman = parts
        # map I/II → 1/2
        n = {"I": "1", "II": "2"}.get(roman.upper(), "1")
        # map season → code
        season_map = {"Spring": "SP", "Summer": "SU", "Fall": "FA"}
        code = season_map.get(season, season[:2].upper()) + n
        # section based on UniqueID’s last digit
        uid = str(uniqueid).strip()
        last = uid[-1] if uid else ""
        section = "01" if last == "0" else "02" if last == "1" else "01"
        return f"{year}_{section}_{code}"
    return str(project)

def main():
    st.set_page_config(page_title="Reformat Instructor Report", layout="wide")
    st.title("Reformat Instructor Report → Student Comments CSV")

    instr_file = st.file_uploader("Upload Instructor Report (Excel)", type=["xls","xlsx"])
    df = load_excel(instr_file)
    if df.empty:
        st.info("Please upload your Instructor Report to begin.")
        return

    # required columns check
    required = [
        "Instructor Firstname",
        "Instructor Lastname",
        "Project",
        "Course Code",
        "Course Title",
        "Course UniqueID",
        "QuestionKey",
        "Comments"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error("Missing columns in report: " + ", ".join(missing))
        return

    # build reformatted table
    out = pd.DataFrame({
        "Term":         df.apply(lambda r: format_term(r["Project"], r["Course UniqueID"]), axis=1),
        "Course_Code":  df["Course Code"].astype(str).str[:6],
        "Course_Name":  df["Course Title"].astype(str).str.strip(),
        "Inst_FName":   df["Instructor Firstname"].astype(str).str.strip(),
        "Inst_LName":   df["Instructor Lastname"].astype(str).str.strip(),
        "Question":     df["QuestionKey"].astype(str),
        "Response":     df["Comments"].astype(str),
        "Comment_Type": ""
    })

    st.header("Preview of Reformatted CSV")
    st.dataframe(out, use_container_width=True)

    # determine filename
    terms = out["Term"].unique()
    term_code = terms[0] if len(terms) == 1 else "MULTI_TERM"
    filename = f"{term_code}_Comments_Watermark.csv"

    # download button
    buf = StringIO()
    out.to_csv(buf, index=False)
    st.download_button(
        "📥 Download reformatted CSV",
        buf.getvalue(),
        file_name=filename,
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
