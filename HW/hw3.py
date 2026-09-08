import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from google import genai
from google.genai import types


st.title("HW 3 - URL Chatbot")

st.write(
    "This chatbot can use up to two webpages as context for your conversation. "
    "Choose a URL and an LLM in the sidebar. The webpage content is stored in a "
    "system prompt that is never removed. The chatbot uses a 6-message conversation "
    "buffer, meaning it remembers the most recent 3 user-assistant exchanges."
)


def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()

    except requests.RequestException as e:
        print(f"Error reading {url}: {e}")
        return None


st.sidebar.header("Chatbot Options")

url1 = st.sidebar.text_input(
    "URL 1",
    placeholder="https://example.com"
)

url2 = st.sidebar.text_input(
    "URL 2",
    placeholder="https://example.com"
)

llm_choice = st.sidebar.selectbox(
    "Select LLM",
    [
        "OpenAI",
        "Gemini"
    ]
)


if llm_choice == "OpenAI":
    model_to_use = "gpt-5.6-sol"

else:
    model_to_use = "gemini-3.8-flash"


st.sidebar.write(f"Model: **{model_to_use}**")


current_urls = (
    url1.strip(),
    url2.strip()
)


if "loaded_urls" not in st.session_state:
    st.session_state.loaded_urls = ("", "")


if "url_context" not in st.session_state:
    st.session_state.url_context = ""


if current_urls != st.session_state.loaded_urls:

    context_parts = []

    if url1:

        with st.spinner("Reading URL 1..."):

            content1 = read_url_content(url1)

        if content1:

            context_parts.append(
                f"""
WEBPAGE 1
URL: {url1}

{content1}
"""
            )

        else:

            st.warning("URL 1 could not be read.")


    if url2:

        with st.spinner("Reading URL 2..."):

            content2 = read_url_content(url2)

        if content2:

            context_parts.append(
                f"""
WEBPAGE 2
URL: {url2}

{content2}
"""
            )

        else:

            st.warning("URL 2 could not be read.")


    st.session_state.url_context = "\n\n".join(context_parts)

    st.session_state.loaded_urls = current_urls


system_prompt = f"""
You are a helpful chatbot.

Answer all questions using simple language that a 10-year-old
can understand.

After answering a user's question, always ask:
"Do you want more info?"

If the user says "Yes", provide more information about the
previous answer and then ask "Do you want more info?" again.

If the user says "No", ask the user what you can help them with.

Use the following webpage information as context when it is
relevant to the user's question.

WEBPAGE CONTEXT:

{st.session_state.url_context}
"""


if "messages" not in st.session_state:

    st.session_state.messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "assistant",
            "content": "How can I help you?"
        }
    ]

else:

    if st.session_state.messages[0]["role"] == "system":

        st.session_state.messages[0]["content"] = system_prompt

    else:

        st.session_state.messages.insert(
            0,
            {
                "role": "system",
                "content": system_prompt
            }
        )


for msg in st.session_state.messages:

    if msg["role"] != "system":

        chat_msg = st.chat_message(msg["role"])

        chat_msg.write(msg["content"])


def get_conversation_buffer(messages):

    system_message = messages[0]

    conversation_messages = messages[1:]

    conversation_buffer = conversation_messages[-6:]

    return [system_message] + conversation_buffer


if prompt := st.chat_input("What is up?"):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    with st.chat_message("user"):

        st.markdown(prompt)


    messages_to_send = get_conversation_buffer(
        st.session_state.messages
    )


    if llm_choice == "OpenAI":

        try:

            if "openai_client" not in st.session_state:

                st.session_state.openai_client = OpenAI(
                    api_key=st.secrets["OPENAI_API_KEY"]
                )


            stream = st.session_state.openai_client.chat.completions.create(
                model=model_to_use,
                messages=messages_to_send,
                stream=True
            )


            with st.chat_message("assistant"):

                response = st.write_stream(stream)


        except Exception as e:

            st.error(f"OpenAI Error: {e}")

            response = None


    else:

        try:

            if "gemini_client" not in st.session_state:

                st.session_state.gemini_client = genai.Client(
                    api_key=st.secrets["GEMINI_API_KEY"]
                )


            gemini_system_prompt = messages_to_send[0]["content"]


            gemini_messages = []


            for msg in messages_to_send[1:]:

                if msg["role"] == "assistant":
                    gemini_role = "model"

                else:
                    gemini_role = "user"


                gemini_messages.append(
                    types.Content(
                        role=gemini_role,
                        parts=[
                            types.Part.from_text(
                                text=msg["content"]
                            )
                        ]
                    )
                )


            gemini_stream = (
                st.session_state.gemini_client.models.generate_content_stream(
                    model=model_to_use,
                    contents=gemini_messages,
                    config=types.GenerateContentConfig(
                        system_instruction=gemini_system_prompt
                    )
                )
            )


            def stream_gemini():

                for chunk in gemini_stream:

                    if chunk.text:

                        yield chunk.text


            with st.chat_message("assistant"):

                response = st.write_stream(
                    stream_gemini()
                )


        except Exception as e:

            st.error(f"Gemini Error: {e}")

            response = None


    if response:

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response
            }
        )