import ResultCard from './ResultCard';

export default function ResultsList({ 
  results, 
  loading, 
  queryTime, 
  hasSearched,
  onViewSession,
  onFindSimilar 
}) {
  // Loading state
  if (loading) {
    return (
      <div className="w-full max-w-3xl mx-auto mt-8">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div 
              key={i} 
              className="bg-void-900 border border-void-700 rounded-xl p-5 animate-pulse"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-void-700" />
                <div className="space-y-2">
                  <div className="h-4 w-32 bg-void-700 rounded" />
                  <div className="h-3 w-24 bg-void-800 rounded" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-3 w-full bg-void-800 rounded" />
                <div className="h-3 w-3/4 bg-void-800 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // No search yet
  if (!hasSearched) {
    return (
      <div className="w-full max-w-3xl mx-auto mt-16 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-void-800 mb-4">
          <svg className="w-8 h-8 text-void-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16l2.879-2.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-void-300 text-lg font-medium mb-2">Search AI Coding Sessions</h3>
        <p className="text-void-500 text-sm max-w-md mx-auto">
          Find conversations about video encoding, WebRTC, streaming, and more. 
          Our semantic search understands what you're looking for.
        </p>
        
        {/* Quick search suggestions */}
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {[
            'video encoding',
            'file upload',
            'WebRTC',
            'error handling',
            'quality selector',
            'iOS playback'
          ].map((term) => (
            <button
              key={term}
              className="px-3 py-1.5 bg-void-800 hover:bg-void-700 text-void-400 hover:text-white text-sm rounded-full transition"
            >
              {term}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // No results
  if (results.length === 0) {
    return (
      <div className="w-full max-w-3xl mx-auto mt-12 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-void-800 mb-4">
          <svg className="w-8 h-8 text-void-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-void-300 text-lg font-medium mb-2">No results found</h3>
        <p className="text-void-500 text-sm">
          Try different keywords or remove some filters
        </p>
      </div>
    );
  }

  // Results
  return (
    <div className="w-full max-w-3xl mx-auto mt-8">
      {/* Results header */}
      <div className="flex items-center justify-between mb-4 px-1">
        <p className="text-void-400 text-sm">
          Found <span className="text-white font-medium">{results.length}</span> results
        </p>
        {queryTime && (
          <p className="text-void-500 text-sm">
            {queryTime.toFixed(0)}ms
          </p>
        )}
      </div>
      
      {/* Results list */}
      <div className="space-y-4">
        {results.map((result, index) => (
          <ResultCard 
            key={result.id} 
            result={result} 
            index={index}
            onViewSession={onViewSession}
            onFindSimilar={onFindSimilar}
          />
        ))}
      </div>
    </div>
  );
}
