import streamlit as st
import pandas as pd
import pdfplumber
import docx
from openai import OpenAI
import tempfile
import os
import re

# Initialize OpenAI client
try:
    client = OpenAI(api_key=st.secrets["openai_api_key"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {str(e)}")
    client = None

st.title('📄 Smart Document Analyzer')

# File processing functions
def extract_text_from_pdf(file):
    """Extract text from PDF using pdfplumber"""
    with pdfplumber.open(file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

def extract_text_from_csv(file):
    """Extract text content from CSV file"""
    try:
        df = pd.read_csv(file)
        # Convert DataFrame to readable text
        text_content = f"CSV File Contents:\n\n{df.to_string(index=False)}"
        
        # Also extract the data as tables
        tables = [df.values.tolist()]
        
        return text_content, tables
    except Exception as e:
        st.error(f"Failed to process CSV file: {str(e)}")
        return None, None

def extract_text_from_docx(file):
    """Extract text from DOCX using python-docx"""
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_xlsx(file):
    """Extract text content from Excel file"""
    try:
        # Read all sheets from the Excel file
        xls = pd.ExcelFile(file)
        text_content = []
        tables = []
        
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            text_content.append(f"\n\nSheet: {sheet_name}\n\n{df.to_string(index=False)}")
            tables.append(df.values.tolist())
        
        return "\n".join(text_content), tables
    except Exception as e:
        st.error(f"Failed to process Excel file: {str(e)}")
        return None, None

def extract_tables_from_pdf(file):
    """Extract tables from PDF using pdfplumber with better error handling"""
    tables = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            try:
                page_tables = page.extract_tables()
                if page_tables:
                    for table in page_tables:
                        # Clean table data
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            cleaned_table.append(cleaned_row)
                        tables.append(cleaned_table)
            except Exception as e:
                st.warning(f"Could not extract tables from page {page.page_number}: {str(e)}")
    return tables

def clean_text(text):
    """Clean extracted text"""
    text = re.sub(r'\s+', ' ', text)  # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Limit consecutive newlines
    return text.strip()

def structure_text(text):
    """Attempt to structure the extracted text"""
    sections = re.split(r'\n{2,}', text)
    structured = []
    for section in sections:
        if len(section.split()) > 5:  # Only include meaningful sections
            structured.append({
                'content': section,
                'type': 'paragraph',
                'length': len(section)
            })
    return structured

# Initialize session state
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
if 'structured_data' not in st.session_state:
    st.session_state.structured_data = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

# File uploader
uploaded_file = st.file_uploader("Upload your document", 
                               type=["pdf", "docx", "txt", "csv", "xlsx"])

if uploaded_file is not None:
    # Display file info
    file_extension = uploaded_file.name.split('.')[-1].lower()
    st.success(f"Uploaded {file_extension.upper()} file: {uploaded_file.name}")

    if st.button('Process Document'):
        with st.spinner('Processing document...'):
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                text = ""
                tables = []
                
                if file_extension == 'pdf':
                    text = extract_text_from_pdf(tmp_file_path)
                    tables = extract_tables_from_pdf(tmp_file_path)
                elif file_extension == 'docx':
                    text = extract_text_from_docx(tmp_file_path)
                elif file_extension == 'txt':
                    text = uploaded_file.read().decode("utf-8")
                elif file_extension == 'csv':
                    text, tables = extract_text_from_csv(uploaded_file)
                    if text:
                        text = clean_text(text)
                        st.session_state.extracted_text = text
                        st.session_state.structured_data = structure_text(text)
                    if tables:
                        st.session_state.tables = tables
                elif file_extension == 'xlsx':
                    text, tables = extract_text_from_xlsx(uploaded_file)
                    if text:
                        text = clean_text(text)
                        st.session_state.extracted_text = text
                        st.session_state.structured_data = structure_text(text)
                    if tables:
                        st.session_state.tables = tables
                
                # Clean and structure the text
                if text:
                    text = clean_text(text)
                    st.session_state.extracted_text = text
                    st.session_state.structured_data = structure_text(text)
                
                # Process tables
                if tables:
                    st.session_state.tables = tables
                
                os.unlink(tmp_file_path)
                
                st.success("Document processed successfully!")
                
            except Exception as e:
                st.error(f"Document processing failed: {str(e)}")

# Display results
if st.session_state.get('extracted_text'):
    st.subheader("📝 Document Content")
    
    with st.expander("View Full Text"):
        st.text_area("Text Content", 
                    value=st.session_state.extracted_text, 
                    height=300,
                    label_visibility="collapsed")
    
    if st.session_state.get('structured_data'):
        st.subheader("📑 Document Structure")
        for i, section in enumerate(st.session_state.structured_data[:5]):  # Show first 5 sections
            with st.expander(f"Section {i+1} ({section['length']} chars)"):
                st.write(section['content'])
    
    if st.session_state.get('tables'):
        st.subheader("📊 Extracted Tables")
        for i, table in enumerate(st.session_state.tables[:3]):  # Show first 3 tables
            with st.expander(f"Table {i+1}"):
                try:
                    if len(table) > 1:
                        headers = table[0]
                        data = table[1:]
                        
                        # Generate unique column names
                        seen = {}
                        unique_headers = []
                        for i, h in enumerate(headers):
                            if pd.isna(h) or h == '':
                                unique_headers.append(f"Column_{i+1}")
                            elif h in seen:
                                seen[h] += 1
                                unique_headers.append(f"{h}_{seen[h]}")
                            else:
                                seen[h] = 0
                                unique_headers.append(h)
                        
                        # Create DataFrame and replace NaN with empty strings
                        df = pd.DataFrame(data, columns=unique_headers)
                        df = df.fillna('')  # Replace all NaN values
                        
                        st.dataframe(df)
                    else:
                        st.warning(f"Table {i+1} doesn't have enough rows to display")
                except Exception as e:
                    st.error(f"Could not display table {i+1}: {str(e)}")
                    st.write("Raw table data (first 5 rows):")
                    st.write(table[:5])

# AI Analysis Section
if st.session_state.get('extracted_text') and client:
    st.subheader("🤖 AI Document Analysis")
    
    analysis_type = st.radio("Analysis Type",
                            ["Summarize", "Extract Key Points", "Find Action Items", "Custom Query"],
                            horizontal=True)
    
    query = ""
    if analysis_type == "Custom Query":
        query = st.text_input("Enter your analysis query")
    else:
        query = analysis_type
    
    if st.button("Run Analysis"):
        with st.spinner("Analyzing document..."):
            try:
                prompt = f"""
                Perform this analysis on the document: {query}
                
                Document Content:
                {st.session_state.extracted_text[:10000]}  # Limit to first 10k chars
                
                Instructions:
                1. Be concise and structured
                2. Use bullet points for key information
                3. Highlight important names, dates, and figures
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                st.session_state.analysis_results = response.choices[0].message.content
                
                st.subheader("Analysis Results")
                st.markdown(st.session_state.analysis_results)
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")

# Clear button
if st.button("Clear All"):
    st.session_state.clear()
    st.success("All content cleared!")
    st.rerun()

# Debug view
#with st.expander("Debug: Session State"):
#    st.write(st.session_state)