import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import textract
from phi.agent import Agent
from phi.model.google import Gemini
import google.generativeai as genai
from dotenv import load_dotenv
import os
import tempfile

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
    page_title="Document Analysis & QA System",
    page_icon="📄",
    layout="wide"
)

st.title("Document Analysis & QA System 📄🔍")
st.header("Powered by Google Gemini")

def get_agent():
    return Agent(
        name="Document AI Analyzer",
        model=Gemini(id="gemini-pro"),
        markdown=True,
    )

# Initialize the agent
doc_agent = get_agent()

# Function to generate summary
def generate_summary(text):
    summary_prompt = f"""
    You are a professional document analyzer. Please provide a comprehensive summary of the following document:
    
    {text}
    
    Include:
    1. Main topics and key points
    2. Important findings or conclusions
    3. Key takeaways
    
    Format the response in a clear, structured manner using markdown.
    Make sure to highlight the most important information.
    """
    return doc_agent.run(summary_prompt)

# Function to extract key information
def extract_key_info(text):
    extraction_prompt = f"""
    You are a professional information extractor. Analyze the following document and extract key information:
    
    {text}
    
    Please provide:
    1. Key entities mentioned
    2. Important dates and numbers
    3. Critical facts and findings
    4. Main arguments or points
    5. Any notable quotes
    
    Format the response in a well-structured manner using markdown.
    Make sure to categorize and organize the information clearly.
    """
    return doc_agent.run(extraction_prompt)

# File uploader
document_file = st.file_uploader(
    "Upload a document file",
    type=['pdf', 'docx', 'txt'],
    help="Upload a document for AI analysis"
)

if document_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.' + document_file.name.split('.')[-1]) as temp_doc:
        temp_doc.write(document_file.read())
        doc_path = temp_doc.name

    try:
        # Extract text from the document
        extracted_text = textract.process(doc_path).decode('utf-8')
        
        # Create tabs for different analysis options
        tab1, tab2, tab3 = st.tabs(["📝 Summary", "🔍 Key Information", "❓ Q&A"])
        
        with tab1:
            st.subheader("Document Summary")
            if st.button("Generate Summary"):
                with st.spinner("Generating comprehensive summary..."):
                    summary_response = generate_summary(extracted_text)
                    st.markdown(summary_response.content)

        with tab2:
            st.subheader("Key Information Extraction")
            if st.button("Extract Key Information"):
                with st.spinner("Extracting key information..."):
                    key_info_response = extract_key_info(extracted_text)
                    st.markdown(key_info_response.content)

        with tab3:
            st.subheader("Ask Questions")
            user_question = st.text_area(
                "Ask a question about the document",
                placeholder="Enter your question here...",
                help="Ask specific questions about the document content"
            )

            if st.button("Get Answer"):
                if not user_question:
                    st.warning("Please enter a question.")
                else:
                    with st.spinner("Finding answer..."):
                        qa_prompt = f"""
                        You are an expert document analyst. Your task is to answer questions about the following document content accurately and comprehensively.

                        Document Content:
                        ```
                        {extracted_text}
                        ```

                        Question: {user_question}

                        Instructions:
                        1. Provide a clear and direct answer to the question
                        2. Support your answer with relevant quotes or references from the document
                        3. If the question cannot be answered from the document content, clearly state that
                        4. If you need to make assumptions, explicitly state them
                        5. Format your response in markdown for better readability

                        Response format:
                        - Answer: [Your detailed answer]
                        - Supporting Evidence: [Relevant quotes or references from the document]
                        - Additional Context: [Any important context or clarifications]
                        """
                        qa_response = doc_agent.run(qa_prompt)
                        
                        # Add a separator for better readability
                        st.markdown("---")
                        st.markdown("### Answer:")
                        st.markdown(qa_response.content)

                        # Option to see relevant text
                        if st.checkbox("Show document context"):
                            st.markdown("### Document Content:")
                            st.text_area("", value=extracted_text, height=200, disabled=True)

    except Exception as error:
        st.error(f"An error occurred during analysis: {error}")
    finally:
        # Clean up temporary document file
        os.remove(doc_path)
else:
    st.info("Upload a document file (PDF, DOCX, or TXT) to begin analysis.")

# Customize UI elements
st.markdown(
    """
    <style>
    .stTextArea textarea {
        height: 100px;
    }
    .stTab {
        font-size: 1.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)
