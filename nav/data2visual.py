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
    """Generate aggregation suggestions using AI with column validation"""
    if not client or df is None:
        return None
        
    with st.spinner("Analyzing data structure..."):
        try:
            # Get actual available columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            category_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
            
            prompt = f"""
            Analyze this dataset and suggest 3-5 meaningful visualizations.
            Only use columns that actually exist in the dataset.
            
            **Available Numeric Columns:** {numeric_cols}
            **Available Categorical Columns:** {category_cols}
            
            For each suggestion:
            1. Specify exactly which columns to use (must exist in the lists above)
            2. Recommend chart type (Column/Pie/Line/Scatter)
            3. Explain why it's meaningful
            
            Rules:
            - For Column/Pie charts: Use categorical columns for grouping
            - For Scatter/Line: Use numeric columns for axes
            - Never suggest using non-existent columns
            - Prefer columns with <20 unique values for categorical data
            
            Provide 3-5 suggestions following this exact format:
            1. [Visualization Title]:
            - Columns: [exact column names from available lists]
            - Chart: [Column/Pie/Line/Scatter]
            - Reason: [analysis value]
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to generate suggestions: {str(e)}")
            return None

def validate_columns(df, chart_type, x_col, y_col=None, color_col=None):
    """Validate column selections for the chosen chart type"""
    errors = []
    
    # Get column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    category_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    # Validate based on chart type
    if chart_type in ["Column Chart", "Pie Chart"]:
        if x_col not in category_cols:
            errors.append(f"X-axis must be a categorical column for {chart_type}")
            
        if chart_type == "Pie Chart" and y_col and y_col not in numeric_cols:
            errors.append("Value column must be numeric for Pie Charts")
            
    elif chart_type == "Scatter Plot":
        if x_col not in numeric_cols:
            errors.append("X-axis must be numeric for Scatter Plot")
        if y_col not in numeric_cols:
            errors.append("Y-axis must be numeric for Scatter Plot")
        if color_col and color_col not in category_cols:
            errors.append("Color-by column must be categorical")
            
    elif chart_type == "Line Chart":
        if x_col not in category_cols + numeric_cols:
            errors.append("X-axis must be categorical or numeric for Line Chart")
        if y_col not in numeric_cols:
            errors.append("Y-axis must be numeric for Line Chart")
    
    # Check for missing values
    for col in [x_col, y_col, color_col]:
        if col and df[col].isnull().any():
            errors.append(f"Column '{col}' contains missing values")
    
    return errors if errors else None

# Data selection section
option = st.radio("Select data source:", ("Upload a file", "Use sample Titanic dataset"))

if option == "Upload a file":
    uploaded_file = st.file_uploader("Choose a data file", 
                                   type=SUPPORTED_TYPES,
                                   accept_multiple_files=False)
else:
    # Load sample Titanic dataset
    sample_path = "data/Dataset/Titanic.csv"
    try:
        if os.path.exists(sample_path):
            st.info("Sample Titanic dataset loaded. Click 'Process Data' to analyze it.")
        else:
            st.error(f"Sample dataset not found at: {sample_path}")
    except Exception as e:
        st.error(f"Failed to load sample dataset: {str(e)}")

if (option == "Upload a file" and uploaded_file is not None) or (option == "Use sample Titanic dataset" and os.path.exists(sample_path)):
    # Display file info
    if option == "Upload a file":
        file_extension = uploaded_file.name.split('.')[-1].lower()
        st.success(f"Uploaded {file_extension.upper()} file: {uploaded_file.name}")
    else:
        file_extension = "csv"

    if st.button('Process Data'):
        with st.spinner('Processing data...'):
            try:
                if option == "Upload a file":
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                else:
                    tmp_file_path = sample_path
                
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
                
                if option == "Upload a file":
                    os.unlink(tmp_file_path)
                
                # Show preview
                st.subheader("Data Preview")
                st.dataframe(st.session_state.df.head())
                
            except Exception as e:
                st.error(f"Data processing failed: {str(e)}")

# Visualization section
# Visualization section
if st.session_state.get('show_visualization', False) and st.session_state.df is not None:
    st.subheader("📈 Visualization Options")
    df = st.session_state.df
    
    # Get available columns (all columns can be used as categories)
    all_cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Show AI suggestions with validation note
    if st.session_state.aggregation_suggestions:
        with st.expander("🔍 AI Visualization Suggestions"):
            st.write(st.session_state.aggregation_suggestions)
            st.info("Note: Verify suggested columns exist in your dataset before applying")
    
    # Chart type selection
    chart_type = st.radio("Select chart type:",
                         ["Column Chart", "Pie Chart", "Line Chart", "Scatter Plot"],
                         horizontal=True)
    
    # Dynamic column selection UI
    col1, col2 = st.columns(2)
    
    with col1:
        # X-axis/category selection - allows any column type
        if chart_type in ["Column Chart", "Pie Chart"]:
            x_axis = st.selectbox("Category Column", 
                                options=all_cols,
                                help="Select any column for grouping (will be treated as categorical)")
        else:
            x_options = numeric_cols if chart_type == "Scatter Plot" else all_cols
            x_axis = st.selectbox("X-axis Column", 
                                options=x_options,
                                help="Select numeric column for Scatter, any column for Line")
    
    with col2:
        # Y-axis/value selection
        if chart_type == "Pie Chart":
            if numeric_cols:
                value_col = st.selectbox("Value Column", 
                                       options=numeric_cols,
                                       help="Select numeric column to aggregate")
                agg_method = st.selectbox("Aggregation Method",
                                        ["sum", "mean", "count"],
                                        help="How to aggregate the values")
            else:
                value_col = None
                agg_method = "count"
                st.info("No numeric columns - will show category counts")
        
        elif chart_type == "Scatter Plot":
            y_axis = st.selectbox("Y-axis Column", 
                                options=[col for col in numeric_cols if col != x_axis],
                                help="Select different numeric column than X-axis")
            
            # Color by can use any column (converted to string for coloring)
            if len(all_cols) > 0:
                color_by = st.selectbox("Color By (optional)", 
                                      [None] + all_cols,
                                      help="Color points by any column (will be treated as categorical)")
            else:
                color_by = None
        
        else:  # Column/Line charts
            y_axis = st.selectbox("Value Column", 
                                options=numeric_cols,
                                help="Select numeric column to visualize")
            
            agg_method = st.selectbox("Aggregation Method",
                                    ["None", "sum", "mean", "count", "median"],
                                    disabled=chart_type=="Line Chart" and x_axis not in numeric_cols,
                                    help="Aggregate values when needed")
    
    # Validation and visualization generation
    if st.button("Generate Visualization"):
        # Validate column selections
        validation_errors = []
        
        # Check for missing values
        for col in [x_axis, 
                   y_axis if chart_type != "Pie Chart" else value_col, 
                   color_by if chart_type == "Scatter Plot" else None]:
            if col and df[col].isnull().any():
                validation_errors.append(f"Column '{col}' contains missing values")
        
        # Chart-specific validation
        if chart_type == "Pie Chart" and value_col and value_col not in numeric_cols:
            validation_errors.append("Pie Chart value column must be numeric")
            
        if chart_type == "Scatter Plot":
            if x_axis not in numeric_cols:
                validation_errors.append("Scatter Plot X-axis must be numeric")
            if y_axis not in numeric_cols:
                validation_errors.append("Scatter Plot Y-axis must be numeric")
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            # Generate the visualization
            fig, ax = plt.subplots(figsize=(10, 6))
            plot_df = df.copy()
            
            # Convert numeric category columns to strings for proper grouping
            if chart_type in ["Column Chart", "Pie Chart"] and x_axis in numeric_cols:
                plot_df[x_axis] = plot_df[x_axis].astype(str)
            
            try:
                if chart_type == "Pie Chart":
                    if value_col:
                        plot_df = plot_df.groupby(x_axis)[value_col].agg(agg_method).reset_index()
                        plot_df = plot_df.sort_values(value_col, ascending=False)
                        ax.pie(plot_df[value_col], 
                              labels=plot_df[x_axis],
                              autopct='%1.1f%%',
                              startangle=90)
                        ax.set_title(f"{agg_method.title()} of {value_col} by {x_axis}")
                    else:
                        counts = plot_df[x_axis].value_counts()
                        ax.pie(counts, 
                              labels=counts.index,
                              autopct='%1.1f%%',
                              startangle=90)
                        ax.set_title(f"Distribution of {x_axis}")
                
                elif chart_type == "Scatter Plot":
                    if color_by:
                        # Convert color_by to string if it's numeric
                        if color_by in numeric_cols:
                            plot_df[color_by] = plot_df[color_by].astype(str)
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
                                desc = f"distribution of {x_axis}" + (f" by {agg_method} of {value_col}" if value_col else "")
                            elif chart_type == "Scatter Plot":
                                desc = f"relationship between {x_axis} and {y_axis}" + (f" colored by {color_by}" if color_by else "")
                            else:
                                desc = f"{agg_method + ' of ' if agg_method != 'None' else ''}{y_axis} by {x_axis}"
                            
                            prompt = f"""
                            Analyze this {chart_type} showing {desc}.
                            
                            Dataset characteristics:
                            - Rows: {len(df)}
                            - Columns: {df.columns.tolist()}
                            - Aggregation: {agg_method if agg_method != "None" else "No aggregation"}
                            
                            Provide 3-5 key insights about:
                            1. The overall patterns in the data
                            2. Any notable outliers or anomalies
                            3. Potential implications
                            """
                            
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.5
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