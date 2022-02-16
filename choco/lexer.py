from io import TextIOBase
from enum import Enum, auto
from dataclasses import dataclass

import io

from typing import Any, List, Union, Optional, Tuple


class TokenKind(Enum):
    def __hash__(self):
        return 1    

    # RM new keywords
    REGISTERS_SYMBOL = auto()
    HALT = auto()
    DECJZ = auto() #decjz
    INC = auto()

    EOF = auto()
    NEWLINE = auto()
    COLON = auto()

    IDENTIFIER = auto()
    MINUS = auto()
    INTEGER = auto()
    REGISTER = auto()

@dataclass
class Token:
    kind: TokenKind
    value: Any = None
    line : int = -1
    col : int = -1
    length : int = 0

    '''
    line and column of the starting character
    index starts from 0
    '''    
    def __repr__(self) -> str:
        return self.kind.name + (
            (":" + str(self.value)) if self.value is not None else "")
    def __hash__(self):
        return hash(self.__repr__())

class StrLnCol(str):
    line : int
    col : int
    def __new__(cls, value, line, col):    
        obj = str.__new__(cls, value)
        obj.line = line
        obj.col = col
        return obj    
    def __add__(self, other):
        obj = StrLnCol(str(self) + str(other), self.line, self.col)
        return obj    
        
class Scanner:
    line : int = 0
    col : int = 0

    file_content_by_line = []

    def __init__(self, stream: TextIOBase):
        """ Create a new scanner.

        The scanner's input is a stream derived from a string or a file.

        # Lexing a string
        s = io.StringIO("1 + 2")
        Scanner(s)

        # Lexing a file
        s = open("file.choc")
        Scanner(s)

        :param stream: The stream of characters to be lexed.
        """

        self.file_content_by_line = stream.readlines()
        self.stream = io.StringIO(''.join(self.file_content_by_line))
        # self.stream: TextIOBase = stream
        # self.file_content_by_line = open(stream.name).readlines()
        self.buffer: Optional[StrLnCol] = None  # A buffer of one character.

    def peek(self) -> StrLnCol:
        """ Return the next character from input without consuming it.

        :return: The next character in the input stream or None at the end of the stream.
        """
        # A buffer of one character is used to store the last scanned character.
        # If the buffer is empty, it is filled with the next character from the input.
        if not self.buffer:
            self.buffer = self.consume()
        return self.buffer

    def consume(self) -> StrLnCol:
        """ Consume and return the next character from input.

        :return: The next character in the input stream or None at the end of the stream.
        """
        # If the buffer is full, we empty the buffer and return the character it contains.
        if self.buffer:
            c = self.buffer
            self.buffer = None
            return c

        c = self.stream.read(1)
        line_ret = self.line
        col_ret = self.col
        
        # TODO: RM ME
        # print(c + " " + str(self.line)+":"+str(self.col))
        
        # READ FILE TWICE, DETELE THIS
        # self.file_content[self.line].append(c)
        
        # update value 
        if (c == '\n'): 
            self.line += 1
            # READ FILE TWICE, DETELE THIS
            #self.file_content.append([])
            self.col = 0
        else: 
            self.col += 1

        return StrLnCol(c, line_ret, col_ret)


