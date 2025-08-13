import streamlit as st

st.set_page_config(
    page_title="Multi-Modal Document Intelligence Platform",
    page_icon=":rocket:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page Setup
intro_page = st.Page(
    page="nav/intro.py",
    title="Introduction",
    icon="🏠",
    default=True,
)

image2text_page = st.Page(
    page="nav/image2text.py",
    title="Smart Image Analyzer",
    icon="🖼️",
)

doc2text_page = st.Page(
    page="nav/doc2text.py",
    title="Smart Document Analyzer",
    icon="📄",
)

data2visual_page = st.Page(
    page="nav/data2visual.py",
    title="Smart Data Visualizer",
    icon="📊",
)

if not st.user.get('is_logged_in', False):
    st.title("Multi-Modal Document Intelligence Platform")
    st.markdown("""
    ## 🚀 Transform Your Document Workflows with AI   
    """)
    st.warning("Please login to access the platform tools")
    if st.button("Login"):
        st.login("auth0")
else:
    # Store user information in session state
    st.session_state['username'] = st.user["name"]
    st.session_state['userpicture'] = st.user["picture"]
    
    # Navigation setup
    pg = st.navigation(
        pages=[intro_page, image2text_page, doc2text_page, data2visual_page],
    )
    
    # Display user info and navigation
    with st.sidebar:
        st.image(st.session_state.userpicture, width=100)
        st.subheader(f"Welcome {st.session_state.username}")
        if st.button("Logout"):
            st.logout()
            del st.session_state['username']
            del st.session_state['userpicture']
            st.rerun()
    
    pg.run()