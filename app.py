import streamlit as st
import pandas as pd
from io import StringIO

# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

SEASON_MAP = {"spring": "SP", "summer": "SU", "fall": "FA"}
ROMAN_TO_NUM = {"I": "1", "II": "2"}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and standardize column names (no case change to keep UX)."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df

def derive_course_code_from_title(title: str) -> str:
    """
    Derive Course Code from Course Title.
    Ex: 'CUL210_191 Intro to ...' -> 'CUL210'
    Fallback: first token (up to space), up to 6 chars uppercased.
    """
    s = str(title).strip()
    if not s:
        return ""
    first_token = s.split(maxsplit=1)[0]          # e.g., "CUL210_191"
    head = first_token.split("_", 1)[0]           # -> "CUL210"
    return head[:6].upper()

def safe_course_name_from_title(title: str) -> str:
    """
    Extract course name from Course Title (strip the first token).
    Ex: 'CUL210_191 Intro to Something' -> 'Intro to Something'
    """
    s = str(title).strip()
    if not s:
        return ""
    parts = s.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""

def parse_term_code(project: str) -> tuple[str, str]:
    """
    Parse 'Project' into (year, code) where code is like 'SU1', 'FA2', etc.
    Expected 'Project' shape: 'YYYY Summer Term I' or similar.
    If parsing fails, return (str(project), "") so caller can decide fallback.
    """
    parts = str(project).split()
    if len(parts) == 4:
        year, season, _, roman = parts
        year = str(year).strip()
        season_code = SEASON_MAP.get(season.strip().lower(), season[:2].upper())
        term_num = ROMAN_TO_NUM.get(str(roman).upper(), "1")
        return year, f"{season_code}{term_num}"
    return str(project), ""

def compute_section_from_title_suffix(course_title: str) -> str:
    """
    Compute 2-digit section from the numeric suffix of the first token.
    Logic mirrors original: last two digits - 90 + 1 (min 1).
    'CUL210_191' -> suffix 191 -> last2=91 -> section=02
    """
    token = str(course_title).split(maxsplit=1)[0]
    suffix = token.split("_")[-1]
    try:
        val = int(suffix)
        last2 = val % 100
        section_num = max(last2 - 90 + 1, 1)
    except ValueError:
        section_num = 1
    return f"{section_num:02d}"

def format_term(project: str, course_title: str) -> str:
    """
    Build Term as 'YYYY_SS_TTn' where SS is 2-digit section, TTn is e.g., SU1.
    Fallback: return str(project) if parsing fails.
    """
    year, code = parse_term_code(project)
    if code:
        section = compute_section_from_title_suffix(course_title)
        return f"{year}_{section}_{code}"
    return str(project)

def build_output_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the normalized DF into the desired CSV schema."""
    # Decide Course_Code source
    if "Course Code" in df.columns:
        course_code_series = df["Course Code"].astype(str).str.strip().str[:6].str.upper()
    else:
        course_code_series = df["Course Title"].astype(str).apply(derive_course_code_from_title)

    out = pd.DataFrame({
        "Term":        df.apply(lambda r: format_term(r["Project"], r["Course Title"]), axis=1),
        "Course_Code": course_code_series,
        "Course_Name": df["Course Title"].astype(str).apply(safe_course_name_from_title),
        "Inst_FName":  df["Instructor Firstname"].astype(str).str.strip(),
        "Inst_LName":  df["Instructor Lastname"].astype(str).str.strip(),
        "Question":    df["QuestionKey"].astype(str),
        "Response":    df["Comments"].astype(str),
    })
    return out

def derive_filename(term_value: str) -> str:
    """
    Build filename 'YYYY_TTn_Student_Comments_Watermark.csv' where TTn is e.g., SU1.
    If Term is already a fallback (no underscores), just use it as-is.
    """
    parts = str(term_value).split("_")
    if len(parts) == 3:
        year, _, code = parts
        filename_term = f"{year}_{code}"
    else:
        filename_term = term_value
    return f"{filename_term}_Student_Comments_Watermark.csv"

# ───────────────────────────────────────────────────────────────────────────────
# Data Loading
# ───────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_excel(uploader) -> pd.DataFrame:
    if not uploader:
        return pd.DataFrame()
    try:
        df = pd.read_excel(uploader)
        return normalize_columns(df)
    except Exception as e:
        st.error(f"Failed to read Instructor Report: {e}")
        return pd.DataFrame()

# ───────────────────────────────────────────────────────────────────────────────
# App
# ───────────────────────────────────────────────────────────────────────────────

REQUIRED_BASE_COLS = [
    "Instructor Firstname",
    "Instructor Lastname",
    "Project",
    "Course Title",
    "QuestionKey",
    "Comments",
]
OPTIONAL_COLS = ["Course Code"]  # used if present

def main():
    st.set_page_config(page_title="Reformat Instructor Report", layout="wide")
    st.title("Reformat Instructor Report → Student Comments CSV")

    instr_file = st.file_uploader("Upload Instructor Report (Excel)", type=["xls", "xlsx"])
    df = load_excel(instr_file)

    if df.empty:
        st.info("Please upload your Instructor Report to begin.")
        return

    # Validate required columns (Course Code is optional)
    missing = [c for c in REQUIRED_BASE_COLS if c not in df.columns]
    with st.expander("Detected columns", expanded=False):
        st.write(list(df.columns))

    if missing:
        st.error("Missing columns in report: " + ", ".join(missing))
        st.stop()

    # Build output
    out = build_output_dataframe(df)

    # Preview
    st.header("Preview")
    st.dataframe(out, use_container_width=True)

    # Download
    first_term = out["Term"].iloc[0]
    filename = derive_filename(first_term)

    buf = StringIO()
    out.to_csv(buf, index=False)
    st.download_button(
        label="📥 Download re-formatted CSV",
        data=buf.getvalue(),
        file_name=filename,
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
