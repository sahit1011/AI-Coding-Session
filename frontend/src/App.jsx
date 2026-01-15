import { useState, useCallback, useEffect } from 'react';
import SearchBar from './components/SearchBar';
import FilterPanel from './components/FilterPanel';
import ResultsList from './components/ResultsList';
import SessionModal from './components/SessionModal';
import SimilarModal from './components/SimilarModal';
import { 
  useSearch, 
  useEngineers, 
  useProjects, 
  useStats,
  useSessionDetail,
  useSimilar,
  useSuggestions
} from './hooks/useSearch';

function App() {
  const { results, loading, queryTime, hasSearched, search } = useSearch();
  const { engineers, fetchEngineers } = useEngineers();
  const { projects, fetchProjects } = useProjects();
  const { stats, fetchStats } = useStats();
  const { session, loading: sessionLoading, fetchSession, clearSession } = useSessionDetail();
  const { similar, loading: similarLoading, sourceChunk, findSimilar, clearSimilar } = useSimilar();
  const { suggestions, fetchSuggestions } = useSuggestions();
  
  const [selectedEngineer, setSelectedEngineer] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);
  const [currentQuery, setCurrentQuery] = useState('');
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showSimilarModal, setShowSimilarModal] = useState(false);

  // Fetch initial data
  const fetchData = useCallback(() => {
    fetchEngineers();
    fetchProjects();
    fetchStats();
    fetchSuggestions(); // Load initial suggestions
  }, [fetchEngineers, fetchProjects, fetchStats, fetchSuggestions]);

  // Handle search
  const handleSearch = useCallback((query) => {
    setCurrentQuery(query);
    search(query, {
      engineer: selectedEngineer,
      project: selectedProject,
    });
  }, [search, selectedEngineer, selectedProject]);

  // Handle query change for suggestions
  const handleQueryChange = useCallback((query) => {
    fetchSuggestions(query);
  }, [fetchSuggestions]);

  // Re-search when filters change
  useEffect(() => {
    if (currentQuery) {
      search(currentQuery, {
        engineer: selectedEngineer,
        project: selectedProject,
      });
    }
  }, [selectedEngineer, selectedProject]);

  // Handle view session
  const handleViewSession = useCallback((sessionId) => {
    fetchSession(sessionId);
    setShowSessionModal(true);
  }, [fetchSession]);

  // Handle find similar
  const handleFindSimilar = useCallback((chunkId) => {
    findSimilar(chunkId);
    setShowSimilarModal(true);
  }, [findSimilar]);

  // Close session modal
  const handleCloseSessionModal = useCallback(() => {
    setShowSessionModal(false);
    clearSession();
  }, [clearSession]);

  // Close similar modal
  const handleCloseSimilarModal = useCallback(() => {
    setShowSimilarModal(false);
    clearSimilar();
  }, [clearSimilar]);

  return (
    <div className="min-h-screen gradient-bg">
      {/* Header */}
      <header className="pt-12 pb-8 px-4">
        <div className="max-w-4xl mx-auto text-center">
          {/* Logo/Title */}
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-white">
              Session<span className="text-accent-cyan">Search</span>
            </h1>
          </div>
          
          <p className="text-void-400 text-lg mb-8 max-w-xl mx-auto">
            Search through AI coding assistant conversations using semantic understanding
          </p>

          {/* Search bar with suggestions */}
          <SearchBar 
            onSearch={handleSearch} 
            loading={loading}
            suggestions={suggestions}
            onQueryChange={handleQueryChange}
          />
          
          {/* Filters */}
          <FilterPanel
            engineers={engineers}
            projects={projects}
            selectedEngineer={selectedEngineer}
            selectedProject={selectedProject}
            onEngineerChange={setSelectedEngineer}
            onProjectChange={setSelectedProject}
            onFetchData={fetchData}
          />
        </div>
      </header>

      {/* Main content */}
      <main className="px-4 pb-24">
        <ResultsList 
          results={results} 
          loading={loading} 
          queryTime={queryTime}
          hasSearched={hasSearched}
          onViewSession={handleViewSession}
          onFindSimilar={handleFindSimilar}
        />
      </main>

      {/* Footer with stats */}
      <footer className="fixed bottom-0 left-0 right-0 bg-void-950/80 backdrop-blur border-t border-void-800">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between text-sm">
          <div className="flex items-center gap-4 text-void-500">
            {stats && (
              <>
                <span>{stats.total_chunks} conversations</span>
                <span className="text-void-700">•</span>
                <span>{stats.total_engineers} engineers</span>
                <span className="text-void-700">•</span>
                <span>{stats.languages?.join(', ')}</span>
              </>
            )}
          </div>
          <div className="text-void-600">
            Powered by <span className="text-accent-cyan">Semantic Search</span>
          </div>
        </div>
      </footer>

      {/* Session Detail Modal */}
      {showSessionModal && (
        <SessionModal
          session={session}
          loading={sessionLoading}
          onClose={handleCloseSessionModal}
        />
      )}

      {/* Similar Sessions Modal */}
      {showSimilarModal && (
        <SimilarModal
          similar={similar}
          loading={similarLoading}
          sourceChunk={sourceChunk}
          onClose={handleCloseSimilarModal}
          onViewSession={(sessionId) => {
            handleCloseSimilarModal();
            handleViewSession(sessionId);
          }}
        />
      )}
    </div>
  );
}

export default App;
