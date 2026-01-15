import { useMemo } from 'react';
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import go from 'highlight.js/lib/languages/go';
import swift from 'highlight.js/lib/languages/swift';
import bash from 'highlight.js/lib/languages/bash';
import 'highlight.js/styles/tokyo-night-dark.css';

// Register languages
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('go', go);
hljs.registerLanguage('swift', swift);
hljs.registerLanguage('bash', bash);

// Helper to detect and highlight code blocks
function highlightCodeInText(text) {
  if (!text) return '';
  
  // Match code blocks with triple backticks
  const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
  
  let result = text;
  let match;
  
  while ((match = codeBlockRegex.exec(text)) !== null) {
    const language = match[1] || 'plaintext';
    const code = match[2].trim();
    
    let highlighted;
    try {
      highlighted = hljs.highlight(code, { language }).value;
    } catch {
      try {
        highlighted = hljs.highlightAuto(code).value;
      } catch {
        highlighted = code;
      }
    }
    
    const replacement = `<div class="code-block my-2 rounded-lg overflow-hidden border border-void-700">
      <div class="code-header bg-void-950 px-2 py-0.5 text-xs text-void-500">${language}</div>
      <pre class="bg-void-950 p-2 overflow-x-auto text-xs"><code class="hljs">${highlighted}</code></pre>
    </div>`;
    
    result = result.replace(match[0], replacement);
  }
  
  // Handle inline code
  result = result.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 bg-void-800 rounded text-accent-cyan text-xs">$1</code>');
  
  return result;
}

export default function ResultCard({ result, index, onViewSession, onFindSimilar }) {
  const { score, engineer, project, session, context } = result;
  
  // Memoize highlighted content
  const highlightedResponse = useMemo(() => 
    highlightCodeInText(context.assistant_response),
    [context.assistant_response]
  );
  
  // Format timestamp
  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Get color for score
  const getScoreColor = (score) => {
    if (score >= 0.7) return 'from-emerald-400 to-cyan-400';
    if (score >= 0.5) return 'from-cyan-400 to-blue-400';
    return 'from-blue-400 to-purple-400';
  };

  // Truncate text
  const truncate = (text, maxLength) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div 
      className="result-card fade-in bg-void-900 border border-void-700 rounded-xl p-5 opacity-0"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center text-white font-bold text-sm">
            {engineer.name.split(' ').map(n => n[0]).join('')}
          </div>
          
          {/* Engineer info */}
          <div>
            <h3 className="text-white font-medium">{engineer.name}</h3>
            <p className="text-void-400 text-sm">{engineer.role}</p>
          </div>
        </div>
        
        {/* Score badge */}
        <div className={`score-badge bg-gradient-to-r ${getScoreColor(score)} px-3 py-1 rounded-full`}>
          <span className="text-white text-sm font-medium">{Math.round(score * 100)}%</span>
        </div>
      </div>
      
      {/* Project and session info */}
      <div className="flex flex-wrap items-center gap-2 mb-4 text-sm">
        <span className="px-2 py-1 bg-void-800 rounded text-accent-cyan">
          {project.name}
        </span>
        <span className="px-2 py-1 bg-void-800 rounded text-void-300">
          {project.language}
        </span>
        {project.framework && (
          <span className="px-2 py-1 bg-void-800 rounded text-void-400">
            {project.framework}
          </span>
        )}
        <span className="text-void-500">•</span>
        <span className="text-void-400">{formatDate(session.timestamp)}</span>
      </div>
      
      {/* Task description */}
      {session.task && (
        <div className="mb-4 p-3 bg-void-950 rounded-lg border-l-2 border-accent-purple">
          <p className="text-void-300 text-sm">
            <span className="text-void-500">Task:</span> {session.task}
          </p>
        </div>
      )}
      
      {/* Conversation context */}
      <div className="space-y-3">
        {/* User query */}
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-void-700 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-void-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-void-400 text-xs mb-1">Question</p>
            <p className="text-void-200 text-sm leading-relaxed">
              {truncate(context.user_query, 200)}
            </p>
          </div>
        </div>
        
        {/* Assistant response with code highlighting */}
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-accent-cyan/30 to-accent-purple/30 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-void-400 text-xs mb-1">AI Response</p>
            <div 
              className="text-void-200 text-sm leading-relaxed prose-code"
              dangerouslySetInnerHTML={{ 
                __html: truncate(highlightedResponse, 600) 
              }}
            />
          </div>
        </div>
      </div>
      
      {/* Action buttons */}
      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-void-800">
        <button
          onClick={() => onViewSession && onViewSession(session.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-void-800 hover:bg-void-700 text-void-300 hover:text-white rounded-lg text-sm transition"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          View Full Session
        </button>
        
        <button
          onClick={() => onFindSimilar && onFindSimilar(result.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-void-800 hover:bg-void-700 text-void-300 hover:text-white rounded-lg text-sm transition"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Find Similar
        </button>
      </div>
    </div>
  );
}
