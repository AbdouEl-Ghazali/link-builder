#!/usr/bin/env python3
"""
Activity logging utility for link-building workflow.

Provides a simple interface for logging agent activities and workflow events.
Uses standard library only.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configuration
LOG_DIR = Path(__file__).parent.parent / "data"
ACTIVITY_LOG = LOG_DIR / "activity_log.jsonl"  # JSON Lines format


def log_activity(
    agent_name: str,
    action: str,
    status: str = "completed",
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """
    Log an activity from an agent or workflow step.
    
    Args:
        agent_name: Name of the agent or workflow step
        action: Description of the action performed
        status: Status of the action (completed, failed, skipped, in_progress)
        details: Optional dictionary with additional details
        error: Optional error message if status is "failed"
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "action": action,
        "status": status,
    }
    
    if details:
        log_entry["details"] = details
    
    if error:
        log_entry["error"] = error
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Append to JSON Lines file
    with open(ACTIVITY_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    # Print to console for immediate feedback
    status_icon = {
        "completed": "✓",
        "failed": "✗",
        "skipped": "⊘",
        "in_progress": "→"
    }.get(status, "•")
    
    print(f"{status_icon} [{agent_name}] {action} ({status})")


def read_activity_log(limit: Optional[int] = None) -> list:
    """
    Read activity log entries.
    
    Args:
        limit: Optional limit on number of entries to return (most recent first)
    
    Returns:
        List of log entries
    """
    if not ACTIVITY_LOG.exists():
        return []
    
    entries = []
    with open(ACTIVITY_LOG, "r") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    # Return most recent first
    entries.reverse()
    
    if limit:
        return entries[:limit]
    
    return entries


def get_agent_stats(agent_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get statistics about agent activities.
    
    Args:
        agent_name: Optional filter by specific agent
    
    Returns:
        Dictionary with statistics
    """
    entries = read_activity_log()
    
    if agent_name:
        entries = [e for e in entries if e.get("agent") == agent_name]
    
    if not entries:
        return {
            "total_activities": 0,
            "by_status": {},
            "by_agent": {}
        }
    
    stats = {
        "total_activities": len(entries),
        "by_status": {},
        "by_agent": {},
        "recent_activity": entries[:10]  # Last 10 activities
    }
    
    for entry in entries:
        status = entry.get("status", "unknown")
        agent = entry.get("agent", "unknown")
        
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1
    
    return stats


def main():
    """CLI interface for activity logging."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python log_activity.py log <agent> <action> [status]")
        print("  python log_activity.py read [limit]")
        print("  python log_activity.py stats [agent_name]")
        return
    
    command = sys.argv[1]
    
    if command == "log":
        if len(sys.argv) < 4:
            print("Error: log requires agent and action")
            return
        agent = sys.argv[2]
        action = sys.argv[3]
        status = sys.argv[4] if len(sys.argv) > 4 else "completed"
        log_activity(agent, action, status)
    
    elif command == "read":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        entries = read_activity_log(limit)
        for entry in entries:
            print(json.dumps(entry, indent=2))
    
    elif command == "stats":
        agent_name = sys.argv[2] if len(sys.argv) > 2 else None
        stats = get_agent_stats(agent_name)
        print(json.dumps(stats, indent=2))
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()

