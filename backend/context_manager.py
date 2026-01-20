"""
Context Manager for conversation state.
Tracks conversation history for better intent classification and continuations.
"""

class ContextManager:
    def __init__(self):
        # Store last N question-answer pairs
        self.history = []  # List of {"question": str, "answer": str}
        self.max_history = 3  # Keep last 3 Q&A pairs
        self.active_subject = None
    
    def add_turn(self, question: str, answer: str):
        """Add a Q&A turn to history"""
        self.history.append({
            "question": question,
            "answer": answer
        })
        
        # Keep only last N turns
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self, limit: int = None) -> list:
        """Get conversation history (most recent first)"""
        if limit:
            return list(reversed(self.history[-limit:]))
        return list(reversed(self.history))
    
    def get_previous_question(self) -> str:
        """Get the most recent question"""
        if self.history:
            return self.history[-1]["question"]
        return None
    
    def get_last_n_questions(self, n: int = 3) -> list:
        """Get last N questions (most recent first)"""
        return [turn["question"] for turn in reversed(self.history[-n:])]
    
    def set_previous_question(self, question: str):
        """Legacy method - stores question without answer (will be added later)"""
        # Check if this question already exists as the last entry
        if self.history and self.history[-1]["question"] == question:
            return
        
        # Add question with placeholder answer (will be updated when answer comes)
        self.history.append({
            "question": question,
            "answer": None
        })
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def update_last_answer(self, answer: str):
        """Update the answer for the most recent question"""
        if self.history and self.history[-1]["answer"] is None:
            self.history[-1]["answer"] = answer
    
    def set_active_subject(self, subject: str):
        """Set the active subject for continuations"""
        self.active_subject = subject
    
    def get_active_subject(self) -> str:
        """Get the active subject"""
        return self.active_subject
    
    def clear_session(self):
        """Clear all context"""
        self.history = []
        self.active_subject = None
    
    def get_context_summary(self) -> str:
        """Get formatted context summary for LLM prompts"""
        if not self.history:
            return ""
        
        lines = []
        for i, turn in enumerate(reversed(self.history)):
            q = turn["question"]
            a = turn["answer"]
            
            # Most recent = 1, earlier = 2, 3, etc.
            position = i + 1
            
            if a:
                lines.append(f"Q{position}: {q}")
                lines.append(f"A{position}: {a[:100]}...")  # Truncate long answers
            else:
                lines.append(f"Q{position}: {q}")
        
        return "\n".join(lines)


# Global instance
context_manager = ContextManager()