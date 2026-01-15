import { useState, useCallback } from 'react';

const API_BASE = '/api';

export function useSearch() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [queryTime, setQueryTime] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const search = useCallback(async (query, filters = {}) => {
    if (!query.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const response = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          limit: 20,
          filters: {
            engineer: filters.engineer || null,
            project: filters.project || null,
            language: filters.language || null,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setResults(data.results);
      setQueryTime(data.query_time_ms);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setResults([]);
    setHasSearched(false);
    setQueryTime(null);
    setError(null);
  }, []);

  return {
    results,
    loading,
    error,
    queryTime,
    hasSearched,
    search,
    clearResults,
  };
}

export function useEngineers() {
  const [engineers, setEngineers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchEngineers = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/engineers`);
      const data = await response.json();
      setEngineers(data.engineers);
    } catch (err) {
      console.error('Failed to fetch engineers:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { engineers, loading, fetchEngineers };
}

export function useProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/projects`);
      const data = await response.json();
      setProjects(data.projects);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { projects, loading, fetchProjects };
}

export function useStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/stats`);
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { stats, loading, fetchStats };
}

// NEW: Hook for fetching full session details
export function useSessionDetail() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSession = useCallback(async (sessionId) => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
      if (!response.ok) {
        throw new Error('Session not found');
      }
      const data = await response.json();
      setSession(data);
    } catch (err) {
      setError(err.message);
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearSession = useCallback(() => {
    setSession(null);
    setError(null);
  }, []);

  return { session, loading, error, fetchSession, clearSession };
}

// NEW: Hook for finding similar sessions
export function useSimilar() {
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sourceChunk, setSourceChunk] = useState(null);

  const findSimilar = useCallback(async (chunkId, limit = 5) => {
    if (!chunkId) return;
    
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/similar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chunk_id: chunkId, limit }),
      });
      const data = await response.json();
      setSimilar(data.results || []);
      setSourceChunk(data.source_chunk || null);
    } catch (err) {
      console.error('Failed to find similar:', err);
      setSimilar([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearSimilar = useCallback(() => {
    setSimilar([]);
    setSourceChunk(null);
  }, []);

  return { similar, loading, sourceChunk, findSimilar, clearSimilar };
}

// NEW: Hook for search suggestions
export function useSuggestions() {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchSuggestions = useCallback(async (query = '') => {
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/suggestions?q=${encodeURIComponent(query)}&limit=8`);
      const data = await response.json();
      setSuggestions(data.suggestions || []);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return { suggestions, loading, fetchSuggestions };
}

// NEW: Hook for analytics
export function useAnalytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/analytics`);
      const data = await response.json();
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return { analytics, loading, fetchAnalytics };
}
