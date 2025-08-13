import streamlit as st
from PIL import Image
import easyocr
from openai import OpenAI
import numpy as np
import tempfile
import os
import re

# Initialize EasyOCR reader once
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'])

# Initialize OpenAI client
try:
    client = OpenAI(api_key=st.secrets["openai_api_key"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {str(e)}")
    client = None

st.title('🖼️ Smart Image Analyzer')

# Initialize session state
if 'image' not in st.session_state:
    st.session_state.image = None
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

def preprocess_image(image):
    """Basic image preprocessing"""
    img = np.array(image.convert('L'))  # Convert to grayscale
    img = (img > 128).astype(np.uint8) * 255  # Basic thresholding
    return img

def clean_ocr_text(text):
    """Clean OCR results"""
    text = re.sub(r'[^\w\s\-.,$€£¥%]', '', text)  # Remove special chars
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
    return text

# Image upload section
uploaded_image = st.file_uploader("Upload an image", 
                                type=["jpg", "jpeg", "png", "bmp"])

if uploaded_image is not None:
    st.session_state.image = Image.open(uploaded_image)
    st.image(st.session_state.image, 
            caption='Uploaded Image', 
            use_container_width=True)

    if st.button('Extract Text'):
        with st.spinner('Processing image...'):
            try:
                reader = load_reader()
                
                # Save to temp file for processing
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                    st.session_state.image.save(tmp_file, format='PNG')
                    tmp_file_path = tmp_file.name
                
                # Perform OCR
                results = reader.readtext(tmp_file_path, 
                                       detail=0,
                                       paragraph=True,
                                       rotation_info=[0, 90, 180, 270])
                
                # Clean and store results
                cleaned_results = [clean_ocr_text(text) for text in results if text.strip()]
                st.session_state.extracted_text = "\n\n".join(cleaned_results)
                
                os.unlink(tmp_file_path)
                st.success("Text extraction complete!")
                
            except Exception as e:
                st.error(f"Text extraction failed: {str(e)}")

# Display extracted text
if st.session_state.get('extracted_text'):
    st.subheader("📝 Extracted Text")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_area("OCR Results", 
                    value=st.session_state.extracted_text, 
                    height=300,
                    label_visibility="collapsed")
    
    with col2:
        st.download_button(
            label="Download Text",
            data=st.session_state.extracted_text,
            file_name="extracted_text.txt",
            mime="text/plain"
        )

# AI Analysis Section
if st.session_state.get('extracted_text') and client:
    st.subheader("🤖 AI Text Analysis")
    
    analysis_options = {
        "Summarize": "Provide a concise summary of the key information",
        "Extract Contacts": "Extract all email addresses, phone numbers, and contact information",
        "Find Important Data": "Identify important numbers, dates, and figures",
        "Custom Analysis": ""
    }
    
    analysis_type = st.selectbox("Select analysis type", 
                               list(analysis_options.keys()))
    
    custom_prompt = ""
    if analysis_type == "Custom Analysis":
        custom_prompt = st.text_input("Enter your custom analysis prompt")
    else:
        st.caption(analysis_options[analysis_type])
    
    if st.button("Analyze Text"):
        with st.spinner("Performing analysis..."):
            try:
                prompt = analysis_options[analysis_type] if analysis_type != "Custom Analysis" else custom_prompt
                
                full_prompt = f"""
                Perform this analysis: {prompt}
                
                Extracted Text:
                {st.session_state.extracted_text}
                
                Instructions:
                1. Be precise and structured
                2. Format results clearly
                3. Highlight key information
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": full_prompt}],
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