from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
import os
from typing import List, Dict

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = "uploads"
VECTOR_FOLDER = "vectorstore"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VECTOR_FOLDER, exist_ok=True)

# Google Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC515gql9O0RQaultZyMFnranz2r32phHY")
genai.configure(api_key=GEMINI_API_KEY)

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GEMINI_API_KEY
)

vector_db = None
chat_history: List[Dict] = []
uploaded_documents: List[Dict] = []


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    global vector_db, uploaded_documents

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    if file.filename.endswith('.pdf'):
        loader = PyPDFLoader(filepath)
    elif file.filename.endswith('.txt'):
        loader = TextLoader(filepath)
    else:
        return jsonify({"error": "Only PDF and TXT files are supported"}), 400

    documents = loader.load()

    for i, doc in enumerate(documents):
        doc.metadata['source'] = file.filename
        doc.metadata['chunk_index'] = i
        if 'page' not in doc.metadata:
            doc.metadata['page'] = 1

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    docs = splitter.split_documents(documents)

    uploaded_documents.append({
        'filename': file.filename,
        'num_chunks': len(docs),
        'filepath': filepath
    })

    if vector_db is None:
        vector_db = FAISS.from_documents(docs, embedding_model)
    else:
        vector_db.add_documents(docs)

    return jsonify({
        "message": f"File '{file.filename}' uploaded and processed successfully",
        "total_documents": len(uploaded_documents),
        "total_chunks": len(docs)
    })


def generate_answer_with_gemini(question: str, context: str, chat_history_context: str) -> tuple[str, float]:
    """Generate a clear step-by-step answer using Gemini 1.5 Flash."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""You are a helpful document assistant. Answer the user's question using ONLY the context below.

--- DOCUMENT CONTEXT ---
{context}
--- END CONTEXT ---

--- PREVIOUS CONVERSATION ---
{chat_history_context if chat_history_context else "None"}
--- END CONVERSATION ---

User Question: {question}

STRICT FORMATTING RULES — follow these exactly:
1. ALWAYS respond using a numbered list. Every single point must be on its own numbered line.
2. NEVER write paragraphs or long continuous sentences. Break every idea into its own numbered step.
3. Each numbered step should be short, clear, and actionable (1-2 sentences max).
4. If there are sub-points, use a dash (-) indented under the parent step.
5. Do NOT use any markdown headers or bold text.
6. Do NOT say you cannot answer unless the context has absolutely zero relevant information.
7. Last line must be exactly: Confidence: <0-100>

Example format:
1. First step or point here.
2. Second step or point here.
   - Sub-detail if needed.
3. Third step or point here.
Confidence: 85

Now answer:"""

    response = model.generate_content(prompt)
    response_text = response.text.strip()

    # Extract confidence score from last line
    confidence = 80.0
    lines = response_text.splitlines()
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line.lower().startswith("confidence:"):
            try:
                confidence = float(line.split(":")[1].strip().split()[0])
                # Remove the confidence line from the answer
                response_text = "\n".join(lines[:i]).strip()
            except Exception:
                pass
            break

    return response_text, confidence


@app.route('/ask', methods=['POST'])
def ask_question():
    global vector_db, chat_history

    data = request.json
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "No question provided"}), 400

    if vector_db is None:
        return jsonify({"error": "Please upload a document first"}), 400

    # Retrieve top 5 relevant chunks (more context = better answers)
    docs_with_scores = vector_db.similarity_search_with_score(question, k=5)

    if not docs_with_scores:
        return jsonify({
            "answer": "No relevant information found in the uploaded documents.",
            "confidence": 0.0,
            "sources": [],
            "is_out_of_scope": True
        })

    # Build context string
    context = "\n\n---\n\n".join([
        f"[Source: {doc.metadata.get('source', 'Unknown')} | Page: {doc.metadata.get('page', 'N/A')}]\n{doc.page_content}"
        for doc, _ in docs_with_scores
    ])

    # Build conversation history (last 5 turns)
    chat_history_context = ""
    if chat_history:
        chat_history_context = "\n".join([
            f"Q: {item['question']}\nA: {item['answer']}"
            for item in chat_history[-5:]
        ])

    # Build sources list for frontend
    sources = []
    for i, (doc, score) in enumerate(docs_with_scores):
        sources.append({
            "document": doc.metadata.get('source', 'Unknown'),
            "page": doc.metadata.get('page', 'N/A'),
            "chunk_index": doc.metadata.get('chunk_index', i),
            "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
            "similarity_score": float(score)
        })

    # Call Gemini — fallback to raw chunks if API fails
    try:
        answer, confidence = generate_answer_with_gemini(question, context, chat_history_context)
        # Only mark out-of-scope if Gemini explicitly says so
        is_out_of_scope = answer.lower().strip().startswith("i cannot answer") or \
                          answer.lower().strip().startswith("there is no information")
    except Exception as e:
        print(f"Gemini API error: {e}")
        # Fallback: FAISS L2 distance — lower = more relevant
        avg_score = sum(score for _, score in docs_with_scores) / len(docs_with_scores)
        if avg_score < 1.5:
            # Extract sentences from chunks and present as numbered steps
            lines = []
            for doc, _ in docs_with_scores:
                # Split chunk into sentences and add each as a step
                sentences = [s.strip() for s in doc.page_content.replace('\n', ' ').split('.') if len(s.strip()) > 20]
                lines.extend(sentences)
            # Deduplicate while preserving order
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            answer = "\n".join(f"{i+1}. {line}." for i, line in enumerate(unique_lines[:15]))
            confidence = 60.0
            is_out_of_scope = False
        else:
            answer = "1. No relevant information was found in the uploaded documents for this question.\n2. Please ask a question related to the content of your uploaded documents."
            confidence = 10.0
            is_out_of_scope = True

    result = {
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "sources": sources,
        "is_out_of_scope": is_out_of_scope
    }

    chat_history.append(result)
    return jsonify(result)


@app.route('/history', methods=['GET'])
def history():
    return jsonify(chat_history)


@app.route('/reset', methods=['POST'])
def reset_chat():
    global chat_history
    chat_history = []
    return jsonify({"message": "Chat history cleared"})


@app.route('/documents', methods=['GET'])
def get_documents():
    return jsonify(uploaded_documents)


@app.route('/clear', methods=['POST'])
def clear_all():
    global vector_db, chat_history, uploaded_documents
    import shutil
    vector_db = None
    chat_history = []
    uploaded_documents = []
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return jsonify({"message": "All data cleared"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)