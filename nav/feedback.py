import streamlit as st
from datetime import datetime
import pandas as pd
import os
import numpy as np

# Feedback storage setup
FEEDBACK_FILE = r"data\feedback\feedback_data.csv"

def load_feedback():
    """Load feedback data from CSV"""
    if os.path.exists(FEEDBACK_FILE):
        df = pd.read_csv(FEEDBACK_FILE)
        # Convert NaN values to empty string in admin_response column
        df['admin_response'] = df['admin_response'].fillna('')
        return df
    return pd.DataFrame(columns=["timestamp", "user_id", "username", "user_email", 
                               "category", "comment", "status", "admin_response"])

def save_feedback(df):
    """Save feedback data to CSV"""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    df.to_csv(FEEDBACK_FILE, index=False)

def show():
    st.title("💬 Feedback & Support")
    
    if not st.user.get('is_logged_in', False):
        st.warning("Please login to submit feedback")
        return
    
    # Initialize session state
    if 'feedback_df' not in st.session_state:
        st.session_state.feedback_df = load_feedback()
    
    user_id = st.user["sub"]
    username = st.user.get("name", "Anonymous")
    user_email = st.user.get("email", "no-email@example.com")
    
    with st.expander("➕ Submit New Feedback", expanded=True):
        with st.form("feedback_form"):
            category = st.selectbox(
                "Category",
                ["General Feedback", "Bug Report", "Feature Request", "Question"],
                help="Select the type of feedback"
            )
            
            comment = st.text_area(
                "Your feedback",
                placeholder="Describe your feedback in detail...",
                height=150
            )
            
            submitted = st.form_submit_button("Submit Feedback")
            
            if submitted and comment.strip():
                new_feedback = pd.DataFrame([{
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "user_id": user_id,
                    "username": username,
                    "user_email": user_email,
                    "category": category,
                    "comment": comment.strip(),
                    "status": "Open",
                    "admin_response": ""  # Initialize as empty string
                }])
                
                st.session_state.feedback_df = pd.concat(
                    [st.session_state.feedback_df, new_feedback],
                    ignore_index=True
                )
                save_feedback(st.session_state.feedback_df)
                st.success("Thank you for your feedback! We'll review it soon.")
                st.rerun()
    
    st.divider()
    
    # Display feedback history
    st.subheader("📝 Your Feedback History")
    
    user_feedback = st.session_state.feedback_df[
        st.session_state.feedback_df["user_id"] == user_id
    ].sort_values("timestamp", ascending=False)
    
    if user_feedback.empty:
        st.info("You haven't submitted any feedback yet")
    else:
        for _, row in user_feedback.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([0.7, 0.3])
                with col1:
                    st.markdown(f"**{row['category']}** - {row['status']}")
                    st.caption(f"Submitted on {row['timestamp']}")
                with col2:
                    st.caption(f"Status: {row['status']}")
                
                st.markdown(f"```\n{row['comment']}\n```")
                
                # Check if admin_response exists and is not NaN/empty
                if pd.notna(row.get("admin_response")) and str(row["admin_response"]).strip():
                    st.markdown("---")
                    st.markdown("**Admin Response:**")
                    st.info(row["admin_response"])
    
    # Admin section (visible only to admins)
    if st.user.get("email", "").endswith("fabianchew@gmail.com"):  # Admin email check
        st.divider()
        st.subheader("🔧 Admin Panel")
        
        all_feedback = st.session_state.feedback_df.sort_values("timestamp", ascending=False)
        
        for _, row in all_feedback.iterrows():
            with st.expander(f"{row['username']} - {row['category']} ({row['status']})"):
                st.markdown(f"**User:** {row['username']} ({row['user_email']})")
                st.markdown(f"**Submitted:** {row['timestamp']}")
                st.markdown(f"**Status:** {row['status']}")
                
                st.markdown("**Original Comment:**")
                st.markdown(f"```\n{row['comment']}\n```")
                
                current_response = row["admin_response"] if pd.notna(row.get("admin_response")) else ""
                
                if current_response:
                    st.markdown("**Current Response:**")
                    st.info(current_response)
                
                with st.form(key=f"response_form_{row.name}"):
                    new_response = st.text_area(
                        "Admin Response",
                        value=current_response,
                        key=f"response_{row.name}"
                    )
                    new_status = st.selectbox(
                        "Status",
                        ["Open", "In Progress", "Resolved", "Closed"],
                        index=["Open", "In Progress", "Resolved", "Closed"].index(row["status"]),
                        key=f"status_{row.name}"
                    )
                    
                    if st.form_submit_button("Update Response"):
                        st.session_state.feedback_df.at[row.name, "admin_response"] = new_response
                        st.session_state.feedback_df.at[row.name, "status"] = new_status
                        save_feedback(st.session_state.feedback_df)
                        st.success("Response updated successfully!")
                        st.rerun()

if __name__ == "__main__":
    show()