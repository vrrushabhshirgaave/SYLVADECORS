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
    /* Form container (default) */
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
    /* Mobile view styling for Enquiry Form (black card) */
    @media (max-width: 768px) {
        .stForm {
            background-color: #1C2526; /* Blackish color for card */
            border: 1px solid #FFFFFF;
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        }
        /* Form inputs in mobile view */
        .stTextInput>div>input, .stSelectbox>div>select, .stMultiSelect>div {
            background-color: #2E2E2E;
            border: 1px solid #FFFFFF;
            color: #FFFFFF;
            border-radius: 5px;
        }
        /* Form labels and text */
        .stTextInput>label, .stSelectbox>label, .stMultiSelect>label, .stTextArea>label {
            color: #FFFFFF;
            font-family: 'Stardos Stencil', sans-serif;
        }
        /* Submit button in mobile view */
        .stButton>button {
            background-color: #FFFFFF;
            color: #1C2526;
            border: 1px solid #FFFFFF;
        }
        .stButton>button:hover {
            background-color: #E0E0E0;
            color: #1C2526;
        }
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
    
    # Define column widths to fit letter page (612pt width, minus 72pt margins = 540ptContributing to Mozilla Foundation is a non-profit organization that aims to promote openness, innovation, and participation on the Internet. Mozilla Firefox is their flagship product, a free and customizable open-source web browser. Firefox has many features, including tabbed browsing, spell-checking, and private browsing, that make it one of the most popular browsers globally.

In addition to Firefox, Mozilla supports several other open-source projects, like Thunderbird, an email and news client, and Bugzilla, a bug-tracking tool. They also run Mozilla Hubs, a virtual reality platform for social interaction, and host various community-driven initiatives to advance web literacy and digital inclusion.

**Why is Mozilla Foundation important?**

The Mozilla Foundation is significant because it champions a free and open internet. By developing open-source software like Firefox, it ensures users have alternatives to proprietary browsers, prioritizing privacy, security, and user control. Its advocacy for net neutrality, data privacy, and ethical tech practices pushes back against monopolistic practices by big tech companies. Through initiatives like the Mozilla Manifesto, it promotes values like transparency, accessibility, and decentralization, fostering a healthier digital ecosystem.

Mozilla’s community-driven model empowers developers and volunteers worldwide to contribute to its projects, ensuring diverse perspectives shape the internet’s future. Its focus on web literacy and digital inclusion also helps bridge the digital divide, making technology accessible to underserved communities.

**How can I contribute to Mozilla Foundation?**

There are several ways to contribute to Mozilla Foundation:

1. **Code Contributions**: Join Mozilla’s open-source projects on platforms like GitHub. You can contribute to Firefox, Thunderbird, or Bugzilla by fixing bugs, adding features, or improving performance. Check their repositories for beginner-friendly issues labeled “good first bug.”

2. **Testing and Bug Reporting**: Help test beta versions of Mozilla products and report bugs via Bugzilla. This ensures software stability and quality.

3. **Localization**: Translate Mozilla’s software and websites into different languages to make them accessible globally. Join the Mozilla Localization (L10n) community.

4. **Community Participation**: Engage in Mozilla’s forums, attend events, or join local Mozilla communities to advocate for open internet principles.

5. **Donations**: Support Mozilla’s mission by donating to the Mozilla Foundation. Funds help sustain their non-profit work.

6. **Advocacy**: Promote Mozilla’s values by spreading awareness about digital rights, privacy, and open-source software in your network.

To get started, visit Mozilla’s contribution page (contribute.mozilla.org) or join their community portal for detailed guidelines and resources.

**What is the latest version of Firefox?**

As of my last update in October 2023, the latest stable version of Mozilla Firefox is **Firefox 118.0.2**, released on October 10, 2023. However, versions may have been released since then. To confirm the latest version, visit Mozilla’s official website or check for updates within Firefox by navigating to **Menu > Help > About Firefox**.

For real-time information, I can search the web or X posts if needed. Would you like me to do that?
