# Backend Structure

## 📁 Directory Organization

```
backend/
├── basic/              # Basic search implementation
│   ├── __init__.py
│   └── search_engine.py    # Simple vector search with ChromaDB
│
├── enhanced/           # Enhanced search implementation
│   ├── __init__.py
│   ├── enhanced_search.py      # Hybrid search (BM25 + Vector) + Reranking
│   └── enhanced_chunking.py    # Advanced chunking strategies
│
├── shared/             # Shared utilities and models
│   ├── __init__.py
│   ├── data_loader.py         # JSON parsing and chunking
│   ├── models.py              # Pydantic schemas
│   ├── config.py              # Configuration settings
│   └── evaluation.py          # Quality metrics
│
├── main.py             # FastAPI application (uses both basic & enhanced)
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

---

## 🔧 Module Descriptions

### `basic/` - Basic Search Engine

**Purpose**: Simple, fast semantic search implementation.

**Files**:
- `search_engine.py`: Vector search using Sentence Transformers + ChromaDB

**Features**:
- ✅ Fast (~50ms queries)
- ✅ Simple architecture
- ✅ Good for small datasets
- ✅ No external dependencies beyond ChromaDB

**Use When**:
- Latency is critical
- Dataset is small (<100 chunks)
- Simple keyword matching is sufficient

---

### `enhanced/` - Enhanced Search Engine

**Purpose**: Advanced RAG pipeline with hybrid search and reranking.

**Files**:
- `enhanced_search.py`: Hybrid search (BM25 + Vector) with cross-encoder reranking
- `enhanced_chunking.py`: Advanced chunking strategies (overlapping, hierarchical, enriched)

**Features**:
- ✅ Hybrid search (keyword + semantic)
- ✅ Cross-encoder reranking
- ✅ Query expansion
- ✅ Advanced chunking strategies
- ✅ Better quality (+7.9% precision)

**Use When**:
- Quality is priority
- Complex queries expected
- Dataset is large (>100 chunks)
- Latency < 1s is acceptable

---

### `shared/` - Shared Utilities

**Purpose**: Common code used by both basic and enhanced implementations.

**Files**:
- `data_loader.py`: JSON parsing, chunking, session indexing
- `models.py`: Pydantic request/response schemas
- `config.py`: Configuration (search mode, parameters)
- `evaluation.py`: Quality metrics and evaluation framework

**Note**: These modules are imported by both basic and enhanced implementations.

---

## 🚀 Usage

### Import Basic Search

```python
from basic import SearchEngine, get_search_engine

engine = get_search_engine()
results = engine.search("query", limit=10)
```

### Import Enhanced Search

```python
from enhanced import EnhancedSearchEngine
from shared.config import ENHANCED_SEARCH_CONFIG

engine = EnhancedSearchEngine(
    embedding_model=ENHANCED_SEARCH_CONFIG["embedding_model"],
    reranker_model=ENHANCED_SEARCH_CONFIG["reranker_model"],
    use_reranking=True,
    hybrid_weight=0.7
)
results = engine.search("query", limit=10)
```

### Import Shared Utilities

```python
from shared.data_loader import load_session_files, create_searchable_chunks
from shared.models import SearchRequest, SearchResponse
from shared.config import SEARCH_MODE
```

---

## 🔄 Switching Between Modes

The main application (`main.py`) automatically uses the appropriate search engine based on `SEARCH_MODE` in `shared/config.py`:

```python
# In shared/config.py
SEARCH_MODE = "basic"      # Use basic search
SEARCH_MODE = "enhanced"    # Use enhanced search
```

Or via environment variable:
```bash
export SEARCH_MODE=enhanced
python main.py
```

---

## 📊 Architecture

```
main.py (FastAPI)
    │
    ├─→ basic/search_engine.py (if SEARCH_MODE="basic")
    │   └─→ Uses: shared/data_loader.py
    │
    └─→ enhanced/enhanced_search.py (if SEARCH_MODE="enhanced")
        ├─→ Uses: shared/data_loader.py
        └─→ Uses: enhanced/enhanced_chunking.py
```

---

## 🧪 Testing

### Test Basic Search
```python
from basic import SearchEngine
from shared.data_loader import load_session_files, create_searchable_chunks

engine = SearchEngine()
chunks = create_searchable_chunks(load_session_files("data"))
engine.index_chunks(chunks)
results = engine.search("test query")
```

### Test Enhanced Search
```python
from enhanced import EnhancedSearchEngine
from shared.data_loader import load_session_files, create_searchable_chunks

engine = EnhancedSearchEngine()
chunks = create_searchable_chunks(load_session_files("data"))
engine.index_chunks(chunks)
results = engine.search("test query")
```

### Compare Both
```bash
python compare_search_metrics.py
```

---

## 📝 Adding New Features

### Add to Basic Search
1. Create new file in `basic/`
2. Update `basic/__init__.py` to export it
3. Update `main.py` to use it when `SEARCH_MODE="basic"`

### Add to Enhanced Search
1. Create new file in `enhanced/`
2. Update `enhanced/__init__.py` to export it
3. Update `main.py` to use it when `SEARCH_MODE="enhanced"`

### Add Shared Utility
1. Create new file in `shared/`
2. Update `shared/__init__.py` to export it
3. Import in both basic and enhanced modules as needed

---

## 🎯 Benefits of This Structure

1. **Clear Separation**: Easy to understand what's basic vs enhanced
2. **Maintainability**: Changes to one don't affect the other
3. **Testability**: Can test each implementation independently
4. **Scalability**: Easy to add new search strategies
5. **Flexibility**: Can switch between implementations easily

