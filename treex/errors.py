from typing import Optional, Tuple, Any
from .tokens import Token, TokenType


class ParserError(Exception):
    """Base class for parser errors."""
    
    def __init__(self, message: str, position: Optional[Tuple[int, int]] = None) -> None:
        """
        Initialize a parser error.
        
        Args:
            message: Error message
            position: (line, column) position where error occurred
        """
        super().__init__(message)
        self.position: Optional[Tuple[int, int]] = position
        self.message: str = message
    
    def __str__(self) -> str:
        """Format the error message with position if available."""
        if self.position:
            return f"{self.message} at {self.position}"
        return self.message


class UnexpectedTokenError(ParserError):
    """Error raised when encountering an unexpected token."""
    
    def __init__(
        self,
        expected: TokenType,
        actual: Token,
        position: Tuple[int, int]
    ) -> None:
        """
        Initialize an unexpected token error.
        
        Args:
            expected: Expected token type
            actual: Actual token encountered
            position: Position where error occurred
        """
        message = f"Expected {expected.name}, got {actual.type.name} '{actual.value}'"
        super().__init__(message, position)


class UnclosedGroupError(ParserError):
    """Error raised when a group is not properly closed."""
    
    def __init__(self, group_type: str, position: Tuple[int, int]) -> None:
        """
        Initialize an unclosed group error.
        
        Args:
            group_type: Type of unclosed group (e.g., 'brace', 'bracket')
            position: Position where error occurred
        """
        message = f"Unclosed {group_type} group"
        super().__init__(message, position)