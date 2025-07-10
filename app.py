import streamlit as st
import pandas as pd
from io import StringIO

# — Helpers to load with encoding fallback —
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
    st.error("Could not decode CSV. Check file encoding.")
    return pd.DataFrame()

# — Convert raw Term (YYYY_SS_TTn) → human Project string —
def convert_term(term_str):
    parts = str(term_str).split("_")
    if len(parts) != 3:
        return term_str
    year, sec, code = parts
    season = {
        "SP": "Summer", "SU": "Summer",
        "FA": "Fall",   "WI": "Winter"
    }.get(code[:2], code[:2])
    term_no  = code[2:]
    return f"{year} {season} Term {term_no} Section {int(sec)}"

def main():
    st.set_page_config(page_title="Merge Instructor → Comments", layout="wide")
    st.title("Merge Instructor Report into Student Comments")

    instr_u = st.sidebar.file_uploader(
        "Instructor Report (Excel)", ["xls","xlsx"], key="instr"
    )
    comm_u  = st.sidebar.file_uploader(
        "Student Comments (CSV)", ["csv"], key="comm"
    )

    instr_df  = load_excel(instr_u)
    comments  = load_csv(comm_u)

    if comments.empty:
        st.info("Upload your Student Comments CSV to begin.")
        return
    if instr_df.empty:
        st.info("Then upload your Instructor Report Excel.")
        return

    # — Normalize columns in each DF so we can join on the same names —
    # 1) Instructor Report → keys & mapped columns
    instr = instr_df.rename(columns={
        "Project":               "Project",
        "Course Code":           "Course_Code",
        "Course Title":          "Course_Name",
        "Instructor Firstname":  "Inst_FName",
        "Instructor Lastname":   "Inst_LName",
        "QuestionKey":           "Question",
        "Comments":              "Response"
    })[[
        "Project",
        "Course_Code",
        "Course_Name",
        "Inst_FName",
        "Inst_LName",
        "Question",
        "Response"
    ]].copy()
    # truncate to 6 chars
    instr["Course_Code"] = instr["Course_Code"].astype(str).str[:6]

    # 2) Student Comments → add a temporary Project column
    comments = comments.copy()
    comments["Project"] = comments["Term"].apply(convert_term)

    # — Define merge keys & validate existence —
    merge_keys = [
        "Project",
        "Course_Code",
        "Course_Name",
        "Inst_FName",
        "Inst_LName",
        "Question"
    ]
    missing = [k for k in merge_keys if k not in comments.columns] \
            + [k for k in merge_keys if k not in instr.columns]
    if missing:
        st.error("Missing columns for merge: " + ", ".join(missing))
        return

    # — Merge (left join keeps all student‐comment rows) —
    merged = pd.merge(
        comments,
        instr,
        on=merge_keys,
        how="left",
        suffixes=("", "_instr")
    )

    # — Overwrite only A–G in the original layout —
    comments["Term"]         = merged["Project"]
    comments["Course_Code"]  = merged["Course_Code"]
    comments["Course_Name"]  = merged["Course_Name"]
    comments["Inst_FName"]   = merged["Inst_FName"]
    comments["Inst_LName"]   = merged["Inst_LName"]
    comments["Question"]     = merged["Question"]
    comments["Response"]     = merged["Response"]

    # — Drop our helper column and show a preview —
    comments = comments.drop(columns=["Project"])
    st.header("Updated Student Comments Preview")
    st.dataframe(comments, use_container_width=True)

    # — Download button —
    buf = StringIO()
    comments.to_csv(buf, index=False)
    st.download_button(
        "📥 Download merged Comments CSV",
        buf.getvalue(),
        file_name="Student_Comments_merged.csv",
        mime="text/csv",
        key="download"
    )

if __name__ == "__main__":
    main()
