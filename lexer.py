import re
import sys

class Token:
    def __init__(self, type, value, line=None, column=None):
        self.type = type
        self.value = value
        self.line = line
        self.column = column
    def __str__(self):
        return f'Token({self.type}, {repr(self.value)}, L{self.line}:C{self.column})'
    def __repr__(self):
        return self.__str__()

T_PROGRAM = 'PROGRAM'
T_VAR = 'VAR'
T_CONST = 'CONST'
T_PROCEDURE = 'PROCEDURE'
T_BEGIN = 'BEGIN'
T_END = 'END'
T_INTEGER = 'INTEGER'
T_REAL = 'REAL'
T_IF = 'IF'
T_THEN = 'THEN'
T_ELSE = 'ELSE'
T_WHILE = 'WHILE'
T_DO = 'DO'
T_READ = 'READ'
T_WRITE = 'WRITE'
T_DIV = 'DIV'
T_AND = 'AND'
T_OR = 'OR'
T_NOT = 'NOT'
T_PLUS = 'PLUS'
T_MINUS = 'MINUS'
T_MUL = 'MUL'
T_REAL_DIV = 'REAL_DIV'
T_ASSIGN = 'ASSIGN'
T_SEMI = 'SEMI'
T_DOT = 'DOT'
T_COLON = 'COLON'
T_COMMA = 'COMMA'
T_LPAREN = 'LPAREN'
T_RPAREN = 'RPAREN'
T_LBRACE = 'LBRACE'
T_RBRACE = 'RBRACE'
T_EQUAL = 'EQUAL'
T_NOT_EQUAL = 'NOT_EQUAL'
T_LESS_THAN = 'LESS_THAN'
T_LESS_EQUAL = 'LESS_EQUAL'
T_GREATER_THAN = 'GREATER_THAN'
T_GREATER_EQUAL = 'GREATER_EQUAL'
T_ID = 'ID'
T_INTEGER_CONST = 'INTEGER_CONST'
T_REAL_CONST = 'REAL_CONST'
T_STRING_LITERAL = 'STRING_LITERAL'
T_EOF = 'EOF'

