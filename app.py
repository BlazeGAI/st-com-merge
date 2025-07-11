import streamlit as st
import pandas as pd
from io import StringIO

# — Loader for Excel with fallback —
@st.cache_data
def load_excel(uploader):
    if not uploader:
        return pd.DataFrame()
    try:
        return pd.read_excel(uploader)
    except Exception as e:
        st.error(f"Failed to read Instructor Report: {e}")
        return pd.DataFrame()

# — Build Term as YYYY_SS_TTn using UniqueID’s last digit —
def format_term(project, uniqueid):
    # project: “2025 Summer Term I”, uniqueid: e.g. “190” or “191”
    parts = str(project).split()
    if len(parts) == 4:
        year, season, _, roman = parts
        # I/II → 1/2
        roman_map  = {"I":"1","II":"2"}
        num        = roman_map.get(roman.upper(), "1")
        # Spring/Summer/Fall/Winter → SP/SU/FA/WI
        season_map = {"Spring":"SP","Summer":"SU","Fall":"FA","Winter":"WI"}
        code       = season_map.get(season, season[:2].upper()) + num
        # UniqueID’s last digit → section 01 if 0, 02 if 1
        last       = str(uniqueid).strip()[-1]
        section    = "01" if last == "0" else "02" if last == "1" else f"{int(last):02d}"
        return f"{year}_{section}_{code}"
    return str(project)

def main():
    st.set_page_config(page_title="Reformat Instructor Report", layout="wide")
    st.title("Reformat Instructor Report → Student Comments CSV")

    instr_file = st.file_uploader(
        "Upload Instructor Report (Excel)",
        type=["xls", "xlsx"],
        key="instr"
    )
    df = load_excel(instr_file)
    if df.empty:
        st.info("Please upload your Instructor Report to begin.")
        return

    # make sure we have the columns you listed
    required = [
        "Instructor Firstname", "Instructor Lastname",
        "Project", "Course Code", "Course Title",
        "Course UniqueID", "QuestionKey", "Comments"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error("Missing columns in Report: " + ", ".join(missing))
        return

    # build the new table
    out = pd.DataFrame({
        "Term":          df.apply(lambda r: format_term(r["Project"], r["Course UniqueID"]), axis=1),
        "Course_Code":   df["Course Code"].astype(str).str[:6],
        "Course_Name":   df["Course Title"].astype(str).str.strip(),
        "Inst_FName":    df["Instructor Firstname"].astype(str).str.strip(),
        "Inst_LName":    df["Instructor Lastname"].astype(str).str.strip(),
        "Question":      df["QuestionKey"].astype(str),
        "Response":      df["Comments"].astype(str),
        "Comment_Type":  ""  # blank by default
    })

    st.header("Preview of Reformatted CSV")
    st.dataframe(out, use_container_width=True)

    # download button
    buf = StringIO()
    out.to_csv(buf, index=False)
    st.download_button(
        "📥 Download reformatted CSV",
        buf.getvalue(),
        file_name="Instructor_As_StudentComments.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
