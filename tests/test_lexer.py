import unittest
from treex.lexer import LaTeXLexer
from treex.tokens import TokenType, Token

class TestLaTeXLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = LaTeXLexer()

    def test_simple_command(self):
        tokens = self.lexer.tokenize(r"\section")
        self.assertEqual(len(tokens), 3)  # COMMAND, NEWLINE, EOF
        self.assertEqual(tokens[0].type, TokenType.COMMAND)
        self.assertEqual(tokens[0].value, r"section")

    def test_command_with_braces(self):
        tokens = self.lexer.tokenize(r"\section{Introduction}")
        expected_types = [
            TokenType.COMMAND,    # \section
            TokenType.BRACE_OPEN, # {
            TokenType.TEXT,       # Introduction
            TokenType.BRACE_CLOSE,# }
            TokenType.NEWLINE,    # \n
            TokenType.EOF         # EOF
        ]
        self.assertEqual(len(tokens), len(expected_types))
        for token, expected_type in zip(tokens, expected_types):
            self.assertEqual(token.type, expected_type)

    def test_math_inline(self):
        tokens = self.lexer.tokenize(r"$E=mc^2$")
        self.assertEqual(tokens[0].type, TokenType.MATH_INLINE)
        self.assertEqual(tokens[0].value, "E=mc^2")

    def test_math_display(self):
        tokens = self.lexer.tokenize(r"$$ \int_a^b f(x)dx $$")
        self.assertEqual(tokens[0].type, TokenType.MATH_FORMULA)
        self.assertEqual(tokens[0].value, " \\int_a^b f(x)dx ")

    def test_environment(self):
        tokens = self.lexer.tokenize(r"\begin{document}\end{document}")
        self.assertEqual(len(tokens), 4)  # ENV_BEGIN, ENV_END, NEW_LINE, EOF
        self.assertEqual(tokens[0].type, TokenType.ENV_BEGIN)
        self.assertEqual(tokens[0].value, r"document")
        self.assertEqual(tokens[1].type, TokenType.ENV_END)
        self.assertEqual(tokens[1].value, r"document")

    def test_escape_sequence(self):
        tokens = self.lexer.tokenize(r"\$ \%")
        self.assertEqual(tokens[0].type, TokenType.ESCAPE_SEQUENCE)
        self.assertEqual(tokens[0].value, "$")
        self.assertEqual(tokens[2].type, TokenType.ESCAPE_SEQUENCE)
        self.assertEqual(tokens[2].value, "%")

    def test_comment(self):
        tokens = self.lexer.tokenize(r"% This is a comment\nHello")
        self.assertEqual(tokens[0].type, TokenType.COMMENT)
        self.assertTrue(tokens[0].value.startswith("% This is a comment"))

    def test_special_characters(self):
        tokens = self.lexer.tokenize(r"&_^~")
        expected_types = [
            TokenType.SPECIAL_CHAR,
            TokenType.SPECIAL_CHAR,
            TokenType.SPECIAL_CHAR,
            TokenType.SPECIAL_CHAR,
            TokenType.NEWLINE,
            TokenType.EOF
        ]
        self.assertEqual(len(tokens), len(expected_types))
        for token, expected_type in zip(tokens, expected_types):
            self.assertEqual(token.type, expected_type)

    def test_parameter_marker(self):
        tokens = self.lexer.tokenize(r"#1 #2")
        self.assertEqual(tokens[0].type, TokenType.PARAM_MARKER)
        self.assertEqual(tokens[0].value, "#1")
        self.assertEqual(tokens[2].type, TokenType.PARAM_MARKER)
        self.assertEqual(tokens[2].value, "#2")

    def test_complex_math_escape(self):
        tokens = self.lexer.tokenize(r"$ 1+1=\\\\$ \$")
        self.assertEqual(tokens[0].type, TokenType.MATH_INLINE)
        self.assertEqual(tokens[0].value, r" 1+1=\\\\")

    def test_full_document(self):
        latex_source = r"""
\documentclass{article}
\begin{document}
\section{Introduction}
Hello, $E=mc^2$ and $\alpha$
\end{document}
"""
        tokens = self.lexer.tokenize(latex_source)
        self.assertGreater(len(tokens), 10)
        self.assertEqual(tokens[1].type, TokenType.COMMAND)
        self.assertEqual(tokens[1].value, "documentclass")
        self.assertEqual(tokens[3].type, TokenType.TEXT)
        self.assertEqual(tokens[3].value, "article")
        self.assertEqual(tokens[6].type, TokenType.ENV_BEGIN)
        self.assertEqual(tokens[6].value, r"document")

if __name__ == '__main__':
    unittest.main()