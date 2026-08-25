import streamlit as st
from openai import OpenAI, AuthenticationError
from PyPDF2 import PdfReader

def read_pdf(uploaded_file):
    pdf_reader = PdfReader(uploaded_file)
    document = ""

    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            document += text + "\n"

    return document

# Show title and description.
st.title("MY Document question answering")
st.write(
    "Upload a document below and ask a question about it – GPT will answer! "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    try:
        # Create an OpenAI client.
        client = OpenAI(api_key=openai_api_key)

        # Verify that the API key actually works.
        client.models.list()

        st.success("API key verified!")

        # Let the user upload a file.
        uploaded_file = st.file_uploader(
            "Upload a document (.txt or .pdf)",
            type=("txt", "pdf")
        )

        # Ask the user for a question.
        question = st.text_area(
            "Now ask a question about the document!",
            placeholder="Can you give me a short summary?",
            disabled=not uploaded_file,
        )

        if uploaded_file and question:

            # Determine file type
            file_extension = uploaded_file.name.split('.')[-1].lower()

            if file_extension == "txt":
                document = uploaded_file.read().decode()

            elif file_extension == "pdf":
                document = read_pdf(uploaded_file)

            else:
                st.error("Unsupported file type.")
                st.stop()

            messages = [
                {
                    "role": "user",
                    "content": f"Here's a document: {document}\n\n---\n\n{question}",
                }
            ]

            # Generate an answer using the OpenAI API.
            stream = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True,
            )

            # Stream response to the app.
            st.write_stream(stream)

    except AuthenticationError:
        st.error(
            "Invalid OpenAI API key. Please check your key and try again."
        )