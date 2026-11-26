
import ply.yacc as yacc
from lexer import tokens, crear_lexer

# NOT tiene mayor precedencia que AND y OR.
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
)

# Consulta principal
def p_consulta(p):
    '''consulta : select_stmt opt_semicolon
                | update_stmt opt_semicolon
                | delete_stmt opt_semicolon
                | drop_stmt opt_semicolon'''
    p[0] = p[1]


def p_opt_semicolon(p):
    '''opt_semicolon : SEMICOLON
                     | empty'''
    p[0] = None

# SELECT
def p_select(p):
    'select_stmt : SELECT columnas FROM tabla where_opt order_opt limit_opt'

    p[0] = {
        'tipo': 'SELECT',
        'tabla': p[4],
        'condicion': p[5],
        'sentencias': 1
    }

def p_columnas(p):
    '''columnas : STAR
                | lista_columnas'''
    p[0] = p[1]

def p_lista_columnas(p):
    '''lista_columnas : ID
                      | lista_columnas COMMA ID'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_tabla(p):
    'tabla : ID'
    p[0] = p[1].lower()

# WHERE
def p_where_opt(p):
    '''where_opt : WHERE condicion
                 | empty'''
    p[0] = p[2] if len(p) == 3 else None

# Condiciones
def p_condicion_binaria(p):
    '''condicion : condicion AND condicion
                 | condicion OR condicion'''
    p[0] = {
        'tipo': p[2],
        'izquierda': p[1],
        'derecha': p[3]
    }

def p_condicion_not(p):
    'condicion : NOT condicion'
    p[0] = {'tipo': 'NOT', 'valor': p[2]}

def p_condicion_parentesis(p):
    'condicion : LPAREN condicion RPAREN'
    p[0] = p[2]

def p_condicion_comparacion(p):
    '''condicion : valor EQ valor
                 | valor NE valor
                 | valor LT valor
                 | valor GT valor
                 | valor LE valor
                 | valor GE valor'''
    p[0] = {
        'tipo': 'COMPARACION',
        'izquierda': p[1],
        'operador': p[2],
        'derecha': p[3]
    }

def p_valor(p):
    '''valor : ID
             | NUMBER
             | STRING'''
    p[0] = p[1]

# UPDATE
def p_update(p):
    'update_stmt : UPDATE ID SET ID EQ valor where_opt'
    p[0] = {
        'tipo': 'UPDATE',
        'tabla': p[2].lower(),
        'condicion': p[7],
        'sentencias': 1
    }

# DELETE
def p_delete(p):
    'delete_stmt : DELETE FROM ID where_opt'
    p[0] = {
        'tipo': 'DELETE',
        'tabla': p[3].lower(),
        'condicion': p[4],
        'sentencias': 1
    }

# DROP TABLE
def p_drop(p):
    'drop_stmt : DROP TABLE ID'
    p[0] = {
        'tipo': 'DROP',
        'tabla': p[3].lower(),
        'condicion': None,
        'sentencias': 1
    }

# ORDER BY
def p_order_opt(p):
    '''order_opt : ORDER BY ID
                 | ORDER BY ID ASC
                 | ORDER BY ID DESC
                 | empty'''
    p[0] = None

# LIMIT
def p_limit_opt(p):
    '''limit_opt : LIMIT NUMBER
                 | empty'''
    p[0] = None

def p_empty(p):
    'empty :'
    p[0] = None

def p_error(p):
    if p:
        raise ValueError(
            f"Error sintáctico cerca de '{p.value}'"
        )
    raise ValueError("Error sintáctico: expresión incompleta")

parser = yacc.yacc()

def analizar_sql(texto):
    lexer = crear_lexer()
    return parser.parse(texto, lexer=lexer)