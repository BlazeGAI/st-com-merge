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

# — Build Term = YYYY_SS_TTn, using the numeric suffix in Course Title —
def format_term(project, course_title):
    # project: "2025 Summer Term I"
    parts = str(project).split()
    if len(parts) == 4:
        year, season, _, roman = parts
        n = {"I": "1", "II": "2"}.get(roman.upper(), "1")
        season_map = {"Spring": "SP", "Summer": "SU", "Fall": "FA"}
        code = season_map.get(season, season[:2].upper()) + n

        # extract section-id from title, e.g. "CUL210_191 Comparative Cultures"
        first_token = str(course_title).split(maxsplit=1)[0]
        # assume format CODE_UNIQUEID
        uniqueid = first_token.split("_")[-1]
        last = uniqueid[-1] if uniqueid.isdigit() else "0"
        section = "01" if last == "0" else "02"

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

    # required columns
    req = [
        "Instructor Firstname", "Instructor Lastname",
        "Project", "Course Code", "Course Title",
        "QuestionKey", "Comments"
    ]
    missing = [c for c in req if c not in df.columns]
    if missing:
        st.error("Missing columns in report: " + ", ".join(missing))
        return

    # build reformatted table
    out = pd.DataFrame({
        "Term":        df.apply(lambda r: format_term(r["Project"], r["Course Title"]), axis=1),
        "Course_Code": df["Course Code"].astype(str).str[:6],
        "Course_Name": df["Course Title"].astype(str).apply(
                          lambda s: s.split(" ",1)[1] if " " in s else ""
                       ).str.strip(),
        "Inst_FName":  df["Instructor Firstname"].astype(str).str.strip(),
        "Inst_LName":  df["Instructor Lastname"].astype(str).str.strip(),
        "Question":    df["QuestionKey"].astype(str),
        "Response":    df["Comments"].astype(str)
    })

    st.header("Preview")
    st.dataframe(out, use_container_width=True)

    # determine filename
    terms = out["Term"].unique()
    term_code = terms[0] if len(terms)==1 else "MULTI_TERM"
    filename = f"{term_code}_Comments_Watermark.csv"

    # download button
    buf = StringIO()
    out.to_csv(buf, index=False)
    st.download_button(
        "📥 Download re-formatted CSV",
        buf.getvalue(),
        file_name=filename,
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
