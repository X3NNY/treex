from __future__ import annotations
from typing import List, Optional, Dict, Tuple, TypeVar, Any, Union

T = TypeVar('T', bound='ASTNode')

class ASTNode:
    """Abstract Syntax Tree base node."""
    
    def __init__(self) -> None:
        self.children: List[ASTNode] = []
        self.parent: Optional[ASTNode] = None  # Parent node
        self.index: int = 0  # Position among siblings
    
    def add_child(self, node: ASTNode) -> None:
        """Add a child node."""
        node.parent = self
        node.index = len(self.children)
        self.children.append(node)
    
    def remove_childs(self, indexs: List[int]) -> int:
        """Remove childs by index"""
        new_childs = []
        for child in self.children:
            if child.index not in indexs:
                child.index = len(new_childs)
                new_childs.append(child)
        self.children = new_childs
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({len(self.children)})"
    
    def _find_all(self, node_type: type[T]) -> List[T]:
        """Recursively find all nodes of specified type."""
        results: List[T] = []
        for child in self.children:
            if isinstance(child, node_type):
                results.append(child)
            results.extend(child._find_all(node_type))
        return results
    
    def _find_env(self, name: Optional[str] = None) -> Optional[T]:
        res = None
        for child in self.children:
            if isinstance(child, EnvironmentNode):
                if name is None or child.name == name:
                    res = child
                    break
            res = child._find_env(name)
            
            if res:
                break
        
        return res
    
    def _find_cmd(self, name: Optional[str] = None) -> Optional[T]:
        res = None
        for child in self.children:
            if isinstance(child, CommandNode):
                if name is None or child.name == name:
                    res = child
                    break
            res = child._find_cmd(name)
            
            if res:
                break
        
        return res

    def to_tree(self, indent: int = 0, last: bool = True, prefix: str = '') -> str:
        """
        Convert node to tree text representation.
        
        Args:
            indent: Current indentation level
            last: Whether this is the last child of its parent
            prefix: Current prefix string
            
        Returns:
            Tree representation as string
        """
        # Current node representation
        result = prefix
        result += "└── " if last else "├── "
        result += self._node_description()
        result += "\n"
        
        # Child nodes processing
        child_prefix = prefix + ("    " if last else "│   ")
        child_count = len(self.children)
        for i, child in enumerate(self.children):
            is_last = i == child_count - 1
            result += child.to_tree(indent + 1, is_last, child_prefix)
        
        return result
    
    def _node_description(self) -> str:
        """Node description, can be overridden by subclasses."""
        return self.__class__.__name__
    
    def get_text_content(self): ...


class DocumentNode(ASTNode):
    """Document root node."""
    
    @property
    def sections(self) -> List[SectionNode]:
        return [node for node in self.children if isinstance(node, SectionNode)]
    
    @property
    def environments(self) -> List[EnvironmentNode]:
        return self._find_all(EnvironmentNode)
    
    @property
    def commands(self) -> List[CommandNode]:
        return self._find_all(CommandNode)
    
    @property
    def abstract(self) -> Optional[EnvironmentNode]:
        return self._find_env('abstract')
    
    @property
    def title(self) -> Optional[CommandNode]:
        return self._find_cmd('title')
    
    def _node_description(self) -> str:
        return "Document"


class EnvironmentNode(ASTNode):
    """Environment node (e.g., \\begin{env}...\\end{env})."""
    
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name
        self.options: List[Any] = []
        self.parameters: List[Any] = []
    
    
    def get_text_content(self) -> str:
        """Get the text content of the environment, including options and parameters.
    
        Returns:
            String representation of the environment content in LaTeX format.
        """
        options_str = ""
        if self.options:
            options_str = "".join(
                f"[{option.get_text_content()}]"
                for option in self.options
            )
        
        params_str = "".join(
            f"{{{param.get_text_content()}}}"
            for param in self.parameters
        )
        
        body_content = "".join(
            child.get_text_content() 
            for child in self.children
            if hasattr(child, 'get_text_content')
        )
        
        return f"\\begin{{{self.name}}}{options_str}{params_str}{body_content}\\end{{{self.name}}}"
    
    def _node_description(self) -> str:
        return f"Environment: \\{self.name}"


class CommandNode(ASTNode):
    """Command node (e.g., \\command)."""
    
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name
        self.options: List[Any] = []
        self.parameters: List[Any] = []
        
    def get_text_content(self) -> str:
        """Get text content from command parameters."""
        return ''.join(param.get_text_content() for param in self.parameters)
    
    def get_optional_args(self) -> List[Any]:
        """Get all optional arguments."""
        return [arg for arg in self.options if arg.is_optional]
    
    def get_required_args(self) -> List[Any]:
        """Get all required arguments."""
        return [arg for arg in self.parameters if not arg.is_optional]
    
    def is_section(self) -> bool:
        return self.name.startswith(('section', 'subsection', 'subsubsection'))
    
    def is_footnote(self) -> bool:
        return self.name == 'footnote'
    
    def is_cite(self) -> bool:
        return self.name in ('cite', 'citep', 'citet')

    def _node_description(self) -> str:
        return f"Command: \\{self.name}"


