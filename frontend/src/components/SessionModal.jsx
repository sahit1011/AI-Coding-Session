import { useEffect, useRef } from 'react';
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import go from 'highlight.js/lib/languages/go';
import swift from 'highlight.js/lib/languages/swift';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import 'highlight.js/styles/tokyo-night-dark.css';

// Register languages
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('go', go);
hljs.registerLanguage('swift', swift);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('json', json);

// Helper to detect and highlight code blocks in content
function highlightCodeBlocks(content) {
  if (!content) return '';
  
  // Match code blocks with optional language
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
  
  let result = content;
  let match;
  
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const language = match[1] || 'plaintext';
    const code = match[2].trim();
    
    let highlighted;
    try {
      highlighted = hljs.highlight(code, { language }).value;
    } catch {
      highlighted = hljs.highlightAuto(code).value;
    }
    
    const replacement = `<div class="code-block my-3 rounded-lg overflow-hidden">
      <div class="code-header bg-void-950 px-3 py-1 text-xs text-void-400 border-b border-void-700">${language}</div>
      <pre class="bg-void-950 p-3 overflow-x-auto"><code class="hljs language-${language}">${highlighted}</code></pre>
    </div>`;
    
    result = result.replace(match[0], replacement);
  }
  
  // Handle inline code
  result = result.replace(/`([^`]+)`/g, '<code class="inline-code px-1.5 py-0.5 bg-void-800 rounded text-accent-cyan text-sm">$1</code>');
  
  // Convert newlines to <br> for non-code content
  result = result.replace(/\n/g, '<br>');
  
  return result;
}

export default function SessionModal({ session, loading, onClose }) {
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
  
  // Format timestamp
  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!session && !loading) return null;

  return (
    <div 
      ref={modalRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fadeIn"
    >
      <div className="bg-void-900 border border-void-700 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-void-700 bg-void-950">
          <div className="flex items-center gap-4">
            {loading ? (
              <div className="h-8 w-48 bg-void-700 rounded animate-pulse" />
            ) : (
              <>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center text-white font-bold text-sm">
                  {session?.engineer?.name?.split(' ').map(n => n[0]).join('')}
                </div>
                <div>
                  <h2 className="text-white font-semibold text-lg">{session?.engineer?.name}</h2>
                  <p className="text-void-400 text-sm">{session?.engineer?.role}</p>
                </div>
              </>
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
        
        {/* Session info bar */}
        {!loading && session && (
          <div className="px-5 py-3 bg-void-950/50 border-b border-void-800 flex flex-wrap items-center gap-3 text-sm">
            <span className="px-2 py-1 bg-accent-cyan/20 text-accent-cyan rounded">
              {session.project?.name}
            </span>
            <span className="px-2 py-1 bg-void-800 text-void-300 rounded">
              {session.project?.language}
            </span>
            <span className="text-void-500">•</span>
            <span className="text-void-400">{formatDate(session.started_at)}</span>
            <span className="text-void-500">•</span>
            <span className="text-void-400">{session.message_count} messages</span>
          </div>
        )}
        
        {/* Task description */}
        {!loading && session?.task && (
          <div className="px-5 py-3 bg-void-950/30 border-b border-void-800">
            <p className="text-void-300 text-sm">
              <span className="text-void-500">Task:</span> {session.task}
            </p>
          </div>
        )}
        
        {/* Conversation */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            // Loading skeleton
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3 animate-pulse">
                  <div className="w-8 h-8 rounded-full bg-void-700 flex-shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-20 bg-void-700 rounded" />
                    <div className="h-20 bg-void-800 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // Actual conversation
            session?.conversation?.map((msg, index) => (
              <div 
                key={msg.id || index} 
                className={`flex gap-3 ${msg.type === 'assistant_response' ? 'pl-4' : ''}`}
              >
                {/* Avatar */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  msg.type === 'user_query' 
                    ? 'bg-void-700' 
                    : 'bg-gradient-to-br from-accent-cyan/30 to-accent-purple/30'
                }`}>
                  {msg.type === 'user_query' ? (
                    <svg className="w-4 h-4 text-void-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  )}
                </div>
                
                {/* Message content */}
                <div className="flex-1 min-w-0">
                  <p className="text-void-500 text-xs mb-1">
                    {msg.type === 'user_query' ? 'User' : 'Claude'}
                  </p>
                  <div 
                    className={`p-3 rounded-lg text-sm leading-relaxed ${
                      msg.type === 'user_query'
                        ? 'bg-void-800 text-void-200'
                        : 'bg-void-800/50 text-void-200 border-l-2 border-accent-cyan/30'
                    }`}
                    dangerouslySetInnerHTML={{ __html: highlightCodeBlocks(msg.content) }}
                  />
                </div>
              </div>
            ))
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

