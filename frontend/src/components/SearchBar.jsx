import { useState, useRef, useEffect } from 'react';

const EXAMPLE_QUERIES = [
  "How to handle large file uploads",
  "Video encoding optimization",
  "WebRTC signaling implementation",
  "React quality selector for streaming",
  "S3 multipart upload retry logic",
  "iOS picture-in-picture support",
];

export default function SearchBar({ onSearch, loading, suggestions = [], onQueryChange }) {
  const [query, setQuery] = useState('');
  const [placeholder, setPlaceholder] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Typing animation for placeholder
  useEffect(() => {
    let currentIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let timeout;

    const type = () => {
      const currentQuery = EXAMPLE_QUERIES[currentIndex];
      
      if (!isDeleting) {
        setPlaceholder(currentQuery.substring(0, charIndex + 1));
        charIndex++;
        
        if (charIndex === currentQuery.length) {
          isDeleting = true;
          timeout = setTimeout(type, 2000);
          return;
        }
      } else {
        setPlaceholder(currentQuery.substring(0, charIndex - 1));
        charIndex--;
        
        if (charIndex === 0) {
          isDeleting = false;
          currentIndex = (currentIndex + 1) % EXAMPLE_QUERIES.length;
        }
      }
      
      timeout = setTimeout(type, isDeleting ? 30 : 50);
    };

    type();
    return () => clearTimeout(timeout);
  }, []);

  // Fetch suggestions when query changes
  useEffect(() => {
    if (query.trim().length >= 2 && onQueryChange) {
      onQueryChange(query);
    }
    setSelectedSuggestionIndex(-1);
  }, [query, onQueryChange]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    onSearch(suggestion);
    setShowSuggestions(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setQuery('');
      setShowSuggestions(false);
      inputRef.current?.blur();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedSuggestionIndex(prev => 
        Math.min(prev + 1, (suggestions?.length || 0) - 1)
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedSuggestionIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && selectedSuggestionIndex >= 0) {
      e.preventDefault();
      const selected = suggestions[selectedSuggestionIndex];
      if (selected) {
        handleSuggestionClick(selected);
      }
    }
  };

  const filteredSuggestions = suggestions?.filter(s => 
    s.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 6) || [];

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="relative group" ref={suggestionsRef}>
        {/* Glow effect */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-xl opacity-20 group-hover:opacity-30 blur transition duration-300" />
        
        {/* Search input container */}
        <div className="relative flex items-center bg-void-900 rounded-xl border border-void-700 overflow-hidden">
          {/* Search icon */}
          <div className="pl-5 pr-3 text-void-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          
          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            placeholder={`Try: "${placeholder}"`}
            className="search-input flex-1 py-4 pr-4 bg-transparent text-white text-lg placeholder-void-500 outline-none"
            autoFocus
          />
          
          {/* Loading indicator or submit button */}
          {loading ? (
            <div className="pr-5">
              <div className="w-6 h-6 border-2 border-accent-cyan border-t-transparent rounded-full animate-spin" />
            </div>
          ) : query.trim() && (
            <button
              type="submit"
              className="mr-3 px-4 py-2 bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium rounded-lg hover:opacity-90 transition"
            >
              Search
            </button>
          )}
        </div>
        
        {/* Suggestions dropdown */}
        {showSuggestions && query.length >= 2 && filteredSuggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-void-900 border border-void-700 rounded-xl shadow-2xl overflow-hidden z-50">
            <div className="p-2">
              <p className="text-void-500 text-xs px-3 py-1.5">Suggestions</p>
              {filteredSuggestions.map((suggestion, index) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => handleSuggestionClick(suggestion)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                    index === selectedSuggestionIndex
                      ? 'bg-accent-cyan/20 text-accent-cyan'
                      : 'text-void-300 hover:bg-void-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-void-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    {suggestion}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* Hint text */}
      <p className="mt-3 text-center text-void-500 text-sm">
        Search by meaning, not just keywords • Press <kbd className="px-1.5 py-0.5 bg-void-800 rounded text-void-400">Enter</kbd> to search
      </p>
    </form>
  );
}
