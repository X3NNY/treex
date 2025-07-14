from enum import Enum
from typing import Tuple, Any, Optional


class TokenType(Enum):
    """Enumeration of token types in LaTeX parsing."""
    
    # Basic structure tokens
    BRACE_OPEN = 1        # {
    BRACE_CLOSE = 2       # }
    BRACKET_OPEN = 3      # [
    BRACKET_CLOSE = 4     # ]
    
    # Command and environment tokens
    COMMAND = 11          # \command
    ENV_BEGIN = 12        # \begin{env}
    ENV_END = 13          # \end{env}
    
    # Content type tokens
    TEXT = 21             # Plain text
    MATH_INLINE = 22      # Inline math ($...$)
    MATH_FORMULA = 23     # Display math ($$...$$)
    COMMENT = 24          # Comment (%...)
    ESCAPE_SEQUENCE = 25  # Escape sequence (\#, \$, etc.)
    
    # Special characters
    SPECIAL_CHAR = 31     # &, %, #, _, etc.
    
    # Whitespace tokens
    SPACE = 41            # Space character
    NEWLINE = 42          # Newline character
    
    # Parameter tokens
    PARAM_MARKER = 43     # #1, #2, etc.
    
    # Control tokens
    EOF = 101             # End of file
    ERROR = 102           # Lexical error


class Token:
    """Represents a lexical token in LaTeX source code."""
    
    __slots__ = ('type', 'value', 'position')
    
    def __init__(
        self,
        type_: TokenType,
        value: str,
        position: Tuple[int, int]
    ) -> None:
        """
        Initialize a token.
        
        Args:
            type_: Type of the token
            value: String value of the token
            position: (line, column) position in source
        """
        self.type: TokenType = type_
        self.value: str = value
        self.position: Tuple[int, int] = position
    
    def __repr__(self) -> str:
        """Return a string representation of the token."""
        return f"Token({self.type.name}, '{self.value}', {self.position})"
    
    def __eq__(self, other: Any) -> bool:
        """
        Compare tokens for equality.
        
        Args:
            other: Another object to compare with
            
        Returns:
            True if tokens are equal, False otherwise
        """
        if not isinstance(other, Token):
            return False
        return (self.type == other.type and 
                self.value == other.value and 
                self.position == other.position)