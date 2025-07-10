import streamlit as st
import pandas as pd
from io import StringIO

# --- Loaders with encoding fallback ---
@st.cache_data
def load_excel(u):
    if not u:
        return pd.DataFrame()
    try:
        return pd.read_excel(u)
    except Exception as e:
        st.error(f"Failed to read Excel: {e}")
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
    st.error("Could not decode CSV. Check file encoding.")
    return pd.DataFrame()

# --- Convert Term strings into Project ---
def convert_term(term_str):
    parts = term_str.split("_")
    if len(parts) != 3:
        return term_str
    year, sec, code = parts
    season = {
        "SP": "Summer", 
        "SU": "Summer",
        "FA": "Fall",
        "WI": "Winter"
    }.get(code[:2], code[:2])
    term_no = code[2:]
    return f"{year} {season} Term {term_no} Section {int(sec)}"

def main():
    st.set_page_config(page_title="Merge Instructor → Comments", layout="wide")
    st.title("Merge Instructor Report into Student Comments")

    instr_file = st.sidebar.file_uploader(
        "Instructor Report (Excel)", ["xls", "xlsx"], key="instr_upload"
    )
    comm_file = st.sidebar.file_uploader(
        "Student Comments (CSV)", ["csv"], key="comm_upload"
    )

    instr_df = load_excel(instr_file)
    comm_df  = load_csv(comm_file)

    if comm_df.empty:
        st.info("Upload your Student Comments CSV first.")
        return
    if instr_df.empty:
        st.info("Then upload your Instructor Report Excel.")
        return

    # --- Normalize Student Comments ---
    comm_df = comm_df.rename(columns={
        "Term":        "Term_raw",
        "Course_Code": "Course_Code",
        "Course_Name": "Course_Name",
        "Inst_FName":  "Inst_FName",
        "Inst_LName":  "Inst_LName",
        "Question":    "QuestionKey",
        "Response":    "Comments"
    })
    comm_df["Project"] = comm_df["Term_raw"].astype(str).apply(convert_term)
    comm_df["Course_Code"] = comm_df["Course_Code"].astype(str).str[:6]

    # --- Normalize Instructor Report ---
    instr_df = instr_df.rename(columns={
        "Instructor Firstname": "Inst_FName",
        "Instructor Lastname":  "Inst_LName",
        "Course Code":          "Course_Code",
        "Course Title":         "Course_Name"
    })

    # --- Define merge keys & validate ---
    keys = [
        "Project",
        "Course_Code",
        "Course_Name",
        "Inst_FName",
        "Inst_LName",
        "QuestionKey"
    ]
    missing = [k for k in keys if k not in comm_df.columns] \
            + [k for k in keys if k not in instr_df.columns]
    if missing:
        st.error("Missing columns for merge: " + ", ".join(missing))
        return

    # --- Perform the merge ---
    merged = pd.merge(
        comm_df,
        instr_df,
        on=keys,
        how="left",
        suffixes=("", "_instr")
    ).drop(columns=["Term_raw"])

    st.header("Preview of Merged Comments")
    st.dataframe(merged, use_container_width=True)

    # --- Download button ---
    csv_buf = StringIO()
    merged.to_csv(csv_buf, index=False)
    st.download_button(
        "📥 Download updated Comments CSV",
        data=csv_buf.getvalue(),
        file_name="Student_Comments_merged.csv",
        mime="text/csv",
        key="download_merged"
    )

if __name__ == "__main__":
    main()
