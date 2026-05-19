# Context-Aware Document Q&A Bot

A RAG (Retrieval-Augmented Generation) chatbot that answers questions based ONLY on uploaded documents (PDF or text files), not general knowledge.

## Features

### Core Requirements (Mandatory)
- **File Upload**: Upload PDF or .txt files through a simple chat-style interface
- **Document Processing**: Parse documents and split them into smaller chunks using RecursiveCharacterTextSplitter
- **Question Answering**: 
  - Retrieve relevant chunks using FAISS vector similarity search
  - Send retrieved context to Google Gemini LLM
  - Generate answers based ONLY on retrieved content
- **Source References**: Show document name, page number, and chunk content for each answer
- **Conversation History**: Maintain conversation history during the session for context-aware responses

### Bonus Features Implemented
- **Embeddings + Similarity Search**: Uses sentence-transformers embeddings with FAISS for cosine similarity search
- **Multiple Document Support**: Upload and query across multiple documents simultaneously
- **Confidence Scores**: Displays confidence scores (0-100%) for each answer
- **Out-of-Scope Handling**: Clearly indicates when questions are outside the scope of uploaded documents
- **Similarity Scores**: Shows similarity scores for retrieved chunks

## Architecture

### Chunking Strategy
- **Chunk Size**: 500 characters
- **Chunk Overlap**: 100 characters
- **Splitter**: RecursiveCharacterTextSplitter (preserves paragraph boundaries)

### Retrieval Approach
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2
- **Vector Store**: FAISS (Facebook AI Similarity Search)
- **Similarity Metric**: Cosine similarity
- **Top-K Retrieval**: Retrieves top 3 most relevant chunks per query

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Google Gemini API Key

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Set Google Gemini API Key
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or set it in your system environment variables.

### Step 3: Run the Backend Server
```bash
cd backend
python app.py
```

The backend will start on `http://127.0.0.1:5000`

### Step 4: Open the Frontend
Open `frontend/index.html` in your web browser.

## Usage

1. **Upload a Document**: Click "Choose File" and select a PDF or TXT file, then click "Upload Document"
2. **Ask Questions**: Type your question in the input field and click "Send" or press Enter
3. **View Results**: The bot will display:
   - The answer based on document content
   - Confidence score (color-coded: green ≥70%, orange ≥40%, red <40%)
   - Source references with document name, page number, and content
   - Similarity scores for retrieved chunks
4. **Manage Session**: Use "Reset Chat" to clear conversation history or "Clear All" to remove all documents

## API Endpoints

- `POST /upload` - Upload a document (PDF/TXT)
- `POST /ask` - Ask a question about uploaded documents
- `GET /history` - Get conversation history
- `GET /documents` - Get list of uploaded documents
- `POST /reset` - Clear chat history only
- `POST /clear` - Clear all data (documents and history)

## Testing

Test with a real document such as:
- Academic papers
- Technical reports
- Textbooks
- Company documentation

Example questions to try:
- "What is the main topic of this document?"
- "Summarize the key findings"
- "What are the conclusions?"

## Evaluation Criteria

- **Retrieval Accuracy (30%)**: How well the system retrieves relevant chunks
- **LLM Integration (30%)**: Quality of answers generated from retrieved context
- **UI/Chat Experience (25%)**: User interface design and interaction quality
- **Code Quality (15%)**: Code organization, readability, and best practices

## Technologies Used

- **Backend**: Flask, Flask-CORS
- **Document Processing**: LangChain, PyPDF
- **Embeddings**: sentence-transformers, HuggingFace
- **Vector Store**: FAISS
- **LLM**: Google Gemini API
- **Frontend**: HTML, CSS, JavaScript

## License

MIT License
