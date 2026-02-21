import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(
    page_title="Telugu Voter Text to Excel Converter",
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

with st.sidebar:
    st.header("📖 How to Use")
    st.markdown("""
    ### Steps:
    1. **Copy Text from PDF**: Open your PDF and copy all the text (Ctrl+A, Ctrl+C)
    2. **Paste Text**: Paste the copied text into the text area
    3. **Process Text**: Click the 'Process Text' button to extract data
    4. **Preview Data**: Review the extracted voter information in the table
    5. **Download Excel**: Click the download button to get your Excel file
    
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

def clean_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if 'సంస్థ పేరు' in line or '& పేరు' in line:
            continue
        if re.match(r'^[A-Za-z]$', line.strip()):
            continue
        if 'పేజీ సంఖ' in line or 'SEC Telangana' in line:
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def parse_voter_data(text):
    cleaned_text = clean_text(text)
    
    # voter_id_pattern = re.compile(r'ఓటరు\s*ఐడి\s*([A-Z]{3}\d{7})')
    # voter_id_pattern = re.compile(r'ఓటరు\s*ఐడి\.?\s*([A-Z]{3}\d{7})') ## ఓటరు ఐడి. XTM0650672

    voter_id_pattern = re.compile(r'EPIC\s*No\.?\s*([A-Z]{3}\d{7})') ## English
    id_matches = list(voter_id_pattern.finditer(cleaned_text))
    
    seen_ids = set()
    voters = []
    serial = 0
    
    # ac_ps_serial_re = re.compile(r'ఎ\.సి\s*-పి\.ఎస్\s*-\s*వరుస\s*సంఖ్య\.?\s*:\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)')
    ac_ps_serial_re = re.compile(r'A\.?C\.?\s*No\.?-?\s*PS\.?\s*No\.?-?\s*SL\.?\s*No\.?\s*:\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)', re.IGNORECASE) # English AC No- PS No- SL No: 45- 12- 003
    
    # name_re = re.compile(r'పేరు\s*:\s*(.+?)(?=\n|తండ్రి|భర్త|వయసు)')
    name_re = re.compile(r'Name\s*:\s*(.+?)(?=\nFather\s*Name|\nHusband|\nAge)',re.IGNORECASE) # English

    # father_re = re.compile(r'తండ్రి\s*పేరు\s*:\s*(.*?)(?=\n|వయసు)')
    # father_re = re.compile(r'Father\s*Name\s*:\s*(.+?)(?=\nAge)',re.IGNORECASE) # English
    # father_re = re.compile(r'Father\s*Name\s*:\s*(.+?)(?=\nAge)', re.IGNORECASE | re.DOTALL) # English
    father_re = re.compile(r'Father\s*Name\s*:\s*(.+?)(?=\nAge|\nSex|\nDoor|\nEPIC)',re.IGNORECASE | re.DOTALL)


    # husband_re = re.compile(r'భర్త\s*పేరు\s*:\s*(.*?)(?=\n|వయసు)')
    husband_re = re.compile(r'Husband\s*Name\s*:?\s*(.+?)(?=\nAge)',re.IGNORECASE | re.DOTALL) #English

    # age_gender_re = re.compile(r'వయసు\s*:\s*(\d{1,3})\s*లింగ\s*:\s*:?\s*([MF])')
    age_gender_re = re.compile(r'Age\s*:\s*(\d{1,3})\s*Sex\s*:\s*:?\s*([MF])', re.IGNORECASE) # English

    # door_re = re.compile(r'డోర్\s*నెం\s*\.?\s*:\s*(.+?)(?=\n|ఓటరు)')
    door_re = re.compile(r'Door\s*No\.?\s*:\s*(.+?)(?=\nEPIC)',re.IGNORECASE) # English

    mother_re = re.compile(r'Mother\s*Name\s*:?\s*(.+?)(?=\nAge|\nSex|\nDoor|\nEPIC)',re.IGNORECASE | re.DOTALL) #English
    
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

st.title("📄 Telugu Voter Text to Excel Converter")
st.markdown('<p class="subtitle">Paste copied text from Telugu voter PDF and convert to Excel format</p>', unsafe_allow_html=True)

st.markdown("---")

pasted_text = st.text_area(
    "Paste the copied text from your PDF here:",
    height=300,
    placeholder="Copy all text from your PDF (Ctrl+A, Ctrl+C) and paste it here (Ctrl+V)..."
)

st.markdown("---")

if pasted_text and len(pasted_text.strip()) > 0:
    st.success(f"✅ Text pasted successfully: **{len(pasted_text):,}** characters")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        process_button = st.button("🔄 Process Text", use_container_width=True)
    
    if process_button:
        with st.spinner("⏳ Processing voter data from pasted text..."):
            voter_data = parse_voter_data(pasted_text)
            
            if voter_data:
                st.session_state['voter_data'] = voter_data
                st.session_state['processed'] = True
                st.success(f"✅ Successfully extracted **{len(voter_data)}** voter records!")
            else:
                st.error("❌ No voter data found in the pasted text. Make sure you copied the text correctly from the PDF.")

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
