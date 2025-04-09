import os
import io
import base64
import json
import uuid
import re
import time
from datetime import datetime
import subprocess
import pypdf
import requests
from supabase import create_client, Client
from docx import Document
import streamlit as st  # Import Streamlit first

# --- Configuration ---
# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Resume Optimizer Pro",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.resumeoptimizer.pro/help',
        'Report a bug': "https://www.resumeoptimizer.pro/bug",
        'About': "# Resume Optimizer Pro\nYour AI-powered resume enhancement tool."
    }
)

# Check for google.generativeai package
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    with st.expander("Package Installation Status", expanded=True):
        st.warning("Google Generative AI package not found. Installing required packages...")
        # Try to install the package
        try:
            subprocess.check_call(["pip", "install", "google-generativeai"])
            import google.generativeai as genai
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            GEMINI_AVAILABLE = True
            st.success("Google Generative AI package installed successfully!")
        except Exception as e:
            st.error(f"Failed to install Google Generative AI package: {str(e)}")
            st.info("Using fallback methods for resume parsing and analysis.")

# Check for reportlab package (needed for PDF generation)
REPORTLAB_AVAILABLE = False
try:
    import reportlab
    REPORTLAB_AVAILABLE = True
except ImportError:
    with st.expander("PDF Generation Status", expanded=True):
        st.warning("ReportLab package not found. Installing required packages...")
        # Try to install the package
        try:
            subprocess.check_call(["pip", "install", "reportlab"])
            import reportlab
            REPORTLAB_AVAILABLE = True
            st.success("ReportLab package installed successfully!")
        except Exception as e:
            st.error(f"Failed to install ReportLab package: {str(e)}")
            st.info("PDF generation may not work properly without ReportLab.")

