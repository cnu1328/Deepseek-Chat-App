import streamlit as st
import pandas as pd
import re
from io import BytesIO
import PyPDF2

# Page configuration
st.set_page_config(
    page_title="Telugu Voter PDF to Excel Converter",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for better UI
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

# Sidebar - How to Use
with st.sidebar:
    st.header("📖 How to Use")
    st.markdown("""
    ### Steps:
    1. **Upload PDF File**: Click on the file uploader and select your Telugu voter list PDF
    2. **Process PDF**: Click the 'Process PDF' button to extract data
    3. **Preview Data**: Review the extracted voter information in the table
    4. **Download Excel**: Click the download button to get your Excel file
    
    ### Extracted Data Fields:
    - **S.No**: Serial Number
    - **Voter ID**: Voter identification number (ATM/JSB numbers)
    - **Voter Name**: Name of the voter (ఓటరు పేరు)
    - **Father/Husband Name**: Parent or spouse name
    - **House No**: Residence number
    - **Age**: Voter's age
    - **Gender**: Male (పురుషులు) or Female (స్త్రీలు)
    
    ### Tips:
    - Ensure PDF is clear and readable
    - PDF should contain structured voter data
    - Telugu text should be properly formatted
    
    ### Support:
    This tool extracts data from Telugu voter lists and converts them to Excel format for easy data management.
    """)

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file with better encoding handling"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        full_text = ""
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        return full_text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def clean_text(text):
    """Clean extracted text by removing extra spaces and formatting"""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

import re

def parse_voter_data(text):
    """Parse voter data using index-based mapping (ATM/JSB style)"""

    voters = []

    # ---------------------------
    # 1️⃣ Voter IDs
    # ---------------------------
    # voter_id_pattern = r'(ATM\d+|JSB\d+)'
    # voter_ids = re.findall(voter_id_pattern, text)
    # print(f"Found Voter IDs: {len(voter_ids)}")
    voter_id_pattern = r'(?<![A-Z])[A-Z]{2,3}\d+'
    voter_ids = re.findall(voter_id_pattern, text)
    print(f"Found Voter IDs: {len(voter_ids)}")

    # ---------------------------
    # 2️⃣ Voter Names
    # ---------------------------
    voter_name_pattern = re.compile(
        r'ఓటరు\s*పేరు\s*[:\s]*'        # Label
        r'(.+?)'                      # Name (lazy)
        r'(?='                        # Stop when next label starts
        r'ఓటరు\s*పేరు'
        r'|తండ్రి\s*పేరు'
        r'|భర్త\s*పేరు'
        r'|ఇంటి\s*సంఖ్య'
        r'|వయస్సు'
        r'|లింగము'
        r'|Photo'
        r'|Available'
        r'|ATM\d+'
        r'|JSB\d+'
        r'|$)'
        ,
        re.DOTALL
    )


    voter_names = [
        re.sub(r'\s+', ' ', name).strip()
        for name in voter_name_pattern.findall(text)
    ]

    print(f"Found Voter Names: {len(voter_names)}")
    # ---------------------------
    # 3️⃣ Father / Husband Names
    # ---------------------------
    relation_name_pattern = re.compile(
        r'(?:'
        r'తండ్రి\s*పేరు\s*[:\s]*'
        r'|'
        r'భర్త\s*పేరు\s*[:\s]*'
        r')'
        r'(.+?)'
        r'(?='
        r'ఓటరు\s*పేరు'
        r'|తండ్రి\s*పేరు'
        r'|భర్త\s*పేరు'
        r'|ఇంటి\s*సంఖ్య'
        r'|వయస్సు'
        r'|లింగము'
        r'|Photo'
        r'|Available'
        r'|ATM\d+'
        r'|JSB\d+'
        r'|$)'
        ,
        re.DOTALL
    )


    relation_names = [
        re.sub(r'\s+', ' ', name).strip()
        for name in relation_name_pattern.findall(text)
    ]

    print(f"Found Relation Names: {len(relation_names)}")

    # ---------------------------
    # 4️⃣ House Numbers
    # ---------------------------
    house_no_pattern = re.compile(
        r'ఇంటి\s*సంఖ్య\s*[:\s]*'     # Label
        r'(.+?)'                      # House number (lazy)
        r'(?='                        # Stop at next field
        r'ఓటరు\s*పేరు'
        r'|తండ్రి\s*పేరు'
        r'|భర్త\s*పేరు'
        r'|వయస్సు'
        r'|లింగము'
        r'|Photo'
        r'|Available'
        r'|ATM\d+'
        r'|JSB\d+'
        r'|$)'
        ,
        re.DOTALL
    )

    house_numbers = [
        re.sub(r'[^\dA-Za-z\-\/]', '', h)   # Keep only valid chars
        for h in house_no_pattern.findall(text)
    ]

    print(f"Found House Numbers: {len(house_numbers)}")


    # ---------------------------
    # 5️⃣ Ages
    # ---------------------------
    age_pattern = re.compile(
        r'వయస్సు\s*[:\s]*'        # Label
        r'(\d{1,3})'              # Age
        r'\s*'                    # OCR noise tolerance
        r'(?='                    # Stop at next field
        r'ఓటరు\s*పేరు'
        r'|తండ్రి\s*పేరు'
        r'|భర్త\s*పేరు'
        r'|ఇంటి\s*సంఖ్య'
        r'|లింగము\s*[:\s]*'
        r'|Photo'
        r'|Available'
        r'|ATM\d+'
        r'|JSB\d+'
        r'|$)'
        ,
        re.DOTALL
    )


    ages = age_pattern.findall(text)

    print(f"Found Ages: {len(ages)}")

    # ---------------------------
    # 6️⃣ Gender
    # ---------------------------
    gender_pattern = re.compile(
        r'లింగము\s*[:\s]*'        # Label
        r'(పురుషులు|స్త్రీలు)'     # Gender values
        r'(?='                    # Stop at next field
        r'ఓటరు\s*పేరు'
        r'|తండ్రి\s*పేరు'
        r'|భర్త\s*పేరు'
        r'|ఇంటి\s*సంఖ్య'
        r'|వయస్సు'
        r'|Photo'
        r'|Available'
        r'|ATM\d+'
        r'|JSB\d+'
        r'|$)'
        ,
        re.DOTALL
    )

    genders = gender_pattern.findall(text)

    print(f"Found Genders: {len(genders)}")


    # ---------------------------
    # 7️⃣ Index-based mapping
    # ---------------------------
    total_records = len(voter_ids)

    for i in range(total_records):
        voters.append({
            'S.No': i + 1,
            'Voter_ID': voter_ids[i],
            'Voter_Name': voter_names[i] if i < len(voter_names) else '',
            'Father_Husband_Name': relation_names[i] if i < len(relation_names) else '',
            'House_No': house_numbers[i] if i < len(house_numbers) else '',
            'Age': ages[i] if i < len(ages) else '',
            'Gender': genders[i] if i < len(genders) else ''
        })

    return voters


def convert_to_excel(data):
    """Convert data to Excel format"""
    df = pd.DataFrame(data)
    
    # Rename columns for Excel
    df.columns = ['S.No', 'Voter ID', 'Voter Name', 'Father/Husband Name', 'House No', 'Age', 'Gender']
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Voter Data')
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Voter Data']
        
        # Format headers
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#0066cc',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Cell format
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        
        # Write headers with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 8)   # S.No
        worksheet.set_column('B:B', 15)  # Voter ID
        worksheet.set_column('C:C', 25)  # Voter Name
        worksheet.set_column('D:D', 25)  # Father/Husband Name
        worksheet.set_column('E:E', 12)  # House No
        worksheet.set_column('F:F', 8)   # Age
        worksheet.set_column('G:G', 15)  # Gender
    
    output.seek(0)
    return output

# Main App
st.title("📄 Telugu Voter PDF to Excel Converter")
st.markdown('<p class="subtitle">Extract voter data from Telugu PDF files and convert to Excel format with accurate data parsing</p>', unsafe_allow_html=True)

st.markdown("---")

# File uploader
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    uploaded_file = st.file_uploader(
        "Upload Telugu Voter List PDF File",
        type=['pdf'],
        help="Select a PDF file containing Telugu voter data"
    )

st.markdown("---")

# Process button and results
if uploaded_file is not None:
    st.success(f"✅ File uploaded successfully: **{uploaded_file.name}**")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        process_button = st.button("🔄 Process PDF", use_container_width=True)
    
    if process_button:
        with st.spinner("⏳ Extracting and processing voter data from PDF..."):
            # Extract text from PDF
            text = extract_text_from_pdf(uploaded_file)
            
            if text:
                # Parse voter data
                voter_data = parse_voter_data(text)
                
                if voter_data:
                    # Store in session state
                    st.session_state['voter_data'] = voter_data
                    st.session_state['processed'] = True
                    
                    st.success(f"✅ Successfully extracted **{len(voter_data)}** voter records!")
                else:
                    st.error("❌ No voter data found in the PDF. Please check the file format.")
            else:
                st.error("❌ Failed to extract text from PDF. Please ensure the file is readable.")

# Display results if data is processed
if 'processed' in st.session_state and st.session_state['processed']:
    voter_data = st.session_state['voter_data']
    
    st.markdown("---")
    st.subheader(f"📊 Extracted Voter Data ({len(voter_data)} records)")
    
    # Create DataFrame with proper column names
    df = pd.DataFrame(voter_data)
    df.columns = ['S.No', 'Voter ID', 'Voter Name', 'Father/Husband Name', 'House No', 'Age', 'Gender']
    
    # Display data
    st.dataframe(df, use_container_width=True, height=400)
    
    st.markdown("---")
    
    # Download section
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Convert to Excel
        excel_file = convert_to_excel(voter_data)
        
        st.download_button(
            label="⬇️ Download Excel File",
            data=excel_file,
            file_name=f"voter_data_{len(voter_data)}_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # Statistics
    st.markdown("---")
    st.subheader("📈 Data Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Voters", len(voter_data))
    
    with col2:
        male_count = sum(1 for v in voter_data if 'పురుష' in v.get('Gender', ''))
        st.metric("Male Voters", male_count)
    
    with col3:
        female_count = sum(1 for v in voter_data if 'స్త్రీ' in v.get('Gender', ''))
        st.metric("Female Voters", female_count)
    
    with col4:
        ages = [int(v['Age']) for v in voter_data if v.get('Age', '').isdigit()]
        avg_age = sum(ages) / len(ages) if ages else 0
        st.metric("Average Age", f"{avg_age:.1f}")
    
    # Data Quality Check
    st.markdown("---")
    st.subheader("🔍 Data Quality Check")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        missing_names = sum(1 for v in voter_data if not v.get('Voter_Name', '').strip())
        st.metric("Records Missing Voter Name", missing_names)
    
    with col2:
        missing_relation = sum(1 for v in voter_data if not v.get('Father_Husband_Name', '').strip())
        st.metric("Records Missing Relation Name", missing_relation)
    
    with col3:
        missing_age = sum(1 for v in voter_data if not v.get('Age', '').strip())
        st.metric("Records Missing Age", missing_age)

else:
    st.info("👆 Please upload a PDF file and click '**Process PDF**' to extract voter data.")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>Telugu Voter PDF to Excel Converter</strong></p>
        <p>Accurately extracts voter data from Telugu language PDF files</p>
        <p style='font-size: 0.9rem;'>Supports both ATM and JSB voter ID formats</p>
    </div>
""", unsafe_allow_html=True)