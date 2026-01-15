# AI Coding Session Search

A semantic search application for searching through AI coding assistant (Claude Code) session history. Built with FastAPI, Sentence Transformers, ChromaDB, and React.

![Architecture](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)
![AI](https://img.shields.io/badge/AI-Sentence%20Transformers-FF6F00?style=flat-square)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square)
![Search](https://img.shields.io/badge/Search-ChromaDB-4285F4?style=flat-square)

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd Dexicon_assignment

# Copy environment file (optional)
cp .env.example .env

# Edit .env if needed (set GROQ_API_KEY for enhanced mode)

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8001
```

**Services:**
- Frontend: http://localhost (port 80)
- Backend: http://localhost:8001
- Redis: localhost:6379

**Stop services:**
```bash
docker-compose down
```

**Rebuild after changes:**
```bash
docker-compose up -d --build
```

---

### Option 2: Local Development

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn
- Redis (optional, for caching)

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

> **Note**: First run will download the embedding model (~90MB). This may take a minute.

### 2. Start the Backend

```bash
# Create and activate virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the server
cd backend
python main.py
```

The server will:
1. Load session JSON files from `data/` directory
2. Parse and create searchable chunks
3. Generate embeddings using Sentence Transformers
4. Index into ChromaDB
5. Start API server at `http://localhost:8001`

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 4. Start the Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 📁 Project Structure

```
├── backend/
│   ├── basic/               # Basic search implementation
│   │   ├── __init__.py
│   │   └── search_engine.py
│   │
│   ├── enhanced/            # Enhanced search (hybrid + reranking)
│   │   ├── __init__.py
│   │   ├── enhanced_search.py
│   │   └── enhanced_chunking.py
│   │
│   ├── shared/              # Shared utilities
│   │   ├── __init__.py
│   │   ├── data_loader.py
│   │   ├── models.py
│   │   ├── config.py
│   │   └── evaluation.py
│   │
│   ├── main.py              # FastAPI application
│   ├── requirements.txt
│   └── README.md            # Backend documentation
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main application
│   │   ├── components/      # React components
│   │   └── hooks/           # Custom hooks
│   └── package.json
│
├── data/                    # Session JSON files
│   ├── andrew_wang_sessions.json
│   ├── daniel_lin_sessions.json
│   └── diana_lu_sessions.json
│
├── docker-compose.yml       # Docker Compose configuration
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

---

## 🎯 Assignment Questions

### What were the MVP features you decided to build? Why?

**MVP Features:**
1. **Semantic Search** - Search by meaning, not just keywords. A search for "memory optimization" can find discussions about "buffer pools".
2. **Filter by Engineer** - Narrow results to specific team members (with equal quota for all, as per workspace rules).
3. **Filter by Project** - Focus on specific codebases/projects.
4. **Rich Result Display** - Show engineer, project, task context, and conversation excerpts.

**Why these?**
- Semantic search is the core value proposition - it demonstrates AI understanding and provides genuinely useful results.
- Filters make it practical for real team use (finding what *your* teammate discussed about a specific project).
- Rich results give context without needing to dig deeper - users can assess relevance at a glance.

### What features did you deprioritize? Why?

**Deprioritized:**
1. **Full conversation view** - Clicking to see entire session. Would require additional API and routing.
2. **Code syntax highlighting** - Nice polish but not core to finding relevant sessions.
3. **Date range filtering** - Less common use case than engineer/project filters.
4. **Search history** - Useful for power users but not MVP.
5. **Export results** - Enterprise feature, not needed for MVP.

**Why deprioritized?**
- Limited time (3 hours) meant focusing on core search experience.
- These features add complexity without fundamentally improving search quality.
- The semantic search itself is the differentiator; polish can come later.

### What trade-offs did you make?

| Decision | Trade-off |
|----------|-----------|
| **Local embeddings** (Sentence Transformers) vs OpenAI API | Slightly lower quality but zero setup, free, works offline |
| **In-memory ChromaDB** vs persistent storage | Faster development, but requires re-indexing on restart |
| **Q+A pair chunking** vs smaller chunks | Larger chunks but more semantic context; better retrieval |
| **Simple filters** vs faceted search | Easier implementation, covers 90% of use cases |
| **React SPA** vs server-rendered | More interactive UX but requires separate frontend build |

### If you had 3 more hours, what would you build next?

1. **Conversation Expansion** (45 min)
   - Click result to see full session conversation
   - Would require session detail API and modal/page routing
   - High value: users often want full context

2. **Code Syntax Highlighting** (30 min)
   - Detect and highlight code blocks in results
   - Use highlight.js or Prism
   - Improves readability significantly

3. **Persistent ChromaDB Storage** (30 min)
   - Save embeddings to disk
   - Skip re-indexing on server restart
   - Important for production use

4. **Search Suggestions** (45 min)
   - Auto-complete based on common queries
   - Show popular searches
   - Improves discoverability

5. **Analytics Dashboard** (30 min)
   - Most searched topics
   - Most referenced engineers/projects
   - Helps understand usage patterns

---

## 🔧 API Reference

### POST /api/search
Search for relevant coding sessions.

```bash
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to handle large file uploads", "limit": 10}'
```

### GET /api/engineers
List all engineers in the dataset.

### GET /api/projects
List all projects in the dataset.

### GET /api/stats
Get dataset statistics.

---

## 🧠 How It Works

### Semantic Search Pipeline

1. **Data Loading**: Parse JSON session files, extract Q+A conversation pairs
2. **Chunking**: Each user query + assistant response becomes a searchable "chunk"
3. **Embedding**: Generate 384-dimensional vectors using `all-MiniLM-L6-v2`
4. **Indexing**: Store embeddings in ChromaDB with metadata
5. **Search**: Query embedding compared via cosine similarity; top K returned

### Why Sentence Transformers?

- **Zero API setup**: No keys, no costs, works offline
- **Fast inference**: ~14ms per query on CPU
- **Good quality**: MiniLM achieves ~90% of larger models' performance
- **Semantic understanding**: Captures meaning beyond keywords

### Why ChromaDB?

- **Embedded**: Just a Python library, no server to run
- **Metadata filtering**: Built-in support for engineer/project filters
- **Fast**: Uses HNSW for approximate nearest neighbor search
- **Simple**: Perfect for prototypes and small-to-medium datasets

---

## 📊 Dataset

The sample data includes sessions from 3 engineers working at a video streaming company:

| Engineer | Role | Topics |
|----------|------|--------|
| Andrew Wang | Staff Backend Engineer | Video encoding, S3 uploads, Celery |
| Daniel Lin | Senior Full-Stack Engineer | WebRTC, video validation, FFprobe |
| Diana Lu | Senior Frontend Engineer | HLS streaming, iOS PiP, SwiftUI |

**Languages**: Python, Go, TypeScript, Swift
**Frameworks**: FastAPI, Chi, Next.js, React, SwiftUI

---

## 🎨 Design Decisions

### Chunking Strategy

Chose **Q+A pairs** (user query + assistant response) as chunks because:
- Semantic completeness: Question and answer together carry full meaning
- Better retrieval: Search finds complete discussions, not fragments
- Display-ready: Can show conversation context directly

Alternative considered: Smaller chunks (individual messages) - would retrieve more results but lose context.

### UI/UX

- **Dark theme**: Matches IDE aesthetic, easier on eyes for developers
- **Animated placeholders**: Show example queries to guide users
- **Score badges**: Visual indicator of relevance
- **Staggered animations**: Results feel more dynamic and responsive
- **Minimal filters**: Only most useful (engineer, project) to avoid clutter

---

## 🚀 Running in Production

### Docker Deployment

The easiest way to deploy is using Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **Backend**: FastAPI server with enhanced search
- **Frontend**: React app served via Nginx
- **Redis**: Caching layer

### Environment Variables

Create a `.env` file:

```bash
SEARCH_MODE=enhanced          # or "basic"
GROQ_API_KEY=your_key_here    # Optional, for query expansion
CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/0
```

### Production Considerations

1. **Use persistent ChromaDB storage** (already configured in Docker)
2. **Set GROQ_API_KEY** for enhanced query expansion
3. **Configure CORS** for your domain in `backend/main.py`
4. **Add authentication** if needed
5. **Use environment variables** for sensitive data
6. **Monitor Redis** for cache performance
7. **Consider Pinecone/Weaviate** for larger datasets (>100K chunks)

---

## 📝 License

MIT

