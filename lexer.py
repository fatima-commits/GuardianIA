
import ply.lex as lex

# Palabras reservadas
reserved = {
    'select': 'SELECT',
    'from': 'FROM',
    'where': 'WHERE',
    'update': 'UPDATE',
    'set': 'SET',
    'delete': 'DELETE',
    'drop': 'DROP',
    'table': 'TABLE',
    'union': 'UNION',
    'order': 'ORDER',
    'by': 'BY',
    'asc': 'ASC',
    'desc': 'DESC',
    'limit': 'LIMIT',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT'
}

tokens = [
    'ID', 'NUMBER', 'STRING',
    'EQ', 'NE', 'LT', 'GT', 'LE', 'GE',
    'STAR', 'COMMA', 'LPAREN', 'RPAREN',
    'SEMICOLON'
] + list(reserved.values())

# Expresiones regulares
t_LE = r'<='
t_GE = r'>='
t_NE = r'<>'
t_EQ = r'='
t_LT = r'<'
t_GT = r'>'

t_STAR = r'\*'
t_COMMA = r','
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_SEMICOLON = r';'

# Ignorar espacios y tabuladores
t_ignore = ' \t\r'

def t_STRING(t):
    r"'([^'\\]|\\.)*'"
    t.value = t.value[1:-1]
    return t

def t_NUMBER(t):
    r'\d+(\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value.lower(), 'ID')
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    raise ValueError(
        f"Error léxico: carácter no válido '{t.value[0]}'"
    )

def crear_lexer():
    return lex.lex()
