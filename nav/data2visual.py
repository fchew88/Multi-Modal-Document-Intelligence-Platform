import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from openai import OpenAI
import tempfile
import os

# Initialize OpenAI client
try:
    client = OpenAI(api_key=st.secrets["openai_api_key"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {str(e)}")
    client = None

st.title('📊 Smart Data Visualizer')

# Supported file types
SUPPORTED_TYPES = ["csv", "xlsx", "json"]

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'show_visualization' not in st.session_state:
    st.session_state.show_visualization = False
if 'aggregation_suggestions' not in st.session_state:
    st.session_state.aggregation_suggestions = None

def get_aggregation_suggestions(df):
    """Generate aggregation suggestions using AI"""
    if not client:
        return None
        
    with st.spinner("Analyzing data structure..."):
        try:
            prompt = f"""
            Analyze this dataset and suggest 3-5 meaningful ways to aggregate the data for visualization.  
            Focus on the most statistically significant columns and logical groupings.  
            For each suggestion, recommend the best chart type (column, pie, line, or scatter plot) and justify your choice.  

            **Dataset sample:**  
            {df.head().to_string()}  

            **Dataset columns:** {df.columns.tolist()}  
            **Numeric columns:** {df.select_dtypes(include=[np.number]).columns.tolist()}  
            **Categorical columns:** {df.select_dtypes(exclude=[np.number]).columns.tolist()}  

            Provide your suggestions in this format:  
            1. **[Aggregation Method]:** [Column(s) to aggregate] by [Grouping Column]  
            - **Chart Type:** [Column/Pie/Line/Scatter]  
            - **Reason:** [E.g., "Column chart to compare discrete categories"]  
            2. **[Aggregation Method]:** [Column(s) to aggregate] by [Grouping Column]  
            - **Chart Type:** [Column/Pie/Line/Scatter]  
            - **Reason:** [E.g., "Line chart to show trends over time"]  

            **Chart Selection Guidelines:**  
            - **Column Chart:** Compare discrete categories or limited time periods (e.g., sales by region).  
            - **Pie Chart:** Show parts of a whole (only if ≤5 categories and % totals matter).  
            - **Line Chart:** Display trends over continuous time (e.g., monthly revenue).  
            - **Scatter Plot:** Reveal relationships/correlations between two numeric variables.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to generate aggregation suggestions: {str(e)}")
            return None

# File uploader
uploaded_file = st.file_uploader("Upload your data file", 
                               type=SUPPORTED_TYPES,
                               accept_multiple_files=False)

if uploaded_file is not None:
    # Display file info
    file_extension = uploaded_file.name.split('.')[-1].lower()
    st.success(f"Uploaded {file_extension.upper()} file: {uploaded_file.name}")

    # Process file based on type
    if st.button('Process Data'):
        with st.spinner('Processing data...'):
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                if file_extension == 'csv':
                    df = pd.read_csv(tmp_file_path)
                elif file_extension == 'xlsx':
                    df = pd.read_excel(tmp_file_path)
                elif file_extension == 'json':
                    df = pd.read_json(tmp_file_path)
                else:
                    st.error("Unsupported file type")
                    df = None
                
                if df is not None:
                    st.session_state.df = df
                    st.session_state.show_visualization = True
                    st.session_state.aggregation_suggestions = get_aggregation_suggestions(df)
                    st.success("Data processed successfully!")
                
                os.unlink(tmp_file_path)
                
                # Show preview
                st.subheader("Data Preview")
                st.dataframe(st.session_state.df.head())
                
            except Exception as e:
                st.error(f"Data processing failed: {str(e)}")

# Visualization section
if st.session_state.get('show_visualization', False) and st.session_state.df is not None:
    st.subheader("📈 Visualization Options")
    
    # Show aggregation suggestions if data is granular
    if st.session_state.aggregation_suggestions:
        with st.expander("🔍 Recommended Aggregations (AI Suggestions)"):
            st.write(st.session_state.aggregation_suggestions)
    
    # Select chart type
    chart_type = st.radio("Select chart type:",
                         ["Column Chart", "Pie Chart", "Line Chart", "Scatter Plot"],
                         horizontal=True)
    
    # Get column lists
    numeric_cols = st.session_state.df.select_dtypes(include=[np.number]).columns.tolist()
    category_cols = st.session_state.df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    # Configure options based on chart type
    if chart_type == "Pie Chart":
        col1, col2 = st.columns(2)
        
        with col1:
            category = st.selectbox("Category", options=category_cols)
        
        with col2:
            if len(numeric_cols) > 0:
                value_col = st.selectbox("Value Column", options=numeric_cols)
                agg_method = st.selectbox("Aggregation Method",
                                        ["sum", "mean", "count"],
                                        index=0)
            else:
                # For non-numeric data, we'll do a simple count
                value_col = None
                agg_method = "count"
    
    elif chart_type == "Scatter Plot":
        col1, col2 = st.columns(2)
        
        with col1:
            x_axis = st.selectbox("X-axis", options=numeric_cols)
        
        with col2:
            y_axis = st.selectbox("Y-axis", options=numeric_cols)
            
        # Optional: Add color by category
        if len(category_cols) > 0:
            color_by = st.selectbox("Color by (optional)", 
                                  [None] + category_cols)
        else:
            color_by = None
    
    else:  # Column, Line charts
        col1, col2 = st.columns(2)
        
        with col1:
            x_axis = st.selectbox("X-axis", 
                                options=category_cols if chart_type == "Column Chart" 
                                else category_cols + numeric_cols)
        
        with col2:
            y_axis = st.selectbox("Y-axis", options=numeric_cols)
        
        if len(st.session_state.df) > 100:
            agg_method = st.selectbox("Aggregation Method",
                                    ["None", "sum", "mean", "count", "median"],
                                    help="Recommended for large datasets")
        else:
            agg_method = "None"
    
    # Generate visualization
    if st.button("Generate Visualization"):
        fig, ax = plt.subplots(figsize=(10, 6))
        plot_df = st.session_state.df.copy()
        
        try:
            if chart_type == "Pie Chart":
                if value_col:
                    # For numeric data with aggregation
                    plot_df = plot_df.groupby(category)[value_col].agg(agg_method).reset_index()
                    plot_df = plot_df.sort_values(value_col, ascending=False)
                    ax.pie(plot_df[value_col], 
                          labels=plot_df[category],
                          autopct='%1.1f%%',
                          startangle=90)
                    ax.set_title(f"{agg_method.title()} of {value_col} by {category}")
                else:
                    # For categorical data (simple count)
                    counts = plot_df[category].value_counts()
                    ax.pie(counts, 
                          labels=counts.index,
                          autopct='%1.1f%%',
                          startangle=90)
                    ax.set_title(f"Distribution of {category}")
            
            elif chart_type == "Scatter Plot":
                if color_by:
                    groups = plot_df.groupby(color_by)
                    for name, group in groups:
                        ax.scatter(group[x_axis], group[y_axis], 
                                 label=name, alpha=0.6)
                    ax.legend()
                else:
                    ax.scatter(plot_df[x_axis], plot_df[y_axis], alpha=0.6)
                
                ax.set_title(f"{y_axis} vs {x_axis}")
                ax.set_xlabel(x_axis)
                ax.set_ylabel(y_axis)
                ax.grid(True)
            
            elif chart_type == "Column Chart":
                if agg_method != "None":
                    plot_df = plot_df.groupby(x_axis)[y_axis].agg(agg_method).reset_index()
                
                plot_df.plot.bar(x=x_axis, y=y_axis, ax=ax)
                ax.set_title(f"{agg_method + ' of ' if agg_method != 'None' else ''}{y_axis} by {x_axis}")
                ax.set_ylabel(y_axis)
                plt.xticks(rotation=45)
            
            elif chart_type == "Line Chart":
                if agg_method != "None":
                    plot_df = plot_df.groupby(x_axis)[y_axis].agg(agg_method).reset_index()
                
                plot_df.plot.line(x=x_axis, y=y_axis, ax=ax, marker='o')
                ax.set_title(f"{agg_method + ' of ' if agg_method != 'None' else ''}{y_axis} over {x_axis}")
                ax.set_ylabel(y_axis)
                plt.xticks(rotation=45)
            
            st.pyplot(fig)
            
            # Generate AI insights
            if client:
                with st.spinner("Generating insights..."):
                    try:
                        if chart_type == "Pie Chart":
                            desc = f"distribution of {category}" + (f" by {agg_method} of {value_col}" if value_col else "")
                        elif chart_type == "Scatter Plot":
                            desc = f"relationship between {x_axis} and {y_axis}" + (f" colored by {color_by}" if color_by else "")
                        else:
                            desc = f"{agg_method + ' of ' if agg_method != 'None' else ''}{y_axis} by {x_axis}"
                        
                        prompt = f"""
                        Analyze this {chart_type} showing {desc}.
                        
                        Dataset characteristics:
                        - Rows: {len(st.session_state.df)}
                        - Columns: {st.session_state.df.columns.tolist()}
                        - Aggregation: {agg_method if agg_method != "None" else "No aggregation"}
                        
                        Provide 3-5 key insights about:
                        1. The overall patterns in the data
                        2. Any notable outliers or anomalies
                        3. Potential business implications
                        """
                        
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.7
                        )
                        st.subheader("🔍 AI-Generated Insights")
                        st.write(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"AI analysis failed: {str(e)}")
        
        except Exception as e:
            st.error(f"Failed to generate visualization: {str(e)}")

# Clear button
if st.button("Clear All"):
    st.session_state.clear()
    st.success("All content cleared!")
    st.rerun()

# Debug view
#with st.expander("Debug: Session State"):
#    st.write(st.session_state)