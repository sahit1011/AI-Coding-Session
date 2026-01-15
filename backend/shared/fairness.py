"""
Fairness utilities for ensuring equal quota/representation.

Implements the workspace rule: "everyone should get equal quota"
"""

from typing import List, Dict, Any
from collections import defaultdict


def ensure_fair_distribution(
    results: List[Dict[str, Any]],
    target_count: int = 10,
    fairness_mode: str = "balanced"  # "balanced", "round_robin", "proportional"
) -> List[Dict[str, Any]]:
    """
    Ensure fair distribution of results across engineers.
    
    FIXED: Implements "equal quota" rule from workspace requirements.
    
    Args:
        results: Search results
        target_count: Number of results to return
        fairness_mode: How to ensure fairness
            - "balanced": Equal representation if possible (recommended)
            - "round_robin": Strict alternation between engineers
            - "proportional": Based on relevance scores only
    
    Returns:
        Reordered results with fair distribution
    """
    if not results or len(results) <= target_count:
        return results
    
    # Group by engineer
    by_engineer = defaultdict(list)
    for result in results:
        engineer = result.get("engineer", {}).get("username", "unknown")
        by_engineer[engineer].append(result)
    
    # Sort each engineer's results by score
    for engineer in by_engineer:
        by_engineer[engineer].sort(key=lambda x: x.get("score", 0), reverse=True)
    
    if fairness_mode == "round_robin":
        # Strict alternation between engineers
        fair_results = []
        max_per_engineer = max(len(results) for results in by_engineer.values())
        
        for i in range(max_per_engineer):
            for engineer in sorted(by_engineer.keys()):
                if i < len(by_engineer[engineer]):
                    fair_results.append(by_engineer[engineer][i])
                if len(fair_results) >= target_count:
                    return fair_results
        
        return fair_results
    
    elif fairness_mode == "balanced":
        # Try to include at least one result from each engineer
        fair_results = []
        engineers = sorted(by_engineer.keys())
        
        # First pass: Include top result from each engineer
        for engineer in engineers:
            if by_engineer[engineer]:
                fair_results.append(by_engineer[engineer].pop(0))
                if len(fair_results) >= target_count:
                    return fair_results
        
        # Second pass: Fill remaining slots with highest scores
        remaining_results = []
        for engineer in engineers:
            remaining_results.extend(by_engineer[engineer])
        
        remaining_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        fair_results.extend(remaining_results[:target_count - len(fair_results)])
        
        return fair_results[:target_count]
    
    else:  # proportional or default
        # Just return top N by score (no fairness adjustment)
        return results[:target_count]


def get_distribution_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate distribution statistics for results.
    
    Returns:
        Dict with engineer distribution stats
    """
    if not results:
        return {
            "total_results": 0,
            "unique_engineers": 0,
            "distribution": {},
            "is_balanced": True
        }
    
    by_engineer = defaultdict(int)
    for result in results:
        engineer = result.get("engineer", {}).get("username", "unknown")
        by_engineer[engineer] += 1
    
    total = len(results)
    distribution = {
        engineer: {
            "count": count,
            "percentage": round((count / total) * 100, 1) if total > 0 else 0
        }
        for engineer, count in by_engineer.items()
    }
    
    return {
        "total_results": total,
        "unique_engineers": len(by_engineer),
        "distribution": distribution,
        "is_balanced": _is_balanced(list(by_engineer.values()))
    }


def _is_balanced(counts: List[int], threshold: float = 0.3) -> bool:
    """
    Check if distribution is reasonably balanced.
    
    Args:
        counts: List of counts per engineer
        threshold: Maximum deviation from mean (as fraction)
    
    Returns:
        True if all counts are within threshold of mean
    """
    if not counts or len(counts) <= 1:
        return True
    
    mean = sum(counts) / len(counts)
    if mean == 0:
        return True
    
    # Check if all counts are within threshold of mean
    for count in counts:
        if abs(count - mean) / mean > threshold:
            return False
    
    return True


def check_quota_limits(
    engineer: str,
    usage_stats: Dict[str, int],
    limit_per_engineer: int = 100
) -> bool:
    """
    Check if engineer has exceeded their quota.
    
    Args:
        engineer: Engineer username
        usage_stats: Dict of {engineer: request_count}
        limit_per_engineer: Max requests per engineer
    
    Returns:
        True if within quota, False if exceeded
    """
    current_usage = usage_stats.get(engineer, 0)
    return current_usage < limit_per_engineer

