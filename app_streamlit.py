import os
import cv2
import requests
import streamlit as st
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="BArcode - Product Safety Scanner",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Database setup
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(120), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    mobile = Column(String(20), unique=True, nullable=False)
    age = Column(Integer, nullable=False)
    allergies = Column(String(255), default="")
    health_conditions = Column(String(255), default="")

# Create database engine and session
engine = create_engine('sqlite:///users.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db_session = Session()

# Suggested values
SUGGESTED_ALLERGIES = [
    "Peanuts", "Dust", "Pollen", "Gluten", "Dairy", "Eggs", "Fish", "Shellfish",
    "Soy", "Wheat", "Tree Nuts", "Corn", "Sesame", "Mustard", "Sulfites",
    "Nightshades", "Legumes", "Citrus", "Bananas", "Chocolate", "Alcohol",
    "Histamine", "Salicylates", "Mushrooms", "Lactose"
]

SUGGESTED_HEALTH_CONDITIONS = [
    "Diabetes", "Hypertension", "Asthma", "Thyroid", "Celiac Disease",
    "Kidney Disease", "Gout", "Lactose Intolerance", "IBS", "Histamine Intolerance",
    "Alpha-gal Syndrome", "Hypersensitivity", "Oral Allergy Syndrome",
    "Shellfish Allergy", "Fish Allergy", "Gluten Sensitivity", "Insulin Resistance",
    "Autoimmune Diseases", "Heart Disease", "High Cholesterol"
]

# Barcode and product functions
def read_barcode(image):
    """
    Reads a barcode from an image and returns decoded data.
    Returns a list of tuples (barcode_data, barcode_type) if found,
    or None if no barcodes are detected.
    """
    try:
        # Convert PIL Image to OpenCV format
        img = np.array(image)
        # Convert RGB to BGR (OpenCV format)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        barcodes = decode(img)
        if not barcodes:
            return None

        results = []
        for barcode in barcodes:
            try:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                results.append((barcode_data, barcode_type))
            except UnicodeDecodeError:
                continue  # Skip barcodes that can't be decoded as UTF-8
                
        return results
    except Exception as e:
        st.error(f"Error processing barcode: {str(e)}")
        return None

def get_product_from_openfoodfacts(barcode):
    """
    Fetches product details using the OpenFoodFacts API.
    Returns a dictionary with product information if found, else None.
    """
    if not barcode:
        st.error("Barcode cannot be empty")
        return None
        
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data.get("product"):
            return None
            
        product = data["product"]
        return {
            "barcode": barcode,
            "title": product.get("product_name", "No product title found"),
            "brand": product.get("brands", "Unknown brand"),
            "description": product.get("generic_name", "No description available"),
            "ingredients": product.get("ingredients_text", "") or "",
            "category": product.get("categories", "Unknown category")
        }
    except requests.RequestException as e:
        st.error(f"Failed to fetch product data: {str(e)}")
        return None
    except ValueError as e:
        st.error(f"Invalid product data received: {str(e)}")
        return None

def check_product_safety(product_info, user):
    """
    Checks product's ingredients against user's allergies or health conditions.
    Returns a dictionary with analysis results.
    """
    if not product_info:
        st.error("Product information is required")
        return None
    if not user:
        st.error("User information is required")
        return None
        
    try:
        # Convert user allergies and health conditions into lists
        user_allergies = [
            a.strip().lower() 
            for a in user.allergies.split(",") 
            if a.strip()
        ]
        user_conditions = [
            h.strip().lower() 
            for h in user.health_conditions.split(",") 
            if h.strip()
        ]

        # Convert product ingredients to lower for checking
        ingredients_lower = product_info.get("ingredients", "").lower()

        # Find conflicting allergies and conditions
        conflicting_allergies = [
            allergy for allergy in user_allergies
            if allergy and allergy in ingredients_lower
        ]
        
        conflicting_conditions = [
            condition for condition in user_conditions
            if condition and condition in ingredients_lower
        ]

        return {
            "is_safe": not (conflicting_allergies or conflicting_conditions),
            "conflicting_allergies": conflicting_allergies,
            "conflicting_conditions": conflicting_conditions,
            "product_name": product_info.get("title", "Unknown"),
            "product_brand": product_info.get("brand", "Unknown"),
            "product_ingredients": product_info.get("ingredients", "")
        }
    except Exception as e:
        st.error(f"Error checking product safety: {str(e)}")
        return None

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_mobile' not in st.session_state:
    st.session_state.user_mobile = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'

# Navigation functions
def navigate_to(page):
    st.session_state.current_page = page
    st.rerun()

def logout():
    st.session_state.logged_in = False
    st.session_state.user_mobile = None
    st.session_state.current_page = 'login'
    st.rerun()

# Sidebar navigation
st.sidebar.title("BArcode App")

if st.session_state.logged_in:
    st.sidebar.button("Profile", on_click=navigate_to, args=('profile',))
    st.sidebar.button("Scan Barcode", on_click=navigate_to, args=('scan',))
    st.sidebar.button("Update Profile", on_click=navigate_to, args=('update_profile',))
    st.sidebar.button("Logout", on_click=logout)
else:
    st.sidebar.button("Login", on_click=navigate_to, args=('login',))
    st.sidebar.button("Register", on_click=navigate_to, args=('register',))

if st.session_state.current_page == 'login':
    st.title("Login")
    
    mobile = st.text_input("Mobile Number", key="login_mobile")
    login_button = st.button("Login", key="login_button")
    
    if login_button:
        if not mobile:
            st.error("Mobile number is required.")
        else:
            user = db_session.query(User).filter_by(mobile=mobile).first()
            if user:
                st.session_state.logged_in = True
                st.session_state.user_mobile = user.mobile
                st.session_state.current_page = 'profile'
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("User not found. Please register first.")
    
    st.markdown("Don't have an account? [Register](javascript:void(0))", unsafe_allow_html=True)
    if st.button("Go to Register", key="goto_register_button"):
        navigate_to('register')

elif st.session_state.current_page == 'register':
    st.title("Register")
    
    username = st.text_input("Username")
    name = st.text_input("Name")
    mobile = st.text_input("Mobile Number")
    age = st.number_input("Age", min_value=1, max_value=120, value=30)
    
    # Initialize empty lists for new users
    current_health_conditions = []
    
    st.subheader("Allergies")
    allergy_cols = st.columns(3)
    selected_allergies = []
    
    for i, allergy in enumerate(SUGGESTED_ALLERGIES):
        col_idx = i % 3
        if allergy_cols[col_idx].checkbox(allergy, key=f"allergy_{i}"):
            selected_allergies.append(allergy)
    
    custom_allergy = st.text_input("Custom Allergy (if not in the list)")
    
    st.subheader("Health Conditions")
    health_cols = st.columns(3)
    selected_health_conditions = []
    
    for i, condition in enumerate(SUGGESTED_HEALTH_CONDITIONS):
        col_idx = i % 3
        is_checked = condition in current_health_conditions
        if health_cols[col_idx].checkbox(condition, value=is_checked, key=f"update_health_{i}"):
            selected_health_conditions.append(condition)
    
    custom_health = st.text_input("Custom Health Condition (if not in the list)")
    
    register_button = st.button("Register", key="register_button")
    
    if register_button:
        # Process allergies and health conditions
        if custom_allergy:
            selected_allergies.append(custom_allergy)
        if custom_health:
            selected_health_conditions.append(custom_health)
        
        # Create a new user instead of updating an existing one
        if not username or not name or not mobile:
            st.error("Username, name, and mobile number are required.")
        else:
            # Check if user already exists
            existing_user = db_session.query(User).filter_by(mobile=mobile).first()
            if existing_user:
                st.error("A user with this mobile number already exists.")
            else:
                # Create new user
                new_user = User(
                    username=username,
                    name=name,
                    mobile=mobile,
                    age=age,
                    allergies=", ".join(selected_allergies),
                    health_conditions=", ".join(selected_health_conditions)
                )
                
                try:
                    db_session.add(new_user)
                    db_session.commit()
                    st.success("Registration successful! Please login.")
                    navigate_to('login')
                except Exception as e:
                    db_session.rollback()
                    st.error(f"An unexpected error occurred: {str(e)}")

    # Remove the update button from here - it doesn't belong in the register page

elif st.session_state.current_page == 'profile':
    if not st.session_state.logged_in:
        st.warning("Please log in to view your profile.")
        navigate_to('login')
    else:
        user = db_session.query(User).filter_by(mobile=st.session_state.user_mobile).first()
        if not user:
            st.error("User not found.")
            logout()
        else:
            st.title(f"Welcome, {user.name}!")
            
            # Display user information in a card-like format
            st.subheader("Your Profile")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Personal Information")
                st.write(f"**Username:** {user.username}")
                st.write(f"**Name:** {user.name}")
                st.write(f"**Mobile:** {user.mobile}")
                st.write(f"**Age:** {user.age}")
            
            with col2:
                # Display allergies
                st.markdown("#### Your Allergies")
                allergies = [a.strip() for a in user.allergies.split(",") if a.strip()]
                if allergies:
                    for allergy in allergies:
                        st.write(f"• {allergy}")
                else:
                    st.write("No allergies recorded.")
                
                # Display health conditions
                st.markdown("#### Your Health Conditions")
                conditions = [c.strip() for c in user.health_conditions.split(",") if c.strip()]
                if conditions:
                    for condition in conditions:
                        st.write(f"• {condition}")
                else:
                    st.write("No health conditions recorded.")
            
            # Add action buttons
            st.markdown("---")
            st.subheader("What would you like to do?")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Scan a Barcode", key="profile_scan_button"):
                    st.session_state.current_page = 'scan'
                    st.rerun()
            
            with col2:
                if st.button("Update Profile", key="profile_update_button"):
                    st.session_state.current_page = 'update_profile'
                    st.rerun()

elif st.session_state.current_page == 'update_profile':
    if not st.session_state.logged_in:
        st.warning("Please log in to update your profile.")
        navigate_to('login')
    else:
        user = db_session.query(User).filter_by(mobile=st.session_state.user_mobile).first()
        if not user:
            st.error("User not found.")
            logout()
        else:
            st.title("Update Profile")
            
            # Display current user info
            st.write(f"**Username:** {user.username}")
            st.write(f"**Name:** {user.name}")
            st.write(f"**Mobile:** {user.mobile}")
            st.write(f"**Age:** {user.age}")
            
            # Get current allergies and health conditions
            current_allergies = [a.strip() for a in user.allergies.split(",") if a.strip()]
            current_health_conditions = [h.strip() for h in user.health_conditions.split(",") if h.strip()]
            
            # Allergies section
            st.subheader("Allergies")
            allergy_cols = st.columns(3)
            selected_allergies = []
            
            for i, allergy in enumerate(SUGGESTED_ALLERGIES):
                col_idx = i % 3
                is_checked = allergy in current_allergies
                if allergy_cols[col_idx].checkbox(allergy, value=is_checked, key=f"update_allergy_{i}"):
                    selected_allergies.append(allergy)
            
            custom_allergy = st.text_input("Custom Allergy (if not in the list)", key="update_custom_allergy")
            
            # Health conditions section
            st.subheader("Health Conditions")
            health_cols = st.columns(3)
            selected_health_conditions = []
            
            for i, condition in enumerate(SUGGESTED_HEALTH_CONDITIONS):
                col_idx = i % 3
                is_checked = condition in current_health_conditions
                if health_cols[col_idx].checkbox(condition, value=is_checked, key=f"update_health_condition_{i}"):
                    selected_health_conditions.append(condition)
            
            custom_health = st.text_input("Custom Health Condition (if not in the list)", key="update_custom_health")
            
            # Update button
            if st.button("Save Changes", key="save_profile_changes"):
                # Process allergies and health conditions
                if custom_allergy:
                    selected_allergies.append(custom_allergy)
                if custom_health:
                    selected_health_conditions.append(custom_health)
                
                # Update user
                user.allergies = ", ".join(selected_allergies)
                user.health_conditions = ", ".join(selected_health_conditions)
                
                try:
                    db_session.commit()
                    st.success("Profile updated successfully!")
                    # Don't use st.rerun() in a button callback
                    # Instead, use session state to track updates
                    st.session_state.profile_updated = True
                except Exception as e:
                    db_session.rollback()
                    st.error(f"An unexpected error occurred: {str(e)}")
            
            # Add a back button
            if st.button("Back to Profile", key="back_to_profile"):
                navigate_to('profile')

elif st.session_state.current_page == 'scan':
    if not st.session_state.logged_in:
        st.warning("Please log in to scan barcodes.")
        navigate_to('login')
    else:
        user = db_session.query(User).filter_by(mobile=st.session_state.user_mobile).first()
        if not user:
            st.error("User not found.")
            logout()
        else:
            st.title("Scan Barcode")
            st.write("Upload an image containing a barcode to check product safety.")
            
            uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
            
            if uploaded_file is not None:
                # Display the uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_container_width=True)
                
                # Process the image when user clicks the button
                if st.button("Process Barcode", key="process_barcode_button"):
                    with st.spinner("Processing barcode..."):
                        # Read barcode from image
                        barcode_results = read_barcode(image)
                        
                        if not barcode_results:
                            st.error("No barcode detected in the image. Please try another image.")
                        else:
                            # Get the first barcode
                            barcode_data, barcode_type = barcode_results[0]
                            st.success(f"Barcode detected: {barcode_data} (Type: {barcode_type})")
                            
                            # Fetch product information
                            with st.spinner("Fetching product information..."):
                                product_info = get_product_from_openfoodfacts(barcode_data)
                                
                                if not product_info:
                                    st.error("Product not found in the database. Try another product.")
                                else:
                                    # Display product information
                                    st.subheader("Product Information")
                                    product_col1, product_col2 = st.columns(2)
                                    
                                    with product_col1:
                                        st.write(f"**Title:** {product_info['title']}")
                                        st.write(f"**Brand:** {product_info['brand']}")
                                        st.write(f"**Description:** {product_info['description']}")
                                    
                                    with product_col2:
                                        st.write(f"**Category:** {product_info['category']}")
                                        st.write(f"**Barcode:** {product_info['barcode']}")
                                    
                                    st.write("**Ingredients:**")
                                    st.write(product_info['ingredients'])
                                    
                                    # Check product safety
                                    with st.spinner("Analyzing product safety..."):
                                        safety_report = check_product_safety(product_info, user)
                                        
                                        if safety_report:
                                            st.subheader("Safety Analysis")
                                            
                                            if safety_report["is_safe"]:
                                                st.success("✅ This product appears to be safe for you!")
                                            else:
                                                st.error("❌ This product may not be safe for you!")
                                                
                                                if safety_report["conflicting_allergies"]:
                                                    st.warning("**Conflicting Allergies:**")
                                                    for allergy in safety_report["conflicting_allergies"]:
                                                        st.write(f"- {allergy.capitalize()}")
                                                
                                                if safety_report["conflicting_conditions"]:
                                                    st.warning("**Conflicting Health Conditions:**")
                                                    for condition in safety_report["conflicting_conditions"]:
                                                        st.write(f"- {condition.capitalize()}")