import streamlit as st
from datetime import datetime
import pandas as pd
import mysql.connector
from mysql.connector import Error

# Database configuration (using secrets.toml)
def get_db_config():
    return {
        'host': st.secrets["cloudsql"]["host"],
        'database': st.secrets["cloudsql"]["database"],
        'user': st.secrets["cloudsql"]["user"],
        'password': st.secrets["cloudsql"]["password"],
        'port': st.secrets["cloudsql"]["port"]
    }

def create_connection():
    """Create a database connection to the MySQL instance"""
    try:
        config = get_db_config()
        connection = mysql.connector.connect(
            host=config['host'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            port=config['port']
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

def create_table_if_not_exists():
    """Create the feedback table if it doesn't exist"""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    comment TEXT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'Open',
                    admin_response TEXT,
                    INDEX idx_user_id (user_id),
                    INDEX idx_status (status)
                )
            """)
            conn.commit()
        except Error as e:
            st.error(f"Error creating table: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

def load_feedback(user_id=None):
    """Load feedback data from MySQL"""
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM feedback"
            params = []
            
            if user_id:
                query += " WHERE user_id = %s"
                params.append(user_id)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params if params else None)
            results = cursor.fetchall()
            
            # Create DataFrame with default columns if empty
            if not results:
                df = pd.DataFrame(columns=[
                    "id", "timestamp", "user_id", "username", 
                    "user_email", "category", "comment", 
                    "status", "admin_response"
                ])
            else:
                df = pd.DataFrame(results)
            
            # Initialize admin_response if column doesn't exist
            if 'admin_response' not in df.columns:
                df['admin_response'] = ''
            else:
                df['admin_response'] = df['admin_response'].fillna('')
            
            return df
    except Error as e:
        st.error(f"Error loading feedback: {e}")
    return pd.DataFrame(columns=[
        "id", "timestamp", "user_id", "username", 
        "user_email", "category", "comment", 
        "status", "admin_response"
    ])

def save_feedback(feedback_data):
    """Save new feedback to MySQL"""
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (timestamp, user_id, username, user_email, category, comment, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                feedback_data['timestamp'],
                feedback_data['user_id'],
                feedback_data['username'],
                feedback_data['user_email'],
                feedback_data['category'],
                feedback_data['comment'],
                feedback_data['status']
            ))
            conn.commit()
            return cursor.lastrowid
    except Error as e:
        st.error(f"Error saving feedback: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def update_feedback(feedback_id, admin_response, status):
    """Update feedback with admin response and status"""
    try:
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE feedback
                SET admin_response = %s, status = %s
                WHERE id = %s
            """, (admin_response, status, feedback_id))
            conn.commit()
            return True
    except Error as e:
        st.error(f"Error updating feedback: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def show():
    st.title("💬 Feedback & Support")
    
    # Initialize database table
    create_table_if_not_exists()
    
    # Initialize session state if it doesn't exist
    if 'feedback_df' not in st.session_state:
        st.session_state.feedback_df = load_feedback()
    
    if not st.user.get('is_logged_in', False):
        st.warning("Please login to submit feedback")
        return
    
    user_id = st.user["sub"]
    username = st.user.get("name", "Anonymous")
    user_email = st.user.get("email", "no-email@example.com")
    
    # Submit new feedback
    with st.expander("➕ Submit New Feedback", expanded=True):
        with st.form("feedback_form", clear_on_submit=True):
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
                    "admin_response": ""
                }])
                
                # Save directly to database
                save_feedback({
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'user_id': user_id,
                    'username': username,
                    'user_email': user_email,
                    'category': category,
                    'comment': comment.strip(),
                    'status': "Open"
                })
                
                # Refresh the session state from database
                st.session_state.feedback_df = load_feedback()
                st.success("Thank you for your feedback! We'll review it soon.")
    
    st.divider()
    
    # Display feedback history - uses the session state
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
                
                if pd.notna(row.get("admin_response")) and str(row["admin_response"]).strip():
                    st.markdown("---")
                    st.markdown("**Admin Response:**")
                    st.info(row["admin_response"])
    
    # Admin section
    if st.user.get("email", "").endswith("fabianchew@gmail.com"):
        st.divider()
        st.subheader("🔧 Admin Panel")
        
        all_feedback = load_feedback()
        
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
                
                with st.form(key=f"response_form_{row['id']}"):
                    new_response = st.text_area(
                        "Admin Response",
                        value=current_response,
                        key=f"response_{row['id']}"
                    )
                    new_status = st.selectbox(
                        "Status",
                        ["Open", "In Progress", "Resolved", "Closed"],
                        index=["Open", "In Progress", "Resolved", "Closed"].index(row["status"]),
                        key=f"status_{row['id']}"
                    )
                    
                    if st.form_submit_button("Update Response"):
                        if update_feedback(row['id'], new_response, new_status):
                            st.success("Response updated successfully!")
                            st.rerun()

if __name__ == "__main__":
    show()