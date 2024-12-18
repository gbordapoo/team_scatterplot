#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 26 12:29:33 2023

@author: gustavoborda
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import streamlit as st
import os
from PIL import Image
import unicodedata
import hmac

# App configuration
st.set_page_config(page_title='Performance Field - Logos Scatter Plot',
                   page_icon="flag_chile",
                   layout='wide')

# Function to normalize text
def normalize_text(text):
    """
    Normalize text to remove special characters and ensure consistent encoding.
    """
    return unicodedata.normalize('NFC', text).encode('ascii', 'ignore').decode('utf-8').lower()

# Resize all logos to a consistent size and normalize filenames
def resize_logos(logos_path, output_path, size=(50, 50)):
    """
    Resize all logos in the given directory to the specified size.
    Normalize filenames to handle special characters.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for logo_file in os.listdir(logos_path):
        if logo_file.endswith(".png"):
            # Normalize the filename
            normalized_name = normalize_text(os.path.splitext(logo_file)[0])
            logo_path = os.path.join(logos_path, logo_file)
            output_file = os.path.join(output_path, f"{normalized_name}.png")

            with Image.open(logo_path) as img:
                resized_img = img.resize(size, Image.Resampling.LANCZOS)
                resized_img.save(output_file)

# Normalize logos
resize_logos("./logos", "./normalized_logos", size=(50, 50))

# Authentication
def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False


if not check_password():
    st.stop()

# Add the app logo to the top of the sidebar
logo_placeholder = st.sidebar.empty()
logo_placeholder.image("performancefield_logo.jpeg", width=150)

# File uploader for Excel data in the main area
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    # Load the Excel file
    excel_data = pd.ExcelFile(uploaded_file)
    sheet_names = excel_data.sheet_names

    # Select a sheet from the uploaded Excel file
    selected_sheet = st.sidebar.selectbox("Select a sheet:", sheet_names)

    if selected_sheet:
        # Load the selected sheet into a DataFrame
        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

        # Drop the first row from dropdowns and select default variables
        dropdown_columns = df.columns[1:]  # Exclude the first column
        x_axis = st.sidebar.selectbox("Select X-axis Variable:", dropdown_columns, index=0)
        y_axis = st.sidebar.selectbox("Select Y-axis Variable:", dropdown_columns, index=1)

        # Checkbox for including variable names in the plot
        include_axis_labels = st.sidebar.checkbox("Include Variable Names in Plot", value=True)

        # Display the DataFrame
        st.dataframe(df)

        # Generate and display scatter plot using logos
        if x_axis and y_axis:
            fig, ax = plt.subplots(figsize=(10, 6))

            # Set axis limits dynamically, but force them to start at 0
            x_min, x_max = 0, df[x_axis].max() + 1  # X-axis starts at 0
            y_min, y_max = 0, df[y_axis].max() + 1  # Y-axis starts at 0
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)

            def add_logo_marker(ax, x, y, team_name, logos_path="./normalized_logos", zoom=0.4):
                """
                Add a logo as a marker on the scatter plot.
                Normalize the team name to match the logo filename.
                """
                # Normalize the team name to handle special characters
                normalized_team_name = normalize_text(team_name)
                logo_file = os.path.join(logos_path, f"{normalized_team_name}.png")

                if os.path.exists(logo_file):
                    img = plt.imread(logo_file)
                    imagebox = OffsetImage(img, zoom=zoom)
                    ab = AnnotationBbox(imagebox, (x, y), frameon=False)
                    ax.add_artist(ab)
                else:
                    # If logo is not available, fallback to a red dot
                    ax.scatter(x, y, color="red", marker="o", s=50, label=team_name)

            # Plot each team's logo
            for _, row in df.iterrows():
                team_name = row.get("Equipo", None)  # Update "Equipo" to match your team column name
                x_value = row[x_axis]
                y_value = row[y_axis]

                # Validate X and Y values
                if not (isinstance(x_value, (int, float)) and isinstance(y_value, (int, float))):
                    continue  # Skip invalid rows

                # Add the logo marker
                add_logo_marker(ax, x_value, y_value, team_name, zoom=0.4)

            # Add or omit axis labels based on user preference
            if include_axis_labels:
                ax.set_xlabel(x_axis, fontsize=12)
                ax.set_ylabel(y_axis, fontsize=12)
            else:
                ax.set_xlabel("")
                ax.set_ylabel("")

            # Customize the scatter plot
            ax.grid(True, linestyle="--", alpha=0.5)

            # Reduce font size of axis numbers
            ax.tick_params(axis='both', labelsize=10)

            # Display the scatter plot in the app
            st.pyplot(fig)

            # Generate file name dynamically
            file_name = f"{x_axis}_vs_{y_axis}.png"

            # Save the scatter plot as a PNG file for download
            import io
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)

            # Add download button
            st.download_button(
                label="Download Logos Scatter Plot",
                data=buf,
                file_name=file_name,
                mime="image/png"
            )
