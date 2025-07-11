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
    # Expect project like "2025 Summer Term I"
    parts = str(project).split()
    if len(parts) == 4:
        year, season, _, roman = parts
        # I/II → 1/2
        n = {"I":"1","II":"2"}.get(roman.upper(), "1")
        # Season → SP/SU/FA
        code = {
            "Spring":"SP", "Summer":"SU", "Fall":"FA"
        }.get(season, season[:2].upper()) + n
        # Section from UniqueID’s last digit
        uid = str(uniqueid).strip()
        last = uid[-1] if uid else ""
        section = "01" if last=="0" else "02" if last=="1" else "01"
        return f"{year}_{section}_{code}"
    return str(project)

def main():
    st.set_page_config(page_title="Reformat Instructor Report", layout="wide")
    st.title("Reformat Instructor Report → Student Comments CSV")

    instr = st.file_uploader(
        "Upload Instructor Report (Excel)",
        type=["xls","xlsx"], key="instr"
    )
    df = load_excel(instr)
    if df.empty:
        st.info("Please upload your Instructor Report to begin.")
        return

    # ensure required columns exist
    req = [
        "Instructor Firstname","Instructor Lastname",
        "Project","Course Code","Course Title",
        "Course UniqueID","QuestionKey","Comments"
    ]
    missing = [c for c in req if c not in df.columns]
    if missing:
        st.error("Missing columns in Report: " + ", ".join(missing))
        return

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

    st.header("Preview")
    st.dataframe(out, use_container_width=True)

    buf = StringIO()
    out.to_csv(buf, index=False)
    st.download_button(
        "📥 Download reformatted CSV",
        buf.getvalue(),
        file_name="Instructor_As_StudentComments.csv",
        mime="text/csv",
        key="download"
    )

if __name__ == "__main__":
    main()
