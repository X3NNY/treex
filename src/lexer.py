from enum import Enum
from typing import List, Optional, Tuple, Dict
from .tokens import Token, TokenType


class LexerState(Enum):
    """Lexer state enumeration."""
    NORMAL = 0            # Normal text processing
    ESCAPE = 1            # Processing escape sequence
    MATH_INLINE = 2       # Inline math mode ($...$)
    MATH_DISPLAY = 3      # Display math mode ($$...$$)
    COMMENT = 4           # Processing comment
    ENVIRONMENT = 5       # Processing environment
    PARAMETER = 6         # Processing parameter


class LaTeXLexer:
    """LaTeX lexer that converts LaTeX source code into a token stream."""
    
    def __init__(self, debug: bool = False) -> None:
        """Initialize the lexer."""
        self.state: LexerState = LexerState.NORMAL
        self.tokens: List[Token] = []
        self.buffer: List[str] = []
        self.position: Tuple[int, int] = (1, 1)  # (line, column)
        self.math_delimiter_stack: List[TokenType] = []
        self.command_name: str = ""
        self.debug: bool = debug
        self.current_line: str = ""
        self.in_math_mode: bool = False
    
    def tokenize(self, input_str: str) -> List[Token]:
        """
        Main entry point: convert LaTeX source to a list of tokens.
        
        Args:
            input_str: The LaTeX source code to tokenize
            
        Returns:
            List of tokens
        """
        self._reset()
        lines = input_str.split('\n')
        
        total_lines = len(lines)
        for line_num, line in enumerate(lines, 1):
            self.current_line = line
            self.position = (line_num, 1)
            self._process_line(line, line_num != total_lines)
            
        # Flush remaining buffer content
        self._flush_buffer()
        self.tokens.append(Token(TokenType.EOF, '', self.position))
        return self.tokens
    
    def _reset(self) -> None:
        """Reset the lexer state."""
        self.state = LexerState.NORMAL
        self.tokens = []
        self.buffer = []
        self.position = (1, 1)
        self.math_delimiter_stack = []
        self.command_name = ""
        self.in_math_mode = False
    
    def _process_line(self, line: str, newline: bool) -> None:
        """
        Process a single line of LaTeX source.
        
        Args:
            line: The line to process
            newline: Whether to add a newline token at the end
        """
        col = 0
        while col < len(line):
            char = line[col]
            next_char = line[col + 1] if col + 1 < len(line) else None
            
            # Update current position
            self.position = (self.position[0], col + 1)
            
            # Dispatch processing based on current state
            handler = self._get_state_handler()
            col = handler(char, next_char, line, col)
            
            col += 1

        if newline:
            self.position = (self.position[0], col + 1)
            handler = self._get_state_handler()
            handler('\n', None, line, col)
        
    def _get_state_handler(self):
        """Get the handler function for current state."""
        handlers = {
            LexerState.NORMAL: self._handle_normal,
            LexerState.ESCAPE: self._handle_escape,
            LexerState.MATH_INLINE: self._handle_math_inline,
            LexerState.MATH_DISPLAY: self._handle_math_display,
            LexerState.COMMENT: self._handle_comment,
            LexerState.ENVIRONMENT: self._handle_environment,
            LexerState.PARAMETER: self._handle_parameter,
        }
        return handlers.get(self.state, self._handle_normal)
    
    def _handle_normal(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle normal text state."""
        # Handle escape sequence start
        if char == '\\':
            self._flush_buffer()
            self.state = LexerState.ESCAPE
        
        # Handle display math start ($$)
        elif char == '$' and next_char == '$':
            self._flush_buffer()
            self.state = LexerState.MATH_DISPLAY
            self.math_delimiter_stack.append(TokenType.MATH_FORMULA)
            self.in_math_mode = True
            return col + 1  # Skip both characters
        
        # Handle inline math start ($)
        elif char == '$':
            self._flush_buffer()
            self.state = LexerState.MATH_INLINE
            self.math_delimiter_stack.append(TokenType.MATH_INLINE)
            self.in_math_mode = True
        
        # Handle comment start
        elif char == '%':
            self._flush_buffer()
            self.state = LexerState.COMMENT
            self.buffer.append(char)
        
        # Handle special characters
        elif char in ('{', '}'):
            self._flush_buffer()
            token_type = TokenType.BRACE_OPEN if char == '{' else TokenType.BRACE_CLOSE
            self.tokens.append(Token(token_type, char, self.position))
        
        elif char in ('[', ']'):
            self._flush_buffer()
            token_type = TokenType.BRACKET_OPEN if char == '[' else TokenType.BRACKET_CLOSE
            self.tokens.append(Token(token_type, char, self.position))
        
        # Handle parameter marker
        elif char == '#':
            self._flush_buffer()
            self.state = LexerState.PARAMETER
            self.buffer.append(char)
        
        # Handle other special characters
        elif char in ('&', '_', '^', '~'):
            self._flush_buffer()
            self.tokens.append(Token(TokenType.SPECIAL_CHAR, char, self.position))
        
        # Handle whitespace
        elif char.isspace() or char == '\n':
            self._flush_buffer()
            if char == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, char, self.position))
            else:
                self.tokens.append(Token(TokenType.SPACE, char, self.position))
        
        # Normal text character
        else:
            self.buffer.append(char)
        
        return col
    
    def _handle_escape(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle escape state."""
        special_escapes = {
            '$': '$', '%': '%', '&': '&', '#': '#', '_': '_',
            '{': '{', '}': '}', '\\': '\\', ' ': ' ', '~': '~', '^': '^'
        }
        
        # Handle known special escapes
        if char in special_escapes:
            self.buffer.append(special_escapes[char])
            self._flush_buffer_as(TokenType.ESCAPE_SEQUENCE)
            self.state = LexerState.NORMAL if not self.in_math_mode else LexerState.MATH_INLINE
        
        # Handle commands (letter sequences)
        elif char.isalpha() or char == '*':
            command = [char]
            next_idx = col + 1
            # Collect entire command (letter sequence)
            while next_idx < len(line) and (line[next_idx].isalpha() or line[next_idx] == '*'):
                command.append(line[next_idx])
                next_idx += 1
            
            full_command = ''.join(command)
            self.buffer.append(full_command)
            
            # Check if it's an environment command
            if full_command in ('begin', 'end'):
                self.command_name = full_command
                self.state = LexerState.ENVIRONMENT
            else:
                self._flush_buffer_as(TokenType.COMMAND)
                self.state = LexerState.NORMAL if not self.in_math_mode else LexerState.MATH_INLINE
            
            return col + len(command) - 1  # Skip processed characters
        
        # Handle unknown escapes (keep as-is)
        else:
            self.buffer.append(char)
            self._flush_buffer_as(TokenType.ESCAPE_SEQUENCE)
            self.state = LexerState.NORMAL if not self.in_math_mode else LexerState.MATH_INLINE
        
        return col
    
    def _handle_math_inline(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle inline math mode."""
        return self._handle_math(char, next_char, line, col, TokenType.MATH_INLINE)
    
    def _handle_math_display(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle display math mode."""
        return self._handle_math(char, next_char, line, col, TokenType.MATH_FORMULA)
    
    def _handle_math(self, char: str, next_char: Optional[str], line: str, col: int, math_type: TokenType) -> int:
        """Common math mode handling logic."""
        # Handle display math end ($$)
        if math_type == TokenType.MATH_FORMULA and char == '$' and next_char == '$':
            if self.math_delimiter_stack and self.math_delimiter_stack[-1] == math_type:
                self.math_delimiter_stack.pop()
                self._flush_buffer()
                self.state = LexerState.NORMAL
                self.in_math_mode = False
                return col + 1  # Skip both characters
            else:
                self.buffer.append(char)
        
        # Handle inline math end ($)
        elif math_type == TokenType.MATH_INLINE and char == '$':
            if self.math_delimiter_stack and self.math_delimiter_stack[-1] == math_type:
                self.math_delimiter_stack.pop()
                self._flush_buffer()
                self.state = LexerState.NORMAL
                self.in_math_mode = False
            else:
                self.buffer.append(char)
        
        # Escape in math mode
        elif char == '\\':
            self.buffer.append(char)
            self.buffer.append(next_char)
            return col + 1  # Skip both characters
        
        # Normal character in math mode
        else:
            self.buffer.append(char)
        
        return col
    
    def _handle_comment(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle comment state."""
        self.buffer.append(char)
        if char == '\n':
            self._flush_buffer_as(TokenType.COMMENT)
            self.state = LexerState.NORMAL
        return col
    
    def _handle_environment(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle environment declaration state."""
        if char == '{':
            self.buffer = []
        elif char == '}':
            env_name = ''.join(self.buffer)
            self.buffer = []
            
            if self.command_name == 'begin':
                self.tokens.append(Token(TokenType.ENV_BEGIN, env_name, self.position))
            elif self.command_name == 'end':
                self.tokens.append(Token(TokenType.ENV_END, env_name, self.position))
            
            self.command_name = ""
            self.state = LexerState.NORMAL
        else:
            self.buffer.append(char)
        return col
    
    def _handle_parameter(self, char: str, next_char: Optional[str], line: str, col: int) -> int:
        """Handle parameter marker state."""
        if char.isdigit():
            self.buffer.append(char)
            param_marker = ''.join(self.buffer)
            self.tokens.append(Token(TokenType.PARAM_MARKER, param_marker, self.position))
            self.buffer = []
            self.state = LexerState.NORMAL
        else:
            self._flush_buffer_as(TokenType.SPECIAL_CHAR)
            self.buffer.append(char)
            self.state = LexerState.NORMAL
        return col
    
    def _flush_buffer(self) -> None:
        """Flush buffer based on current state."""
        if not self.buffer:
            return
            
        content = ''.join(self.buffer)
        
        token_type_map = {
            LexerState.MATH_INLINE: TokenType.MATH_INLINE,
            LexerState.MATH_DISPLAY: TokenType.MATH_FORMULA,
            LexerState.COMMENT: TokenType.COMMENT,
            LexerState.ESCAPE: TokenType.ESCAPE_SEQUENCE,
            LexerState.PARAMETER: TokenType.PARAM_MARKER,
        }
        
        token_type = token_type_map.get(self.state, TokenType.TEXT)
        
        if self.state == LexerState.NORMAL and content.startswith('\\'):
            token_type = TokenType.COMMAND
        
        self.tokens.append(Token(token_type, content, self.position))
        self.buffer = []
    
    def _flush_buffer_as(self, token_type: TokenType) -> None:
        """Force flush buffer with specified token type."""
        if self.buffer:
            content = ''.join(self.buffer)
            self.tokens.append(Token(token_type, content, self.position))
            self.buffer = []