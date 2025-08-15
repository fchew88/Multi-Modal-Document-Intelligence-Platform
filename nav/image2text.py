import streamlit as st
from PIL import Image
from openai import OpenAI
import pytesseract
import re
import os

#print(pytesseract.get_tesseract_version())
# Should print version like '5.3.3'

#print(pytesseract.pytesseract.tesseract_cmd)
# Should show path to tesseract.exe

# Configure Tesseract path for Streamlit Cloud
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
else:
    st.warning("Tesseract not found in default location. Some features may not work.")

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
    return image.convert('L')  # Convert to grayscale

def clean_ocr_text(text):
    """Clean OCR results"""
    text = re.sub(r'[^\w\s\-.,$€£¥%]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text(image):
    """Perform OCR using pytesseract"""
    try:
        # Custom configuration for better accuracy
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        return text if text.strip() else None
    except Exception as e:
        st.error(f"OCR Error: {str(e)}")
        return None

# Image selection section
option = st.radio("Select image source:", ("Upload an image", "Use sample receipt"))

if option == "Upload an image":
    uploaded_image = st.file_uploader("Choose an image file", 
                                    type=["jpg", "jpeg", "png", "bmp"])
    if uploaded_image is not None:
        try:
            st.session_state.image = Image.open(uploaded_image)
        except Exception as e:
            st.error(f"Failed to load image: {str(e)}")
else:
    # Load sample receipt
    sample_path = "data/image/receipt.jpeg"
    try:
        if os.path.exists(sample_path):
            st.session_state.image = Image.open(sample_path)
            st.info("Sample receipt loaded. Click 'Extract Text' to process it.")
        else:
            st.error(f"Sample image not found at: {sample_path}")
    except Exception as e:
        st.error(f"Failed to load sample image: {str(e)}")

# Display the selected image in half width
if st.session_state.image is not None:
    col1, col2 = st.columns([1, 1])  # Create two equal-width columns
    
    with col1:
        st.image(st.session_state.image, 
                caption='Selected Image', 
                use_container_width=True)  # This will now take half the container width
    
    with col2:
        # Empty space or you can add other elements here
        pass

    if st.button('Extract Text'):
        with st.spinner('Processing image...'):
            try:
                # Preprocess image
                processed_img = preprocess_image(st.session_state.image)
                
                # Perform OCR
                raw_text = extract_text(processed_img)
                
                if not raw_text:
                    st.warning("No text found. Try a clearer image.")
                    st.session_state.extracted_text = ""
                else:
                    st.session_state.extracted_text = clean_ocr_text(raw_text)
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
                    model="gpt-5-nano",
                    messages=[{"role": "user", "content": full_prompt}],
                    temperature=1.0,
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