class Tokenizer:

    def __init__(self, scanner: Scanner):
        self.scanner = scanner
        self.buffer: List[Token] = []  # A buffer of tokens
        self.is_new_line = True
        self.is_logical_line = False
        self.line_indent_lvl = 0  # How "far" we are inside the line, i.e. what column.
        # Resets after every end-of-line sequence.
        self.indent_stack = [0]

    def peek(self, k: int = 1) -> Union[Token, List[Token]]:
        """ Peeks through the next `k` number of tokens.

        This functions looks ahead the next `k` number of tokens,
        and returns them as a list.
        It uses a FIFO buffer to store tokens temporarily.
        :param k: number of tokens
        :return: one token or a list of tokens
        """
        if not self.buffer:
            self.buffer = [self.consume()]

        # Fill the buffer up to `k` tokens, if needed.
        buffer_size = len(self.buffer)
        if buffer_size < k:
            for _ in list(range(k - buffer_size)):
                self.buffer.append(self.consume(keep_buffer=True))

        # If you need only one token, return it as an element,
        # not as a list with one element.
        if k == 1:
            return self.buffer[0]

        return self.buffer[0:k]

    def consume(self, keep_buffer: bool = False) -> Token:
        """ Consumes one token and implements peeking through the next one.

        If we want to only peek and not consume, we set the `keep_buffer` flag.
        This argument is passed to additional calls to `next`.
        The idea is that we can peek through more than one tokens (by keeping them in the buffer),
        but we consume tokens only one by one.
        :param keep_buffer: whether to keep the buffer intact, or consume a token from it
        :return: one token
        """
        if self.buffer and not keep_buffer:
            c = self.buffer[0]
            self.buffer = self.buffer[1:]
            return c

        c : StrLnCol = self.scanner.peek()

        while True:
            if c.isspace():
                if c == '\t':
                    pass
                elif c == '\n':  # line feed handling
                    self.is_new_line = True
                    if self.is_logical_line:
                        self.is_logical_line = False
                        self.scanner.consume()
                        return Token(TokenKind.NEWLINE, None, c.line, c.col) 
                elif c == '\r':  # carriage return handling
                    self.is_new_line = True
                    if self.is_logical_line:
                        self.is_logical_line = False
                        self.scanner.consume()
                        return Token(TokenKind.NEWLINE, None, c.line, c.col) 
                # Consume whitespace
                self.scanner.consume()
                return self.consume(keep_buffer)

            # One line comments
            elif c == '#':
                self.scanner.consume()
                c = self.scanner.peek()
                while c and c != '\n' and c != '\r':
                    self.scanner.consume()
                    c = self.scanner.peek()
                return self.consume(keep_buffer)

            elif c and not c.isspace() and c != '#' and self.is_new_line:
                self.is_logical_line = True
                self.is_new_line = False
            
            elif c == ':':
                self.scanner.consume()
                return Token(TokenKind.COLON, None, c.line, c.col, 1)

            # elif c == 'r':
                # self.scanner.consume()
                # c += self.scanner.peek()
                # if c.isnumeric():
                    # address = self.scanner.consume()
                    # return Token(TokenKind.REGISTER , address , c.line, c.col, None)
                # else:
                    # raise Exception('Unknown lexeme: {}'.format(c))

            # Identifier: [a-zA-Z_][a-zA-Z0-9_]*
            elif c.isalpha() or c == '_':
                token_start_line, token_start_col = c.line, c.col
                name = self.scanner.consume()
                c = self.scanner.peek()
                while c.isalnum() or c == '_':
                    name += self.scanner.consume()
                    c = self.scanner.peek()
                
                if name == 'registers':
                    return Token(TokenKind.REGISTERS_SYMBOL, None, token_start_line, token_start_col, 9)
                # if name == 'HALT':
                    # return Token(TokenKind.HALT, None, token_start_line, token_start_col, 4)
                if name == 'decjz':
                    return Token(TokenKind.DECJZ, None, token_start_line, token_start_col, 9)
                if name == 'inc':
                    return Token(TokenKind.INC, None, token_start_line, token_start_col, 4)
                if name[0] == 'r' and name[1::].isnumeric():
                    return Token(TokenKind.REGISTER , int(name[1::]) , c.line, c.col, None)

                return Token(TokenKind.IDENTIFIER, name, token_start_line, token_start_col, len(name))
            
            # Number: [0-9]+
            elif c.isdigit() or c == '-':
                value = self.scanner.consume()
                while self.scanner.peek().isnumeric():
                    value += self.scanner.consume()
                return Token(TokenKind.INTEGER, int(value), c.line, c.col, len(value))

            # End of file
            elif not c:
                # The end of input also serves as an implicit terminator of the physical line.
                # For a logical line emit a newline token.
                if self.is_logical_line:
                    self.is_logical_line = False
                    return Token(TokenKind.NEWLINE, None, c.line, c.col)

                return Token(TokenKind.EOF, None, c.line, c.col)
            else:
                raise Exception("Invalid character detected: '" + c + "'")


class Lexer:

    # line : int = 0
    # col : int = 0

    def __init__(self, stream: TextIOBase):
        scanner = Scanner(stream)
        self.tokenizer = Tokenizer(scanner)

    def peek(self, k: int = 1) -> Union[Token, List[Token]]:
        return self.tokenizer.peek(k)

    def consume(self) -> Token:
        # self.line = self.tokenizer.scanner.line
        # self.col = self.tokenizer.scanner.col
        ret = self.tokenizer.consume()
        return ret
