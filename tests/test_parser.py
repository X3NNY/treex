import unittest
from treex.lexer import LaTeXLexer
from treex.parse import LaTeXParser
from treex.nodes import CommandNode, DocumentNode, ParagraphNode, SectionNode, EnvironmentNode, MathNode, TextNode

class TestLaTeXParser(unittest.TestCase):
    def test_parse_simple_document(self):
        latex_source = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Hello, world!
\end{document}
"""
        lexer = LaTeXLexer()
        tokens = lexer.tokenize(latex_source)
        parser = LaTeXParser(tokens)
        ast = parser.parse()
        
        self.assertIsInstance(ast, DocumentNode)
        self.assertEqual(len(ast.environments), 1)
        env = ast.environments[0]
        self.assertIsInstance(env, EnvironmentNode)
        self.assertEqual(env.name, "document")
        self.assertEqual(len(env.children), 1)
        self.assertIsInstance(env.children[0], SectionNode)
        self.assertEqual(env.children[0].title_text, "Introduction")
        self.assertIsInstance(env.children[0].children[0], ParagraphNode)
        self.assertEqual(env.children[0].children[0].get_text_content(), "Hello, world!")

    def test_parse_math(self):
        latex_source = r"$E=mc^2$ and $$\int_a^b f(x)dx$$"
        lexer = LaTeXLexer()
        tokens = lexer.tokenize(latex_source)
        parser = LaTeXParser(tokens)
        ast = parser.parse()
        
        self.assertEqual(len(ast.children), 5)
        self.assertIsInstance(ast.children[0], MathNode)
        self.assertEqual(ast.children[0].content, "E=mc^2")
        self.assertFalse(ast.children[0].display)
        self.assertIsInstance(ast.children[2], TextNode)
        self.assertEqual(ast.children[2].content, "and")
        self.assertIsInstance(ast.children[4], MathNode)
        self.assertEqual(ast.children[4].content, "\\int_a^b f(x)dx")
        self.assertTrue(ast.children[4].display)

    def test_parse_commands(self):
        latex_source = r"\textbf{Bold text} \emph{Italic text}"
        lexer = LaTeXLexer()
        tokens = lexer.tokenize(latex_source)
        self.assertEqual(len(tokens), 14)
        parser = LaTeXParser(tokens)
        ast = parser.parse()
        
        self.assertEqual(len(ast.children), 3)
        self.assertIsInstance(ast.children[0], CommandNode)
        self.assertEqual(ast.children[0].name, "textbf")
        self.assertEqual(len(ast.children[0].parameters[0].children), 3)
        self.assertEqual(ast.children[0].parameters[0].children[0].content, "Bold")
        self.assertIsInstance(ast.children[2], CommandNode)
        self.assertEqual(ast.children[2].name, "emph")
        self.assertEqual(ast.children[2].parameters[0].children[2].content, "text")

    def test_parse_sections(self):
        latex_source = r"""
\section{First}
\subsection{Second}
\subsubsection*{Third}
"""
        lexer = LaTeXLexer()
        tokens = lexer.tokenize(latex_source)
        parser = LaTeXParser(tokens)
        ast = parser.parse()
        
        sections = ast.sections
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].level, 1)
        self.assertEqual(sections[0].title_text, "First")
        self.assertEqual(sections[0].children[0].level, 2)
        self.assertEqual(sections[0].children[0].title_text, "Second")
        self.assertEqual(sections[0].children[0].children[0].level, 3)
        self.assertEqual(sections[0].children[0].children[0].title_text, "Third")

if __name__ == '__main__':
    unittest.main()