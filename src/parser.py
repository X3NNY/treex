from typing import List, Literal
from .errors import ParserError
from .registry import CommandRegistry
from .tokens import TokenType, Token
from .nodes import CiteNode, DocumentNode, FootnoteNode, GroupNode, MathNode, ParagraphNode, SectionNode, EnvironmentNode, CommandNode, SpecialCharNode, TextNode

class LaTeXParser:
    """LaTeX 语法分析器，将Token流转换为抽象语法树（AST）"""
    
    def __init__(self,
                tokens: List[Token],
                text_merge: bool = False,
                newline_mode: Literal['default', 'literal', 'compact'] = 'default'):
        self.tokens = tokens
        self.current_token = None
        self.index = -1
        self.advance()  # 初始化当前token
        self.document = DocumentNode()
        self.current_node = self.document
        
        self.in_document_env = False
        self.text_merge = text_merge
        self.newline_mode = newline_mode
        
        self.command_registry = CommandRegistry()
        self.section_stack = []
        
        self._register_special_commands()
    
    def _register_special_commands(self):
        """注册特殊命令处理器"""
        self.command_registry.register_handler('section', SectionNode)
        self.command_registry.register_handler('subsection', SectionNode)
        self.command_registry.register_handler('subsubsection', SectionNode)
        self.command_registry.register_handler('footnote', FootnoteNode)
        self.command_registry.register_handler('cite', CiteNode)
        self.command_registry.register_handler('citep', CiteNode)
        self.command_registry.register_handler('citet', CiteNode)
    
    def advance(self):
        """前进到下一个token"""
        self.index += 1
        if self.index < len(self.tokens):
            self.current_token = self.tokens[self.index]
        else:
            self.current_token = None
        return self.current_token
    
    def parse_token(self):
        if self.current_token.type == TokenType.COMMAND:
            self.parse_command()
        elif self.current_token.type == TokenType.ENV_BEGIN or self.current_token.type == TokenType.ENV_END:
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
            # 跳过不处理的token
            self.advance()
        
    def parse(self):
        """解析Token流，生成AST"""
        while self.current_token:
            self.parse_token()
        
        return self.document
    
    def parse_command(self):
        """解析命令"""
        command_name = self.current_token.value
        self.advance()  # 跳过命令token
        
        node = self.command_registry.create_command_node(command_name)
        
        if isinstance(node, SectionNode):
            self.process_section_node(node)
            return
        
        self.current_node.add_child(node)
        
        # 保存当前节点并设置新上下文
        prev_node = self.current_node
        self.current_node = node
        
        self.parse_command_arguments(node)
        
        # 特殊处理：为特定命令提取信息
        if isinstance(node, FootnoteNode):
            self.process_footnote_node(node)
        elif isinstance(node, CiteNode):
            self.process_cite_node(node)
        
        # 恢复之前的节点
        self.current_node = prev_node

    def parse_command_arguments(self, command_node: CommandNode):
        """解析命令参数（可选和必选）"""
        # 解析可选参数
        while self.current_token and self.current_token.type == TokenType.BRACKET_OPEN:
            self.advance()  # 跳过 [
            option_group = self.parse_group_content(is_optional=True)
            command_node.options.append(option_group)
            self.expect(TokenType.BRACKET_CLOSE, "Expected ] to close optional argument")
            self.advance()  # 跳过 ]
        
        # 解析必选参数
        while self.current_token and self.current_token.type == TokenType.BRACE_OPEN:
            self.advance()  # 跳过 {
            required_group = self.parse_group_content(is_optional=False)
            command_node.parameters.append(required_group)
            self.expect(TokenType.BRACE_CLOSE, "Expected } to close required argument")
            self.advance()  # 跳过 }

    def process_section_node(self, section_node: SectionNode):
        """解析章节命令"""
        """处理章节节点的特殊逻辑"""
        
        # 解析节标题参数
        self.parse_command_arguments(section_node)
        
        # 提取标题文本
        if section_node.parameters:
            section_node.title = section_node.parameters[0]
        # 提取短标题（可选参数）
        if section_node.options:
            section_node.short_title = section_node.options[0]
        # 确定章节层级
        section_node.level = section_node._determine_level()
        # 确定是否有编号
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
        
        # 将节添加到当前父节点
        parent.add_child(section_node)
        self.current_node = section_node
        self._start_new_paragraph()

    def process_footnote_node(self, footnote_node: FootnoteNode):
        """处理脚注节点的特殊逻辑"""
        if footnote_node.parameters:
            footnote_node.content = footnote_node.parameters[0]
    
    def process_cite_node(self, cite_node: CiteNode):
        """处理引用节点的特殊逻辑"""
        if cite_node.parameters:
            # 解析引用键：可能是逗号分隔的列表
            keys_text = cite_node.parameters[0].get_text_content()
            cite_node.keys = [key.strip() for key in keys_text.split(',')]

    def parse_environment(self):
        """解析环境"""
        env_name = self.current_token.value
        is_begin = self.current_token.type == TokenType.ENV_BEGIN
        # env_name = env_value.split("{")[1].split("}")[0]
        
        if is_begin:
            # 开始环境
            env_node = EnvironmentNode(env_name)
            
            if env_name == 'document':
                self.in_document_env = True
            
            self.current_node.add_child(env_node)
            self.current_node = env_node
        else:
            # 结束环境
            if isinstance(self.current_node, EnvironmentNode) and self.current_node.name == env_name:
                self.current_node = self.current_node.parent
        
        self.advance()
    
    def expect(self, token_type, error_message="Unexpected token"):
        """检查当前token类型，如果不匹配则报错"""
        if not self.current_token or self.current_token.type != token_type:
            position = self.current_token.position if self.current_token else "end of file"
            raise ParserError(f"{error_message} at {position}")
        return self.current_token
    
    def parse_math(self, display=False):
        """解析数学内容"""
        math_content = self.current_token.value
        math_node = MathNode(math_content, display=display)
        self.current_node.add_child(math_node)
        self.advance()
    
    def parse_group_content(self, is_optional=False):
        """
        解析分组内容（{}或[]中的内容）
        返回一个GroupNode，包含分组内的所有内容
        """
        group_node = GroupNode(is_optional=is_optional)
        
        # 保存当前上下文
        prev_node = self.current_node
        self.current_node = group_node
        
        # 解析分组内的所有内容
        depth = 1  # 当前分组深度
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
                # 解析分组内的各种元素
                # if self.current_token.type == TokenType.COMMAND:
                #     self.parse_command()
                # elif self.current_token.type == TokenType.ENV_BEGIN or self.current_token.type == TokenType.ENV_END:
                #     self.parse_environment()
                # elif self.current_token.type in (TokenType.TEXT, TokenType.SPACE, TokenType.NEWLINE):
                #     self.parse_text()
                # elif self.current_token.type == TokenType.SPECIAL_CHAR:
                #     self.parse_special_char()
                # elif self.current_token.type == TokenType.MATH_INLINE:
                #     self.parse_math()
                # elif self.current_token.type == TokenType.MATH_FORMULA:
                #     self.parse_math(display=True)
                # else:
                #     self.advance()
                    
        
        # 恢复上下文
        self.current_node = prev_node
        
        return group_node
    
    def parse_group(self):
        """解析花括号分组 {}"""
        self.expect(TokenType.BRACE_OPEN)
        self.advance()  # 跳过 {
        
        group_node = GroupNode(is_optional=False)
        self.current_node.add_child(group_node)
        
        # 保存当前上下文
        prev_node = self.current_node
        self.current_node = group_node
        
        # 解析分组内容
        self.parse_group_content(is_optional=False)
        
        self.expect(TokenType.BRACE_CLOSE)
        self.advance()  # 跳过 }
        
        # 恢复上下文
        self.current_node = prev_node
    
    def parse_option_group(self):
        """解析方括号分组 []"""
        self.expect(TokenType.BRACKET_OPEN)
        self.advance()  # 跳过 [
        
        option_node = GroupNode(is_optional=True)
        self.current_node.add_child(option_node)
        
        # 保存当前上下文
        prev_node = self.current_node
        self.current_node = option_node
        
        # 解析分组内容
        self.parse_group_content(is_optional=True)
        
        self.expect(TokenType.BRACKET_CLOSE)
        self.advance()  # 跳过 ]
        
        # 恢复上下文
        self.current_node = prev_node
    
    def parse_paragraph(self):
        paragraph = ParagraphNode()  # 新增的段落节点类型
        self.current_node.add_child(paragraph)
        
        prev_node = self.current_node
        self.current_node = paragraph
        
        # 收集直到遇到两个连续换行
        while self.current_token:
            if (self.current_token.type == TokenType.NEWLINE and 
                self.peek_next().type == TokenType.NEWLINE):
                self.advance()  # 跳过第一个换行
                self.advance()  # 跳过第二个换行
                break
            self.parse_token()  # 正常解析内容
        
        self.current_node = prev_node
    
    def parse_text(self):
        """解析文本内容"""
        if not self.text_merge:
            text_content = self.current_token.value
            text_node = TextNode(text_content)
            self.current_node.add_child(text_node)
            self.advance()
            return
        
        # 合并模式实现
        buffer = [self.current_token.value]
        start_pos = self.current_token.position
        token_ranges = [(
            start_pos[0], start_pos[1],
            start_pos[0], start_pos[1] + len(self.current_token.value)
        )]
        self.advance()

        # 合并后续相邻的TEXT/SPACE
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

        # 创建合并节点
        merged_text = ''.join(buffer)
        text_node = TextNode(merged_text, source_ranges=token_ranges)
        text_node.position = start_pos
        self.current_node.add_child(text_node)
    
    def parse_special_char(self):
        """解析特殊字符"""
        char_node = SpecialCharNode(self.current_token.value)
        self.current_node.add_child(char_node)
        self.advance()
        
    def _is_document_level(self):
        return isinstance(self.current_node, DocumentNode) or \
            any(isinstance(p, EnvironmentNode) for p in self.current_node.parents)
    
    def parse_newline(self):
        """统一处理换行符逻辑"""
        if self.newline_mode == 'literal':
            self.current_node.add_child(TextNode('\n'))
            self.advance()
            return

        # 检查是否在需要保留换行的环境中
        in_special_env = False
        parent_node = self.current_node
        while isinstance(parent_node, EnvironmentNode) and \
            parent_node.name in ('tabular', 'matrix', 'array'):
                in_special_env = True
                break

        if in_special_env or self.newline_mode == 'compact':
            # 直接转为空格
            self.current_node.add_child(TextNode(' '))
            self.advance()
            return

        # 智能模式处理
        count = 1
        next_token = self.peek_next()
        while next_token and next_token.type == TokenType.NEWLINE:
            count += 1
            self.advance()
            next_token = self.peek_next()
            
        if self.in_document_env:
            if count > 1:
                # 双换行-创建新段落
                self._start_new_paragraph()
            elif len(self.current_node.children) > 0:
                # 单换行-转为空格
                space = TextNode(' ')
                space.is_newline_converted = True
                self.current_node.add_child(space)
        self.advance()

    def _start_new_paragraph(self):
        """创建新段落节点"""
        if isinstance(self.current_node, ParagraphNode):
            # 结束当前段落
            self.current_node = self.current_node.parent
        
        new_para = ParagraphNode()
        self.current_node.add_child(new_para)
        self.current_node = new_para

    def peek_next(self):
        """查看下一个token但不移动指针"""
        if self.index + 1 < len(self.tokens):
            return self.tokens[self.index + 1]
        return None