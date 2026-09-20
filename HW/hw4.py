from pathlib import Path

import streamlit as st
from openai import OpenAI
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import pysqlite3

sys.modules["sqlite3"] = pysqlite3

import chromadb


st.title("HW 4 - Syracuse Organization Information Chatbot")

st.write(
    "Ask questions about the Syracuse University student organizations."
)


if "openai_client" not in st.session_state:
    st.session_state.openai_client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )


def add_to_collection(collection, text, file_name, chunk_number):
    client = st.session_state.openai_client

    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )

    embedding = response.data[0].embedding

    collection.add(
        documents=[text],
        ids=[f"{file_name}_chunk_{chunk_number}"],
        embeddings=[embedding],
        metadatas=[
            {
                "filename": file_name,
                "chunk": chunk_number
            }
        ]
    )


def extract_text_from_html(html_path):
    html = html_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    soup = BeautifulSoup(html, "html.parser")

    # Remove content that is not useful to the chatbot.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Remove blank lines so the text is cleaner before chunking.
    clean_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return "\n".join(clean_lines)


def chunk_document(text):
    """
    Chunking method:
    The chunking method is a midpoint split, however the code looks for the line break
    closest to the middle of the cleaned document instead of cutting directly
    through the middle, in order to prevent the document from being chunked middle of
    a sentance.
    """

    if len(text) < 2:
        return [text, text]

    midpoint = len(text) // 2

    split_before = text.rfind("\n", 0, midpoint)
    split_after = text.find("\n", midpoint)

    possible_splits = [
        split_point
        for split_point in [split_before, split_after]
        if split_point != -1
    ]

    if possible_splits:
        split_point = min(
            possible_splits,
            key=lambda x: abs(x - midpoint)
        )
    else:
        # Fallback for a document with no line breaks.
        split_before = text.rfind(" ", 0, midpoint)
        split_after = text.find(" ", midpoint)

        possible_splits = [
            split_point
            for split_point in [split_before, split_after]
            if split_point != -1
        ]

        if possible_splits:
            split_point = min(
                possible_splits,
                key=lambda x: abs(x - midpoint)
            )
        else:
            split_point = midpoint

    chunk_1 = text[:split_point].strip()
    chunk_2 = text[split_point:].strip()

    return [chunk_1, chunk_2]


def load_html_to_collection(folder_path, collection):
    folder = Path(folder_path)

    html_files = list(folder.glob("*.html")) + list(folder.glob("*.htm"))

    for html_file in html_files:
        text = extract_text_from_html(html_file)

        if text:
            chunks = chunk_document(text)

            for chunk_number, chunk in enumerate(chunks, start=1):
                if chunk:
                    add_to_collection(
                        collection,
                        chunk,
                        html_file.name,
                        chunk_number
                    )

    return len(html_files)


def create_vector_db():
    """
    ChromaDB is persistent, so the database is stored in the
    ChromaDB_for_HW4 folder. The HTML files are embedded only when the
    collection is empty. On later Streamlit runs, the existing database is
    reused instead of being rebuilt.
    """

    chroma_client = chromadb.PersistentClient(
        path="./ChromaDB_for_HW4"
    )

    collection = chroma_client.get_or_create_collection(
        "HW4Collection"
    )

    if collection.count() == 0:
        load_html_to_collection(
            "./su_orgs/",
            collection
        )

    return collection


if "HW4_VectorDB" not in st.session_state:
    st.session_state.HW4_VectorDB = create_vector_db()


def get_info_from_vector_db(collection, question):
    client = st.session_state.openai_client

    response = client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )

    query_embedding = response.data[0].embedding

    # The vector DB contains every HTML page. For each question, retrieve the
    # chunks whose embeddings are most similar to the user's question.
    number_to_retrieve = min(8, collection.count())

    if number_to_retrieve == 0:
        return ""

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=number_to_retrieve,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    context = ""

    for i in range(len(results["documents"][0])):
        document = results["documents"][0][i]
        metadata = results["metadatas"][0][i]

        file_name = metadata["filename"]
        chunk_number = metadata["chunk"]

        context += (
            f"\n\nDOCUMENT NAME: {file_name}\n"
            f"CHUNK: {chunk_number}\n"
            f"DOCUMENT CONTENT:\n"
            f"{document}\n"
        )

    return context


def get_conversation_buffer(messages, max_interactions=5):
    """
    Keep up to the last 5 user interactions and their assistant responses.
    The welcome message is not part of the memory buffer.
    """

    conversation = messages[1:]
    buffer = []
    user_turns = 0

    for message in reversed(conversation):
        if message["role"] == "user":
            user_turns += 1

            if user_turns > max_interactions:
                break

        buffer.append(message)

    return list(reversed(buffer))


if "hw4_messages" not in st.session_state:
    st.session_state.hw4_messages = [
        {
            "role": "assistant",
            "content": "How can I help you with Syracuse University student organization information?"
        }
    ]


for message in st.session_state.hw4_messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


if prompt := st.chat_input(
    "Ask a question about the student organizations"
):
    st.session_state.hw4_messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.write(prompt)

    organization_context = get_info_from_vector_db(
        st.session_state.HW4_VectorDB,
        prompt
    )

    system_prompt = (
        "You are a Syracuse University student organization information chatbot.\n\n"

        "Use the retrieved HTML document content below to answer the "
        "questions provided by the user.\n\n"

        "For questions about the organizations, only use information that appears "
        "in the provided document context. Absolutely do not make up organization information.\n\n"

        "Use only the document information that is relevant to the user's question.\n\n"

        "If the requested information cannot be found in the provided context, "
        "clearly say that the information was not found in the provided documents.\n\n"

        "RETRIEVED ORGANIZATION DOCUMENTS:\n"
        + organization_context
    )

    messages_to_send = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    messages_to_send += get_conversation_buffer(
        st.session_state.hw4_messages,
        max_interactions=5
    )

    response = (
        st.session_state.openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages_to_send
        )
    )

    answer = response.choices[0].message.content

    with st.chat_message("assistant"):
        st.write(answer)

    st.session_state.hw4_messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
