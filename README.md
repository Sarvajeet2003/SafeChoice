# SafeChoice - Product Safety Scanner

SafeChoice is a Streamlit application that allows users to scan product barcodes and check if the products are safe for them based on their allergies and health conditions. The app uses the OpenFoodFacts API to retrieve product information and analyzes the ingredients against the user's health profile.

## Features

- **User Registration and Authentication**: Create and manage user profiles with personal information, allergies, and health conditions
- **Barcode Scanning**: Upload images containing barcodes to identify products
- **Product Information**: Retrieve detailed product information including ingredients, brand, and category
- **Safety Analysis**: Automatically check if a product is safe based on the user's allergies and health conditions
- **Profile Management**: Update allergies and health conditions as needed

## Prerequisites

- Python 3.7+
- SQLite (included with Python)
- ZBar library (for barcode scanning)
