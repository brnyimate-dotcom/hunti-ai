import sqlite3
from datetime import datetime, timedelta
from database import get_connection

def check_rate_limit(user_id: str, action: str = "chat", max_requests: int = 10, window_minutes: int = 60) -> tuple[bool, str]:
    """
    Check if user has exceeded rate limit.
    Returns (allowed: bool, message: str)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calculate time window
        window_start = datetime.now() - timedelta(minutes=window_minutes)
        
        # Count recent requests
        cursor.execute('''
            SELECT COUNT(*) FROM usage_logs 
            WHERE user_id = ? AND action = ? AND timestamp > ?
        ''', (user_id, action, window_start))
        
        count = cursor.fetchone()[0]
        
        if count >= max_requests:
            conn.close()
            return False, f"Rate limit exceeded. You've made {count} requests in the last {window_minutes} minutes. Please wait before trying again."
        
        # Log this request
        cursor.execute('''
            INSERT INTO usage_logs (user_id, action) VALUES (?, ?)
        ''', (user_id, action))
        
        conn.commit()
        conn.close()
        
        return True, f"Request {count + 1} of {max_requests} allowed"
    
    except sqlite3.OperationalError:
        # Table doesn't exist - allow the request but don't track
        return True, "Demo mode - rate limiting disabled"

def get_usage_stats(user_id: str) -> dict:
    """Get user's usage statistics."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total, 
                   MAX(timestamp) as last_request,
                   COUNT(CASE WHEN timestamp > datetime('now', '-1 hour') THEN 1 END) as last_hour
            FROM usage_logs 
            WHERE user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        conn.close()
        
        return {
            'total_requests': stats[0] if stats[0] else 0,
            'last_request': stats[1] if stats[1] else 'N/A',
            'requests_last_hour': stats[2] if stats[2] else 0
        }
    
    except sqlite3.OperationalError:
        # Table doesn't exist - return demo stats
        return {
            'total_requests': 0,
            'last_request': 'N/A',
            'requests_last_hour': 0
        }