# Enhanced Custom CSS for advanced styling and interactivity
st.markdown("""
    <style>
    /* Modern UI Theme */
    :root {
        --primary-color: #2E7DAF;
        --secondary-color: #34495E;
        --accent-color: #16A085;
        --background-color: #F8F9FA;
        --text-color: #2C3E50;
        --error-color: #E74C3C;
        --success-color: #27AE60;
        --warning-color: #F39C12;
        --light-gray: #ECEFF1;
        --dark-gray: #607D8B;
        --border-radius: 10px;
        --box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Global Styles */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--light-gray);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--dark-gray);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-color);
    }

    /* Button Styles */
    .stButton>button {
        background: linear-gradient(45deg, var(--primary-color), var(--accent-color));
        color: white;
        border-radius: var(--border-radius);
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: var(--transition);
        box-shadow: var(--box-shadow);
        text-transform: uppercase;
        font-size: 14px;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.2);
        filter: brightness(110%);
    }

    .stButton>button:active {
        transform: translateY(0);
    }

    .stButton>button:disabled {
        background: #6C757D;
        cursor: not-allowed;
        transform: none;
    }
    
    /* Primary Action Button */
    .primary-action-btn {
        background: linear-gradient(45deg, #2E7DAF, #16A085) !important;
        font-weight: 700 !important;
        padding: 14px 28px !important;
    }
    
    /* Secondary Action Button */
    .secondary-action-btn {
        background: linear-gradient(45deg, #34495E, #2C3E50) !important;
        font-weight: 600 !important;
    }
    
    /* Danger Action Button */
    .danger-action-btn {
        background: linear-gradient(45deg, #E74C3C, #C0392B) !important;
    }

    /* Section Headers */
    .section-header {
        font-size: 28px;
        font-weight: 700;
        color: var(--secondary-color);
        margin: 25px 0 15px;
        padding-bottom: 10px;
        border-bottom: 3px solid var(--accent-color);
        text-transform: uppercase;
        letter-spacing: 1px;
        position: relative;
        overflow: hidden;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-color), transparent);
    }
    
    /* Subsection Headers */
    .subsection-header {
        font-size: 20px;
        font-weight: 600;
        color: var(--primary-color);
        margin: 15px 0 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid var(--primary-color);
    }

    /* Score Display */
    .score-display {
        font-size: 20px;
        font-weight: 600;
        padding: 15px;
        border-radius: var(--border-radius);
        margin: 10px 0;
        text-align: center;
        box-shadow: var(--box-shadow);
        transition: var(--transition);
        position: relative;
        overflow: hidden;
    }

    .score-display:hover {
        transform: scale(1.02);
    }

    .score-low { 
        background: linear-gradient(135deg, #FFC107, #FF9800);
        color: #fff;
    }
    
    .score-medium {
        background: linear-gradient(135deg, #3498DB, #2980B9);
        color: white;
    }

    .score-high { 
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: white;
    }
    
    .score-display::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: rgba(255, 255, 255, 0.1);
        transform: rotate(30deg);
        transition: var(--transition);
        z-index: 0;
    }
    
    .score-display:hover::before {
        transform: rotate(0deg);
    }
    
    .score-display span {
        position: relative;
        z-index: 1;
    }

    /* Missing Section Indicator */
    .missing-section {
        color: var(--error-color);
        font-style: italic;
        padding: 8px;
        border-left: 3px solid var(--error-color);
        background-color: rgba(231, 76, 60, 0.1);
        margin: 5px 0;
        border-radius: 0 var(--border-radius) var(--border-radius) 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 0.7; }
        50% { opacity: 1; }
        100% { opacity: 0.7; }
    }

    /* Sidebar Styling */
    .sidebar .sidebar-content {
        background-color: var(--background-color);
        padding: 25px;
        border-right: 1px solid rgba(0,0,0,0.1);
    }
    
    /* Sidebar Navigation */
    .sidebar-nav {
        margin-bottom: 20px;
    }
    
    .sidebar-nav-item {
        display: block;
        padding: 10px 15px;
        margin-bottom: 5px;
        border-radius: var(--border-radius);
        color: var(--text-color);
        text-decoration: none;
        transition: var(--transition);
    }
    
    .sidebar-nav-item:hover {
        background-color: rgba(46, 125, 175, 0.1);
        color: var(--primary-color);
    }
    
    .sidebar-nav-item.active {
        background-color: var(--primary-color);
        color: white;
    }

    /* Enhanced Tooltip */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }

    .tooltip .tooltiptext {
        visibility: hidden;
        width: 250px;
        background-color: var(--secondary-color);
        color: white;
        text-align: center;
        border-radius: 8px;
        padding: 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -125px;
        opacity: 0;
        transition: opacity 0.3s, transform 0.3s;
        transform: translateY(10px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        font-size: 14px;
        line-height: 1.4;
    }

    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
        transform: translateY(0);
    }
    
    /* Tooltip arrow */
    .tooltip .tooltiptext::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: var(--secondary-color) transparent transparent transparent;
    }

    /* File Uploader */
    .uploadedFile {
        border: 2px dashed var(--primary-color);
        border-radius: var(--border-radius);
        padding: 20px;
        text-align: center;
        transition: var(--transition);
        background-color: rgba(46, 125, 175, 0.05);
    }

    .uploadedFile:hover {
        border-color: var(--accent-color);
        background-color: rgba(46, 125, 175, 0.1);
        transform: translateY(-2px);
    }
    
    /* Custom File Uploader */
    .custom-file-upload {
        display: inline-block;
        padding: 12px 20px;
        cursor: pointer;
        background: linear-gradient(45deg, var(--primary-color), var(--accent-color));
        color: white;
        border-radius: var(--border-radius);
        transition: var(--transition);
        box-shadow: var(--box-shadow);
        margin-bottom: 10px;
    }
    
    .custom-file-upload:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.2);
    }
    
    .custom-file-upload i {
        margin-right: 8px;
    }

    /* Progress Bars */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        height: 8px;
        border-radius: 4px;
    }
    
    /* Custom Progress Bar */
    .progress-container {
        width: 100%;
        height: 10px;
        background-color: var(--light-gray);
        border-radius: 5px;
        margin: 10px 0;
        overflow: hidden;
        position: relative;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        border-radius: 5px;
        transition: width 0.5s ease;
        position: relative;
    }
    
    .progress-bar::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(
            45deg,
            rgba(255, 255, 255, 0.2) 25%,
            transparent 25%,
            transparent 50%,
            rgba(255, 255, 255, 0.2) 50%,
            rgba(255, 255, 255, 0.2) 75%,
            transparent 75%,
            transparent
        );
        background-size: 20px 20px;
        animation: progress-animation 2s linear infinite;
    }
    
    @keyframes progress-animation {
        0% { background-position: 0 0; }
        100% { background-position: 40px 0; }
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        background-color: rgba(46, 125, 175, 0.05);
        border-radius: var(--border-radius);
        padding: 10px 15px;
        font-weight: 600;
        color: var(--primary-color);
        transition: var(--transition);
        border: 1px solid rgba(46, 125, 175, 0.1);
    }
    
    .streamlit-expanderHeader:hover {
        background-color: rgba(46, 125, 175, 0.1);
        color: var(--accent-color);
    }
    
    .streamlit-expanderContent {
        border: 1px solid rgba(46, 125, 175, 0.1);
        border-top: none;
        border-radius: 0 0 var(--border-radius) var(--border-radius);
        padding: 15px;
    }

    /* Text Area Enhancement */
    .stTextArea>div>div>textarea {
        border-radius: var(--border-radius);
        border: 1px solid rgba(0,0,0,0.1);
        padding: 12px;
        font-size: 15px;
        transition: var(--transition);
        background-color: white;
    }

    .stTextArea>div>div>textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(46, 125, 175, 0.2);
    }
    
    /* Text Input Enhancement */
    .stTextInput>div>div>input {
        border-radius: var(--border-radius);
        border: 1px solid rgba(0,0,0,0.1);
        padding: 12px;
        font-size: 15px;
        transition: var(--transition);
        background-color: white;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(46, 125, 175, 0.2);
    }
    
    /* Select Box Enhancement */
    .stSelectbox>div>div {
        border-radius: var(--border-radius);
        border: 1px solid rgba(0,0,0,0.1);
        transition: var(--transition);
    }
    
    .stSelectbox>div>div:focus-within {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(46, 125, 175, 0.2);
    }

    /* Loading Animation */
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }

    .stSpinner {
        animation: pulse 1.5s infinite;
    }
    
    /* Card Component */
    .card {
        background-color: white;
        border-radius: var(--border-radius);
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: var(--box-shadow);
        transition: var(--transition);
        border: 1px solid var(--light-gray);
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    
    .card-header {
        font-size: 18px;
        font-weight: 600;
        color: var(--primary-color);
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--light-gray);
    }
    
    .card-content {
        color: var(--text-color);
    }
    
    /* Badge Component */
    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 5px;
        margin-bottom: 5px;
    }
    
    .badge-primary {
        background-color: var(--primary-color);
        color: white;
    }
    
    .badge-secondary {
        background-color: var(--secondary-color);
        color: white;
    }
    
    .badge-success {
        background-color: var(--success-color);
        color: white;
    }
    
    .badge-warning {
        background-color: var(--warning-color);
        color: white;
    }
    
    .badge-error {
        background-color: var(--error-color);
        color: white;
    }
    
    /* Alert Component */
    .alert {
        padding: 15px;
        border-radius: var(--border-radius);
        margin-bottom: 15px;
        position: relative;
        border-left: 4px solid;
    }
    
    .alert-info {
        background-color: rgba(52, 152, 219, 0.1);
        border-left-color: #3498DB;
        color: #2980B9;
    }
    
    .alert-success {
        background-color: rgba(46, 204, 113, 0.1);
        border-left-color: #2ECC71;
        color: #27AE60;
    }
    
    .alert-warning {
        background-color: rgba(241, 196, 15, 0.1);
        border-left-color: #F1C40F;
        color: #F39C12;
    }
    
    .alert-error {
        background-color: rgba(231, 76, 60, 0.1);
        border-left-color: #E74C3C;
        color: #C0392B;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: var(--border-radius) var(--border-radius) 0 0;
        gap: 1px;
        padding: 10px 16px;
        color: var(--text-color);
        font-weight: 400;
        border: 1px solid var(--light-gray);
        border-bottom: none;
        transition: var(--transition);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: white;
        color: var(--primary-color);
        font-weight: 600;
        border-top: 3px solid var(--primary-color);
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        background-color: white;
        border-radius: 0 var(--border-radius) var(--border-radius) var(--border-radius);
        border: 1px solid var(--light-gray);
        padding: 20px;
    }
    
    /* Checkbox Styling */
    .stCheckbox > div > div > label {
        display: flex;
        align-items: center;
        cursor: pointer;
    }
    
    .stCheckbox > div > div > label > div {
        border-radius: 4px;
        border: 2px solid var(--primary-color);
        width: 18px;
        height: 18px;
        margin-right: 10px;
        transition: var(--transition);
    }
    
    .stCheckbox > div > div > label:hover > div {
        border-color: var(--accent-color);
        background-color: rgba(22, 160, 133, 0.1);
    }
    
    /* Radio Button Styling */
    .stRadio > div {
        padding: 10px;
        border-radius: var(--border-radius);
        background-color: white;
        box-shadow: var(--box-shadow);
    }
    
    .stRadio [role="radiogroup"] {
        display: flex;
        gap: 10px;
    }
    
    .stRadio [role="radio"] {
        border-radius: var(--border-radius);
        padding: 10px 15px;
        transition: var(--transition);
        border: 1px solid var(--light-gray);
    }
    
    .stRadio [role="radio"]:hover {
        background-color: rgba(46, 125, 175, 0.05);
    }
    
    .stRadio [data-baseweb="radio"] [aria-checked="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    
    /* PDF Preview Container */
    .pdf-preview-container {
        border: 1px solid var(--light-gray);
        border-radius: var(--border-radius);
        padding: 15px;
        background-color: white;
        box-shadow: var(--box-shadow);
        margin-top: 20px;
        position: relative;
    }
    
    .pdf-preview-container::before {
        content: 'PDF Preview';
        position: absolute;
        top: -10px;
        left: 20px;
        background-color: white;
        padding: 0 10px;
        color: var(--primary-color);
        font-weight: 600;
        font-size: 14px;
    }
    
    /* Template Card */
    .template-card {
        border: 2px solid var(--light-gray);
        border-radius: var(--border-radius);
        padding: 15px;
        margin-bottom: 15px;
        transition: var(--transition);
        cursor: pointer;
        position: relative;
        overflow: hidden;
        background-color: white;
    }
    
    .template-card:hover {
        border-color: var(--primary-color);
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    
    .template-card.selected {
        border-color: var(--accent-color);
        background-color: rgba(22, 160, 133, 0.1);
    }
    
    .template-card h4 {
        margin-top: 0;
        color: var(--secondary-color);
        font-weight: 600;
    }
    
    .template-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        background: var(--accent-color);
        color: white;
        padding: 3px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
        z-index: 1;
    }
    
    .template-features {
        margin-top: 10px;
        font-size: 14px;
    }
    
    .template-features li {
        margin-bottom: 5px;
        position: relative;
        padding-left: 20px;
    }
    
    .template-features li::before {
        content: '✓';
        position: absolute;
        left: 0;
        color: var(--accent-color);
        font-weight: bold;
    }
    
    .template-preview {
        width: 100%;
        height: 120px;
        background-color: var(--light-gray);
        border-radius: 5px;
        margin-top: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        transition: var(--transition);
    }
    
    .template-card:hover .template-preview {
        transform: scale(1.05);
    }
    
    /* Animation Keyframes */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    /* Apply animations to elements */
    .section-header {
        animation: fadeIn 0.5s ease-out;
    }
    
    .card {
        animation: fadeIn 0.5s ease-out;
    }
    
    .stTabs {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .stButton>button {
            padding: 10px 16px;
            font-size: 12px;
        }
        
        .section-header {
            font-size: 22px;
        }
        
        .subsection-header {
            font-size: 18px;
        }
        
        .score-display {
            font-size: 16px;
            padding: 10px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- Supabase and Gemini API Setup ---
SUPABASE_URL = "https://qkeyjzxnhnosdlxtwsbm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFrZXlqenhuaG5vc2RseHR3c2JtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE4OTAzNzIsImV4cCI6MjA1NzQ2NjM3Mn0.DsxE9-sTfF0hYaSitoq8uExpk7rusH0NlxqXLGy-G2U"
GEMINI_API_KEY = "AIzaSyDG7RQ0A8dxz2S-I_D3bG9IKNHeWYFMvMY"  # Updated API key
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure Gemini API if available
if GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Define generation config
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        # Define safety settings
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Test the API with a simple call
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content("Hello")
            if response:
                st.sidebar.success("✅ Gemini AI configured and tested successfully!")
            else:
                st.sidebar.warning("⚠️ Gemini AI configured but test response was empty. Some features may not work correctly.")
        except Exception as test_error:
            st.sidebar.warning(f"⚠️ Gemini AI configured but test failed: {str(test_error)}. Some features may not work correctly.")
            
    except Exception as e:
        st.sidebar.error(f"❌ Failed to configure Gemini AI: {str(e)}")
        GEMINI_AVAILABLE = False
        st.sidebar.info("Using fallback methods for resume parsing and analysis.")
else:
    st.sidebar.info("Using fallback methods for resume parsing and analysis.")

# Create local storage directory if it doesn't exist
LOCAL_STORAGE_DIR = "resume_storage"
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

# Initialize Supabase storage bucket
def init_supabase_storage():
    """Check if Supabase storage is accessible."""
    try:
        # Just try to list buckets to check access
        supabase.storage.list_buckets()
        return True
    except Exception as e:
        st.warning("Supabase storage not accessible. Using local storage instead.")
        return False

def store_file_in_supabase(file, user_id, file_type):
    """Store file in Supabase or locally if Supabase is not available."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{user_id}_{file_type}_{timestamp}_{file.name}"
    
    # Try Supabase first
    try:
        # Ensure we're working with bytes
        file_bytes = file.getvalue() if hasattr(file, 'getvalue') else file.read()
        file.seek(0)  # Reset file pointer for potential reuse
        
        # Try to upload to existing bucket
        result = supabase.storage.from_('resumes').upload(
        file_name,
        file_bytes,
       {"content-type": "application/pdf"}
       )

#        result = supabase.storage.from_('resumes').upload(
 #           path=file_name,
  #          file=file_bytes,
   #         file_options={"contentType": "application/pdf"}
    #    )
        
        st.success("File uploaded to Supabase successfully!")
        return file_name
    except Exception as e:
        error_msg = str(e)
        
        # If it's a permissions issue or bucket not found, use local storage
        if "403" in error_msg or "Unauthorized" in error_msg or "Bucket not found" in error_msg:
            return store_file_locally(file, user_id, file_type)
        else:
            st.error(f"Upload error: {error_msg}")
            return None

def store_file_locally(file, user_id, file_type):
    """Store file in local storage as fallback."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    file_name = f"{user_id}_{file_type}_{timestamp}_{unique_id}.pdf"
    file_path = os.path.join(LOCAL_STORAGE_DIR, file_name)
    
    try:
        # Ensure we're working with bytes
        file_bytes = file.getvalue() if hasattr(file, 'getvalue') else file.read()
        file.seek(0)  # Reset file pointer
        
        # Write to local file
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Store metadata
        metadata = {
            'user_id': user_id,
            'file_type': file_type,
            'original_name': getattr(file, 'name', 'unknown.pdf'),
            'timestamp': timestamp,
            'path': file_path
        }
        
        metadata_path = os.path.join(LOCAL_STORAGE_DIR, f"{file_name}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        
        st.success("File stored locally successfully!")
        return file_name
    except Exception as e:
        st.error(f"Failed to store file locally: {str(e)}")
        return None

def get_file(file_name):
    """Get file from Supabase or local storage."""
    # Try Supabase first
    try:
        file_data = supabase.storage.from_('resumes').download(file_name)
        return io.BytesIO(file_data)
    except Exception:
        # Try local storage
        try:
            file_path = os.path.join(LOCAL_STORAGE_DIR, file_name)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    return io.BytesIO(f.read())
        except Exception as e:
            st.error(f"Failed to retrieve file: {str(e)}")
    
    return None

def list_files(user_id=None):
    """List files from Supabase or local storage."""
    files = []
    
    # Try Supabase first
    try:
        supabase_files = supabase.storage.from_('resumes').list()
        files.extend([f['name'] for f in supabase_files])
    except Exception:
        pass
    
    # Add local files
    try:
        for filename in os.listdir(LOCAL_STORAGE_DIR):
            if filename.endswith('.pdf'):
                if user_id is None or filename.startswith(user_id):
                    files.append(filename)
    except Exception:
        pass
    
    return files

# --- Helper Functions ---
def extract_text_from_pdf(file):
    """Extract text from a PDF file using pypdf."""
    try:
        # Make a copy of the file to avoid modifying the original
        if hasattr(file, 'seek'):
            file.seek(0)
        
        pdf_reader = pypdf.PdfReader(file)
        text = []
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                text.append(content)
        return "\n".join(text)
    except Exception as e:
        st.error(f"Failed to extract text from PDF: {str(e)}")
        return ""

def parse_resume_sections(resume_text):
    """Parse resume text into sections using regex patterns and AI assistance."""
    # First try to identify common section headers
    common_sections = {
        "Contact Information": [],
        "Summary": [],
        "Professional Summary": [],
        "Objective": [],
        "Skills": [],
        "Technical Skills": [],
        "Soft Skills": [],
        "Experience": [],
        "Work Experience": [],
        "Employment History": [],
        "Education": [],
        "Projects": [],
        "Certifications": [],
        "Publications": [],
        "Patents": [],
        "Awards": [],
        "Achievements": [],
        "Languages": [],
        "Interests": [],
        "Hobbies": [],
        "Volunteer Experience": [],
        "Professional Affiliations": [],
        "References": []
    }
    
    # Try to extract sections using regex patterns
    lines = resume_text.split('\n')
    current_section = "Contact Information"  # Default first section
    
    # Common section header patterns - expanded with more variations
    section_patterns = {
        r'(?i)^\s*(contact|personal|info|contact information|personal information|contact details|personal details|contact info)\s*:?\s*$': "Contact Information",
        r'(?i)^\s*(summary|professional summary|profile|about me|career summary|executive summary|professional profile)\s*:?\s*$': "Summary",
        r'(?i)^\s*(objective|career objective|professional objective|career goal|job objective)\s*:?\s*$': "Objective",
        r'(?i)^\s*(skills|technical skills|core skills|key skills|competencies|areas of expertise|areas of knowledge)\s*:?\s*$': "Skills",
        r'(?i)^\s*(technical skills|hard skills|technical competencies|technical expertise)\s*:?\s*$': "Technical Skills",
        r'(?i)^\s*(soft skills|interpersonal skills|people skills|communication skills)\s*:?\s*$': "Soft Skills",
        r'(?i)^\s*(experience|work experience|employment|employment history|work history|career history|professional experience)\s*:?\s*$': "Experience",
        r'(?i)^\s*(education|academic background|qualifications|academic qualifications|educational background)\s*:?\s*$': "Education",
        r'(?i)^\s*(projects|project experience|key projects|relevant projects|personal projects)\s*:?\s*$': "Projects",
        r'(?i)^\s*(certifications|certificates|professional certifications|credentials|qualifications)\s*:?\s*$': "Certifications",
        r'(?i)^\s*(publications|papers|research papers|articles|published works)\s*:?\s*$': "Publications",
        r'(?i)^\s*(patents|patent applications|inventions)\s*:?\s*$': "Patents",
        r'(?i)^\s*(awards|honors|recognitions|achievements)\s*:?\s*$': "Awards",
        r'(?i)^\s*(achievements|accomplishments|key achievements)\s*:?\s*$': "Achievements",
        r'(?i)^\s*(languages|language skills|language proficiency|foreign languages)\s*:?\s*$': "Languages",
        r'(?i)^\s*(interests|hobbies|activities|personal interests)\s*:?\s*$': "Interests",
        r'(?i)^\s*(volunteer|volunteering|volunteer experience|community service)\s*:?\s*$': "Volunteer Experience",
        r'(?i)^\s*(affiliations|professional affiliations|memberships|professional memberships)\s*:?\s*$': "Professional Affiliations",
        r'(?i)^\s*(references|professional references|character references)\s*:?\s*$': "References"
    }
    
    # Process each line
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line is a section header
        is_section_header = False
        for pattern, section in section_patterns.items():
            if re.match(pattern, line):
                current_section = section
                is_section_header = True
                break
                
        if not is_section_header:
            common_sections[current_section].append(line)
    
    # Convert lists to strings
    parsed_sections = {}
    for section, content in common_sections.items():
        if content:
            parsed_sections[section] = "\n".join(content)
    
    # If we couldn't parse much, use AI to help if available
    if len(parsed_sections) <= 2 and GEMINI_AVAILABLE:
        return extract_sections_with_ai(resume_text)
    
    # If we still don't have much, try a simpler approach
    if len(parsed_sections) <= 2:
        return extract_sections_simple(resume_text)
        
    return parsed_sections

def extract_sections_simple(resume_text):
    """Simple fallback method to extract resume sections without AI."""
    # Basic extraction based on line breaks and capitalization patterns
    sections = {}
    lines = resume_text.split('\n')
    
    # Try to identify contact info (usually at the top)
    contact_lines = []
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', line) or re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', line):
            contact_lines.append(line)
    
    # Add name (usually the first line)
    if lines and lines[0].strip() and not re.search(r'@|www|\d{3}[-.]?\d{3}[-.]?\d{4}', lines[0]):
        contact_lines.insert(0, lines[0].strip())
            
    if contact_lines:
        sections["Personal Information"] = "\n".join(contact_lines)
    
    # Look for skills (keywords, comma-separated lists)
    skills_pattern = r'\b(python|java|javascript|html|css|react|angular|vue|node|express|django|flask|sql|nosql|mongodb|mysql|postgresql|aws|azure|gcp|docker|kubernetes|git|agile|scrum|machine learning|deep learning|nlp|ai|data science|data analysis|statistics|communication|leadership|teamwork|problem solving)\b'
    skills = set()
    for line in lines:
        matches = re.findall(skills_pattern, line.lower())
        skills.update(matches)
    
    if skills:
        sections["Skills"] = ", ".join(sorted(skills))
    
    # Try to identify education (look for degree keywords)
    education_lines = []
    for i, line in enumerate(lines):
        if re.search(r'\b(degree|bachelor|master|phd|mba|bsc|msc|ba|bs|ms|university|college|school|gpa)\b', line.lower()):
            education_lines.append(line)
    
    if education_lines:
        sections["Education"] = "\n".join(education_lines)
    
    # Try to identify experience (look for date patterns)
    experience_lines = []
    for i, line in enumerate(lines):
        if re.search(r'\b(20\d\d|19\d\d)[-–—]?(20\d\d|19\d\d|present|current)\b', line.lower()):
            # Include this line and the next few lines as they likely describe the role
            experience_lines.append(line)
            for j in range(1, 5):  # Include up to 5 lines after a date pattern
                if i+j < len(lines) and lines[i+j].strip():
                    experience_lines.append(lines[i+j])
    
    if experience_lines:
        sections["Experience"] = "\n".join(experience_lines)
    
    # Try to identify projects (look for project keywords)
    project_lines = []
    in_project_section = False
    for i, line in enumerate(lines):
        if re.search(r'\b(project|projects|portfolio|github)\b', line.lower()):
            in_project_section = True
            project_lines.append(line)
        elif in_project_section and line.strip():
            project_lines.append(line)
            # End project section if we hit another major section
            if re.search(r'\b(education|experience|skills|certification|reference)\b', line.lower()):
                in_project_section = False
    
    if project_lines:
        sections["Projects"] = "\n".join(project_lines)
    
    # Try to identify certifications
    cert_lines = []
    in_cert_section = False
    for i, line in enumerate(lines):
        if re.search(r'\b(certification|certificate|certified|credential)\b', line.lower()):
            in_cert_section = True
            cert_lines.append(line)
        elif in_cert_section and line.strip():
            cert_lines.append(line)
            # End certification section if we hit another major section
            if re.search(r'\b(education|experience|skills|project|reference)\b', line.lower()):
                in_cert_section = False
    
    if cert_lines:
        sections["Certifications"] = "\n".join(cert_lines)
    
    # Try to identify summary/objective (usually near the top, after contact info)
    summary_lines = []
    for i, line in enumerate(lines[1:15]):  # Check lines 1-15
        if re.search(r'\b(summary|objective|profile|about me)\b', line.lower()):
            summary_lines.append(line)
            # Include the next few lines as they likely contain the summary
            for j in range(1, 5):
                if i+j < len(lines) and lines[i+j].strip():
                    summary_lines.append(lines[i+j])
    
    if summary_lines:
        sections["Summary"] = "\n".join(summary_lines)
    
    # If we still don't have much, just split the text into chunks
    if len(sections) <= 2:
        chunk_size = max(5, len(lines) // 5)  # Divide into roughly 5 sections
        for i in range(0, len(lines), chunk_size):
            section_name = f"Section {i//chunk_size + 1}"
            sections[section_name] = "\n".join(lines[i:i+chunk_size])
    
    # Add empty strings for important missing sections
    important_sections = [
        "Personal Information", "Summary", "Skills", "Experience", 
        "Education", "Projects", "Certifications"
    ]
    
    for section in important_sections:
        if section not in sections:
            sections[section] = ""
    
    return sections

def extract_sections_with_ai(resume_text):
    """Use Gemini AI to extract sections from resume text with enhanced categorization."""
    if not GEMINI_AVAILABLE:
        return extract_sections_simple(resume_text)
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a professional resume parser. Extract and categorize ALL information from this resume into appropriate sections.
        
        MANDATORY sections to extract (even if empty):
        - Personal Information: Name, email, phone, location, LinkedIn, GitHub, portfolio URL, etc.
        - Summary/Objective: Professional summary or career objective statement
        - Skills: All skills including technical skills, soft skills, languages, tools, etc.
        - Experience: Work history with companies, titles, dates, and descriptions
        - Education: Degrees, institutions, dates, GPA if available, etc.
        
        ADDITIONAL sections to extract if present:
        - Projects: Personal or professional projects with descriptions
        - Certifications: Professional certifications with dates
        - Publications: Any published works with dates and citations
        - Awards & Honors: Achievements and recognitions
        - Languages: Spoken/written languages and proficiency levels
        - Volunteer Experience: Volunteer work with organizations, roles, dates
        - Interests & Activities: Personal interests, hobbies, activities
        - References: Professional references or "available upon request"
        
        EXTRACTION INSTRUCTIONS:
        1. Be thorough - capture ALL content from the resume
        2. Preserve original formatting of bullet points where possible
        3. For each experience/education entry, include ALL details (dates, titles, descriptions)
        4. Group information into the appropriate sections, even if they're scattered in the original
        5. If information clearly belongs to a section not listed above, create an appropriate section for it
        
        Format your response as a structured JSON object where:
        - Each key is a section name
        - Each value contains the complete content of that section
        - Maintain line breaks and formatting where appropriate
        - If a mandatory section is missing in the resume, include it with an empty string value
        
        Resume text:
        {resume_text}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        
        # Try to find JSON block in markdown
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no code block, try to find the entire JSON object
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
            else:
                # No JSON found, warn and use simple extraction
                st.warning("Could not extract JSON format from AI response. Using simple extraction instead.")
                return extract_sections_simple(resume_text)
        
        try:
            sections = json.loads(json_str)
            
            # Normalize section names and handle case sensitivity
            normalized_sections = {}
            
            # Common section name mappings
            section_mappings = {
                "personal information": "Personal Information",
                "personal details": "Personal Information",
                "contact": "Personal Information",
                "contact information": "Personal Information",
                "profile": "Personal Information",
                
                "summary": "Summary",
                "professional summary": "Summary",
                "career objective": "Summary",
                "objective": "Summary",
                
                "skills": "Skills",
                "technical skills": "Skills",
                "core competencies": "Skills",
                "key skills": "Skills",
                "expertise": "Skills",
                
                "experience": "Experience",
                "work experience": "Experience",
                "professional experience": "Experience",
                "employment history": "Experience",
                "work history": "Experience",
                
                "education": "Education",
                "academic background": "Education",
                "educational qualifications": "Education",
                
                "projects": "Projects",
                "personal projects": "Projects",
                
                "certifications": "Certifications"
            }
            
            # Normalize section names
            for section, content in sections.items():
                section_lower = section.lower()
                
                # Check for mappings
                if section_lower in section_mappings:
                    normalized_name = section_mappings[section_lower]
                else:
                    # Keep original capitalization if no mapping found
                    normalized_name = section
                
                # Handle case where section already exists (merge content)
                if normalized_name in normalized_sections and content:
                    normalized_sections[normalized_name] += "\n\n" + content
                else:
                    normalized_sections[normalized_name] = content
            
            # Ensure mandatory sections exist
            important_sections = [
                "Personal Information", "Summary", "Skills", "Experience", 
                "Education", "Projects", "Certifications"
            ]
            
            for section in important_sections:
                if section not in normalized_sections:
                    normalized_sections[section] = ""
            
            return normalized_sections
                
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract sections manually
            st.warning("Failed to parse AI response as JSON. Using manual extraction.")
            
        # Fallback: extract sections manually from the response
        sections = {}
        current_section = None
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a section header
            if line.endswith(':') and len(line) < 50:
                current_section = line[:-1].strip()
                sections[current_section] = ""
            elif current_section and current_section in sections:
                if sections[current_section]:
                    sections[current_section] += "\n" + line
                else:
                    sections[current_section] = line
        
        # Add missing section indicators for important sections
        important_sections = [
            "Personal Information", "Summary", "Skills", "Experience", 
            "Education", "Projects", "Certifications"
        ]
        
        for section in important_sections:
            if section not in sections:
                sections[section] = ""
                    
        return sections
    except Exception as e:
        st.warning(f"AI extraction failed: {str(e)}")
        # Return basic sections as fallback
        return extract_sections_simple(resume_text)

def score_resume(resume_text, job_type="general"):
    """Score resume using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a professional resume evaluator. Score this resume on a scale of 0-100 for the following categories:
        1. Overall Quality: Evaluate the overall quality, formatting, and professionalism of the resume
        2. ATS Compatibility: Evaluate how well the resume would perform with Applicant Tracking Systems
        3. Content Quality: Evaluate the quality, relevance, and impact of the content
        4. Skills Relevance: Evaluate how relevant the skills are for {job_type} roles
        5. Experience Impact: Evaluate how impactful and well-presented the experience section is
        
        Format your response as a JSON object with these keys: 
        - overall_score: Overall resume score
        - ats_score: ATS compatibility score
        - content_score: Content quality score
        - skills_score: Skills relevance score
        - experience_score: Experience impact score
        - genai_score: Score specifically for GenAI roles (if applicable)
        - ai_score: Score specifically for general AI roles (if applicable)
        
        Resume text:
        {resume_text}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                scores = json.loads(json_str)
                # Ensure we have genai_score and ai_score
                if 'genai_score' not in scores:
                    scores['genai_score'] = int(0.8 * scores.get('overall_score', 70) + 0.2 * scores.get('skills_score', 65))
                if 'ai_score' not in scores:
                    scores['ai_score'] = int(0.7 * scores.get('overall_score', 70) + 0.3 * scores.get('skills_score', 65))
                return scores
            except json.JSONDecodeError:
                pass
                
        # Fallback scores
        return {
            "overall_score": 65,
            "ats_score": 60,
            "content_score": 62,
            "skills_score": 58,
            "experience_score": 63,
            "genai_score": 60,
            "ai_score": 58
        }
    except Exception as e:
        st.error(f"AI scoring failed: {str(e)}")
        return {
            "overall_score": 65,
            "ats_score": 60,
            "content_score": 62,
            "skills_score": 58,
            "experience_score": 63,
            "genai_score": 60,
            "ai_score": 58
        }

def generate_pdf_from_sections(sections, template_name, options=None):
    """Generate a PDF from resume sections using a template with advanced styling options."""
    if not REPORTLAB_AVAILABLE:
        st.error("ReportLab is not available. PDF generation cannot proceed.")
        st.info("Please install ReportLab using: pip install reportlab")
        return None
        
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        
        buffer = io.BytesIO()
        
        # Set up the document with consistent margins
        doc = SimpleDocTemplate(buffer, pagesize=letter, 
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        
        # Create custom styles for all templates
        styles.add(ParagraphStyle(name='Name',
                                 parent=styles['Heading1'],
                                 fontSize=24,
                                 spaceAfter=12,
                                 alignment=TA_CENTER,
                                 textColor=colors.darkblue))
        
        styles.add(ParagraphStyle(name='ContactInfo',
                                 parent=styles['Normal'],
                                 fontSize=10,
                                 alignment=TA_CENTER,
                                 spaceAfter=12))
        
        styles.add(ParagraphStyle(name='SectionHeader',
                                 parent=styles['Heading2'],
                                 fontSize=14,
                                 spaceAfter=6,
                                 textColor=colors.darkblue,
                                 borderWidth=1,
                                 borderColor=colors.darkblue,
                                 borderPadding=5,
                                 borderRadius=0))
        
        styles.add(ParagraphStyle(name='Content',
                                 parent=styles['Normal'],
                                 fontSize=10,
                                 spaceAfter=6))
        
        # Build the document
        elements = []
        
        # Add name if available (usually in contact info)
        name = ""
        if "Contact Information" in sections:
            # Try to extract name from first line of contact info
            name_line = sections["Contact Information"].split('\n')[0]
            if not re.search(r'@|www|\d{3}[-.]?\d{3}[-.]?\d{4}', name_line):
                name = name_line
        
        if name:
            elements.append(Paragraph(name, styles['Name']))
            elements.append(Spacer(1, 6))
        
        # Add contact information
        if "Contact Information" in sections:
            contact_info = sections["Contact Information"].replace('\n', ' | ')
            elements.append(Paragraph(contact_info, styles['ContactInfo']))
            elements.append(Spacer(1, 12))
        
        # Template-specific formatting
        if template_name == "Minimalist":
            # Clean, simple design with focus on content
            for section in ["Summary", "Skills", "Experience", "Education", "Projects", "Certifications"]:
                if section in sections and sections[section]:
                    elements.append(Paragraph(section.upper(), styles['SectionHeader']))
                    elements.append(Paragraph(sections[section].replace('\n', '<br/>'), styles['Content']))
                    elements.append(Spacer(1, 12))
                    
        elif template_name == "ATS-Friendly":
            # Optimized for Applicant Tracking Systems
            for section in ["Summary", "Skills", "Experience", "Education", "Projects", "Certifications"]:
                if section in sections and sections[section]:
                    elements.append(Paragraph(section.upper(), styles['SectionHeader']))
                    # Format content for ATS
                    content = sections[section].replace('\n', '<br/>')
                    if section == "Skills":
                        # Format skills as bullet points for better ATS parsing
                        skills_list = content.split(',')
                        content = "<br/>".join(f"• {skill.strip()}" for skill in skills_list if skill.strip())
                    elements.append(Paragraph(content, styles['Content']))
                    elements.append(Spacer(1, 12))
                    
        elif template_name == "Project-Focused":
            # Highlights projects and technical skills
            # First add Projects section if available
            if "Projects" in sections and sections["Projects"]:
                elements.append(Paragraph("PROJECTS", styles['SectionHeader']))
                projects_text = sections["Projects"]
                # Split by newlines and format each project
                project_entries = projects_text.split('\n\n')
                for entry in project_entries:
                    lines = entry.split('\n')
                    if lines:
                        # First line as project title
                        elements.append(Paragraph(lines[0], styles['SectionHeader']))
                        if len(lines) > 1:
                            # Remaining lines as project description
                            project_desc = '<br/>'.join(lines[1:])
                            elements.append(Paragraph(project_desc, styles['Content']))
                    elements.append(Spacer(1, 8))
                elements.append(Spacer(1, 4))
            
            # Then add other sections
            for section in ["Summary", "Skills", "Experience", "Education", "Certifications"]:
                if section in sections and sections[section]:
                    elements.append(Paragraph(section.upper(), styles['SectionHeader']))
                    elements.append(Paragraph(sections[section].replace('\n', '<br/>'), styles['Content']))
                    elements.append(Spacer(1, 12))
        
        # Build the PDF
        doc.build(elements)
        return buffer.getvalue()
    
    except Exception as e:
        st.error(f"Failed to generate PDF: {str(e)}")
        return None

def generate_suggestions(resume_text, resume_sections):
    """Generate improvement suggestions using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a professional resume improvement expert. Analyze this resume and suggest improvements for the following sections:
        1. Summary/Objective
        2. Skills
        3. Experience descriptions
        
        For each section, provide a completely rewritten version that improves upon the original.
        Format your response as a JSON object with section names as keys and your suggested improvements as values.
        
        Resume sections:
        {json.dumps(resume_sections, indent=2)}
        
        Full resume text:
        {resume_text}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                suggestions = json.loads(json_str)
                return suggestions
            except json.JSONDecodeError:
                pass
                
        # Fallback suggestions
        return {
            "Summary": "Improved summary would go here",
            "Skills": "Improved skills would go here",
            "Experience": "Improved experience descriptions would go here"
        }
    except Exception as e:
        st.error(f"AI suggestion generation failed: {str(e)}")
        return {
            "Summary": "Improved summary would go here",
            "Skills": "Improved skills would go here",
            "Experience": "Improved experience descriptions would go here"
        }

def improve_resume(sections_text, job_type="general"):
    """Improve resume sections using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a professional resume writer. Improve all sections of this resume for {job_type} roles.
        Make the language more impactful, focus on achievements, and ensure it's ATS-friendly.
        
        Format your response as a JSON object with the same section names as keys and your improved content as values.
        
        Resume sections:
        {sections_text}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                improved_sections = json.loads(json_str)
                return improved_sections
            except json.JSONDecodeError:
                # If JSON parsing fails, return the original sections
                try:
                    return json.loads(sections_text)
                except:
                    return {}
        
        return {}
    except Exception as e:
        st.error(f"AI improvement failed: {str(e)}")
        return {}

def extract_job_features(job_description):
    """Extract key features from job description using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a job analysis expert. Extract the following key features from this job description:
        1. Required Skills
        2. Required Experience
        3. Education Requirements
        4. Job Responsibilities
        5. Company Values/Culture
        
        Format your response as a JSON object with these categories as keys and the extracted information as values.
        
        Job Description:
        {job_description}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                job_features = json.loads(json_str)
                return job_features
            except json.JSONDecodeError:
                pass
                
        # Fallback features
        return {
            "Required Skills": "Could not extract automatically",
            "Required Experience": "Could not extract automatically",
            "Education Requirements": "Could not extract automatically",
            "Job Responsibilities": "Could not extract automatically",
            "Company Values/Culture": "Could not extract automatically"
        }
    except Exception as e:
        st.error(f"Job feature extraction failed: {str(e)}")
        return {
            "Required Skills": "Could not extract automatically",
            "Required Experience": "Could not extract automatically",
            "Education Requirements": "Could not extract automatically",
            "Job Responsibilities": "Could not extract automatically",
            "Company Values/Culture": "Could not extract automatically"
        }

def calculate_match_score(resume_sections, job_features):
    """Calculate match score between resume and job using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a resume-job matching expert. Calculate a match score (0-100) between this resume and job description.
        Consider skills match, experience match, and overall fit.
        
        Format your response as a JSON object with these keys: match_score, skills_match, experience_match, education_match, overall_fit.
        Each value should be a number between 0 and 100.
        
        Resume sections:
        {json.dumps(resume_sections, indent=2)}
        
        Job features:
        {json.dumps(job_features, indent=2)}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                match_data = json.loads(json_str)
                return match_data
            except json.JSONDecodeError:
                pass
                
        # Fallback match data
        return {
            "match_score": 55,
            "skills_match": 60,
            "experience_match": 50,
            "education_match": 65,
            "overall_fit": 55
        }
    except Exception as e:
        st.error(f"Match calculation failed: {str(e)}")
        return {
            "match_score": 55,
            "skills_match": 60,
            "experience_match": 50,
            "education_match": 65,
            "overall_fit": 55
        }

def generate_enhancements(resume_sections, job_features):
    """Generate job-specific enhancements using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        prompt = f"""
        You are a resume tailoring expert. Enhance these resume sections to better match the job requirements.
        Focus on the Summary, Skills, and Experience sections.
        
        Format your response as a JSON object with section names as keys and your enhanced content as values.
        
        Resume sections:
        {json.dumps(resume_sections, indent=2)}
        
        Job features:
        {json.dumps(job_features, indent=2)}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                enhancements = json.loads(json_str)
                return enhancements
            except json.JSONDecodeError:
                pass
                
        # Fallback enhancements
        return {
            "Summary": "Enhanced job-specific summary would go here",
            "Skills": "Enhanced job-specific skills would go here",
            "Experience": "Enhanced job-specific experience descriptions would go here"
        }
    except Exception as e:
        st.error(f"Enhancement generation failed: {str(e)}")
        return {
            "Summary": "Enhanced job-specific summary would go here",
            "Skills": "Enhanced job-specific skills would go here",
            "Experience": "Enhanced job-specific experience descriptions would go here"
        }

def improve_for_job(sections_text, job_desc):
    """Improve resume for specific job using Gemini AI."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Parse sections_text into a dictionary if it's not already
        if isinstance(sections_text, str):
            try:
                sections = json.loads(sections_text)
            except:
                # Simple parsing if it's in "key: value" format
                sections = {}
                for line in sections_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        sections[key.strip()] = value.strip()
        else:
            sections = sections_text
        
        prompt = f"""
        You are a professional resume tailoring expert. Improve all sections of this resume to match this specific job description.
        Highlight relevant skills, use keywords from the job description, and focus on achievements that align with the job requirements.
        
        Format your response as a JSON object with the same section names as keys and your improved content as values.
        
        Resume sections:
        {json.dumps(sections, indent=2)}
        
        Job Description:
        {job_desc}
        """
        
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            try:
                improved_sections = json.loads(json_str)
                return improved_sections
            except json.JSONDecodeError:
                # If JSON parsing fails, return the original sections
                return sections
        
        return sections
    except Exception as e:
        st.error(f"Job-specific improvement failed: {str(e)}")
        return sections

def call_gemini_api(endpoint, data):
    """Call appropriate function based on endpoint, with fallbacks for when Gemini is not available."""
    try:
        if endpoint == "extract_sections":
            return parse_resume_sections(data.get("text", ""))
        elif endpoint == "score_resume":
            if GEMINI_AVAILABLE:
                return score_resume(data.get("text", ""))
            else:
                # Fallback scoring without AI
                return {
                    "overall_score": 65,
                    "ats_score": 60,
                    "content_score": 62,
                    "skills_score": 58,
                    "experience_score": 63,
                    "genai_score": 60,
                    "ai_score": 58
                }
        elif endpoint == "generate_suggestions":
            resume_text = data.get("text", "")
            resume_sections = parse_resume_sections(resume_text)
            if GEMINI_AVAILABLE:
                return generate_suggestions(resume_text, resume_sections)
            else:
                # Fallback suggestions without AI
                return {
                    "Summary": "Consider adding more quantifiable achievements and focusing on results.",
                    "Skills": "List skills in order of proficiency and relevance to your target role.",
                    "Experience": "Use action verbs and include metrics to demonstrate impact."
                }
        elif endpoint == "improve_resume":
            if GEMINI_AVAILABLE:
                return improve_resume(data.get("text", ""))
            else:
                # Simple improvements without AI
                sections_text = data.get("text", "")
                try:
                    # Try to parse the sections
                    sections = {}
                    for line in sections_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            sections[key.strip()] = value.strip()
                    return sections
                except:
                    return {}
        elif endpoint == "extract_job_features":
            if GEMINI_AVAILABLE:
                return extract_job_features(data.get("text", ""))
            else:
                # Simple job feature extraction without AI
                job_text = data.get("text", "")
                return {
                    "Required Skills": extract_skills_simple(job_text),
                    "Required Experience": extract_experience_simple(job_text),
                    "Education Requirements": extract_education_simple(job_text),
                    "Job Responsibilities": "Review the job description for detailed responsibilities",
                    "Company Values/Culture": "Review the job description for company culture information"
                }
        elif endpoint == "calculate_match_score":
            if GEMINI_AVAILABLE:
                return calculate_match_score(data.get("resume", {}), data.get("job", {}))
            else:
                # Simple match calculation without AI
                return {
                    "match_score": 55,
                    "skills_match": 60,
                    "experience_match": 50,
                    "education_match": 65,
                    "overall_fit": 55
                }
        elif endpoint == "generate_enhancements":
            if GEMINI_AVAILABLE:
                return generate_enhancements(data.get("resume", {}), data.get("job", {}))
            else:
                # Simple enhancements without AI
                return {
                    "Summary": "Tailor your summary to highlight skills and experiences relevant to this specific job.",
                    "Skills": "Prioritize skills mentioned in the job description and use the same terminology.",
                    "Experience": "Emphasize achievements that demonstrate the skills required for this position."
                }
        elif endpoint == "improve_for_job":
            if GEMINI_AVAILABLE:
                return improve_for_job(data.get("text", ""), data.get("job_desc", ""))
            else:
                # Simple job-specific improvements without AI
                sections_text = data.get("text", "")
                try:
                    # Try to parse the sections
                    sections = {}
                    for line in sections_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            sections[key.strip()] = value.strip()
                    return sections
                except:
                    return {}
        elif endpoint == "generate_pdf":
            # Parse the sections from the text
            sections_text = data.get("text", "")
            template = data.get("template", "Minimalist")
            
            try:
                # Try to parse the sections
                sections = {}
                if isinstance(sections_text, str):
                    for line in sections_text.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            sections[key.strip()] = value.strip()
                else:
                    sections = sections_text
                
                # Check if we have ReportLab available
                if not REPORTLAB_AVAILABLE:
                    st.warning("ReportLab is not available. Using a simple PDF generator.")
                    # Create a simple PDF with the content
                    try:
                        buffer = io.BytesIO()
                        from reportlab.lib.pagesizes import letter
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                        from reportlab.lib.styles import getSampleStyleSheet
                        
                        doc = SimpleDocTemplate(buffer, pagesize=letter)
                        styles = getSampleStyleSheet()
                        flowables = []
                        
                        for section, content in sections.items():
                            flowables.append(Paragraph(f"<b>{section}</b>", styles['Heading2']))
                            flowables.append(Spacer(1, 12))
                            flowables.append(Paragraph(content.replace('\n', '<br/>'), styles['Normal']))
                            flowables.append(Spacer(1, 24))
                        
                        doc.build(flowables)
                        return buffer.getvalue()
                    except Exception as e:
                        st.error(f"Failed to create simple PDF: {str(e)}")
                        return None
                
                # Generate PDF using our custom function
                return generate_pdf_from_sections(sections, template)
            except Exception as e:
                st.error(f"Failed to generate PDF: {str(e)}")
                return None
        else:
            st.error(f"Unknown endpoint: {endpoint}")
            return {}
    except Exception as e:
        st.error(f"API call failed: {str(e)}")
        return {}

# Simple helper functions for fallback mode
def extract_skills_simple(text):
    """Extract skills from text using regex patterns."""
    skills_pattern = r'\b(python|java|javascript|html|css|react|angular|vue|node|express|django|flask|sql|nosql|mongodb|mysql|postgresql|aws|azure|gcp|docker|kubernetes|git|agile|scrum|machine learning|deep learning|nlp|ai|data science|data analysis|statistics|communication|leadership|teamwork|problem solving)\b'
    skills = set()
    for line in text.lower().split('\n'):
        matches = re.findall(skills_pattern, line)
        skills.update(matches)
    
    return ", ".join(sorted(skills)) if skills else "No specific skills extracted"

def extract_experience_simple(text):
    """Extract experience requirements from text."""
    experience_pattern = r'\b(\d+)[+\-]?\s*(year|yr)[s]?\b'
    matches = re.findall(experience_pattern, text.lower())
    if matches:
        years = [int(match[0]) for match in matches]
        return f"{max(years)}+ years of experience required"
    return "Experience requirements not specified"

def extract_education_simple(text):
    """Extract education requirements from text."""
    education_pattern = r'\b(bachelor|master|phd|mba|bsc|msc|ba|bs|ms|degree)\b'
    matches = re.findall(education_pattern, text.lower())
    if matches:
        return f"Requires {', '.join(set(matches))} degree"
    return "Education requirements not specified"

def display_pdf(file):
    """Display PDF in the app."""
    try:
        base64_pdf = base64.b64encode(file.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Failed to display PDF: {str(e)}")

# --- Authentication ---
def login():
    st.title("Login")
    email = st.text_input("Email", key="login_email_unique")
    password = st.text_input("Password", type="password", key="login_password_unique")

    # Initialize session state for button disable
    if 'last_attempt_time' not in st.session_state:
        st.session_state['last_attempt_time'] = 0
    if 'button_disabled' not in st.session_state:
        st.session_state['button_disabled'] = False

    current_time = time.time()
    time_since_last_attempt = current_time - st.session_state['last_attempt_time']
    if time_since_last_attempt < 35 and st.session_state['button_disabled']:
        st.warning(f"Please wait {int(35 - time_since_last_attempt)} seconds before retrying.")
        login_button = st.button("Login", disabled=True, key="login_btn_disabled")
    else:
        login_button = st.button("Login", disabled=False, key="login_btn_enabled")

    if login_button and not st.session_state['button_disabled']:
        try:
            user = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state['user_id'] = user.user.id
            st.success("Logged in successfully!")
            st.session_state['button_disabled'] = False
            st.session_state.pop('last_attempt_time', None)  # Reset timer
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            st.session_state['last_attempt_time'] = time.time()
            st.session_state['button_disabled'] = True

def signup():
    # Keep the title but make the text inputs have unique keys
    st.title("Sign Up")
    email = st.text_input("Email", key="signup_email_unique")
    password = st.text_input("Password", type="password", key="signup_password_unique")

    # Initialize session state for button disable
    if 'last_signup_time' not in st.session_state:
        st.session_state['last_signup_time'] = 0
    if 'signup_button_disabled' not in st.session_state:
        st.session_state['signup_button_disabled'] = False

    current_time = time.time()
    time_since_last_attempt = current_time - st.session_state['last_signup_time']
    if time_since_last_attempt < 35 and st.session_state['signup_button_disabled']:
        st.warning(f"Please wait {int(35 - time_since_last_attempt)} seconds before retrying.")
        signup_button = st.button("Sign Up", disabled=True, key="signup_btn_disabled")
    else:
        signup_button = st.button("Sign Up", disabled=False, key="signup_btn_enabled")

    if signup_button and not st.session_state['signup_button_disabled']:
        try:
            user = supabase.auth.sign_up({"email": email, "password": password})
            st.success("Account created! Please log in.")
            st.session_state['signup_button_disabled'] = False
            st.session_state.pop('last_signup_time', None)  # Reset timer
            st.rerun()
        except Exception as e:
            st.error(f"Sign up failed: {str(e)}")
            st.session_state['last_signup_time'] = time.time()
            st.session_state['signup_button_disabled'] = True

# --- Main App Logic ---
if 'user_id' not in st.session_state:
    tab = st.sidebar.radio("Authentication", ["Login", "Sign Up"], key="sidebar_auth_tabs")
    if tab == "Login":
        # Instead of calling login(), we'll handle authentication in the main function
        st.sidebar.info("Please use the login form on the main page")
    else:
        # Instead of calling signup(), we'll handle authentication in the main function
        st.sidebar.info("Please use the sign up form on the main page")
else:
    # Sidebar Navigation
    st.sidebar.title("Resume Optimizer Pro")
    st.sidebar.markdown("Welcome! Choose a feature below:")
    page = st.sidebar.radio("Features", ["Resume Enhancer", "Resume Job Matching"], label_visibility="collapsed")
    st.sidebar.markdown("""
        <div class='tooltip'>
            <span>ℹ️ Need Help?</span>
            <span class='tooltiptext'>Select a feature to enhance your resume or match it to a job!</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Add logout button
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Resume Enhancer Feature ---
    if page == "Resume Enhancer":
        st.title("Resume Enhancer")
        st.markdown("Optimize your resume for GenAI and AI roles with AI-driven insights.")

        # Step 1: Resume Upload
        uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf", help="Max file size: 5MB")
        if uploaded_file:
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("File size exceeds 5MB limit.")
            else:
                with st.spinner("Uploading and analyzing resume..."):
                    # Store file using our improved function
                    file_name = store_file_in_supabase(uploaded_file, st.session_state['user_id'], "original")
                    if file_name:
                        # Reset file pointer for reading
                        uploaded_file.seek(0)
                        resume_text = extract_text_from_pdf(uploaded_file)

                        # Step 2: Key Feature Extraction
                        extraction_data = {"text": resume_text}
                        sections = call_gemini_api("extract_sections", extraction_data)
                        
                        # If API call failed, provide mock data for testing
                        if not sections:
                            st.warning("API call failed. Using sample data for demonstration.")
                            sections = {
                                "Contact Information": "John Doe\njohndoe@email.com\n(123) 456-7890",
                                "Summary": "Experienced AI engineer with expertise in machine learning and NLP.",
                                "Skills": "Python, TensorFlow, PyTorch, NLP, Computer Vision",
                                "Experience": "AI Engineer, Tech Corp (2020-Present)\nData Scientist, Data Inc (2018-2020)",
                                "Education": "MS in Computer Science, University of Technology (2018)"
                            }

                        st.markdown("<div class='section-header'>Extracted Sections</div>", unsafe_allow_html=True)
                        
                        # Group sections for better organization
                        section_groups = {
                            "Basic Information": ["Contact Information", "Summary", "Objective", "Professional Summary"],
                            "Skills": ["Skills", "Technical Skills", "Soft Skills"],
                            "Experience & Education": ["Experience", "Work Experience", "Employment History", "Education"],
                            "Projects & Achievements": ["Projects", "Awards", "Achievements", "Certifications", "Publications", "Patents"],
                            "Additional Information": ["Languages", "Interests", "Hobbies", "Volunteer Experience", "Professional Affiliations", "References"]
                        }
                        
                        edited_sections = {}
                        
                        # Display sections by group
                        for group_name, group_sections in section_groups.items():
                            with st.expander(f"{group_name}", expanded=group_name == "Basic Information"):
                                st.markdown(f"<h4>{group_name}</h4>", unsafe_allow_html=True)
                                for section in group_sections:
                                    if section in sections and sections[section]:
                                        st.markdown(f"<b>{section}</b>", unsafe_allow_html=True)
                                        edited_sections[section] = st.text_area(f"Edit {section}", value=sections[section], height=150, key=f"edit_{section}")
                                    elif section in sections:
                                        st.markdown(f"<b>{section}</b> <span class='missing-section'>(Missing)</span>", unsafe_allow_html=True)
                                        edited_sections[section] = st.text_area(f"Add {section}", value="", height=150, key=f"add_{section}")
                        
                        # Add option to create additional sections
                        with st.expander("Add Custom Section"):
                            custom_section_name = st.text_input("Section Name")
                            if custom_section_name:
                                custom_section_content = st.text_area(f"Content for {custom_section_name}", height=150)
                                if st.button("Add Section"):
                                    edited_sections[custom_section_name] = custom_section_content
                                    st.success(f"Added {custom_section_name} section!")
                                    st.rerun()

                        # Step 3: AI-Based Scoring
                        st.markdown("<div class='section-header'>Resume Scoring</div>", unsafe_allow_html=True)
                        scoring_data = {"text": resume_text}
                        scores = call_gemini_api("score_resume", scoring_data)
                        
                        # If API call failed, provide mock data for testing
                        if not scores:
                            st.warning("API call failed. Using sample scores for demonstration.")
                            scores = {
                                'overall_score': 65, 
                                'ats_score': 60, 
                                'content_score': 62,
                                'skills_score': 58,
                                'experience_score': 63,
                                'genai_score': 60, 
                                'ai_score': 58
                            }
                            
                        # Display scores in a more organized way
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            overall_score = scores.get('overall_score', 0)
                            score_class = "score-low" if overall_score <= 60 else "score-high"
                            st.markdown(f"<div class='score-display {score_class}'>Overall Score: {overall_score}/100</div>", unsafe_allow_html=True)
                            
                            ats_score = scores.get('ats_score', 0)
                            score_class = "score-low" if ats_score <= 60 else "score-high"
                            st.markdown(f"<div class='score-display {score_class}'>ATS Score: {ats_score}/100</div>", unsafe_allow_html=True)
                        
                        with col2:
                            content_score = scores.get('content_score', 0)
                            score_class = "score-low" if content_score <= 60 else "score-high"
                            st.markdown(f"<div class='score-display {score_class}'>Content Score: {content_score}/100</div>", unsafe_allow_html=True)
                            
                            skills_score = scores.get('skills_score', 0)
                            score_class = "score-low" if skills_score <= 60 else "score-high"
                            st.markdown(f"<div class='score-display {score_class}'>Skills Score: {skills_score}/100</div>", unsafe_allow_html=True)
                        
                        with col3:
                            genai_score = scores.get('genai_score', 0)
                            score_class = "score-low" if (genai_score or 0) <= 60 else "score-high"
                            st.markdown(f"<div class='score-display {score_class}'>GenAI Score: {genai_score}/100</div>", unsafe_allow_html=True)
                            
                            ai_score = scores.get('ai_score', 0)
                            score_class = "score-low" if ai_score <= 60 else "score-high"
                            st.markdown(f"<div class='score-display {score_class}'>AI Score: {ai_score}/100</div>", unsafe_allow_html=True)

                        # Step 4 & 5: Decision Point and AI-Based Enhancement
                        if overall_score <= 70 or genai_score <= 65 or ai_score <= 65:
                            st.markdown("<div class='section-header'>AI Suggestions</div>", unsafe_allow_html=True)
                            suggestions = call_gemini_api("generate_suggestions", {"text": resume_text})
                            
                            # If API call failed, provide mock data for testing
                            if not suggestions:
                                st.warning("API call failed. Using sample suggestions for demonstration.")
                                suggestions = {
                                    "Summary": "Innovative AI Engineer with 5+ years of experience in developing machine learning models and NLP solutions. Proven track record of implementing cutting-edge AI technologies to solve complex business problems.",
                                    "Skills": "Python, TensorFlow, PyTorch, NLP, Computer Vision, Deep Learning, Transformer Models, GPT, BERT, Data Analysis, SQL, Cloud ML (AWS, GCP)"
                                }
                                
                            for section, suggestion in suggestions.items():
                                if section in sections:
                                    with st.expander(f"Suggestion for {section}", expanded=True):
                                        col_orig, col_sugg = st.columns(2)
                                        with col_orig:
                                            st.markdown(f"<b>Original {section}:</b>", unsafe_allow_html=True)
                                            st.write(sections.get(section, "Missing"))
                                        with col_sugg:
                                            st.markdown(f"<b>Suggested {section}:</b>", unsafe_allow_html=True)
                                            st.write(suggestion)
                                        
                                        if st.button(f"Accept Suggestion for {section}", key=f"accept_{section}"):
                                            edited_sections[section] = suggestion
                                            st.success(f"{section} updated!")
                                            st.rerun()

                        # Step 6: Edit Option
                        st.markdown("<div class='section-header'>Resume Enhancement</div>", unsafe_allow_html=True)
                        
                        enhancement_options = st.radio(
                            "Enhancement Options",
                            ["Improve with AI", "Optimize for ATS", "Highlight Achievements"],
                            horizontal=True
                        )
                        
                        if st.button("Apply Enhancement"):
                            with st.spinner("Generating AI improvements..."):
                                improv_data = {"text": "\n".join(f"{k}: {v}" for k, v in edited_sections.items())}
                                
                                if enhancement_options == "Optimize for ATS":
                                    # Add ATS optimization instruction
                                    improv_data["job_type"] = "ATS-optimized"
                                elif enhancement_options == "Highlight Achievements":
                                    # Add achievement focus instruction
                                    improv_data["job_type"] = "achievement-focused"
                                
                                improved_text = call_gemini_api("improve_resume", improv_data)
                                
                                # If API call failed, provide mock data for testing
                                if not improved_text:
                                    st.warning("API call failed. Using sample improvements for demonstration.")
                                    improved_text = {k: f"Improved {v}" for k, v in edited_sections.items()}
                                    
                                for section, content in improved_text.items():
                                    edited_sections[section] = content
                                st.success("AI improvements applied!")
                                st.rerun()

                        # Step 7: Template Selection
                        st.markdown("<div class='section-header'>Resume Template</div>", unsafe_allow_html=True)
                        
                        # Initialize template selection in session state if not present
                        if 'selected_template' not in st.session_state:
                            st.session_state['selected_template'] = "Minimalist"
                        
                        # Create a more visual template selection interface
                        st.markdown("""
                        <style>
                        .template-card {
                            border: 2px solid #ddd;
                            border-radius: 10px;
                            padding: 15px;
                            margin-bottom: 15px;
                            transition: all 0.3s ease;
                            cursor: pointer;
                            position: relative;
                            overflow: hidden;
                        }
                        .template-card:hover {
                            border-color: var(--primary-color);
                            transform: translateY(-5px);
                            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
                        }
                        .template-card.selected {
                            border-color: var(--accent-color);
                            background-color: rgba(22, 160, 133, 0.1);
                        }
                        .template-card h4 {
                            margin-top: 0;
                            color: var(--secondary-color);
                            font-weight: 600;
                        }
                        .template-badge {
                            position: absolute;
                            top: 10px;
                            right: 10px;
                            background: var(--accent-color);
                            color: white;
                            padding: 3px 8px;
                            border-radius: 10px;
                            font-size: 12px;
                            font-weight: 600;
                        }
                        .template-features {
                            margin-top: 10px;
                            font-size: 14px;
                        }
                        .template-features li {
                            margin-bottom: 5px;
                        }
                        .template-preview {
                            width: 100%;
                            height: 120px;
                            background-color: #f8f9fa;
                            border-radius: 5px;
                            margin-top: 10px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            overflow: hidden;
                        }
                        .template-preview img {
                            max-width: 100%;
                            max-height: 100%;
                            object-fit: contain;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            minimalist_class = "template-card selected" if st.session_state['selected_template'] == "Minimalist" else "template-card"
                            st.markdown(f"""
                            <div class="{minimalist_class}" id="minimalist-template">
                                <h4>Minimalist</h4>
                                <div class="template-badge">Professional</div>
                                <div class="template-preview">
                                    <div style="text-align: center; width: 100%;">
                                        <div style="font-size: 18px; font-weight: bold; color: #2E7DAF;">JOHN DOE</div>
                                        <div style="font-size: 10px; color: #666;">johndoe@email.com | (123) 456-7890</div>
                                        <hr style="margin: 5px 0; border-color: #2E7DAF;">
                                        <div style="font-size: 12px; font-weight: bold; color: #2E7DAF;">EXPERIENCE</div>
                                    </div>
                                </div>
                                <div class="template-features">
                                    <ul>
                                        <li>Clean, elegant design</li>
                                        <li>Focuses on content clarity</li>
                                        <li>Ideal for most industries</li>
                                    </ul>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Select Minimalist", key="select_minimalist"):
                                st.session_state['selected_template'] = "Minimalist"
                                st.rerun()
                            
                        with col2:
                            ats_class = "template-card selected" if st.session_state['selected_template'] == "ATS-Friendly" else "template-card"
                            st.markdown(f"""
                            <div class="{ats_class}" id="ats-template">
                                <h4>ATS-Friendly</h4>
                                <div class="template-badge">Optimized</div>
                                <div class="template-preview">
                                    <div style="text-align: left; width: 100%; padding: 10px;">
                                        <div style="font-size: 16px; font-weight: bold; text-align: center;">JOHN DOE</div>
                                        <div style="font-size: 10px; text-align: center;">johndoe@email.com | (123) 456-7890</div>
                                        <div style="font-size: 12px; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #000;">SKILLS</div>
                                        <div style="font-size: 10px;">• Python • Machine Learning • Data Analysis</div>
                                    </div>
                                </div>
                                <div class="template-features">
                                    <ul>
                                        <li>Optimized for ATS systems</li>
                                        <li>Keyword-friendly formatting</li>
                                        <li>Clear section headers</li>
                                    </ul>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Select ATS-Friendly", key="select_ats"):
                                st.session_state['selected_template'] = "ATS-Friendly"
                                st.rerun()
                            
                        with col3:
                            project_class = "template-card selected" if st.session_state['selected_template'] == "Project-Focused" else "template-card"
                            st.markdown(f"""
                            <div class="{project_class}" id="project-template">
                                <h4>Project-Focused</h4>
                                <div class="template-badge">Technical</div>
                                <div class="template-preview">
                                    <div style="text-align: left; width: 100%; padding: 10px;">
                                        <div style="font-size: 16px; font-weight: bold; text-align: center;">JOHN DOE</div>
                                        <div style="font-size: 10px; text-align: center;">johndoe@email.com | (123) 456-7890</div>
                                        <div style="font-size: 12px; font-weight: bold; margin-top: 5px; color: #16A085;">PROJECTS</div>
                                        <div style="font-size: 11px; font-weight: bold;">AI Chatbot (2023)</div>
                                        <div style="font-size: 9px;">Developed using Python & TensorFlow</div>
                                    </div>
                                </div>
                                <div class="template-features">
                                    <ul>
                                        <li>Highlights project work</li>
                                        <li>Perfect for technical roles</li>
                                        <li>Showcases technical skills</li>
                                    </ul>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button("Select Project-Focused", key="select_project"):
                                st.session_state['selected_template'] = "Project-Focused"
                                st.rerun()
                        
                        st.info(f"Current template: {st.session_state['selected_template']}")

                        # Step 8: Standard Format and Download
                        st.markdown("<div class='section-header'>Generate and Download</div>", unsafe_allow_html=True)
                        
                        # Add options for additional enhancements
                        enhancement_col1, enhancement_col2 = st.columns(2)
                        
                        with enhancement_col1:
                            include_qr = st.checkbox("Include QR Code to LinkedIn/Portfolio", value=False, 
                                                    help="Adds a QR code linking to your LinkedIn or portfolio")
                            
                            color_scheme = st.selectbox("Color Scheme", 
                                                      ["Professional Blue", "Modern Green", "Classic Black", "Creative Purple"],
                                                      help="Choose a color scheme for your resume")
                        
                        with enhancement_col2:
                            add_achievements = st.checkbox("Highlight Key Achievements", value=True,
                                                         help="AI will identify and highlight key achievements")
                            
                            formatting_style = st.selectbox("Formatting Style",
                                                          ["Modern", "Traditional", "Compact", "Expanded"],
                                                          help="Choose the overall formatting style")
                        
                        if st.button("Generate and Download Resume", key="generate_resume_btn"):
                            with st.spinner("Generating enhanced PDF..."):
                                # Prepare data with all options
                                template_data = {
                                    "text": "\n".join(f"{k}: {v}" for k, v in edited_sections.items()), 
                                    "template": st.session_state['selected_template'],
                                    "options": {
                                        "include_qr": include_qr,
                                        "color_scheme": color_scheme,
                                        "add_achievements": add_achievements,
                                        "formatting_style": formatting_style
                                    }
                                }
                                
                                pdf_bytes = call_gemini_api("generate_pdf", template_data)
                                
                                if pdf_bytes:
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.download_button(
                                            "📥 Download Enhanced Resume", 
                                            data=pdf_bytes, 
                                            file_name="enhanced_resume.pdf", 
                                            mime="application/pdf",
                                            help="Download your enhanced resume as a PDF file",
                                            use_container_width=True
                                        )
                                    
                                    with col2:
                                        if st.button("📋 Save to My Collection", use_container_width=True):
                                            # Store the enhanced resume
                                            enhanced_file = io.BytesIO(pdf_bytes)
                                            enhanced_file.name = "enhanced_resume.pdf"
                                            file_name = store_file_in_supabase(enhanced_file, st.session_state['user_id'], "enhanced")
                                            if file_name:
                                                st.success("Resume saved to your collection!")
                                    
                                    st.session_state['pdf_preview'] = pdf_bytes
                                    st.success("Resume generated successfully!")
                                else:
                                    st.error("Failed to generate PDF. Please try again.")

                        # Preview with improved styling
                        if 'pdf_preview' in st.session_state:
                            st.markdown("<div class='section-header'>Preview</div>", unsafe_allow_html=True)
                            
                            # Add a more professional preview container
                            st.markdown("""
                            <style>
                            .pdf-preview-container {
                                border: 1px solid #ddd;
                                border-radius: 10px;
                                padding: 10px;
                                background-color: #f8f9fa;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            }
                            </style>
                            <div class="pdf-preview-container">
                            """, unsafe_allow_html=True)
                            
                            display_pdf(io.BytesIO(st.session_state['pdf_preview']))
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                            # Add sharing options
                            st.markdown("### Share Your Resume")
                            share_col1, share_col2, share_col3 = st.columns(3)
                            with share_col1:
                                st.button("📧 Email Resume", use_container_width=True)
                            with share_col2:
                                st.button("🔗 Copy Link", use_container_width=True)
                            with share_col3:
                                st.button("📱 Share to LinkedIn", use_container_width=True)

    # --- Resume Job Matching Feature ---
    elif page == "Resume Job Matching":
        st.title("Resume Job Matching")
        st.markdown("Tailor your resume to a specific job with AI-driven matching and optimization.")

        # Step 1: Resume Upload or Selection
        st.markdown("<div class='section-header'>Resume Selection</div>", unsafe_allow_html=True)
        
        resume_option = st.radio("Resume Source", ["Upload New", "Select Existing"], horizontal=True)
        resume_text = None
        
        if resume_option == "Upload New":
            uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf", 
                                           help="Upload your resume in PDF format (max 5MB)")
            if uploaded_file:
                if uploaded_file.size > 5 * 1024 * 1024:
                    st.error("File size exceeds 5MB limit.")
                else:
                    file_name = store_file_in_supabase(uploaded_file, st.session_state['user_id'], "original")
                    if file_name:
                        uploaded_file.seek(0)
                        resume_text = extract_text_from_pdf(uploaded_file)
                        st.success("Resume uploaded successfully!")
        else:
            # Get list of files from both Supabase and local storage
            user_files = list_files(st.session_state['user_id'])
            
            if user_files:
                selected_resume = st.selectbox("Select a Resume", user_files, 
                                             help="Choose from your previously uploaded resumes")
                if selected_resume:
                    # Get file from either Supabase or local storage
                    resume_file = get_file(selected_resume)
                    if resume_file:
                        resume_text = extract_text_from_pdf(resume_file)
                        st.success(f"Selected resume: {selected_resume}")
                    else:
                        st.error("Failed to retrieve the selected resume.")
            else:
                st.warning("No existing resumes found. Please upload a new resume.")

        # Step 2: Job Description Input
        st.markdown("<div class='section-header'>Job Description</div>", unsafe_allow_html=True)
        
        job_desc_col1, job_desc_col2 = st.columns([3, 1])
        
        with job_desc_col1:
            job_desc = st.text_area("Enter Job Description", height=200, 
                                  help="Paste the job description here to match against your resume")
        
        with job_desc_col2:
            st.markdown("""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 32px;">
                <h4 style="margin-top: 0;">Tips</h4>
                <ul style="font-size: 0.9em; padding-left: 20px;">
                    <li>Include the full job description</li>
                    <li>Make sure to include requirements</li>
                    <li>Copy company values if available</li>
                    <li>Include desired skills section</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # Add option to upload job description as file
            job_desc_file = st.file_uploader("Or upload job description", type=["pdf", "txt", "docx"], 
                                           help="Upload job description as a file")
            if job_desc_file:
                try:
                    if job_desc_file.type == "application/pdf":
                        job_desc_file.seek(0)
                        job_desc = extract_text_from_pdf(job_desc_file)
                    elif job_desc_file.type == "text/plain":
                        job_desc = job_desc_file.getvalue().decode("utf-8")
                    else:
                        st.warning("File type not supported for direct extraction. Please copy and paste the content.")
                except Exception as e:
                    st.error(f"Error extracting text from file: {str(e)}")
        
        if resume_text and job_desc:
            with st.spinner("Processing resume and job description..."):
                # Step 3: Key Feature Extraction
                st.markdown("<div class='section-header'>Resume Analysis</div>", unsafe_allow_html=True)
                
                # Create tabs for different analysis views
                analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["Extracted Sections", "Job Requirements", "Gap Analysis"])
                
                with analysis_tab1:
                    resume_data = {"text": resume_text}
                    resume_sections = call_gemini_api("extract_sections", resume_data)
                    
                    # If API calls failed, provide mock data for testing
                    if not resume_sections:
                        st.warning("API call failed. Using sample resume sections for demonstration.")
                        resume_sections = {
                            "Personal Information": "John Doe\njohndoe@email.com\n(123) 456-7890",
                            "Summary": "Experienced AI engineer with expertise in machine learning and NLP.",
                            "Skills": "Python, TensorFlow, PyTorch, NLP, Computer Vision",
                            "Experience": "AI Engineer, Tech Corp (2020-Present)\nData Scientist, Data Inc (2018-2020)",
                            "Education": "MS in Computer Science, University of Technology (2018)"
                        }
                    
                    # Group sections for better organization
                    section_groups = {
                        "Basic Information": ["Personal Information", "Summary", "Objective", "Professional Summary"],
                        "Skills": ["Skills", "Technical Skills", "Soft Skills"],
                        "Experience & Education": ["Experience", "Work Experience", "Employment History", "Education"],
                        "Projects & Achievements": ["Projects", "Awards", "Achievements", "Certifications", "Publications", "Patents"],
                        "Additional Information": ["Languages", "Interests", "Hobbies", "Volunteer Experience", "Professional Affiliations", "References"]
                    }
                    
                    edited_sections = {}
                    
                    # Display sections by group
                    for group_name, group_sections in section_groups.items():
                        with st.expander(f"{group_name}", expanded=group_name == "Basic Information"):
                            st.markdown(f"<h4>{group_name}</h4>", unsafe_allow_html=True)
                            for section in group_sections:
                                if section in resume_sections and resume_sections[section]:
                                    st.markdown(f"<b>{section}</b>", unsafe_allow_html=True)
                                    edited_sections[section] = st.text_area(f"Edit {section}", value=resume_sections[section], height=150, key=f"job_edit_{section}")
                                elif section in resume_sections:
                                    st.markdown(f"<b>{section}</b> <span class='missing-section'>(Missing)</span>", unsafe_allow_html=True)
                                    edited_sections[section] = st.text_area(f"Add {section}", value="", height=150, key=f"job_add_{section}")
                
                with analysis_tab2:
                    job_data = {"text": job_desc}
                    job_features = call_gemini_api("extract_job_features", job_data)
                    
                    # If API calls failed, provide mock data for testing
                    if not job_features:
                        st.warning("API call failed. Using sample job features for demonstration.")
                        job_features = {
                            "Required Skills": "Python, Machine Learning, Deep Learning, NLP, AWS",
                            "Required Experience": "3-5 years in machine learning or related field",
                            "Education Requirements": "Master's or PhD in Computer Science, Machine Learning, or related field",
                            "Job Responsibilities": "Develop and deploy machine learning models, collaborate with cross-functional teams",
                            "Company Values/Culture": "Innovation, collaboration, excellence"
                        }
                    
                    # Display job features in a more organized way
                    for feature, content in job_features.items():
                        with st.expander(feature, expanded=True):
                            st.write(content)
                
                with analysis_tab3:
                    # Calculate and display gap analysis
                    st.subheader("Skills Gap Analysis")
                    
                    # Extract skills from resume and job - with type checking to fix AttributeError
                    resume_skills_text = resume_sections.get("Skills", "")
                    resume_skills_text = resume_skills_text.lower() if isinstance(resume_skills_text, str) else ""
                    
                    # Handle job_skills which may be a list or string
                    job_skills_data = job_features.get("Required Skills", "")
                    
                    # Fix AttributeError by properly handling different types
                    if isinstance(job_skills_data, list):
                        job_skills_text = ", ".join(str(skill) for skill in job_skills_data)
                    elif isinstance(job_skills_data, str):
                        job_skills_text = job_skills_data.lower()
                    else:
                        job_skills_text = str(job_skills_data)
                    
                    # Convert to sets for comparison - improved tokenization
                    resume_skills_set = {skill.strip() for skill in resume_skills_text.replace(",", " ").split() if skill.strip()}
                    job_skills_set = {skill.strip() for skill in job_skills_text.replace(",", " ").split() if skill.strip()}
                    
                    # Find matching and missing skills
                    matching_skills = resume_skills_set.intersection(job_skills_set)
                    missing_skills = job_skills_set - resume_skills_set
                    
                    # Calculate match percentage
                    if job_skills_set:
                        match_percentage = len(matching_skills) / len(job_skills_set) * 100
                    else:
                        match_percentage = 0
                    
                    # Display match score with visual indicator
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("Match Score", f"{match_percentage:.1f}%")
                    
                    with col2:
                        # Progress bar with color coding
                        if match_percentage >= 80:
                            st.progress(match_percentage/100)
                            st.success("Strong match! Your resume aligns well with this job.")
                        elif match_percentage >= 60:
                            st.progress(match_percentage/100)
                            st.info("Good match with some skill gaps to address.")
                        elif match_percentage >= 40:
                            st.progress(match_percentage/100)
                            st.warning("Moderate match. Consider developing missing skills.")
                        else:
                            st.progress(match_percentage/100)
                            st.error("Significant skill gaps. Major tailoring recommended.")
                    
                    # Display skills comparison
                    st.markdown("### Skills Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 🎯 Skills Present in Your Resume")
                        if matching_skills:
                            for skill in sorted(matching_skills):
                                st.markdown(f"- ✅ {skill}")
                        else:
                            st.markdown("No directly matching skills found.")
                    
                    with col2:
                        st.markdown("#### 🚀 Skills to Develop")
                        if missing_skills:
                            for skill in sorted(missing_skills):
                                st.markdown(f"- ❌ {skill}")
                            
                            # AI-powered advice for addressing skill gaps
                            with st.expander("💡 How to develop these skills"):
                                missing_skills_list = ", ".join(missing_skills)
                                st.markdown(f"""
                                To improve your chances with this job, consider focusing on:
                                
                                1. **Take online courses or certifications** in: {missing_skills_list}
                                2. **Work on personal projects** that utilize these technologies
                                3. **Contribute to open-source projects** that use these skills
                                4. **Highlight transferable skills** in your resume that might relate to these areas
                                """)
                        else:
                            st.markdown("Your resume covers all the required skills. Great job!")
                    
                    # Display tailoring recommendations
                    st.markdown("### 📝 Resume Tailoring Recommendations")
                    
                    # Prepare general recommendations
                    recommendations = [
                        "Quantify achievements with metrics where possible (e.g., 'Increased efficiency by 30%')",
                        "Tailor your professional summary to highlight experience relevant to this position",
                        "Use action verbs at the beginning of bullet points",
                        "Ensure your most relevant experience is listed first in each section"
                    ]
                    
                    # Add skill-specific recommendations if there are missing skills
                    if missing_skills:
                        recommendations.insert(0, f"Add these key skills to your resume (if you possess them): {', '.join(list(missing_skills)[:5])}")
                    
                    # Display recommendations as checklist
                    for idx, rec in enumerate(recommendations):
                        st.checkbox(rec, key=f"rec_{idx}")
                        
                    # Call-to-action button for applying recommendations
                    if st.button("Apply these recommendations", key="apply_tailoring"):
                        st.info("💡 In the full version, we would automatically update your resume with these recommendations!")

                # Step 4: Match Score Calculation
                st.markdown("<div class='section-header'>Match Analysis</div>", unsafe_allow_html=True)
                
                match_data = {"resume": resume_sections, "job": job_features}
                match_result = call_gemini_api("calculate_match_score", match_data)
                
                # If API call failed, provide mock data for testing
                if not match_result:
                    st.warning("API call failed. Using sample match score for demonstration.")
                    match_result = {
                        'match_score': 55,
                        'skills_match': 60,
                        'experience_match': 50,
                        'education_match': 65,
                        'overall_fit': 55
                    }
                
                # Display match scores in a more visual way
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    match_score = match_result.get('match_score', 0)
                    score_class = "score-low" if match_score <= 60 else "score-high"
                    st.markdown(f"<div class='score-display {score_class}'>Overall Match: {match_score}/100</div>", unsafe_allow_html=True)
                
                with col2:
                    skills_match = match_result.get('skills_match', 0)
                    score_class = "score-low" if skills_match <= 60 else "score-high"
                    st.markdown(f"<div class='score-display {score_class}'>Skills Match: {skills_match}/100</div>", unsafe_allow_html=True)
                
                with col3:
                    experience_match = match_result.get('experience_match', 0)
                    score_class = "score-low" if experience_match <= 60 else "score-high"
                    st.markdown(f"<div class='score-display {score_class}'>Experience Match: {experience_match}/100</div>", unsafe_allow_html=True)
                
                # Additional scores
                col1, col2 = st.columns(2)
                
                with col1:
                    education_match = match_result.get('education_match', 0)
                    score_class = "score-low" if education_match <= 60 else "score-high"
                    st.markdown(f"<div class='score-display {score_class}'>Education Match: {education_match}/100</div>", unsafe_allow_html=True)
                
                with col2:
                    overall_fit = match_result.get('overall_fit', 0)
                    score_class = "score-low" if overall_fit <= 60 else "score-high"
                    st.markdown(f"<div class='score-display {score_class}'>Cultural Fit: {overall_fit}/100</div>", unsafe_allow_html=True)

                # Step 5 & 6: Decision Point and AI-Based Enhancement
                st.markdown("<div class='section-header'>Resume Optimization</div>", unsafe_allow_html=True)
                
                # Provide optimization recommendations based on match score
                if match_score <= 75:
                    st.info("Your resume could be better optimized for this job. Let's enhance it!")
                    
                    enhancements = call_gemini_api("generate_enhancements", match_data)
                    
                    # If API call failed, provide mock data for testing
                    if not enhancements:
                        st.warning("API call failed. Using sample enhancements for demonstration.")
                        enhancements = {
                            "Summary": "Results-driven AI Engineer with 5+ years of experience in developing machine learning models and NLP solutions. Proven expertise in Python, AWS, and deep learning frameworks to deliver scalable AI solutions.",
                            "Skills": "Python, TensorFlow, PyTorch, NLP, Computer Vision, AWS, Deep Learning, Transformer Models, REST APIs, Microservices"
                        }
                    
                    # Display enhancements with a better UI
                    for section, enhancement in enhancements.items():
                        if section in resume_sections:
                            with st.expander(f"Optimize {section}", expanded=True):
                                col_orig, col_enh = st.columns(2)
                                
                                with col_orig:
                                    st.markdown(f"<h4>Original {section}</h4>", unsafe_allow_html=True)
                                    st.markdown(f"""
                                    <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; background-color: #f8f9fa;">
                                        {resume_sections.get(section, "Missing").replace('\n', '<br>')}
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col_enh:
                                    st.markdown(f"<h4>Enhanced {section}</h4>", unsafe_allow_html=True)
                                    st.markdown(f"""
                                    <div style="border: 1px solid #27AE60; border-radius: 5px; padding: 10px; background-color: rgba(39, 174, 96, 0.1);">
                                        {enhancement.replace('\n', '<br>')}
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                if st.button(f"Apply this optimization to {section}", key=f"apply_opt_{section}"):
                                    edited_sections[section] = enhancement
                                    st.success(f"{section} updated with optimized content!")
                                    st.rerun()

                # Step 7: Edit Option
                if st.button("Improvise with AI"):
                    with st.spinner("Tailoring with AI..."):
                        improv_data = {"text": "\n".join(f"{k}: {v}" for k, v in edited_sections.items()), "job_desc": job_desc}
                        improved_text = call_gemini_api("improve_for_job", improv_data)
                        
                        # If API call failed, provide mock data for testing
                        if not improved_text:
                            st.warning("API call failed. Using sample improvements for demonstration.")
                            improved_text = {k: f"Job-tailored {v}" for k, v in edited_sections.items()}
                            
                        for section, content in improved_text.items():
                            edited_sections[section] = content
                        st.success("AI tailoring applied!")

                # Step 8: Template Application
                template = st.selectbox("Choose a Template", ["Minimalist", "ATS-Friendly", "Project-Focused"])

                # Step 9: Download and Storage
                if st.button("Generate and Download Tailored Resume"):
                    with st.spinner("Generating tailored PDF..."):
                        template_data = {"text": "\n".join(f"{k}: {v}" for k, v in edited_sections.items()), "template": template}
                        pdf_bytes = call_gemini_api("generate_pdf", template_data)
                        
                        # For demo purposes, if API fails, create a simple PDF
                        if not pdf_bytes:
                            st.warning("API call failed. Creating a simple PDF for demonstration.")
                            # Create a simple PDF with the content
                            try:
                                from reportlab.lib.pagesizes import letter
                                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                                from reportlab.lib.styles import getSampleStyleSheet
                                
                                buffer = io.BytesIO()
                                doc = SimpleDocTemplate(buffer, pagesize=letter)
                                styles = getSampleStyleSheet()
                                flowables = []
                                
                                for section, content in edited_sections.items():
                                    flowables.append(Paragraph(f"<b>{section}</b>", styles['Heading2']))
                                    flowables.append(Spacer(1, 12))
                                    flowables.append(Paragraph(content.replace('\n', '<br/>'), styles['Normal']))
                                    flowables.append(Spacer(1, 24))
                                
                                doc.build(flowables)
                                pdf_bytes = buffer.getvalue()
                            except Exception as e:
                                st.error(f"Failed to create PDF: {str(e)}")
                                pdf_bytes = None
                        
                        if pdf_bytes:
                            st.download_button("Download Tailored Resume", data=pdf_bytes, file_name="tailored_resume.pdf", mime="application/pdf")
                            # Store the tailored resume
                            tailored_file = io.BytesIO(pdf_bytes)
                            tailored_file.name = "tailored_resume.pdf"
                            store_file_in_supabase(tailored_file, st.session_state['user_id'], "tailored")
                            st.success("Tailored resume generated and saved!")
                            st.session_state['pdf_preview_job'] = pdf_bytes

                # Preview
                if 'pdf_preview_job' in st.session_state:
                    st.markdown("<div class='section-header'>Preview</div>", unsafe_allow_html=True)
                    display_pdf(io.BytesIO(st.session_state['pdf_preview_job']))

def display_template_selection():
    st.markdown('<h2 class="section-header">Select Resume Template</h2>', unsafe_allow_html=True)
    
    # Create a 3-column layout for templates
    col1, col2, col3 = st.columns(3)
    
    # Template options with visual cards
    with col1:
        minimalist_selected = st.session_state.get('template', '') == 'Minimalist'
        minimalist_class = "template-card selected" if minimalist_selected else "template-card"
        
        st.markdown(f"""
        <div class="{minimalist_class}" id="minimalist-template">
            <span class="template-badge">Popular</span>
            <h4>Minimalist</h4>
            <div class="template-preview">
                <img src="https://i.imgur.com/JqzGIpZ.png" alt="Minimalist Template Preview" style="max-width: 100%; max-height: 100%;">
            </div>
            <ul class="template-features">
                <li>Clean, modern design</li>
                <li>Excellent for ATS systems</li>
                <li>Focuses on skills & experience</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select Minimalist", key="btn_minimalist"):
            st.session_state['template'] = 'Minimalist'
            st.rerun()
    
    with col2:
        ats_selected = st.session_state.get('template', '') == 'ATS-Friendly'
        ats_class = "template-card selected" if ats_selected else "template-card"
        
        st.markdown(f"""
        <div class="{ats_class}" id="ats-template">
            <span class="template-badge">ATS Optimized</span>
            <h4>ATS-Friendly</h4>
            <div class="template-preview">
                <img src="https://i.imgur.com/8T4FuYd.png" alt="ATS-Friendly Template Preview" style="max-width: 100%; max-height: 100%;">
            </div>
            <ul class="template-features">
                <li>Optimized for applicant tracking</li>
                <li>Clear section hierarchy</li>
                <li>Keyword-friendly formatting</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select ATS-Friendly", key="btn_ats"):
            st.session_state['template'] = 'ATS-Friendly'
            st.rerun()
    
    with col3:
        project_selected = st.session_state.get('template', '') == 'Project-Focused'
        project_class = "template-card selected" if project_selected else "template-card"
        
        st.markdown(f"""
        <div class="{project_class}" id="project-template">
            <span class="template-badge">Technical</span>
            <h4>Project-Focused</h4>
            <div class="template-preview">
                <img src="https://i.imgur.com/pQXQAUi.png" alt="Project-Focused Template Preview" style="max-width: 100%; max-height: 100%;">
            </div>
            <ul class="template-features">
                <li>Highlights projects & achievements</li>
                <li>Great for technical roles</li>
                <li>Includes skills visualization</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select Project-Focused", key="btn_project"):
            st.session_state['template'] = 'Project-Focused'
            st.rerun()
    
    # Display currently selected template
    if 'template' in st.session_state and st.session_state['template']:
        st.markdown(f"""
        <div class="alert alert-success">
            <strong>Selected Template:</strong> {st.session_state['template']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert alert-info">
            <strong>Tip:</strong> Choose a template that best matches your career goals and the position you're applying for.
        </div>
        """, unsafe_allow_html=True)
    
    return st.session_state.get('template', 'Minimalist')  # Default to Minimalist if none selected

def display_resume_score(sections):
    st.markdown('<h2 class="section-header">Resume Score & Analysis</h2>', unsafe_allow_html=True)
    
    # Calculate scores based on resume content
    scores = calculate_resume_scores(sections)
    
    # Create a 3-column layout for score display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        overall_score = scores['overall']
        score_class = "score-high" if overall_score >= 80 else "score-medium" if overall_score >= 60 else "score-low"
        
        st.markdown(f"""
        <div class="score-display {score_class}">
            <span>Overall Score</span>
            <h2>{overall_score}/100</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Display feedback based on overall score
        if overall_score >= 80:
            st.markdown("""
            <div class="alert alert-success">
                <strong>Excellent!</strong> Your resume is well-structured and comprehensive.
            </div>
            """, unsafe_allow_html=True)
        elif overall_score >= 60:
            st.markdown("""
            <div class="alert alert-warning">
                <strong>Good start!</strong> Your resume has potential but needs some improvements.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert alert-error">
                <strong>Needs work!</strong> Your resume requires significant improvements to be competitive.
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        ats_score = scores['ats_compatibility']
        score_class = "score-high" if ats_score >= 80 else "score-medium" if ats_score >= 60 else "score-low"
        
        st.markdown(f"""
        <div class="score-display {score_class}">
            <span>ATS Compatibility</span>
            <h2>{ats_score}/100</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Display custom progress bars for ATS factors
        st.markdown('<div class="subsection-header">ATS Factors</div>', unsafe_allow_html=True)
        
        # Keywords presence
        keyword_score = scores.get('keyword_score', 65)
        st.markdown(f"""
        <div>Keywords Presence</div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {keyword_score}%;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Format compatibility
        format_score = scores.get('format_score', 75)
        st.markdown(f"""
        <div>Format Compatibility</div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {format_score}%;"></div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        content_score = scores['content_quality']
        score_class = "score-high" if content_score >= 80 else "score-medium" if content_score >= 60 else "score-low"
        
        st.markdown(f"""
        <div class="score-display {score_class}">
            <span>Content Quality</span>
            <h2>{content_score}/100</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Display section completeness
        st.markdown('<div class="subsection-header">Section Completeness</div>', unsafe_allow_html=True)
        
        # Check for key sections
        key_sections = {
            'Personal Information': sections.get('Personal Information', '') != '',
            'Summary/Objective': sections.get('Summary', '') != '' or sections.get('Objective', '') != '',
            'Skills': sections.get('Skills', '') != '',
            'Experience': sections.get('Experience', '') != '',
            'Education': sections.get('Education', '') != '',
            'Projects': sections.get('Projects', '') != ''
        }
        
        for section, present in key_sections.items():
            if present:
                st.markdown(f"""
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="color: var(--success-color); margin-right: 10px;">✓</div>
                    <div>{section}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="color: var(--error-color); margin-right: 10px;">✗</div>
                    <div>{section} <span style="color: var(--error-color); font-size: 12px;">(Missing)</span></div>
                </div>
                """, unsafe_allow_html=True)
    
    # Improvement suggestions
    st.markdown('<div class="subsection-header">Improvement Suggestions</div>', unsafe_allow_html=True)
    
    suggestions = generate_improvement_suggestions(sections, scores)
    
    for i, suggestion in enumerate(suggestions):
        st.markdown(f"""
        <div class="card">
            <div class="card-header">Suggestion #{i+1}</div>
            <div class="card-content">{suggestion}</div>
        </div>
        """, unsafe_allow_html=True)

def calculate_resume_scores(sections):
    """Calculate various scores for the resume based on content analysis"""
    scores = {}
    
    # Check for presence of key sections
    key_sections = ['Personal Information', 'Summary', 'Skills', 'Experience', 'Education']
    present_sections = sum(1 for section in key_sections if sections.get(section, '').strip())
    section_score = min(100, (present_sections / len(key_sections)) * 100)
    
    # Calculate content length score
    total_content = sum(len(content) for content in sections.values())
    length_score = min(100, (total_content / 2000) * 100)  # Assuming 2000 chars is optimal
    
    # Calculate keyword richness (simplified)
    all_content = ' '.join(sections.values()).lower()
    keywords = ['experience', 'skill', 'project', 'develop', 'manage', 'create', 'team', 
                'lead', 'analyze', 'implement', 'design', 'collaborate', 'achieve']
    keyword_count = sum(1 for keyword in keywords if keyword in all_content)
    keyword_score = min(100, (keyword_count / len(keywords)) * 100)
    
    # Calculate ATS compatibility score
    ats_score = (section_score * 0.5) + (keyword_score * 0.5)
    
    # Calculate content quality score (simplified)
    content_score = (section_score * 0.4) + (length_score * 0.3) + (keyword_score * 0.3)
    
    # Calculate overall score
    overall_score = int((ats_score * 0.5) + (content_score * 0.5))
    
    # Compile all scores
    scores = {
        'overall': overall_score,
        'ats_compatibility': int(ats_score),
        'content_quality': int(content_score),
        'section_score': int(section_score),
        'length_score': int(length_score),
        'keyword_score': int(keyword_score),
        'format_score': int(min(100, section_score + 10))  # Simplified format score
    }
    
    return scores

def generate_improvement_suggestions(sections, scores):
    """Generate personalized improvement suggestions based on resume content and scores"""
    suggestions = []
    
    # Check for missing sections
    key_sections = ['Personal Information', 'Summary', 'Skills', 'Experience', 'Education', 'Projects']
    for section in key_sections:
        if not sections.get(section, '').strip():
            suggestions.append(f"<strong>Add a {section} section</strong> to your resume. This is a critical section that recruiters look for.")
    
    # Check content quality
    if scores['content_quality'] < 70:
        suggestions.append("<strong>Enhance your content quality</strong> by adding more specific achievements and quantifiable results to your experience section.")
    
    # Check ATS compatibility
    if scores['ats_compatibility'] < 70:
        suggestions.append("<strong>Improve ATS compatibility</strong> by including more industry-specific keywords relevant to your target positions.")
    
    # Check for skills section quality
    skills = sections.get('Skills', '')
    if len(skills) < 100:
        suggestions.append("<strong>Expand your skills section</strong> with both technical and soft skills relevant to your industry.")
    
    # Check for summary quality
    summary = sections.get('Summary', '')
    if len(summary) < 200:
        suggestions.append("<strong>Enhance your professional summary</strong> with a compelling statement that highlights your unique value proposition.")
    
    # If no suggestions were generated, add a generic one
    if not suggestions:
        suggestions.append("<strong>Continue refining your resume</strong> by tailoring it to specific job descriptions and highlighting relevant achievements.")
    
    return suggestions

def display_job_matching_section(sections):
    st.markdown('<h2 class="section-header">Job Matching & Optimization</h2>', unsafe_allow_html=True)
    
    # Create tabs for different job matching features
    job_tabs = st.tabs(["📋 Job Description", "🔍 Skills Gap Analysis", "🚀 Resume Tailoring"])
    
    with job_tabs[0]:
        st.markdown('<div class="subsection-header">Enter Job Description</div>', unsafe_allow_html=True)
        
        # Job description input with placeholder text
        job_description_placeholder = """Paste the job description here to analyze how well your resume matches the requirements.

Example:
Software Engineer with 3+ years of experience in Python development. Proficient in web frameworks (Django, Flask), database design, and RESTful APIs. Experience with cloud services (AWS/Azure) and containerization (Docker) preferred. Strong problem-solving skills and ability to work in an agile team environment."""
        
        job_description = st.text_area("Job Description", 
                                      value=st.session_state.get('job_description', ''), 
                                      height=200,
                                      placeholder=job_description_placeholder)
        
        if job_description:
            st.session_state['job_description'] = job_description
            
            # Add a visually appealing "Analyze" button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                analyze_clicked = st.button("Analyze Job Match", use_container_width=True)
                
                if analyze_clicked:
                    with st.spinner("Analyzing job match..."):
                        # Perform job matching analysis
                        match_results = analyze_job_match(sections, job_description)
                        st.session_state['match_results'] = match_results
                        
                        # Switch to the Skills Gap tab
                        st.rerun()
        else:
            st.markdown("""
            <div class="alert alert-info">
                <strong>Tip:</strong> Paste a job description to see how well your resume matches the requirements and get tailoring suggestions.
            </div>
            """, unsafe_allow_html=True)
    
    with job_tabs[1]:
        if 'match_results' in st.session_state:
            match_results = st.session_state['match_results']
            
            # Display overall match score
            match_score = match_results.get('match_score', 65)
            score_class = "score-high" if match_score >= 80 else "score-medium" if match_score >= 60 else "score-low"
            
            st.markdown(f"""
            <div class="score-display {score_class}" style="margin-bottom: 20px;">
                <span>Job Match Score</span>
                <h2>{match_score}%</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Display skills comparison
            st.markdown('<div class="subsection-header">Skills Comparison</div>', unsafe_allow_html=True)
            
            # Create two columns for matched and missing skills
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div style="background-color: rgba(46, 204, 113, 0.1); padding: 15px; border-radius: 10px; border-left: 4px solid #2ECC71;">
                    <h4 style="color: #27AE60; margin-top: 0;">Matched Skills</h4>
                    <div style="max-height: 200px; overflow-y: auto;">
                """, unsafe_allow_html=True)
                
                matched_skills = match_results.get('matched_skills', ['Python', 'Problem-solving', 'Team collaboration'])
                for skill in matched_skills:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <div style="color: var(--success-color); margin-right: 10px;">✓</div>
                        <div>{skill}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div style="background-color: rgba(231, 76, 60, 0.1); padding: 15px; border-radius: 10px; border-left: 4px solid #E74C3C;">
                    <h4 style="color: #C0392B; margin-top: 0;">Missing Skills</h4>
                    <div style="max-height: 200px; overflow-y: auto;">
                """, unsafe_allow_html=True)
                
                missing_skills = match_results.get('missing_skills', ['Docker', 'AWS/Azure', 'Django'])
                for skill in missing_skills:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 8px;">
                        <div style="color: var(--error-color); margin-right: 10px;">✗</div>
                        <div>{skill}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
            
            # Display keyword frequency comparison
            st.markdown('<div class="subsection-header">Keyword Frequency</div>', unsafe_allow_html=True)
            
            # Create a visual representation of keyword frequency
            keywords = match_results.get('keywords', {
                'Python': {'job': 3, 'resume': 2},
                'Web Development': {'job': 2, 'resume': 1},
                'Database': {'job': 2, 'resume': 0},
                'Team': {'job': 1, 'resume': 3},
                'Problem-solving': {'job': 2, 'resume': 1}
            })
            
            for keyword, counts in keywords.items():
                job_count = counts.get('job', 0)
                resume_count = counts.get('resume', 0)
                
                # Calculate percentages for visual bars
                max_count = max(job_count, resume_count, 1)  # Avoid division by zero
                job_percent = (job_count / max_count) * 100
                resume_percent = (resume_count / max_count) * 100
                
                st.markdown(f"""
                <div style="margin-bottom: 15px;">
                    <div style="font-weight: 500; margin-bottom: 5px;">{keyword}</div>
                    <div style="display: flex; align-items: center; margin-bottom: 3px;">
                        <div style="width: 80px; font-size: 12px;">Job: {job_count}</div>
                        <div class="progress-container" style="flex-grow: 1;">
                            <div class="progress-bar" style="width: {job_percent}%; background: linear-gradient(90deg, #3498DB, #2980B9);"></div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 80px; font-size: 12px;">Resume: {resume_count}</div>
                        <div class="progress-container" style="flex-grow: 1;">
                            <div class="progress-bar" style="width: {resume_percent}%; background: linear-gradient(90deg, #2ECC71, #27AE60);"></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert alert-info">
                <strong>No analysis yet!</strong> Go to the Job Description tab and enter a job description to analyze.
            </div>
            """, unsafe_allow_html=True)
    
    with job_tabs[2]:
        if 'match_results' in st.session_state:
            st.markdown('<div class="subsection-header">Resume Tailoring Suggestions</div>', unsafe_allow_html=True)
            
            # Display tailoring suggestions
            suggestions = st.session_state['match_results'].get('tailoring_suggestions', [
                "Highlight your Python experience more prominently in your summary",
                "Add specific examples of web development projects",
                "Include any experience with cloud services, even if limited",
                "Quantify your achievements with metrics where possible"
            ])
            
            for i, suggestion in enumerate(suggestions):
                st.markdown(f"""
                <div class="card">
                    <div class="card-header">Suggestion #{i+1}</div>
                    <div class="card-content">{suggestion}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Section-by-section enhancement
            st.markdown('<div class="subsection-header">Section Enhancements</div>', unsafe_allow_html=True)
            
            # Create tabs for each section
            section_tabs = st.tabs(["Summary", "Skills", "Experience"])
            
            with section_tabs[0]:
                original_summary = sections.get('Summary', 'No summary section found in your resume.')
                
                col_orig, col_enh = st.columns(2)
                
                with col_orig:
                    st.markdown("<strong>Original Summary:</strong>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #dee2e6; height: 150px; overflow-y: auto;">
                        {original_summary}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_enh:
                    enhanced_summary = st.session_state['match_results'].get('enhanced_summary', 'Click "Enhance with AI" to generate a job-tailored summary.')
                    
                    st.markdown("<strong>Enhanced Summary:</strong>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #e8f4f8; padding: 10px; border-radius: 5px; border: 1px solid #bee5eb; height: 150px; overflow-y: auto;">
                        {enhanced_summary}
                    </div>
                    """, unsafe_allow_html=True)
            
            with section_tabs[1]:
                original_skills = sections.get('Skills', 'No skills section found in your resume.')
                
                col_orig, col_enh = st.columns(2)
                
                with col_orig:
                    st.markdown("<strong>Original Skills:</strong>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #dee2e6; height: 150px; overflow-y: auto;">
                        {original_skills}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_enh:
                    enhanced_skills = st.session_state['match_results'].get('enhanced_skills', 'Click "Enhance with AI" to generate job-tailored skills.')
                    
                    st.markdown("<strong>Enhanced Skills:</strong>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #e8f4f8; padding: 10px; border-radius: 5px; border: 1px solid #bee5eb; height: 150px; overflow-y: auto;">
                        {enhanced_skills}
                    </div>
                    """, unsafe_allow_html=True)
            
            with section_tabs[2]:
                original_experience = sections.get('Experience', 'No experience section found in your resume.')
                
                col_orig, col_enh = st.columns(2)
                
                with col_orig:
                    st.markdown("<strong>Original Experience:</strong>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #dee2e6; height: 200px; overflow-y: auto;">
                        {original_experience}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_enh:
                    enhanced_experience = st.session_state['match_results'].get('enhanced_experience', 'Click "Enhance with AI" to generate job-tailored experience descriptions.')
                    
                    st.markdown("<strong>Enhanced Experience:</strong>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background-color: #e8f4f8; padding: 10px; border-radius: 5px; border: 1px solid #bee5eb; height: 200px; overflow-y: auto;">
                        {enhanced_experience}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Add an "Enhance with AI" button
            if st.button("Enhance with AI", key="enhance_resume_btn", use_container_width=True):
                with st.spinner("Tailoring your resume with AI..."):
                    # Call AI to enhance resume sections
                    enhanced_sections = enhance_resume_for_job(sections, st.session_state['job_description'])
                    
                    # Update session state with enhanced sections
                    st.session_state['match_results']['enhanced_summary'] = enhanced_sections.get('Summary', '')
                    st.session_state['match_results']['enhanced_skills'] = enhanced_sections.get('Skills', '')
                    st.session_state['match_results']['enhanced_experience'] = enhanced_sections.get('Experience', '')
                    
                    # Rerun to display the enhanced sections
                    st.rerun()
            
            # Add an "Apply Changes" button
            if st.button("Apply Changes to Resume", key="apply_changes_btn", use_container_width=True):
                if 'match_results' in st.session_state and any(key in st.session_state['match_results'] for key in ['enhanced_summary', 'enhanced_skills', 'enhanced_experience']):
                    # Update the sections with enhanced content
                    if 'enhanced_summary' in st.session_state['match_results'] and st.session_state['match_results']['enhanced_summary']:
                        sections['Summary'] = st.session_state['match_results']['enhanced_summary']
                    
                    if 'enhanced_skills' in st.session_state['match_results'] and st.session_state['match_results']['enhanced_skills']:
                        sections['Skills'] = st.session_state['match_results']['enhanced_skills']
                    
                    if 'enhanced_experience' in st.session_state['match_results'] and st.session_state['match_results']['enhanced_experience']:
                        sections['Experience'] = st.session_state['match_results']['enhanced_experience']
                    
                    # Update session state with modified sections
                    st.session_state['sections'] = sections
                    
                    # Show success message
                    st.success("Resume updated with tailored content!")
                else:
                    st.warning("No enhanced content available. Please click 'Enhance with AI' first.")
        else:
            st.markdown("""
            <div class="alert alert-info">
                <strong>No job match analysis yet!</strong> Go to the Job Description tab and enter a job description to analyze.
            </div>
            """, unsafe_allow_html=True)

def analyze_job_match(resume_sections, job_description):
    """
    Enhanced implementation for analyzing how well a resume matches a job description.
    Provides detailed gap analysis and skill matching with improved accuracy.
    """
    # Extract all resume text
    resume_text = ' '.join(resume_sections.values()).lower() if isinstance(resume_sections, dict) else ""
    job_text = job_description.lower() if isinstance(job_description, str) else ""
    
    # Extract skills using enhanced method
    job_skills = extract_enhanced_skills(job_text)
    resume_skills = extract_enhanced_skills(resume_text)
    
    # Technical skill synonym mapping for better matching
    tech_synonyms = {
        "js": ["javascript"],
        "javascript": ["js"],
        "react": ["reactjs", "react.js"],
        "reactjs": ["react", "react.js"],
        "python": ["py"],
        "node": ["nodejs", "node.js"],
        "nodejs": ["node", "node.js"],
        "typescript": ["ts"],
        "ts": ["typescript"],
        "aws": ["amazon web services"],
        "azure": ["microsoft azure"],
        "ml": ["machine learning"],
        "ai": ["artificial intelligence"],
        "sql": ["mysql", "postgresql", "tsql", "database"],
        "ui": ["user interface"],
        "ux": ["user experience"],
        "ci/cd": ["continuous integration", "continuous deployment"],
        "api": ["rest", "rest api", "restful"],
        "nlp": ["natural language processing"],
        "cv": ["computer vision"]
    }
    
    # Find matched skills with synonym support
    matched_skills = []
    for resume_skill in resume_skills:
        # Direct match
        if resume_skill.lower() in [s.lower() for s in job_skills]:
            matched_skills.append(resume_skill)
            continue
            
        # Check for synonyms
        resume_skill_lower = resume_skill.lower()
        matched_by_synonym = False
        
        for job_skill in job_skills:
            job_skill_lower = job_skill.lower()
            
            # Check synonyms for resume skill
            if resume_skill_lower in tech_synonyms:
                if job_skill_lower in tech_synonyms[resume_skill_lower]:
                    matched_skills.append(resume_skill)
                    matched_by_synonym = True
                    break
            
            # Check synonyms for job skill
            if job_skill_lower in tech_synonyms:
                if resume_skill_lower in tech_synonyms[job_skill_lower]:
                    matched_skills.append(resume_skill)
                    matched_by_synonym = True
                    break
        
        if matched_by_synonym:
            continue
    
    # Find missing skills
    missing_skills = []
    for job_skill in job_skills:
        job_skill_lower = job_skill.lower()
        if not any(job_skill_lower == skill.lower() for skill in matched_skills):
            # Check if it's a synonym of any matched skill
            has_synonym_match = False
            for matched_skill in matched_skills:
                matched_skill_lower = matched_skill.lower()
                if matched_skill_lower in tech_synonyms and job_skill_lower in tech_synonyms[matched_skill_lower]:
                    has_synonym_match = True
                    break
                if job_skill_lower in tech_synonyms and matched_skill_lower in tech_synonyms[job_skill_lower]:
                    has_synonym_match = True
                    break
            
            if not has_synonym_match:
                missing_skills.append(job_skill)
    
    # Calculate match score with weighted relevance
    if len(job_skills) > 0:
        match_score = int((len(matched_skills) / len(job_skills)) * 100)
    else:
        match_score = 0
    
    # Extract keywords and their frequencies with enhanced list
    keywords = {}
    common_keywords = [
        'python', 'javascript', 'java', 'c++', 'sql', 'database', 'web', 'api', 
        'cloud', 'aws', 'azure', 'docker', 'kubernetes', 'agile', 'team', 
        'leadership', 'project', 'development', 'software', 'engineering',
        'problem-solving', 'communication', 'analysis', 'design', 'testing',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
        'devops', 'ci/cd', 'git', 'github', 'jira', 'scrum', 'kanban',
        'machine learning', 'ai', 'data science', 'tensorflow', 'pytorch',
        'nlp', 'computer vision', 'deep learning', 'automation', 'security',
        'linux', 'windows', 'macos', 'mobile', 'android', 'ios', 'swift',
        'kotlin', 'react native', 'flutter', 'blockchain', 'cybersecurity'
    ]
    
    for keyword in common_keywords:
        job_count = job_text.count(keyword)
        resume_count = resume_text.count(keyword)
        
        if job_count > 0 or resume_count > 0:
            keywords[keyword] = {
                'job_count': job_count,
                'resume_count': resume_count,
                'ratio': resume_count / max(1, job_count)
            }
    
    return {
        'match_score': match_score,
        'matched_skills': matched_skills,
        'missing_skills': missing_skills,
        'keyword_analysis': keywords
    }

def extract_enhanced_skills(text):
    """Extract skills from text using a more sophisticated approach"""
    if not text:
        return []
        
    # Common technical skills (expanded list)
    tech_skills = [
        'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
        'html', 'css', 'sql', 'nosql', 'mongodb', 'mysql', 'postgresql', 'oracle',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'asp.net',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'cloud', 'devops', 'ci/cd',
        'git', 'github', 'gitlab', 'bitbucket', 'jira', 'agile', 'scrum', 'kanban',
        'machine learning', 'ai', 'data science', 'big data', 'hadoop', 'spark',
        'tensorflow', 'pytorch', 'nlp', 'computer vision', 'deep learning',
        'react native', 'flutter', 'mobile development', 'ios', 'android',
        'web development', 'frontend', 'backend', 'full-stack', 'ui/ux',
        'restful api', 'graphql', 'microservices', 'serverless', 'linux',
        'windows', 'macos', 'bash', 'shell scripting', 'powershell',
        'blockchain', 'ethereum', 'solidity', 'smart contracts',
        'cybersecurity', 'penetration testing', 'network security',
        'data analysis', 'data visualization', 'tableau', 'power bi',
        'excel', 'vba', 'sap', 'erp', 'crm', 'salesforce'
    ]
    
    # Common soft skills (expanded list)
    soft_skills = [
        'communication', 'teamwork', 'leadership', 'problem-solving', 'critical thinking',
        'time management', 'organization', 'creativity', 'adaptability', 'flexibility',
        'project management', 'attention to detail', 'analytical', 'interpersonal',
        'presentation', 'negotiation', 'conflict resolution', 'decision making',
        'customer service', 'mentoring', 'coaching', 'collaboration', 'multitasking',
        'strategic thinking', 'innovation', 'emotional intelligence', 'public speaking',
        'research', 'writing', 'editing', 'design thinking', 'user research',
        'stakeholder management', 'client relations', 'sales', 'marketing',
        'budgeting', 'financial planning', 'resource allocation', 'risk management',
        'quality assurance', 'continuous improvement', 'people management',
        'cross-functional collaboration', 'international experience', 'cultural awareness'
    ]
    
    # Combine all skills
    all_skills = tech_skills + soft_skills
    
    # Extract skills from text with improved algorithm
    found_skills = []
    text_lower = text.lower()
    
    # Direct skill matching
    for skill in all_skills:
        # Look for whole word matches
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill.title())  # Capitalize for display
    
    # Skills in bullet points or semicolon-separated lists
    lines = text_lower.split('\n')
    for line in lines:
        # Check for bullet points
        if line.strip().startswith('•') or line.strip().startswith('-') or line.strip().startswith('*'):
            # Split by commas
            parts = [p.strip() for p in line.split(',')]
            for part in parts:
                # Clean up the part
                part = re.sub(r'[•\-*]', '', part).strip()
                # Check if it's a skill
                if part in [s.lower() for s in all_skills]:
                    found_skills.append(part.title())
    
    # Remove duplicates
    found_skills = list(set(found_skills))
    
    return found_skills

def enhance_resume_for_job(sections, job_description):
    """Use AI to enhance resume sections for a specific job"""
    # This is a placeholder implementation - in a real app, this would call an AI service
    
    # For demonstration purposes, we'll create mock enhanced sections
    enhanced_sections = {}
    
    # Extract skills from job description
    job_skills = extract_skills_from_text(job_description.lower())
    
    # Enhance summary
    if 'Summary' in sections:
        original_summary = sections['Summary']
        # In a real implementation, this would call an AI service
        enhanced_summary = f"Results-driven professional with expertise in {', '.join(job_skills[:3])}. {original_summary}"
        enhanced_sections['Summary'] = enhanced_summary
    
    # Enhance skills
    if 'Skills' in sections:
        original_skills = sections['Skills']
        # Add job-specific skills that might be missing
        enhanced_skills = original_skills
        for skill in job_skills:
            if skill.lower() not in original_skills.lower():
                enhanced_skills += f", {skill}"
        enhanced_sections['Skills'] = enhanced_skills
    
    # Enhance experience
    if 'Experience' in sections:
        original_experience = sections['Experience']
        # In a real implementation, this would call an AI service to rewrite experience
        # For now, we'll just highlight keywords from the job
        enhanced_experience = original_experience
        for skill in job_skills:
            # Simple highlighting by adding emphasis
            if skill.lower() in enhanced_experience.lower():
                enhanced_experience = enhanced_experience.replace(
                    skill, f"<strong>{skill}</strong>"
                ).replace(
                    skill.lower(), f"<strong>{skill.lower()}</strong>"
                ).replace(
                    skill.upper(), f"<strong>{skill.upper()}</strong>"
                )
        enhanced_sections['Experience'] = enhanced_experience
    
    return enhanced_sections

def main():
    # DO NOT put st.set_page_config() here - it must be at the top level
    
    # Initialize tabs variable with a default value
    tabs = None
    
    # Only show the title on the login page
    if 'user_id' not in st.session_state or not st.session_state.get('logged_in', False):
        st.title("Resume Optimizer")
        st.markdown("""
        <div class="app-description">
            Enhance your resume with AI-powered optimization, tailoring, and formatting
        </div>
        """, unsafe_allow_html=True)
    
    # Apply custom CSS
    st.markdown("""
    <style>
        .main-header {
            font-size: 36px;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 10px;
            text-align: center;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            padding: 20px 0;
        }
        
        .app-description {
            text-align: center;
            margin-bottom: 30px;
            font-size: 18px;
            color: var(--secondary-color);
        }
        
        .welcome-card {
            background: linear-gradient(135deg, rgba(46, 125, 175, 0.1), rgba(22, 160, 133, 0.1));
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(46, 125, 175, 0.2);
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
            position: relative;
            overflow: hidden;
        }
        
        .welcome-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        }
        
        .welcome-title {
            font-size: 24px;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 15px;
        }
        
        .welcome-subtitle {
            font-size: 18px;
            font-weight: 500;
            color: var(--secondary-color);
            margin-bottom: 20px;
        }
        
        .feature-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            border: 1px solid var(--light-gray);
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        }
        
        .feature-icon {
            font-size: 24px;
            margin-bottom: 10px;
            color: var(--primary-color);
        }
        
        .feature-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--secondary-color);
            margin-bottom: 10px;
        }
        
        .feature-description {
            font-size: 14px;
            color: var(--text-color);
        }
        
        .step-card {
            display: flex;
            align-items: flex-start;
            background-color: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid var(--light-gray);
        }
        
        .step-number {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            background-color: var(--primary-color);
            color: white;
            border-radius: 50%;
            font-weight: 600;
            margin-right: 15px;
            flex-shrink: 0;
        }
        
        .step-content {
            flex-grow: 1;
        }
        
        .step-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--secondary-color);
            margin-bottom: 5px;
        }
        
        .step-description {
            font-size: 14px;
            color: var(--text-color);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    if not st.session_state.get('logged_in', False):
        # Only show main header on login screen
        st.markdown('<h1 class="main-header">Resume Optimizer</h1>', unsafe_allow_html=True)
        st.markdown('<p class="app-description">Enhance your resume with AI-powered optimization, tailoring, and formatting</p>', unsafe_allow_html=True)
    
    # Initialize session state variables if they don't exist
    if 'user_id' not in st.session_state:
        # Don't automatically assign user_id, require login
        # Display login form instead
        login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
        
        with login_tab:
            email = st.text_input("Email", key="login_email_unique")
            password = st.text_input("Password", type="password", key="login_password_unique")
            
            if st.button("Login", key="login_button"):
                if email and password:  # Check that both fields are filled
                    try:
                        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state['user_id'] = user.user.id
                        st.session_state['logged_in'] = True
                        st.success("Logged in successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {str(e)}")
                else:
                    st.error("Please enter both email and password")
        
        with signup_tab:
            signup()
        
        # Stop execution here until logged in
        st.stop()
    
    if 'resume_text' not in st.session_state:
        st.session_state['resume_text'] = ""
    
    if 'sections' not in st.session_state:
        st.session_state['sections'] = {}
    
    if 'welcome_shown' not in st.session_state:
        st.session_state['welcome_shown'] = True
    
    # Welcome screen - only show on login screen
    if not st.session_state.get('logged_in', False) and st.session_state['welcome_shown'] and not st.session_state['sections']:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-title">Welcome to Resume Optimizer!</div>
            <div class="welcome-subtitle">Your AI-powered resume enhancement tool</div>
            <p>Resume Optimizer helps you create professional, ATS-friendly resumes tailored to specific job descriptions. Upload your existing resume or paste its content to get started.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Key features section
        st.markdown('<h2 class="section-header">Key Features</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Resume Analysis</div>
                <div class="feature-description">Get detailed feedback on your resume's strengths and weaknesses, with a comprehensive scoring system that evaluates ATS compatibility and content quality.</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🎯</div>
                <div class="feature-title">Job Matching</div>
                <div class="feature-description">Compare your resume against specific job descriptions to identify skill gaps and receive tailored suggestions to improve your match rate.</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">AI Enhancement</div>
                <div class="feature-description">Leverage AI to improve your resume content, highlight achievements, and optimize for Applicant Tracking Systems (ATS).</div>
            </div>
            """, unsafe_allow_html=True)
        
        # How it works section
        st.markdown('<h2 class="section-header">How It Works</h2>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="step-card">
            <div class="step-number">1</div>
            <div class="step-content">
                <div class="step-title">Upload Your Resume</div>
                <div class="step-description">Upload your existing resume in PDF, DOCX, or TXT format, or paste its content directly into the text area.</div>
            </div>
        </div>
        
        <div class="step-card">
            <div class="step-number">2</div>
            <div class="step-content">
                <div class="step-title">Analyze & Optimize</div>
                <div class="step-description">Review your resume score, analyze job match, and use AI-powered tools to enhance your content.</div>
            </div>
        </div>
        
        <div class="step-card">
            <div class="step-number">3</div>
            <div class="step-content">
                <div class="step-title">Select Template & Generate</div>
                <div class="step-description">Choose from professional templates, customize options, and generate a polished PDF resume.</div>
            </div>
        </div>
        
        <div class="step-card">
            <div class="step-number">4</div>
            <div class="step-content">
                <div class="step-title">Download & Apply</div>
                <div class="step-description">Download your optimized resume and start applying to jobs with confidence!</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Get started button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Get Started", use_container_width=True):
                st.session_state['welcome_shown'] = False
                st.rerun()
    
    # Create tabs for different app sections
    if st.session_state.get('logged_in', False) and (not st.session_state['welcome_shown'] or st.session_state['sections']):
        tabs = st.tabs(["📤 Upload Resume", "📝 Resume Analysis", "🎯 Job Matching", "🔄 Resume Enhancement", "📋 Templates", "📥 Download"])
        
        # Upload Resume Tab
        with tabs[0]:
            st.markdown('<h2 class="section-header">Upload Your Resume</h2>', unsafe_allow_html=True)
            
            # Create columns for upload options
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="card">
                    <div class="card-header">Upload Resume File</div>
                    <div class="card-content">
                        Upload your resume in PDF, DOCX, or TXT format to analyze and optimize it.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
    # Download Tab
    if tabs is not None and len(tabs) > 5:
        with tabs[5]:
            if 'sections' in st.session_state and st.session_state['sections']:
                st.markdown('<h2 class="section-header">Generate & Download Resume</h2>', unsafe_allow_html=True)
                
                # Get the selected template
                template = st.session_state.get('template', 'Minimalist')
                
                # Display the selected template
                selected_template_html = f"<div class='alert alert-success'><strong>Selected Template:</strong> {template}</div>"
                st.markdown(selected_template_html, unsafe_allow_html=True)
                
                # Add options for PDF generation
                st.markdown('<div class="subsection-header">PDF Options</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    color_scheme = st.selectbox("Color Scheme", 
                                              ["Professional Blue", "Modern Gray", "Bold Black", "Creative Green", "Elegant Purple"])
                
                with col2:
                    font_choice = st.selectbox("Font Style", 
                                             ["Default", "Modern", "Classic", "Elegant", "Bold"])
                
                # Additional options
                include_qr = st.checkbox("Include QR Code for LinkedIn/Portfolio", value=False)
                
                # Compile options
                options = {
                    "color_scheme": color_scheme,
                    "font": font_choice,
                    "include_qr": include_qr
                }
                
                # Generate and download button
                if st.button("Generate and Download Resume", key="generate_pdf_btn", use_container_width=True):
                    with st.spinner("Generating PDF resume..."):
                        # Generate PDF
                        pdf_bytes = generate_pdf_from_sections(st.session_state['sections'], template, options)
                        
                        if pdf_bytes:
                            # Store PDF in session state for preview
                            st.session_state['pdf_preview'] = pdf_bytes
                            
                            # Provide download button
                            st.download_button(
                                label="Download Resume PDF",
                                data=pdf_bytes,
                                file_name=f"optimized_resume_{template.lower().replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                            # Show success message
                            st.success("Resume PDF generated successfully!")
                        else:
                            st.error("Failed to generate PDF. Please try again.")
                
                # Preview section
                if 'pdf_preview' in st.session_state:
                    st.markdown('<div class="subsection-header">Preview</div>', unsafe_allow_html=True)
                    st.markdown('<div class="pdf-preview-container">', unsafe_allow_html=True)
                    display_pdf(io.BytesIO(st.session_state['pdf_preview']))
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("<div class='alert alert-info'><strong>No resume uploaded yet!</strong> Please upload your resume in the Upload Resume tab.</div>", unsafe_allow_html=True)

    # Add a footer with helpful information
    footer_html = "".join([
        "<div style='margin-top: 50px; padding: 25px 0; border-top: 1px solid #ECEFF1; text-align: center; font-size: 14px; color: #607D8B;'>",
        "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 15px;'>",
        "<div style='display: flex; gap: 20px; margin-bottom: 10px;'>",
        "<a href='#' style='color: #2E7DAF; text-decoration: none;'>Privacy Policy</a>",
        "<a href='#' style='color: #2E7DAF; text-decoration: none;'>Terms of Service</a>",
        "<a href='#' style='color: #2E7DAF; text-decoration: none;'>Help & Support</a>",
        "<a href='#' style='color: #2E7DAF; text-decoration: none;'>About</a>",
        "</div>",
        "<div>Resume Optimizer helps job seekers create professional, ATS-friendly resumes tailored to specific job descriptions.</div>",
        "<div style='font-size: 12px; opacity: 0.8;'>&copy; 2023 Resume Optimizer. All rights reserved.</div>",
        "</div>",
        "</div>"
    ])
    st.markdown(footer_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()