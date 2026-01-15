import { useEffect, useRef } from 'react';

export default function SimilarModal({ 
  similar, 
  loading, 
  sourceChunk, 
  onClose, 
  onSelectResult,
  onViewSession 
}) {
  const modalRef = useRef(null);
  
  // Close on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);
  
  // Close on backdrop click
  const handleBackdropClick = (e) => {
    if (e.target === modalRef.current) onClose();
  };

  const getScoreColor = (score) => {
    if (score >= 0.7) return 'from-emerald-400 to-cyan-400';
    if (score >= 0.5) return 'from-cyan-400 to-blue-400';
    return 'from-blue-400 to-purple-400';
  };

  const truncate = (text, maxLength) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div 
      ref={modalRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      <div className="bg-void-900 border border-void-700 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-void-700 bg-void-950">
          <div>
            <h2 className="text-white font-semibold text-lg flex items-center gap-2">
              <svg className="w-5 h-5 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Similar Sessions
            </h2>
            {sourceChunk && (
              <p className="text-void-400 text-sm mt-1">
                Related to: {sourceChunk.engineer}'s {sourceChunk.project} session
              </p>
            )}
          </div>
          
          <button 
            onClick={onClose}
            className="p-2 text-void-400 hover:text-white hover:bg-void-800 rounded-lg transition"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        {/* Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="p-4 bg-void-800 rounded-lg animate-pulse">
                  <div className="h-4 w-32 bg-void-700 rounded mb-2" />
                  <div className="h-3 w-full bg-void-700 rounded" />
                </div>
              ))}
            </div>
          ) : similar.length === 0 ? (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-void-800 mb-3">
                <svg className="w-6 h-6 text-void-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-void-400">No similar sessions found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {similar.map((result, index) => (
                <div 
                  key={result.id}
                  className="p-4 bg-void-800 hover:bg-void-750 rounded-lg border border-void-700 hover:border-void-600 transition cursor-pointer group"
                  onClick={() => onSelectResult && onSelectResult(result)}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-cyan/50 to-accent-purple/50 flex items-center justify-center text-white text-xs font-medium">
                        {result.engineer.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">{result.engineer.name}</p>
                        <p className="text-void-500 text-xs">{result.project.name} • {result.project.language}</p>
                      </div>
                    </div>
                    
                    <div className={`bg-gradient-to-r ${getScoreColor(result.score)} px-2 py-0.5 rounded-full`}>
                      <span className="text-white text-xs font-medium">{Math.round(result.score * 100)}%</span>
                    </div>
                  </div>
                  
                  <p className="text-void-400 text-xs mb-2">{result.session.task}</p>
                  
                  <p className="text-void-300 text-sm line-clamp-2">
                    {truncate(result.context.user_query, 150)}
                  </p>
                  
                  <div className="flex items-center gap-2 mt-3 pt-2 border-t border-void-700 opacity-0 group-hover:opacity-100 transition">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewSession && onViewSession(result.session.id);
                      }}
                      className="text-xs text-accent-cyan hover:text-white transition"
                    >
                      View Full Session →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-void-700 bg-void-950 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-void-800 text-void-300 rounded-lg hover:bg-void-700 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