class LexerError(Exception):
    pass

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.current_char = self.text[self.pos] if self.pos < len(self.text) else None
        self.line = 1
        self.column = 1
        self.reserved_keywords = {
            'PROGRAM': Token(T_PROGRAM, 'PROGRAM'), 'VAR': Token(T_VAR, 'VAR'),
            'CONST': Token(T_CONST, 'CONST'), 'PROCEDURE': Token(T_PROCEDURE, 'PROCEDURE'),
            'BEGIN': Token(T_BEGIN, 'BEGIN'), 'END': Token(T_END, 'END'),
            'INTEGER': Token(T_INTEGER, 'INTEGER'), 'REAL': Token(T_REAL, 'REAL'),
            'DIV': Token(T_DIV, 'DIV'), 'IF': Token(T_IF, 'IF'),
            'THEN': Token(T_THEN, 'THEN'), 'ELSE': Token(T_ELSE, 'ELSE'),
            'WHILE': Token(T_WHILE, 'WHILE'), 'DO': Token(T_DO, 'DO'),
            'READ': Token(T_READ, 'READ'), 'WRITE': Token(T_WRITE, 'WRITE'),
            'AND': Token(T_AND, 'AND'), 'OR': Token(T_OR, 'OR'), 'NOT': Token(T_NOT, 'NOT')
        }

    def error(self, message=""):
        raise LexerError(f'Lexer error on L{self.line}:C{self.column}. {message}')

    def advance(self):
        if self.current_char == '\n':
            self.line += 1
            self.column = 0
        self.pos += 1
        if self.pos >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.pos]
            self.column += 1

    def peek_char(self):
        peek_pos = self.pos + 1
        if peek_pos >= len(self.text):
            return None
        else:
            return self.text[peek_pos]

    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def skip_single_line_comment(self):
        if self.current_char == '/' and self.peek_char() == '/':
            self.advance()
            self.advance()
            while self.current_char is not None and self.current_char != '\n':
                self.advance()
            return True
        return False

    def skip_pascal_comment(self):
        if self.current_char == '{':
            start_line, start_col = self.line, self.column
            self.advance()
            while self.current_char != '}':
                if self.current_char is None:
                    raise LexerError(f'Unterminated comment starting at L{start_line}:C{start_col}.')
                self.advance()
            self.advance()
            return True
        return False

    def number(self):
        result_str = ''
        start_line, start_col = self.line, self.column
        is_real = False
        while self.current_char is not None and self.current_char.isdigit():
            result_str += self.current_char
            self.advance()
        if self.current_char == '.':
            if self.peek_char() and self.peek_char().isdigit():
                result_str += '.'
                self.advance()
                is_real = True
                while self.current_char is not None and self.current_char.isdigit():
                    result_str += self.current_char
                    self.advance()
            elif not is_real and result_str:
                return Token(T_INTEGER_CONST, int(result_str), start_line, start_col)

        if is_real:
            if not result_str.split('.')[-1]:
                self.error(f"Invalid real number format near '{result_str}' - missing digits after decimal point.")
            return Token(T_REAL_CONST, float(result_str), start_line, start_col)
        elif result_str:
            return Token(T_INTEGER_CONST, int(result_str), start_line, start_col)
        else:
            self.error("Internal lexer error: number() called unexpectedly.")
            return None


    def _id(self):
        result = ''
        start_line, start_col = self.line, self.column
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        token_info = self.reserved_keywords.get(result.upper())
        if token_info:
            return Token(token_info.type, token_info.value, start_line, start_col)
        else:
            return Token(T_ID, result, start_line, start_col)

    def string_literal(self):
        result_chars = []
        start_line, start_col = self.line, self.column
        self.advance()
        while self.current_char is not None and self.current_char != "'":
            if self.current_char == '\\':
                self.advance()
                if self.current_char is None:
                    self.error(f"Unterminated escape sequence in string literal starting at L{start_line}:C{start_col}")
                    break
                if self.current_char == 'n':
                    result_chars.append('\n')
                elif self.current_char == 't':
                    result_chars.append('\t')
                elif self.current_char == '\\':
                    result_chars.append('\\')
                elif self.current_char == "'":
                    result_chars.append("'")
                else:
                    result_chars.append('\\')
                    result_chars.append(self.current_char)
                self.advance()
            elif self.current_char == "'" and self.peek_char() == "'":
                result_chars.append("'")
                self.advance()
                self.advance()
            else:
                result_chars.append(self.current_char)
                self.advance()
        if self.current_char is None:
            self.error(f"Unterminated string literal starting at L{start_line}:C{start_col}")
        else:
            self.advance()
        return Token(T_STRING_LITERAL, "".join(result_chars), start_line, start_col)

    def _get_token_logic(self):
        while self.current_char is not None:
            start_skipping_pos = self.pos
            if self.current_char.isspace():
                self.skip_whitespace()
                if self.pos == start_skipping_pos and self.current_char is not None: self.advance()
                continue
            if self.current_char == '{':
                if self.skip_pascal_comment():
                    if self.pos == start_skipping_pos and self.current_char is not None: self.advance()
                    continue
            if self.current_char == '/':
                if self.skip_single_line_comment():
                    if self.pos == start_skipping_pos and self.current_char is not None: self.advance()
                    continue
            break

        if self.current_char is None:
            return Token(T_EOF, None, self.line, self.column)

        token_start_line, token_start_col = self.line, self.column

        if self.current_char.isalpha() or self.current_char == '_':
            return self._id()
        if self.current_char.isdigit():
            return self.number()
        if self.current_char == "'":
            return self.string_literal()

        ch = self.current_char
        ch_peek = self.peek_char()

        if ch == ':' and ch_peek == '=':
            self.advance(); self.advance()
            return Token(T_ASSIGN, ':=', token_start_line, token_start_col)
        if ch == '<' and ch_peek == '>':
            self.advance(); self.advance()
            return Token(T_NOT_EQUAL, '<>', token_start_line, token_start_col)
        if ch == '<' and ch_peek == '=':
            self.advance(); self.advance()
            return Token(T_LESS_EQUAL, '<=', token_start_line, token_start_col)
        if ch == '>' and ch_peek == '=':
            self.advance(); self.advance()
            return Token(T_GREATER_EQUAL, '>=', token_start_line, token_start_col)

        token_map = {
            '+': T_PLUS, '-': T_MINUS, '*': T_MUL, '/': T_REAL_DIV,
            ';': T_SEMI, '.': T_DOT, ':': T_COLON, ',': T_COMMA,
            '(': T_LPAREN, ')': T_RPAREN, '=': T_EQUAL,
            '<': T_LESS_THAN, '>': T_GREATER_THAN
        }
        if ch in token_map:
            token_type = token_map[ch]
            self.advance()
            return Token(token_type, ch, token_start_line, token_start_col)

        self.error(f"Unexpected character '{self.current_char}'")
        return None

    def get_next_token(self):
        return self._get_token_logic()

    def peek_token(self):
        temp_lexer = Lexer(self.text)
        temp_lexer.pos = self.pos
        temp_lexer.current_char = self.current_char
        temp_lexer.line = self.line
        temp_lexer.column = self.column
        token = temp_lexer._get_token_logic()
        return token