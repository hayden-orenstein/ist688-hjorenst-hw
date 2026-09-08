import streamlit as st


st.set_page_config(
    page_title="HW Manager",
    page_icon=":material/school:"
)


hw1_page = st.Page(
    "HW/hw1.py",
    title="Homework 1",
    icon=":material/description:"
)

hw2_page = st.Page(
    "HW/hw2.py",
    title="Homework 2",
    icon=":material/language:"
    
)

hw3_page = st.Page(
    "HW/hw3.py",
    title="Homework 3",
    icon=":material/chat:",
    default=True
)


pg = st.navigation([
    hw1_page,
    hw2_page,
    hw3_page
])


pg.run()