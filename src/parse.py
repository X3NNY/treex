from typing import List, Literal, Optional, cast
from .errors import ParserError
from .registry import CommandRegistry
from .tokens import TokenType, Token
from .nodes import (
    CiteNode,
    DocumentNode,
    FootnoteNode,
    GroupNode,
    MathNode,
    ParagraphNode,
    SectionNode,
    EnvironmentNode,
    CommandNode,
    SpecialCharNode,
    TextNode,
    ASTNode,
)


class LaTeXParser:
    """LaTeX parser that converts token stream into Abstract Syntax Tree (AST)."""
    
    def __init__(
        self,
        tokens: List[Token],
        text_merge: bool = False,
        newline_mode: Literal['default', 'literal', 'compact'] = 'default'
    ) -> None:
        self.tokens = tokens
        self.current_token: Optional[Token] = None
        self.index = -1
        self.advance()  # Initialize current token
        self.document = DocumentNode()
        self.current_node: ASTNode = self.document
        
        self.in_document_env = False
        self.text_merge = text_merge
        self.newline_mode = newline_mode
        
        self.command_registry = CommandRegistry()
        self.section_stack: List[SectionNode] = []
        
        self._register_special_commands()
    
    def _register_special_commands(self) -> None:
        """Register handlers for special commands."""
        self.command_registry.register_handler('section', SectionNode)
        self.command_registry.register_handler('subsection', SectionNode)
        self.command_registry.register_handler('subsubsection', SectionNode)
        self.command_registry.register_handler('footnote', FootnoteNode)
        self.command_registry.register_handler('cite', CiteNode)
        self.command_registry.register_handler('citep', CiteNode)
        self.command_registry.register_handler('citet', CiteNode)
    
    def advance(self) -> Optional[Token]:
        """Move to next token."""
        self.index += 1
        if self.index < len(self.tokens):
            self.current_token = self.tokens[self.index]
        else:
            self.current_token = None
        return self.current_token
    
    def parse_token(self) -> None:
        """Parse current token based on its type."""
        if self.current_token is None:
            return
            
        if self.current_token.type == TokenType.COMMAND:
            self.parse_command()
        elif self.current_token.type in (TokenType.ENV_BEGIN, TokenType.ENV_END):
            self.parse_environment()
        elif self.current_token.type == TokenType.MATH_INLINE:
            self.parse_math()
        elif self.current_token.type == TokenType.MATH_FORMULA:
            self.parse_math(display=True)
        elif self.current_token.type == TokenType.BRACE_OPEN:
            self.parse_group()
        elif self.current_token.type in (TokenType.TEXT, TokenType.SPACE):
            self.parse_text()
        elif self.current_token.type == TokenType.NEWLINE:
            self.parse_newline()
        elif self.current_token.type == TokenType.SPECIAL_CHAR:
            self.parse_special_char()
        else:
            # Skip unhandled tokens
            self.advance()
        
    def parse(self) -> DocumentNode:
        """Parse token stream and generate AST."""
        while self.current_token:
            self.parse_token()
        
        return self.document
    
    def parse_command(self) -> None:
        """Parse LaTeX command."""
        if self.current_token is None:
            return
            
        command_name = self.current_token.value
        self.advance()  # Skip command token
        
        node = self.command_registry.create_command_node(command_name)
        
        if isinstance(node, SectionNode):
            self.process_section_node(node)
            return
        
        self.current_node.add_child(node)
        
        # Save current context and set new context
        prev_node = self.current_node
        self.current_node = node
        
        self.parse_command_arguments(node)
        
        # Special handling for specific commands
        if isinstance(node, FootnoteNode):
            self.process_footnote_node(node)
        elif isinstance(node, CiteNode):
            self.process_cite_node(node)
        
        # Restore previous context
        self.current_node = prev_node

    def parse_command_arguments(self, command_node: CommandNode) -> None:
        """Parse command arguments (optional and required)."""
        # Parse optional arguments
        while self.current_token and self.current_token.type == TokenType.BRACKET_OPEN:
            self.advance()  # Skip [
            option_group = self.parse_group_content(is_optional=True)
            command_node.options.append(option_group)
            self.expect(TokenType.BRACKET_CLOSE, "Expected ] to close optional argument")
            self.advance()  # Skip ]
        
        # Parse required arguments
        while self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()  # Skip {
            required_group = self.parse_group_content(is_optional=False)
            command_node.parameters.append(required_group)
            self.expect(TokenType.BRACE_CLOSE, "Expected } to close required argument")
            self.advance()  # Skip }

    def process_section_node(self, section_node: SectionNode) -> None:
        """Handle section command special processing."""
        self.parse_command_arguments(section_node)
        
        # Extract title text
        if section_node.parameters:
            section_node.title = section_node.parameters[0]
        # Extract short title (optional argument)
        if section_node.options:
            section_node.short_title = section_node.options[0]
        # Determine section level
        section_node.level = section_node._determine_level()
        # Determine if numbered
        section_node.numbered = '*' not in section_node.name
        
        parent = self.current_node
        while True:
            if isinstance(parent, SectionNode) and parent.level < section_node.level:
                break
            
            if parent == self.document:
                break
            
            parent = parent.parent
        
        if isinstance(parent, SectionNode):
            print(parent.level, section_node.level, section_node.title)
        
        # Add section to current parent
        parent.add_child(section_node)
        self.current_node = section_node
        self._start_new_paragraph()

    def process_footnote_node(self, footnote_node: FootnoteNode) -> None:
        """Handle footnote command special processing."""
        if footnote_node.parameters:
            footnote_node.content = footnote_node.parameters[0]
    
    def process_cite_node(self, cite_node: CiteNode) -> None:
        """Handle citation command special processing."""
        if cite_node.parameters:
            # Parse citation keys: could be comma-separated list
            keys_text = cite_node.parameters[0].get_text_content()
            cite_node.keys = [key.strip() for key in keys_text.split(',')]

    def parse_environment(self) -> None:
        """Parse LaTeX environment."""
        if self.current_token is None:
            return
            
        env_name = self.current_token.value
        is_begin = self.current_token.type == TokenType.ENV_BEGIN
        
        if is_begin:
            # Begin environment
            env_node = EnvironmentNode(env_name)
            
            if env_name == 'document':
                self.in_document_env = True
            
            self.current_node.add_child(env_node)
            self.current_node = env_node
        else:
            # End environment
            if isinstance(self.current_node, EnvironmentNode) and self.current_node.name == env_name:
                self.current_node = self.current_node.parent
        
        self.advance()
    
    def expect(self, token_type: TokenType, error_message: str = "Unexpected token") -> Token:
        """Verify current token type matches expected or raise error."""
        if not self.current_token or self.current_token.type != token_type:
            position = self.current_token.position if self.current_token else "end of file"
            raise ParserError(f"{error_message} at {position}")
        return self.current_token
    
    def parse_math(self, display: bool = False) -> None:
        """Parse math content."""
        if self.current_token is None:
            return
            
        math_content = self.current_token.value
        math_node = MathNode(math_content, display=display)
        self.current_node.add_child(math_node)
        self.advance()
    
    def parse_group_content(self, is_optional: bool = False) -> GroupNode:
        """
        Parse content within group (either {} or []).
        
        Returns:
            GroupNode containing all content within the group
        """
        group_node = GroupNode(is_optional=is_optional)
        
        # Save current context
        prev_node = self.current_node
        self.current_node = group_node
        
        # Parse all content within group
        depth = 1  # Current group depth
        while self.current_token and depth > 0:
            if self.current_token.type == TokenType.BRACE_OPEN:
                depth += 1
                self.advance()
                self.parse_group_content(is_optional=False)
            elif self.current_token.type == TokenType.BRACKET_OPEN:
                depth += 1
                self.advance()
                self.parse_group_content(is_optional=True)
            elif self.current_token.type == TokenType.BRACE_CLOSE:
                depth -= 1
                if depth == 0:
                    break
                self.advance()
            elif self.current_token.type == TokenType.BRACKET_CLOSE:
                depth -= 1
                if depth == 0:
                    break
                self.advance()
            else:
                self.parse_token()
        
        # Restore context
        self.current_node = prev_node
        
        return group_node
    
    def parse_group(self) -> None:
        """Parse curly brace group {}."""
        self.expect(TokenType.BRACE_OPEN)
        self.advance()  # Skip {
        
        group_node = GroupNode(is_optional=False)
        self.current_node.add_child(group_node)
        
        # Save current context
        prev_node = self.current_node
        self.current_node = group_node
        
        # Parse group content
        self.parse_group_content(is_optional=False)
        
        self.expect(TokenType.BRACE_CLOSE)
        self.advance()  # Skip }
        
        # Restore context
        self.current_node = prev_node
    
    def parse_option_group(self) -> None:
        """Parse square bracket group []."""
        self.expect(TokenType.BRACKET_OPEN)
        self.advance()  # Skip [
        
        option_node = GroupNode(is_optional=True)
        self.current_node.add_child(option_node)
        
        # Save current context
        prev_node = self.current_node
        self.current_node = option_node
        
        # Parse group content
        self.parse_group_content(is_optional=True)
        
        self.expect(TokenType.BRACKET_CLOSE)
        self.advance()  # Skip ]
        
        # Restore context
        self.current_node = prev_node
    
    def parse_paragraph(self) -> None:
        """Parse paragraph content."""
        paragraph = ParagraphNode()
        self.current_node.add_child(paragraph)
        
        prev_node = self.current_node
        self.current_node = paragraph
        
        # Collect until two consecutive newlines
        while self.current_token:
            if (self.current_token.type == TokenType.NEWLINE and 
                self.peek_next() and self.peek_next().type == TokenType.NEWLINE):
                self.advance()  # Skip first newline
                self.advance()  # Skip second newline
                break
            self.parse_token()
        
        self.current_node = prev_node
    
    def parse_text(self) -> None:
        """Parse text content."""
        if not self.text_merge:
            text_content = self.current_token.value if self.current_token else ""
            text_node = TextNode(text_content)
            self.current_node.add_child(text_node)
            self.advance()
            return
        
        # Merge mode implementation
        if self.current_token is None:
            return
            
        buffer = [self.current_token.value]
        start_pos = self.current_token.position
        token_ranges = [(
            start_pos[0], start_pos[1],
            start_pos[0], start_pos[1] + len(self.current_token.value)
        )]
        self.advance()

        # Merge adjacent TEXT/SPACE tokens
        while self.current_token and self.current_token.type in (
            TokenType.TEXT, 
            TokenType.SPACE
        ):
            buffer.append(self.current_token.value)
            token_ranges.append((
                self.current_token.position[0], self.current_token.position[1],
                self.current_token.position[0], self.current_token.position[1] + len(self.current_token.value)
            ))
            self.advance()

        # Create merged node
        merged_text = ''.join(buffer)
        text_node = TextNode(merged_text, source_ranges=token_ranges)
        text_node.position = start_pos
        self.current_node.add_child(text_node)
    
    def parse_special_char(self) -> None:
        """Parse special character."""
        if self.current_token is None:
            return
            
        char_node = SpecialCharNode(self.current_token.value)
        self.current_node.add_child(char_node)
        self.advance()
        
    def _is_document_level(self) -> bool:
        """Check if current position is at document level."""
        return isinstance(self.current_node, DocumentNode) or \
            any(isinstance(p, EnvironmentNode) for p in self.current_node.parents)
    
    def parse_newline(self) -> None:
        """Handle newline tokens."""
        if self.newline_mode == 'literal':
            if self.current_token:
                self.current_node.add_child(TextNode('\n'))
                self.advance()
            return

        # Check if in environment that preserves newlines
        in_special_env = False
        parent_node = self.current_node
        while isinstance(parent_node, EnvironmentNode) and \
            parent_node.name in ('tabular', 'matrix', 'array'):
                in_special_env = True
                break

        if in_special_env or self.newline_mode == 'compact':
            # Convert to space
            if self.current_token:
                self.current_node.add_child(TextNode(' '))
                self.advance()
            return

        # Smart mode handling
        count = 1
        next_token = self.peek_next()
        while next_token and next_token.type == TokenType.NEWLINE:
            count += 1
            self.advance()
            next_token = self.peek_next()
            
        if self.in_document_env:
            if count > 1:
                # Double newline - start new paragraph
                self._start_new_paragraph()
            elif len(self.current_node.children) > 0:
                # Single newline - convert to space
                space = TextNode(' ')
                space.is_newline_converted = True
                self.current_node.add_child(space)
        if self.current_token:
            self.advance()

    def _start_new_paragraph(self) -> None:
        """Start new paragraph node."""
        if isinstance(self.current_node, ParagraphNode):
            # End current paragraph
            self.current_node = self.current_node.parent
        
        new_para = ParagraphNode()
        self.current_node.add_child(new_para)
        self.current_node = new_para

    def peek_next(self) -> Optional[Token]:
        """Peek at next token without advancing."""
        if self.index + 1 < len(self.tokens):
            return self.tokens[self.index + 1]
        return None