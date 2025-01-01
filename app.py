import streamlit as st
from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set environment variables
os.environ['GROQ_API_KEY'] = os.getenv("GROQ_API_KEY")
os.environ['OPENAI_API_KEY'] = os.getenv("OPENAI_API_KEY")

# Streamlit application
def streamlit_pdf_assistant():
    st.title("PDF Assistant")
    st.sidebar.title("Session Settings")

    # Session settings
    new_session = st.sidebar.checkbox("Start a new session", value=False)
    user = st.sidebar.text_input("User ID", value="user")

    # PDF URL input
    pdf_url = st.text_input("Enter the PDF URL:", placeholder="https://example.com/sample.pdf")

    if "knowledge_base" not in st.session_state and pdf_url:
        # Database URL for storage
        db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

        # Initialize knowledge base
        try:
            with st.spinner("Loading knowledge base..."):
                knowledge_base = PDFUrlKnowledgeBase(
                    urls=[pdf_url],
                    vector_db=PgVector2(collection="recipes", db_url=db_url)
                )
                knowledge_base.load()
                st.session_state.knowledge_base = knowledge_base

            # Initialize storage
            storage = PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)
            st.session_state.storage = storage

            st.success("Knowledge base loaded successfully!")
        except Exception as e:
            st.error(f"Failed to load knowledge base: {e}")
            return

    # Ensure knowledge base and storage are loaded
    if "knowledge_base" not in st.session_state or "storage" not in st.session_state:
        st.warning("Please enter a valid PDF URL to initialize the knowledge base.")
        return

    # Determine run ID
    run_id = None
    if not new_session:
        existing_run_ids = st.session_state.storage.get_all_run_ids(user)
        if len(existing_run_ids) > 0:
            run_id = existing_run_ids[0]

    # Initialize Assistant
    assistant = Assistant(
        run_id=run_id,
        user_id=user,
        knowledge_base=st.session_state.knowledge_base,
        storage=st.session_state.storage,
        use_tools=True,
        show_tool_calls=True,
        search_knowledge=True,
        read_chat_history=True,
    )

    # Display session details
    if run_id is None:
        run_id = assistant.run_id
        st.sidebar.write(f"Started new session: {run_id}")
    else:
        st.sidebar.write(f"Continuing session: {run_id}")

    # User input
    st.subheader("Ask a Question")
    user_input = st.text_input("Your question:")

    if user_input:
        with st.spinner("Processing..."):
            try:
                # Process input and get a response
                response = assistant.chat(message=user_input)
            except Exception as e:
                st.error(f"Error: {e}")
                response = "The assistant encountered an error while processing your query."
        st.markdown("### Response")
        st.write(response)

    # Chat history
    st.sidebar.subheader("Chat History")
    if assistant.read_chat_history:
        chat_history = assistant.get_chat_history()

        # Loop through chat history and display each message
        if isinstance(chat_history, list):
            for entry in chat_history:
                if isinstance(entry, dict):  # Check if entry is a dictionary
                    role = entry.get("role", "unknown").capitalize()
                    content = entry.get("content", "")
                    if role == "User":
                        st.sidebar.write(f"**You:** {content}")
                    elif role == "Assistant":
                        st.sidebar.write(f"**Assistant:** {content}")
                else:
                    st.sidebar.write(f"Unexpected chat entry format: {entry}")

if __name__ == "__main__":
    streamlit_pdf_assistant()
