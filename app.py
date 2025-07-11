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

# — Build Term = YYYY_SS_TTn using numeric suffix in Course Title —
def format_term(project, course_title):
    parts = str(project).split()  # e.g. ["2025","Summer","Term","I"]
    if len(parts) == 4:
        year, season, _, roman = parts
        term_num   = {"I":"1","II":"2"}.get(roman.upper(),"1")
        season_map = {"Spring":"SP","Summer":"SU","Fall":"FA"}
        code       = season_map.get(season,season[:2].upper()) + term_num

        # extract numeric suffix from CODE_### or CODE_##
        token  = str(course_title).split(maxsplit=1)[0]
        suffix = token.split("_")[-1]
        try:
            val = int(suffix)
            last2 = val % 100        # e.g. 191→91, 90→90
            # number of sections = last2 - 90 + 1
            section_num = max(last2 - 90 + 1, 1)
        except ValueError:
            section_num = 1
        section = f"{section_num:02d}"

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

    required = [
        "Instructor Firstname","Instructor Lastname",
        "Project","Course Code","Course Title",
        "QuestionKey","Comments"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error("Missing columns in report: " + ", ".join(missing))
        return

    out = pd.DataFrame({
        "Term":        df.apply(lambda r: format_term(r["Project"], r["Course Title"]), axis=1),
        "Course_Code": df["Course Code"].astype(str).str[:6],
        "Course_Name": df["Course Title"].astype(str).apply(lambda s: s.split(" ",1)[1].strip() if " " in s else ""),
        "Inst_FName":  df["Instructor Firstname"].astype(str).str.strip(),
        "Inst_LName":  df["Instructor Lastname"].astype(str).str.strip(),
        "Question":    df["QuestionKey"].astype(str),
        "Response":    df["Comments"].astype(str)
    })

    st.header("Preview")
    st.dataframe(out, use_container_width=True)

    # build filename term as YYYY_TTn (omit section)
    unique_terms = out["Term"].unique()
    raw = unique_terms[0] if len(unique_terms)==1 else "MULTI_TERM"
    parts = raw.split("_")
    filename_term = f"{parts[0]}_{parts[-1]}" if len(parts)==3 else raw
    filename = f"{filename_term}_Student_Comments_Watermark.csv"

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
