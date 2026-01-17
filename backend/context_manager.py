"""
Context Memory Manager - Handles conversation context and subject tracking
"""
from typing import Optional, Dict, Any
import time


class ConversationContext:
    """Manages conversation context across requests"""
    
    def __init__(self, session_timeout: int = 600):  # 10 minutes default
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
    
    def _cleanup_expired(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired = [
            sid for sid, data in self.sessions.items()
            if current_time - data.get("last_updated", 0) > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]
    
    def get_active_subject(self, session_id: str = "default") -> Optional[str]:
        """Get the active subject for a session"""
        self._cleanup_expired()
        session = self.sessions.get(session_id, {})
        return session.get("active_subject")
    
    def set_active_subject(self, subject: str, session_id: str = "default"):
        """Set the active subject for a session"""
        self._cleanup_expired()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        self.sessions[session_id]["active_subject"] = subject
        self.sessions[session_id]["last_updated"] = time.time()
    
    def clear_session(self, session_id: str = "default"):
        """Clear a specific session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_context(self, session_id: str = "default") -> Dict[str, Any]:
        """Get full context for a session"""
        self._cleanup_expired()
        return self.sessions.get(session_id, {})
    
    def update_context(self, updates: Dict[str, Any], session_id: str = "default"):
        """Update context with new data"""
        self._cleanup_expired()
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        
        self.sessions[session_id].update(updates)
        self.sessions[session_id]["last_updated"] = time.time()


# Global instance
context_manager = ConversationContext()