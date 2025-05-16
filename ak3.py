import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import os
from dotenv import load_dotenv
from io import BytesIO
import openpyxl
from sqlalchemy import create_engine, text
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Load environment variables
load_dotenv()

# Streamlit app configuration (MUST be the first Streamlit command)
st.set_page_config(page_title="Sylva Decors Enquiry System", page_icon="🪵", layout="wide")

# Custom CSS for styling with #d8d2ea and white background, dark headers, and Stardos Stencil font
st.markdown("""
    <style>
    /* Import Stardos Stencil font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Stardos+Stencil:wght@400;700&display=swap');
    /* Main app background */
    .stApp {
        background-color: #d8d2ea;
        color: #333333;
    }
    /* Tabs styling */
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF;
        color: #333333;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF;
        color: #333333;
        border-bottom: 2px solid #333333;
    }
    /* Form container */
    .stForm {
        background-color: #FFFFFF;
        border: 1px solid #d8d2ea;
        border-radius: 10px;
        padding: 20px;
    }
    /* Buttons */
    .stButton>button {
        background-color: #333333;
        color: #FFFFFF;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
    }
    .stButton>button:hover {
        background-color: #555555;
        color: #FFFFFF;
    }
    /* Headers */
    h1 {
        font-family: 'Stardos Stencil', sans-serif;
        color: #333333;
    }
    h2, h3 {
        font-family: 'Stardos Stencil', sans-serif;
        color: #d8d2ea;
    }
    /* Text inputs and select boxes */
    .stTextInput>div>input, .stSelectbox>div>select, .stMultiSelect>div {
        background-color: #FFFFFF;
        border: 1px solid #d8d2ea;
        color: #333333;
    }
    /* Dataframe */
    .stDataFrame {
        border: 1px solid #d8d2ea;
        background-color: #FFFFFF;
    }
    /* Hide the Streamlit toolbar (including Deploy button) */
    [data-testid="stToolbar"] {
        display: none;
    }
    /* Hide the entire header */
    header[data-testid="stHeader"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Database connection configuration using SQLAlchemy
def get_db_connection():
    connection_string = f"postgresql+psycopg2://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DATABASE')}"
    return create_engine(connection_string)

# Database initialization
def init_db():
    engine = get_db_connection()
    with engine.connect() as conn:
        conn.execute(text('''CREATE TABLE IF NOT EXISTS enquiries (
                             id SERIAL PRIMARY KEY,
                             name VARCHAR(255),
                             email VARCHAR(255),
                             phone VARCHAR(255),
                             furniture_type VARCHAR(255),
                             message TEXT,
                             timestamp TIMESTAMP
                             )'''))
        conn.execute(text('''CREATE TABLE IF NOT EXISTS users (
                             username VARCHAR(255) PRIMARY KEY,
                             password VARCHAR(255)
                             )'''))
        conn.commit()

# Add default owner credentials if not exists
def add_default_owner():
    engine = get_db_connection()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users WHERE username = :username"), {"username": "owner"}).fetchone()
        if not result:
            hashed = bcrypt.hashpw('sylva123'.encode('utf-8'), bcrypt.gensalt())
            conn.execute(text("INSERT INTO users (username, password) VALUES (:username, :password)"),
                         {"username": "owner", "password": hashed.decode('utf-8')})
            conn.commit()

# Verify login credentials
def verify_login(username, password):
    engine = get_db_connection()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT password FROM users WHERE username = :username"), {"username": username}).fetchone()
        if result:
            stored_password = result[0]
            return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
        return False

# Save enquiry to database
def save_enquiry(name, email, phone, furniture_types, message):
    engine = get_db_connection()
    with engine.connect() as conn:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        furniture_type_str = ", ".join(furniture_types) if furniture_types else ""
        conn.execute(text('''INSERT INTO enquiries (name, email, phone, furniture_type, message, timestamp)
                             VALUES (:name, :email, :phone, :furniture_type, :message, :timestamp)'''),
                     {"name": name, "email": email, "phone": phone, "furniture_type": furniture_type_str,
                      "message": message, "timestamp": timestamp})
        conn.commit()

# Fetch all enquiries
def get_enquiries():
    engine = get_db_connection()
    return pd.read_sql_query("SELECT * FROM enquiries", engine)

# Generate Excel file
def generate_excel(df):
    output = BytesIO()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Enquiries"
    
    # Add title
    sheet['A1'] = "Sylva Decors Inquiry List"
    sheet.merge_cells('A1:G1')  # Merge cells across 7 columns
    title_cell = sheet['A1']
    title_cell.font = openpyxl.styles.Font(bold=True, size=14)
    title_cell.alignment = openpyxl.styles.Alignment(horizontal='center')
    
    # Add dataframe starting from row 3 (leaving row 2 blank for spacing)
    for r_idx, row in enumerate(pd.DataFrame([df.columns]).values, 2):
        for c_idx, value in enumerate(row, 1):
            sheet.cell(row=r_idx, column=c_idx).value = value
            sheet.cell(row=r_idx, column=c_idx).font = openpyxl.styles.Font(bold=True)
    for r_idx, row in enumerate(df.values, 3):
        for c_idx, value in enumerate(row, 1):
            sheet.cell(row=r_idx + 1, column=c_idx).value = value
    
    # Auto-adjust column widths, skipping merged cells
    for col_idx in range(1, 8):  # Columns A to G
        column_letter = openpyxl.utils.get_column_letter(col_idx)
        max_length = 0
        for row in sheet[f"{column_letter}2:{column_letter}{sheet.max_row}"]:  # Start from row 2
            cell = row[0]
            if not isinstance(cell, openpyxl.cell.cell.MergedCell):
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
        adjusted_width = min((max_length + 2), 50)  # Cap width at 50 for readability
        sheet.column_dimensions[column_letter].width = adjusted_width
    
    workbook.save(output)
    return output.getvalue()

# Generate PDF file
def generate_pdf(df):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        spaceAfter=12,
        alignment=1,  # Center
    )
    cell_style = ParagraphStyle(
        name='CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        wordWrap='CJK',  # Enables word wrapping
        alignment=1,  # Center
    )
    
    # Add title
    title = Paragraph("Sylva Decors Inquiry List", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))  # Add spacing after title
    
    # Prepare data for PDF table
    data = [df.columns.tolist()] + df.values.tolist()
    
    # Convert all cells to Paragraphs for wrapping, except header
    wrapped_data = []
    for i, row in enumerate(data):
        if i == 0:  # Header row
            wrapped_row = [Paragraph(str(cell), styles['Heading4']) for cell in row]
        else:  # Data rows
            wrapped_row = [Paragraph(str(cell) if cell else "", cell_style) for cell in row]
        wrapped_data.append(wrapped_row)
    
    # Define column widths to fit letter page (612pt width, minus 72pt margins = 540pt)
    col_widths = [40, 80, 100, 80, 140, 80, 80]  # Adjusted for id, name, email, phone, furniture_type, message, timestamp
    
    # Create table
    table = Table(wrapped_data, colWidths=col_widths)
    
    # Style the table with white and #d8d2ea
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d8d2ea')),  # Header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Header text
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Body background
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d8d2ea')),  # Grid lines
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#d8d2ea')),  # Table border
    ]))
    
    elements.append(table)
    doc.build(elements)
    return output.getvalue()

# Initialize database and default owner
init_db()
add_default_owner()

# Tabs for Enquiry Form and Owner Login
tab1, tab2 = st.tabs(["Enquiry Form", "Owner Login"])

# Enquiry Form (Publicly Accessible)
with tab1:
    st.title("Sylva Decors Enquiry Form")
    st.write("Interested in our resin-based furniture? Fill out the form below!")

    with st.form("enquiry_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        phone = st.text_input("Phone Number")
        furniture_types = st.multiselect(
            "Furniture Types",
            [
                "Resin Furniture- Coffee Table",
                "Resin Furniture-Center Table",
                "Resin Furniture- Wall Panels",
                "Resin Furniture- Dining Table",
                "Resin Furniture- Conference Table",
                "Wall Decors - Geocode Wall Art",
                "Wall Decors-Ocean Inspired Wall Panels",
                "Wall Decors - Resin Wall Clock",
                "Functional Decors - Theme Based Coaster Set",
                "Functional Decors - Wood Resin Trays",
                "Functional Decors - Customized Name Plates",
                "Preservation Arts - Wedding Varmala's & Florals",
                "Preservation Art - Umbilical Cords",
                "Preservation Art - Pet Keepsakes",
                "Corporate Corner - Corporate Gifting",
                "Corporate Corner - Resin Trophies & Medals",
                "Corporate Corner - Artistic Resin Furniture & Corporate Spaces"
            ],
            default=[]  # No default selections
        )
        message = st.text_area("Message/Requirements")
        submit_button = st.form_submit_button("Submit Enquiry")

        if submit_button:
            if name and email and phone and furniture_types:
                save_enquiry(name, email, phone, furniture_types, message)
                st.success("Enquiry submitted successfully!")
            else:
                st.error("Please fill all required fields (Name, Email, Phone, Furniture Types).")

# Owner Login and Dashboard
with tab2:
    st.title("Owner Login - Sylva Decors")

    # Session state for login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")
            
            if login_button:
                if verify_login(username, password):
                    st.session_state.logged_in = True
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    else:
        st.subheader("Owner Dashboard")
        st.write("View and download customer enquiries.")

        # Fetch and display enquiries
        enquiries = get_enquiries()
        if not enquiries.empty:
            st.dataframe(enquiries, use_container_width=True)
            
            # Download buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                excel_data = generate_excel(enquiries)
                st.download_button(
                    label="Download as Excel",
                    data=excel_data,
                    file_name=f"sylva_decors_enquiries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col2:
                pdf_data = generate_pdf(enquiries)
                st.download_button(
                    label="Download as PDF",
                    data=pdf_data,
                    file_name=f"sylva_decors_enquiries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
            with col3:
                if st.button("Logout"):
                    st.session_state.logged_in = False
                    st.success("Logged out successfully!")
                    st.rerun()
        else:
            st.info("No enquiries found.")
