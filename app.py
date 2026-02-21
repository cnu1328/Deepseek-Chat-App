import streamlit as st
import pandas as pd
import re
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

st.set_page_config(
    page_title="Voter Text to Excel Converter",
    page_icon="📄",
    layout="wide"
)

st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #0052a3;
    }
    h1 {
        color: #0066cc;
    }
    .subtitle {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

DEFAULT_REGEX = {
    "voter_id": r'EPIC\s*No\.?\s*([A-Z]{3}\d{7})',
    "ac_ps_serial": r'A\.?C\.?\s*No\.?-?\s*PS\.?\s*No\.?-?\s*SL\.?\s*No\.?\s*:\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)',
    "name": r'Name\s*:\s*(.+?)(?=\nFather\s*Name|\nHusband|\nAge)',
    "father_name": r'Father\s*Name\s*:\s*(.+?)(?=\nAge|\nSex|\nDoor|\nEPIC)',
    "husband_name": r'Husband\s*Name\s*:?\s*(.+?)(?=\nAge)',
    "mother_name": r'Mother\s*Name\s*:?\s*(.+?)(?=\nAge|\nSex|\nDoor|\nEPIC)',
    "age_gender": r'Age\s*:\s*(\d{1,3})\s*Sex\s*:\s*:?\s*([MF])',
    "door_no": r'Door\s*No\.?\s*:\s*(.+?)(?=\nEPIC)',
}

REGEX_FLAGS = {
    "voter_id": 0,
    "ac_ps_serial": re.IGNORECASE,
    "name": re.IGNORECASE,
    "father_name": re.IGNORECASE | re.DOTALL,
    "husband_name": re.IGNORECASE | re.DOTALL,
    "mother_name": re.IGNORECASE | re.DOTALL,
    "age_gender": re.IGNORECASE,
    "door_no": re.IGNORECASE,
}

REGEX_LABELS = {
    "voter_id": "Voter ID",
    "ac_ps_serial": "AC-PS-Serial (3 capture groups)",
    "name": "Voter Name",
    "father_name": "Father Name",
    "husband_name": "Husband Name",
    "mother_name": "Mother Name",
    "age_gender": "Age + Gender (2 capture groups)",
    "door_no": "Door / House Number",
}

REGEX_DESCRIPTIONS = {
    "voter_id": "Captures the voter ID like XTM0650672. Must have 1 capture group.",
    "ac_ps_serial": "Captures AC number, PS number, Serial number. Must have 3 capture groups.",
    "name": "Captures the voter's name. Must have 1 capture group.",
    "father_name": "Captures the father's name. Must have 1 capture group.",
    "husband_name": "Captures the husband's name. Must have 1 capture group.",
    "mother_name": "Captures the mother's name. Must have 1 capture group.",
    "age_gender": "Captures age and gender together. Must have 2 capture groups (age, gender letter).",
    "door_no": "Captures the door/house number. Must have 1 capture group.",
}

FLAG_DESCRIPTIONS = {
    "voter_id": "No special flags",
    "ac_ps_serial": "IGNORECASE",
    "name": "IGNORECASE",
    "father_name": "IGNORECASE | DOTALL",
    "husband_name": "IGNORECASE | DOTALL",
    "mother_name": "IGNORECASE | DOTALL",
    "age_gender": "IGNORECASE",
    "door_no": "IGNORECASE",
}

REQUIRED_GROUPS = {
    "voter_id": 1,
    "ac_ps_serial": 3,
    "name": 1,
    "father_name": 1,
    "husband_name": 1,
    "mother_name": 1,
    "age_gender": 2,
    "door_no": 1,
}


def validate_regex_groups(pattern_str, field_key):
    try:
        compiled = re.compile(pattern_str)
        actual = compiled.groups
        expected = REQUIRED_GROUPS.get(field_key, 1)
        if actual != expected:
            return False, f"Expected {expected} capture group(s), but found {actual}"
        return True, ""
    except re.error as e:
        return False, f"Invalid regex: {e}"


def generate_regex_for_field(client, model, field_key, sample_text):
    prompts = {
        "voter_id": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the Voter ID (like EPIC number or voter identifier).
The pattern MUST have exactly 1 capture group that captures just the voter ID code (e.g., XTM0650672).
Look at the sample to understand the exact format used.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "ac_ps_serial": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the Assembly Constituency number, Polling Station number, and Serial number.
The pattern MUST have exactly 3 capture groups: (AC_number), (PS_number), (Serial_number).
Look at the sample to understand the exact label format (could be in English, Telugu, Hindi, etc).

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "name": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the voter's name.
The pattern MUST have exactly 1 capture group for the name.
Use a lookahead boundary to stop before the next field (like Father Name, Husband Name, Age, etc).
Look at the sample to understand the exact label format.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "father_name": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the Father's Name.
The pattern MUST have exactly 1 capture group for the father's name.
Use a lookahead boundary to stop before the next field (like Age, Sex, Door, EPIC, etc).
Look at the sample to understand the exact label format.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "husband_name": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the Husband's Name.
The pattern MUST have exactly 1 capture group for the husband's name.
Use a lookahead boundary to stop before the next field (like Age, etc).
Look at the sample to understand the exact label format.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "mother_name": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the Mother's Name.
The pattern MUST have exactly 1 capture group for the mother's name.
Use a lookahead boundary to stop before the next field (like Age, Sex, Door, EPIC, etc).
Look at the sample to understand the exact label format.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "age_gender": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures both Age and Gender in one pattern.
The pattern MUST have exactly 2 capture groups: (age_number) and (gender_letter like M or F or the equivalent in the language used).
Look at the sample to understand the exact label format.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",

        "door_no": f"""You are a regex expert. Given this sample voter data text, write a Python regex pattern that captures the Door Number or House Number.
The pattern MUST have exactly 1 capture group for the door/house number.
Use a lookahead boundary to stop before the next field (like EPIC, voter ID, etc).
Look at the sample to understand the exact label format.

Sample text:
---
{sample_text}
---

Reply with ONLY the raw regex pattern string, nothing else. No quotes, no explanation, no code blocks. Just the regex pattern.""",
    }

    prompt = prompts.get(field_key, "")
    if not prompt:
        return None

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        result = response.choices[0].message.content.strip()
        result = result.strip('`').strip()
        if result.startswith('python'):
            result = result[6:].strip()
        if result.startswith("r'") or result.startswith('r"'):
            result = result[2:-1]
        if (result.startswith("'") and result.endswith("'")) or (result.startswith('"') and result.endswith('"')):
            result = result[1:-1]
        re.compile(result)
        return result
    except Exception as e:
        return None


def clean_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if re.match(r'^[A-Za-z]$', line.strip()):
            continue
        if 'సంస్థ పేరు' in line or '& పేరు' in line:
            continue
        if 'పేజీ సంఖ' in line or 'SEC Telangana' in line:
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def parse_voter_data(text, regex_patterns, regex_flags):
    cleaned_text = clean_text(text)

    voter_id_pattern = re.compile(regex_patterns["voter_id"], regex_flags.get("voter_id", 0))
    id_matches = list(voter_id_pattern.finditer(cleaned_text))

    seen_ids = set()
    voters = []
    serial = 0

    ac_ps_serial_re = re.compile(regex_patterns["ac_ps_serial"], regex_flags.get("ac_ps_serial", re.IGNORECASE))
    name_re = re.compile(regex_patterns["name"], regex_flags.get("name", re.IGNORECASE))
    father_re = re.compile(regex_patterns["father_name"], regex_flags.get("father_name", re.IGNORECASE | re.DOTALL))
    husband_re = re.compile(regex_patterns["husband_name"], regex_flags.get("husband_name", re.IGNORECASE | re.DOTALL))
    mother_re = re.compile(regex_patterns["mother_name"], regex_flags.get("mother_name", re.IGNORECASE | re.DOTALL))
    age_gender_re = re.compile(regex_patterns["age_gender"], regex_flags.get("age_gender", re.IGNORECASE))
    door_re = re.compile(regex_patterns["door_no"], regex_flags.get("door_no", re.IGNORECASE))

    for i, m in enumerate(id_matches):
        voter_id = m.group(1)
        if voter_id in seen_ids:
            continue

        if i == 0:
            start = 0
        else:
            start = id_matches[i-1].end()
        end = m.end()
        block = cleaned_text[start:end]

        seen_ids.add(voter_id)
        serial += 1

        ac_ps_match = ac_ps_serial_re.search(block)
        if ac_ps_match:
            ac_ps_serial = f"{ac_ps_match.group(1)} - {ac_ps_match.group(2)} - {ac_ps_match.group(3)}"
        else:
            ac_ps_serial = ''

        name_match = name_re.search(block)
        name = name_match.group(1).strip() if name_match else ''
        name = re.sub(r'\s+', ' ', name)

        father_match = father_re.search(block)
        husband_match = husband_re.search(block)
        mother_match = mother_re.search(block)

        if father_match:
            relation = father_match.group(1).strip()
        elif husband_match:
            relation = husband_match.group(1).strip()
        elif mother_match:
            relation = mother_match.group(1).strip()
        else:
            relation = ''
        relation = re.sub(r'\s+', ' ', relation)

        age_gender_match = age_gender_re.search(block)
        age = age_gender_match.group(1) if age_gender_match else ''
        gender = age_gender_match.group(2) if age_gender_match else ''

        door_match = door_re.search(block)
        door = door_match.group(1).strip() if door_match else ''
        door = re.sub(r'[^0-9A-Za-z\-/]', '', door)

        voters.append({
            'S.No': serial,
            'AC_PS_Serial': ac_ps_serial,
            'Voter_ID': voter_id,
            'Voter_Name': name,
            'Father_Husband_Name': relation,
            'House_No': door,
            'Age': age,
            'Gender': gender
        })

    return voters


def convert_to_excel(data):
    df = pd.DataFrame(data)
    df.columns = ['S.No', 'AC-PS-Serial', 'Voter ID', 'Voter Name', 'Father/Husband Name', 'House No', 'Age', 'Gender']

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Voter Data')

        workbook = writer.book
        worksheet = writer.sheets['Voter Data']

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#0066cc',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 18)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 8)
        worksheet.set_column('H:H', 10)

    output.seek(0)
    return output


if 'regex_patterns' not in st.session_state:
    st.session_state['regex_patterns'] = dict(DEFAULT_REGEX)

st.title("📄 Voter Text to Excel Converter")
st.markdown('<p class="subtitle">Paste copied text from voter PDF and convert to Excel format</p>', unsafe_allow_html=True)

with st.sidebar:
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except KeyError:
        st.error("❌ OPENAI_API_KEY not found in Streamlit secrets. Please add it in Secrets (TOML).")
        st.stop()

    # Additional safety check for empty string
    if not api_key or api_key.strip() == "":
        st.error("❌ OPENAI_API_KEY is empty. Please check your Streamlit secrets.")
        st.stop()
        
    model_choice = 'gpt-4o'
    st.header("📖 How to Use")
    st.markdown("""
    ### Steps:
    1. **Configure Regex**: Edit existing patterns or paste sample data and click "Generate Regex from Sample"
    2. **Paste Full Text**: Paste all voter text from your PDF
    3. **Process & Download**: Extract data and download as Excel

    ### Extracted Data Fields:
    - **S.No**: Serial Number
    - **AC-PS-Serial**: Assembly Constituency - Polling Station - Serial Number
    - **Voter ID**: Voter identification number
    - **Voter Name**: Name of the voter
    - **Father/Husband Name**: Parent or spouse name
    - **House No**: Residence number
    - **Age**: Voter's age
    - **Gender**: Male (M) or Female (F)
    """)

st.markdown("---")
st.subheader("Step 1: Configure Regex Patterns")
st.markdown("The default patterns work for **English** voter data. To support other languages (Telugu, Hindi, etc.), paste a sample voter record below and click **Generate Regex from Sample**.")

with st.expander("📋 Paste Sample Voter Data (for AI regex generation)", expanded=False):
    sample_data = st.text_area(
        "Paste 1-2 sample voter records here:",
        height=200,
        placeholder="Paste a small sample of voter data here (1-2 records). The AI will analyze it and generate matching regex patterns for each field...",
        key="sample_data"
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        generate_btn = st.button("🤖 Generate Regex from Sample", use_container_width=True)

    if generate_btn:
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar first.")
        elif not sample_data or len(sample_data.strip()) < 20:
            st.error("Please paste at least one sample voter record (needs sufficient text to analyze).")
        else:
            client = OpenAI(api_key=api_key)
            field_keys = list(DEFAULT_REGEX.keys())
            progress_bar = st.progress(0, text="Generating regex patterns...")
            results = {}
            errors = []

            for idx, field_key in enumerate(field_keys):
                progress_bar.progress(
                    (idx) / len(field_keys),
                    text=f"Generating regex for: {REGEX_LABELS[field_key]}..."
                )
                generated = generate_regex_for_field(client, model_choice, field_key, sample_data)
                if generated:
                    valid, msg = validate_regex_groups(generated, field_key)
                    if valid:
                        results[field_key] = generated
                    else:
                        errors.append(field_key)
                else:
                    errors.append(field_key)

            progress_bar.progress(1.0, text="Done!")

            if results:
                for key, val in results.items():
                    st.session_state['regex_patterns'][key] = val
                st.success(f"Successfully generated {len(results)} regex patterns!")

            if errors:
                st.warning(f"Could not generate regex for: {', '.join(REGEX_LABELS[e] for e in errors)}. The defaults will be used for those fields.")

            st.rerun()

st.markdown("#### Edit Regex Patterns")
st.markdown("You can edit these patterns directly. The flags (IGNORECASE, DOTALL) are applied automatically and cannot be changed here — only the regex code changes.")

regex_keys = list(DEFAULT_REGEX.keys())
col_left, col_right = st.columns(2)

for idx, key in enumerate(regex_keys):
    target_col = col_left if idx % 2 == 0 else col_right
    with target_col:
        current_val = st.session_state['regex_patterns'].get(key, DEFAULT_REGEX[key])
        new_val = st.text_input(
            f"{REGEX_LABELS[key]}",
            value=current_val,
            key=f"regex_{key}",
            help=f"{REGEX_DESCRIPTIONS[key]}\nFlags: {FLAG_DESCRIPTIONS[key]}"
        )
        st.session_state['regex_patterns'][key] = new_val

col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
with col_reset2:
    if st.button("🔄 Reset to Defaults", use_container_width=True):
        st.session_state['regex_patterns'] = dict(DEFAULT_REGEX)
        st.rerun()

regex_valid = True
for key in regex_keys:
    valid, msg = validate_regex_groups(st.session_state['regex_patterns'][key], key)
    if not valid:
        st.error(f"**{REGEX_LABELS[key]}**: {msg}")
        regex_valid = False

st.markdown("---")
st.subheader("Step 2: Paste Full Voter Text & Extract")

pasted_text = st.text_area(
    "Paste the copied text from your PDF here:",
    height=300,
    placeholder="Copy all text from your PDF (Ctrl+A, Ctrl+C) and paste it here (Ctrl+V)..."
)

st.markdown("---")

if pasted_text and len(pasted_text.strip()) > 0:
    st.success(f"Text pasted successfully: **{len(pasted_text):,}** characters")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        process_button = st.button("🔄 Process Text", use_container_width=True, disabled=not regex_valid)

    if process_button:
        with st.spinner("Processing voter data from pasted text..."):
            voter_data = parse_voter_data(
                pasted_text,
                st.session_state['regex_patterns'],
                REGEX_FLAGS
            )

            if voter_data:
                st.session_state['voter_data'] = voter_data
                st.session_state['processed'] = True
                st.success(f"Successfully extracted **{len(voter_data)}** voter records!")
            else:
                st.error("No voter data found in the pasted text. Make sure the regex patterns match your data format, or try generating new patterns from a sample.")

if 'processed' in st.session_state and st.session_state['processed']:
    voter_data = st.session_state['voter_data']

    st.markdown("---")
    st.subheader(f"📊 Extracted Voter Data ({len(voter_data)} records)")

    search_term = st.text_input("🔍 Search by Voter ID or Name:", "")

    df = pd.DataFrame(voter_data)
    df.columns = ['S.No', 'AC-PS-Serial', 'Voter ID', 'Voter Name', 'Father/Husband Name', 'House No', 'Age', 'Gender']

    if search_term:
        mask = df['Voter ID'].str.contains(search_term, case=False, na=False) | \
               df['Voter Name'].str.contains(search_term, case=False, na=False)
        df_display = df[mask]
        st.write(f"Showing {len(df_display)} matching records")
    else:
        df_display = df

    st.dataframe(df_display, use_container_width=True, height=400)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        excel_file = convert_to_excel(voter_data)
        st.download_button(
            label="⬇️ Download Excel File",
            data=excel_file,
            file_name=f"voter_data_{len(voter_data)}_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    st.subheader("📈 Data Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Voters", len(voter_data))
    male_count = sum(1 for v in voter_data if v.get('Gender', '') == 'M')
    col2.metric("Male (M)", male_count)
    female_count = sum(1 for v in voter_data if v.get('Gender', '') == 'F')
    col3.metric("Female (F)", female_count)
    col4.metric("Gender Unknown", len(voter_data) - male_count - female_count)
