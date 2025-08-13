import streamlit as st

def show():
    st.set_page_config(
        page_title="Multi-Modal Document Intelligence Platform",
        layout="wide"
    )
    
    st.title("Multi-Modal Document Intelligence Platform")
    st.markdown("""
    ## 🚀 Transform Your Document Workflows with AI
    
    **A unified platform for extracting, analyzing, and visualizing insights from documents of all types**:
    - 📄 **PDFs & Word Docs** - Extract structured text and tables
    - 🖼️ **Images & Scans** - OCR for handwritten or printed text
    - 📊 **Spreadsheets** - Auto-analyze and visualize data
    - 🤖 **AI-Powered Insights** - Summarize, query, and generate reports
    """)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Key Features")
        st.markdown("""
        - 🔍 **Smart Extraction**: Pull text/data from any document format
        - 📈 **Auto-Visualization**: Convert tables to interactive charts
        - ✨ **Clean Interface**: No more switching between 5 different tools
        - 🧠 **AI Analysis**: Ask questions about your documents in plain English
        """)
    
    with col2:
        st.subheader("Use Cases")
        st.markdown("""
        - Financial report analysis
        - Research paper summarization
        - Contract review automation
        - Data extraction from scanned forms
        - Meeting minutes processing
        """)
    
    st.divider()
    
    st.success("⬅️ Navigate using the sidebar to access specific tools")

if __name__ == "__main__":
    show()