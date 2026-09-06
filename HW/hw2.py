import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI, AuthenticationError
from google import genai

def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()

    except requests.RequestException as e:
        print(f"Error reading {url}: {e}")
        return None

st.title("Homework 2 - URL Summarizer")

st.write(
    "Enter a webpage URL and select how you would like the page summarized."
)

url = st.text_input(
    "Enter a  URL:",
    placeholder="https://example.com/article"
)


st.sidebar.header("Summary Options")


summary_option = st.sidebar.radio(
    "Select summary instructions:",
    [
        "Summarize the webpage in 100 words",
        "Summarize the webpage in 2 connecting paragraphs",
        "Summarize the webpage using bullet points"
    ]
)


language = st.sidebar.selectbox(
    "Output Language:",
    [
        "English",
        "French",
        "Spanish"
    ]
)


llm_choice = st.sidebar.selectbox(
    "Select LLM:",
    [
        "OpenAI",
        "Gemini"
    ]
)


advanced_model = st.sidebar.checkbox(
    "Use advanced model"
)


if llm_choice == "OpenAI":

    if advanced_model:
        model_name = "gpt-5.6-sol"
    else:
        model_name = "gpt-5.6-luna"

else:

    if advanced_model:
        model_name = "gemini-3.6-flash"
    else:
        model_name = "gemini-3.5-flash-lite"


st.sidebar.write(f"Model: **{model_name}**")

if st.button("Summarize URL"):

    if not url:

        st.warning("Please enter a URL.")

    else:

        with st.spinner("Reading webpage..."):

            document = read_url_content(url)


        if document:

            document = document[:50000]


            prompt = f"""
You are summarizing the contents of a webpage.

Summary instructions:
{summary_option}

Output language:
{language}

Make sure the ENTIRE response is written in {language}.

Webpage content:

{document}
"""


            if llm_choice == "OpenAI":

                try:

                    openai_api_key = st.secrets["OPENAI_API_KEY"]

                    client = OpenAI(
                        api_key=openai_api_key
                    )

                    # Validate API key
                    client.models.list()

                    with st.spinner(
                        f"Generating summary with {model_name}..."
                    ):

                        response = client.responses.create(
                            model=model_name,
                            input=prompt
                        )


                    st.subheader("Summary")

                    st.write(
                        response.output_text
                    )


                except KeyError:

                    st.error(
                        "OPENAI_API_KEY was not found in Streamlit secrets."
                    )


                except AuthenticationError:

                    st.error(
                        "Your OpenAI API key is invalid."
                    )


                except Exception as e:

                    st.error(
                        f"OpenAI Error: {e}"
                    )


            elif llm_choice == "Gemini":

                try:

                    gemini_api_key = st.secrets["GEMINI_API_KEY"]

                    gemini_client = genai.Client(
                        api_key=gemini_api_key
                    )


                    gemini_client.models.get(
                        model=model_name
                    )


                    with st.spinner(
                        f"Generating summary with {model_name}..."
                    ):

                        response = gemini_client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )


                    st.subheader("Summary")

                    st.write(
                        response.text
                    )


                except KeyError:

                    st.error(
                        "GEMINI_API_KEY was not found in Streamlit secrets."
                    )


                except Exception as e:

                    st.error(
                        f"Gemini Error: {e}"
                    )