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

# — Build the Term string as YYYY_SS_TTn, with SS from Course UniqueID’s last digit —
def make_term(project_str, uniqueid):
    year, season, _, roman = str(project_str).split()
    # Roman → 1/2
    roman_map  = {"I": "1", "II": "2"}
    num         = roman_map.get(roman.upper(), "1")
    # Season → SP/SU/FA/WI
    season_map = {"Spring":"SP","Summer":"SU","Fall":"FA","Winter":"WI"}
    code        = season_map.get(season, season[:2].upper()) + num
    # Section code based on UniqueID’s last digit
    last_digit = str(uniqueid).strip()[-1]
    section    = "01" if last_digit == "0" else "02" if last_digit == "1" else f"0{last_digit}"
    return f"{year}_{section}_{code}"

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

    # — Build only columns A–G from Instructor Report —
    new = pd.DataFrame({
        "Term":        instr_df.apply(lambda r: make_term(r["Project"], r["Course UniqueID"]), axis=1),
        "Course_Code": instr_df["Course Code"].astype(str).str[:6],
        "Course_Name": instr_df["Course Code"].astype(str).str[:6]
                         + "_" 
                         + instr_df["Course UniqueID"].astype(str)
                         + " "
                         + instr_df["Course Title"].astype(str),
        "Inst_FName":  instr_df["Instructor Firstname"].astype(str),
        "Inst_LName":  instr_df["Instructor Lastname"].astype(str),
        "Question":    instr_df["QuestionKey"].astype(str),
        "Response":    instr_df["Comments"].astype(str),
    })

    # — Pad out any extra columns so concat keeps your sheet’s layout —
    for col in comm_df.columns:
        if col not in new.columns:
            new[col] = ""

    # — Append without touching the original rows —
    appended = pd.concat([comm_df, new[comm_df.columns]], ignore_index=True)

    st.header("Full Comments Sheet (original + appended)")
    st.dataframe(appended, use_container_width=True)

    # — Download button —
    buf = StringIO()
    appended.to_csv(buf, index=False)
    st.download_button(
        "📥 Download updated Student Comments CSV",
        data=buf.getvalue(),
        file_name="Student_Comments_appended.csv",
        mime="text/csv",
        key="download"
    )

if __name__ == "__main__":
    main()