class SectionNode(CommandNode):
    """Specialized node for section commands."""
    
    def __init__(self, name: str, title: Optional[str] = None, level: Optional[int] = None) -> None:
        super().__init__(name)
        self.special_type: str = 'section'
        self.title: Optional[str] = title  # Title content node
        self.level: int = level or self._determine_level()
        self.label: Optional[str] = None  # Associated label
        self.numbered: bool = '*' not in name  # Whether section is numbered
    
    def _determine_level(self) -> int:
        """Determine section level based on command name."""
        levels: Dict[str, int] = {
            'section': 1,
            'subsection': 2,
            'subsubsection': 3,
            'paragraph': 4,
            'subparagraph': 5
        }
        base_name = self.name.rstrip('*')
        return levels.get(base_name, 1)

    @property
    def title_text(self) -> str:
        """Get title text."""
        if self.parameters:
            return self.parameters[0].get_text_content()
        return ""
    
    @property
    def short_title_text(self) -> str:
        """Get short title text (optional argument)."""
        if self.options:
            return self.options[0].get_text_content()
        return ""
    
    def _node_description(self) -> str:
        level_names = {1: "Section", 2: "Subsection", 3: "Subsubsection"}
        level_name = level_names.get(self.level, f"Level {self.level}")
        return f"{level_name}: {self.title_text}"


class FootnoteNode(CommandNode):
    """Specialized node for footnotes."""
    
    def __init__(self, content: Optional[str] = None) -> None:
        super().__init__('footnote')
        self.special_type: str = 'footnote'
        self.content: Optional[str] = content  # Footnote content


class CiteNode(CommandNode):
    """Specialized node for citations."""
    
    def __init__(self, name: str, keys: Optional[List[str]] = None) -> None:
        super().__init__(name)
        self.special_type: str = 'cite'
        self.keys: List[str] = keys or []  # Citation keys
        self.citations: List[Any] = []  # Associated bibliography items


class ParagraphNode(ASTNode):
    """Node representing LaTeX paragraphs."""
    
    def __init__(self) -> None:
        super().__init__()
        self.content: Optional[str] = None
        
    @property
    def text_content(self):
        if self.content is None:
            return self.get_text_content()
        return self.content
        
    def get_text_content(self, update: bool = False) -> str:
        if not self.content or update:
            texts = [txt for child in self.children if (txt := child.get_text_content()) != ' ']
            self.content = ' '.join(texts)
        return self.content


class TextNode(ASTNode):
    """Node representing plain text."""
    
    def __init__(self, content: str, source_ranges: Optional[List[Tuple[int, int, int, int]]] = None) -> None:
        super().__init__()
        self.content: str = content
        # source_ranges format: [(start_line, start_col, end_line, end_col), ...]
        self.source_ranges: List[Tuple[int, int, int, int]] = source_ranges or []
    
    def get_original_positions(self) -> List[Tuple[int, int]]:
        """Get original positions for each character before merging."""
        if not self.source_ranges:
            return [self.position] * len(self.content)
        
        positions = []
        for (start_line, start_col, end_line, end_col), char in zip(
            self.source_ranges, self.content
        ):
            positions.append((start_line, start_col))
        return positions
    
    def __repr__(self) -> str:
        if self.source_ranges:
            return f"TextNode(merged, len={len(self.content)}, chunks={len(self.source_ranges)})"
        return f"TextNode('{self.content}')"
    
    def get_text_content(self) -> str:
        return self.content
    
    def _node_description(self) -> str:
        content = self.content.replace('\n', '\\n')
        if len(content) > 20:
            return f"Text: '{content[:20]}...'"
        return f"Text: '{content}'"


class MathNode(ASTNode):
    """Node representing math content."""
    
    def __init__(self, content: str, display: bool = False) -> None:
        super().__init__()
        self.content: str = content
        self.display: bool = display  # Whether display math (vs inline)
    
    def __repr__(self) -> str:
        mode = "display" if self.display else "inline"
        return f"MathNode({mode}, '{self.content}')"

    def _node_description(self) -> str:
        mode = "Display" if self.display else "Inline"
        content = self.content.replace('\n', '\\n')
        if len(content) > 20:
            return f"Math ({mode}): '{content[:20]}...'"
        return f"Math ({mode}): '{content}'"

    def get_text_content(self, pack: bool = True) -> str:
        if pack:
            if self.display:
                text = f'$${self.content}$$'
            else:
                text = f'${self.content}$'
            
            return text
        
        return self.content
        

class GroupNode(ASTNode):
    """Group node (represents content in {} or [])."""
    
    def __init__(self, is_optional: bool = False) -> None:
        super().__init__()
        self.is_optional: bool = is_optional  # True=[], False={}
    
    def get_text_content(self) -> str:
        """Get text content within the group."""
        return ''.join(child.get_text_content() for child in self.children)
    
    def __repr__(self) -> str:
        return f"GroupNode(optional={self.is_optional}, children={len(self.children)})"

    def _node_description(self) -> str:
        return f"Group ({'optional' if self.is_optional else 'required'})"


class SpecialCharNode(ASTNode):
    """Node representing special characters."""
    
    def __init__(self, char: str) -> None:
        super().__init__()
        self.char: str = char
    
    def __repr__(self) -> str:
        return f"SpecialCharNode('{self.char}')"