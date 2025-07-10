import streamlit as st
import pandas as pd
from io import StringIO

# --- helpers to load with encoding fallback ---
@st.cache_data
def load_excel(u):
    if not u:
        return pd.DataFrame()
    try:
        return pd.read_excel(u)
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_csv(u):
    if not u:
        return pd.DataFrame()
    for enc in ("utf-8", "ISO-8859-1", "latin-1"):
        try:
            u.seek(0)
            return pd.read_csv(u, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.DataFrame()

# --- convert Term strings into your Project format ---
def convert_term(term_str):
    parts = term_str.split("_")
    if len(parts) != 3:
        return term_str
    year, sec, code = parts
    season = {"SP": "Summer", "SU": "Summer", "FA": "Fall", "WI": "Winter"}.get(code[:2], code[:2])
    term_no = code[2:]
    return f"{year} {season} Term {term_no} Section {int(sec)}"

def main():
    st.set_page_config(page_title="Merge Instructor → Comments", layout="wide")
    st.title("Merge Instructor Report into Student Comments")

    # --- uploaders ---
    instr_file = st.sidebar.file_uploader("Instructor Report (Excel)", ["xls","xlsx"], key="i1")
    comm_file  = st.sidebar.file_uploader("Student Comments (CSV)", key="i2")

    instr_df   = load_excel(instr_file)
    comments   = load_csv(comm_file)

    if comments.empty:
        st.info("Please upload your Student Comments CSV.")
        return
    if instr_df.empty:
        st.info("Please upload your Instructor Report Excel.")
        return

    # --- normalize Student Comments to match your schema ---
    comments = comments.rename(columns={
        "Term":        "Term_raw",
        "Course_Code": "Course_Code",
        "Course_Name": "Course_Name",
        # adjust these if your headers are truncated:
        "Inst_FNam":   "Inst_FName",
        "Inst_LNam":   "Inst_LName",
        "Question":    "QuestionKey",
        "Response":    "Comments"
    })

    # apply the Term → Project conversion
    comments["Project"] = comments["Term_raw"].astype(str).apply(convert_term)
    # truncate course code to 6 chars
    comments["Course_Code"] = comments["Course_Code"].astype(str).str[:6]

    # --- define the merge keys and validate ---
    keys = ["Project","Course_Code","Course_Name","Inst_FName","Inst_LName","QuestionKey"]
    missing = [k for k in keys if k not in comments.columns] + [k for k in keys if k not in instr_df.columns]
    if missing:
        st.error("Missing columns for merge: " + ", ".join(missing))
        return

    # --- perform the merge, keeping all original comment rows ---
    merged = pd.merge(
        comments,
        instr_df,
        on=keys,
        how="left",
        suffixes=("", "_instr")
    )

    # remove helper columns if you like:
    merged = merged.drop(columns=["Term_raw"])

    st.header("Preview of merged Comments file")
    st.dataframe(merged, use_container_width=True)

    # --- offer download of updated Comments CSV ---
    csv_buf = StringIO()
    merged.to_csv(csv_buf, index=False)
    st.download_button(
        label="📥 Download updated Comments CSV",
        data=csv_buf.getvalue(),
        file_name="Student_Comments_merged.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
