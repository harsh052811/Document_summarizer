import warnings

warnings.filterwarnings('ignore')

import streamlit as st
from phi.agent import Agent
from phi.model.google import Gemini
import google.generativeai as genai
from dotenv import load_dotenv
import os
import PyPDF2
from docx import Document
import io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import pickle
from googleapiclient.http import MediaIoBaseDownload

# Load environment variables
load_dotenv()

# Configure Google API
API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("Please set GOOGLE_API_KEY in your environment variables")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Document Chat Assistant",
    page_icon="💬",
    layout="wide"
)

# Style and branding
st.markdown(
    """
    <style>
    .main-header {
        color: #2E4057;
        font-size: 2.5rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        gap: 0.75rem;
    }
    .user-message {
        background-color: #F0F2F6;
    }
    .assistant-message {
        background-color: #E8F0FE;
    }
    .message-content {
        width: 90%;
    }
    .avatar {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 16px;
        font-weight: bold;
    }
    .user-avatar {
        background-color: #4B9CD3;
        color: white;
    }
    .assistant-avatar {
        background-color: #13B287;
        color: white;
    }
    .stTextInput>div>div>input {
        padding: 0.75rem;
        font-size: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<h1 class="main-header">Document Chat Assistant</h1>', unsafe_allow_html=True)

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TESTING_FOLDER_NAME = "testing"  # The specific folder to search in

def get_gdrive_service_from_secrets():
    """Try to get Google Drive service using Streamlit secrets"""
    try:
        # Check if credentials are in Streamlit secrets
        if "google_credentials" in st.secrets:
            # Convert the JSON string to a dictionary
            credentials_info = st.secrets["google_credentials"]
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES)
            return build('drive', 'v3', credentials=credentials)
        else:
            st.warning("Google credentials not found in Streamlit secrets")
            return None
    except Exception as e:
        st.error(f"Error setting up Drive service from secrets: {e}")
        return None

# def get_gdrive_service(): # Comment out this entire function
#     """Get Google Drive service using local credential files"""
#     # OPTION 1: Using service account (recommended for production)
#     try:
#         # Check if service account credentials exist
#         if os.path.exists('service_account.json'):
#             credentials = service_account.Credentials.from_service_account_file(
#                 'service_account.json', scopes=SCOPES)
#             return build('drive', 'v3', credentials=credentials)
#     except Exception as e:
#         st.warning(f"Service account authentication failed: {e}")

#     # OPTION 2: Fall back to user authentication flow (current implementation)
#     creds = None
#     if os.path.exists('token.pickle'):
#         with open('token.pickle', 'rb') as token:
#             creds = pickle.load(token)

#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             # Check if credentials.json exists
#             if not os.path.exists('credentials.json'):
#                 st.error("No credentials found. Please upload credentials.json or service_account.json file.")
#                 st.stop()

#             flow = InstalledAppFlow.from_client_secrets_file(
#                 'credentials.json', SCOPES)
#             creds = flow.run_local_server(port=0)

#         with open('token.pickle', 'wb') as token:
#             pickle.dump(creds, token)

#     return build('drive', 'v3', credentials=creds)


def find_testing_folder(service):
    """Find the 'testing' folder in Google Drive"""
    query = f"name='{TESTING_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields="files(id, name)"
    ).execute()

    folders = results.get('files', [])
    if not folders:
        return None

    # Return the first matching folder
    return folders[0]['id']


def list_files_in_folder(service, folder_id, mime_types=None):
    """List files from a specific folder in Google Drive with optional MIME type filtering"""
    query = f"'{folder_id}' in parents"

    if mime_types:
        mime_query_parts = [f"mimeType='{mime_type}'" for mime_type in mime_types]
        mime_query = " or ".join(mime_query_parts)
        query += f" and ({mime_query})"

    results = service.files().list(
        q=query,
        pageSize=30,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()

    return results.get('files', [])


def download_file(service, file_id):
    """Download a file from Google Drive by its ID"""
    request = service.files().get_media(fileId=file_id)
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)
    done = False

    while not done:
        status, done = downloader.next_chunk()

    file_content.seek(0)
    return file_content


def get_agent():
    return Agent(
        name="Document Chat Assistant",
        model=Gemini(id="gemini-1.5-pro"),
        markdown=True,
    )


def extract_text_from_pdf(file_obj):
    pdf_reader = PyPDF2.PdfReader(file_obj)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(file_obj):
    doc = Document(file_obj)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text_from_file(file_obj, mime_type):
    try:
        if 'pdf' in mime_type:
            return extract_text_from_pdf(file_obj)
        elif 'document' in mime_type or 'docx' in mime_type:
            return extract_text_from_docx(file_obj)
        elif 'text/plain' in mime_type:
            return file_obj.getvalue().decode('utf-8')
        else:
            st.error(f"Unsupported file format: {mime_type}")
            return None
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None


# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'processing_query' not in st.session_state:
    st.session_state.processing_query = False

if 'drive_service' not in st.session_state:
    try:
        # Try secrets first
        st.session_state.drive_service = get_gdrive_service_from_secrets()
        if not st.session_state.drive_service:
            st.error("Could not connect to Google Drive")
            st.stop()
    except Exception as e:
        st.error(f"Error connecting to Google Drive: {str(e)}")
        st.info(
            "Please ensure you have credentials.json or service_account.json file with proper Google Drive API credentials")
        st.stop()

# Find the testing folder
if 'testing_folder_id' not in st.session_state:
    try:
        folder_id = find_testing_folder(st.session_state.drive_service)
        if folder_id:
            st.session_state.testing_folder_id = folder_id
        else:
            st.error(f"Folder '{TESTING_FOLDER_NAME}' not found in your Google Drive")
            st.info(
                f"Please create a folder named '{TESTING_FOLDER_NAME}' in your Google Drive and upload your documents there")
            st.stop()
    except Exception as e:
        st.error(f"Error finding the testing folder: {str(e)}")
        st.stop()

# Initialize the agent
doc_agent = get_agent()

# Sidebar for document selection
with st.sidebar:
    st.header("Select Document")
    st.markdown(f"Files from your '{TESTING_FOLDER_NAME}' folder:")

    # Define supported file types
    supported_mime_types = [
        'application/pdf',
        'application/vnd.google-apps.document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]

    try:
        files = list_files_in_folder(st.session_state.drive_service, st.session_state.testing_folder_id,
                                     supported_mime_types)

        if not files:
            st.info(
                f"No compatible documents found in your '{TESTING_FOLDER_NAME}' folder. Please upload PDF, DOCX, or TXT files to this folder.")
        else:
            file_options = {f"{file['name']}": file for file in files}
            selected_file_option = st.selectbox("Choose a document", options=list(file_options.keys()))
            selected_file = file_options[selected_file_option]

            if st.button("Open Selected Document"):
                with st.spinner(f"Loading {selected_file['name']}..."):
                    file_content = download_file(st.session_state.drive_service, selected_file['id'])
                    extracted_text = extract_text_from_file(file_content, selected_file['mimeType'])

                    if extracted_text:
                        st.session_state.current_text = extracted_text
                        st.session_state.current_document = selected_file['name']
                        st.session_state.messages = []  # Clear the chat when loading a new document

                        # Add a welcome message
                        welcome_message = {
                            "role": "assistant",
                            "content": f"👋 Hi there! I'm your document assistant for *{selected_file['name']}*. How can I help you with this document today?"
                        }
                        st.session_state.messages.append(welcome_message)
                        st.success(f"Document loaded! You can now ask questions about it.")
                    else:
                        st.error("Failed to extract text from the selected document")
    except Exception as e:
        st.error(f"Error accessing Google Drive: {str(e)}")

# Main chat interface
if 'current_text' in st.session_state:
    st.subheader(f"Chat about: {st.session_state.current_document}")

    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.container():
                st.markdown(f"""
                <div class="chat-message user-message">
                    <div class="avatar user-avatar">👤</div>
                    <div class="message-content">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <div class="avatar assistant-avatar">💬</div>
                    <div class="message-content">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)

    # User input
    # Create a form to better control submission
    with st.form(key="question_form", clear_on_submit=True):
        user_input = st.text_input("Type your question here", key="user_input",
                                  placeholder="What would you like to know about this document?")
        submit_button = st.form_submit_button("Send")

    # Handle form submission
    if submit_button and user_input and not st.session_state.processing_query:
        # Set processing flag to prevent multiple runs
        st.session_state.processing_query = True

        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Generate response
        with st.spinner("Thinking..."):
            qa_prompt = f"""
            You are a friendly and helpful customer service representative responding to questions about a business document. 
            Your tone should be conversational, helpful, and professional.

            Document: {st.session_state.current_document}
            Document Content:
            ```
            {st.session_state.current_text}
            ```

            Question: {user_input}

            Instructions:
            1. Respond in a warm, conversational customer service tone
            2. Provide a helpful, well-structured answer without citing evidence or references
            3. Use natural language as if you were chatting with a customer in real-time
            4. If you can't answer from the document, politely explain what information is available
            5. DO NOT include "Supporting Evidence" or reference quotes from the document
            6. DO NOT use phrases like "Based on the document" or "According to the document"
            7. Format your response with appropriate markdown where helpful

            Your response should feel like a natural conversation with a friendly customer service representative.
            """

            response = doc_agent.run(qa_prompt)

            # Add assistant response to chat
            st.session_state.messages.append({"role": "assistant", "content": response.content})

        # Reset processing flag and trigger rerun
        st.session_state.processing_query = False
        st.rerun()

else:
    st.info("👈 Please select a document from the sidebar to start chatting")
