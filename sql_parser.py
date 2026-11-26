"""
Lenguaje 2: analizador sintáctico de las consultas SQL (PLY yacc).

Gramática (G_SQL)
-----------------
Terminales:
  SELECT FROM WHERE UPDATE SET DELETE DROP TABLE UNION ORDER BY ASC DESC
  LIMIT AND OR NOT ID NUMBER STRING EQ NE LT GT LE GE STAR COMMA LPAREN
  RPAREN SEMICOLON

No terminales:
  programa, lista_sentencias, sentencia, consulta_select, union_select,
  select_simple, columnas, lista_columnas, where_opt, condicion, comparador,
  valor, update_stmt, asignaciones, asignacion, delete_stmt, drop_stmt,
  order_opt, direccion_opt, limit_opt, empty

Símbolo inicial: programa

Producciones:
  programa         -> lista_sentencias
                    | lista_sentencias SEMICOLON
  lista_sentencias -> sentencia
                    | lista_sentencias SEMICOLON sentencia
  sentencia        -> consulta_select | update_stmt | delete_stmt | drop_stmt

  consulta_select  -> union_select order_opt limit_opt
  union_select     -> select_simple
                    | union_select UNION select_simple
  select_simple    -> SELECT columnas FROM ID where_opt
  columnas         -> STAR | lista_columnas
  lista_columnas   -> ID | lista_columnas COMMA ID

  update_stmt      -> UPDATE ID SET asignaciones where_opt
  asignaciones     -> asignacion | asignaciones COMMA asignacion
  asignacion       -> ID EQ valor
  delete_stmt      -> DELETE FROM ID where_opt
  drop_stmt        -> DROP TABLE ID

  where_opt        -> WHERE condicion | empty
  condicion        -> condicion OR condicion
                    | condicion AND condicion
                    | NOT condicion
                    | LPAREN condicion RPAREN
                    | valor comparador valor
  comparador       -> EQ | NE | LT | GT | LE | GE
  valor            -> ID | NUMBER | STRING

  order_opt        -> ORDER BY ID direccion_opt | empty
  direccion_opt    -> ASC | DESC | empty
  limit_opt        -> LIMIT NUMBER | empty
  empty            -> ε

Precedencia y ambigüedad
------------------------
Las producciones de `condicion` son ambiguas: 'a OR b AND c' tiene dos
árboles. Eso produce conflictos shift/reduce en la tabla LALR, que se
resuelven con la tabla `precedence` (de menor a mayor):

    nivel  operador  asociatividad
      1      OR        izquierda
      2      AND       izquierda
      3      NOT       derecha (unario)

Así NOT > AND > OR:
  'NOT a = 1 AND b = 2 OR c = 3'  ==  '((NOT a = 1) AND b = 2) OR c = 3'
Los paréntesis cambian el orden porque `( condicion )` se reduce primero.

Sin la tabla de precedencia, yacc reporta 6 conflictos shift/reduce
(AND/OR/NOT contra AND/OR). Con ella se resuelven los 6 y no queda ningún
conflicto (ver `python sql_parser.py --debug`, que genera sql_parser.out).

AST
---
{'sentencias': [sentencia, ...]}
  SELECT -> {'tipo': 'SELECT', 'partes': [{'tabla', 'columnas', 'condicion'}, ...]}
            (más de una parte == UNION)
  UPDATE -> {'tipo': 'UPDATE', 'tabla', 'asignaciones', 'condicion'}
  DELETE -> {'tipo': 'DELETE', 'tabla', 'condicion'}
  DROP   -> {'tipo': 'DROP',   'tabla'}
  condicion: {'tipo': 'OR'|'AND', 'izq', 'der'} | {'tipo': 'NOT', 'valor'}
             | {'tipo': 'COMPARACION', 'izq', 'op', 'der'}
  valor:     {'clase': 'ID'|'NUMBER'|'STRING', 'v': ...}
"""

import sys

import ply.yacc as yacc

from errores import ErrorSintactico
from automata import validar_anidamiento
from ply_comun import LexerDeLista, tokens_esperados
from sql_lexer import tokens, tokenizar_sql  # noqa: F401  (yacc usa `tokens`)

LENGUAJE = "SQL"

precedence = (
    ("left", "OR"),
    ("left", "AND"),
    ("right", "NOT"),
)

# ----------------------------- programa ---------------------------------


def p_programa(p):
    """programa : lista_sentencias
                | lista_sentencias SEMICOLON"""
    p[0] = {"sentencias": p[1]}


def p_lista_sentencias(p):
    """lista_sentencias : sentencia
                        | lista_sentencias SEMICOLON sentencia"""
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_sentencia(p):
    """sentencia : consulta_select
                 | update_stmt
                 | delete_stmt
                 | drop_stmt"""
    p[0] = p[1]

# ------------------------------ SELECT ----------------------------------


def p_consulta_select(p):
    "consulta_select : union_select order_opt limit_opt"
    p[0] = {"tipo": "SELECT", "partes": p[1]}


def p_union_select(p):
    """union_select : select_simple
                    | union_select UNION select_simple"""
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_select_simple(p):
    "select_simple : SELECT columnas FROM ID where_opt"
    p[0] = {"columnas": p[2], "tabla": p[4], "condicion": p[5]}


def p_columnas(p):
    """columnas : STAR
                | lista_columnas"""
    p[0] = ["*"] if p[1] == "*" else p[1]


def p_lista_columnas(p):
    """lista_columnas : ID
                      | lista_columnas COMMA ID"""
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

# --------------------------- UPDATE / DELETE / DROP ---------------------


def p_update(p):
    "update_stmt : UPDATE ID SET asignaciones where_opt"
    p[0] = {"tipo": "UPDATE", "tabla": p[2], "asignaciones": p[4],
            "condicion": p[5]}


def p_asignaciones(p):
    """asignaciones : asignacion
                    | asignaciones COMMA asignacion"""
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_asignacion(p):
    "asignacion : ID EQ valor"
    p[0] = (p[1], p[3])


def p_delete(p):
    "delete_stmt : DELETE FROM ID where_opt"
    p[0] = {"tipo": "DELETE", "tabla": p[3], "condicion": p[4]}


def p_drop(p):
    "drop_stmt : DROP TABLE ID"
    p[0] = {"tipo": "DROP", "tabla": p[3]}

# ------------------------------ WHERE -----------------------------------


def p_where_opt(p):
    """where_opt : WHERE condicion
                 | empty"""
    p[0] = p[2] if len(p) == 3 else None


def p_condicion_binaria(p):
    """condicion : condicion OR condicion
                 | condicion AND condicion"""
    p[0] = {"tipo": p[2].upper(), "izq": p[1], "der": p[3]}


def p_condicion_not(p):
    "condicion : NOT condicion"
    p[0] = {"tipo": "NOT", "valor": p[2]}


def p_condicion_parentesis(p):
    "condicion : LPAREN condicion RPAREN"
    p[0] = p[2]


def p_condicion_comparacion(p):
    "condicion : valor comparador valor"
    p[0] = {"tipo": "COMPARACION", "izq": p[1], "op": p[2], "der": p[3]}


def p_comparador(p):
    """comparador : EQ
                  | NE
                  | LT
                  | GT
                  | LE
                  | GE"""
    p[0] = p[1]


def p_valor(p):
    """valor : ID
             | NUMBER
             | STRING"""
    # Guardamos la CLASE del valor: R2 solo aplica a valores fijos
    # (NUMBER, STRING), no a columnas (ID).
    p[0] = {"clase": p.slice[1].type, "v": p[1]}

# --------------------------- ORDER BY / LIMIT ---------------------------


def p_order_opt(p):
    """order_opt : ORDER BY ID direccion_opt
                 | empty"""
    p[0] = (p[3], p[4]) if len(p) == 5 else None


def p_direccion_opt(p):
    """direccion_opt : ASC
                     | DESC
                     | empty"""
    p[0] = p[1].upper() if p[1] else None


def p_limit_opt(p):
    """limit_opt : LIMIT NUMBER
                 | empty"""
    p[0] = p[2] if len(p) == 3 else None


def p_empty(p):
    "empty :"
    p[0] = None

# ------------------------------ errores ---------------------------------


NOMBRES = {
    "ID": "un identificador", "NUMBER": "un número", "STRING": "una cadena",
    "STAR": "'*'", "COMMA": "','", "LPAREN": "'('", "RPAREN": "')'",
    "SEMICOLON": "';'", "EQ": "'='", "NE": "'<>'", "LT": "'<'", "GT": "'>'",
    "LE": "'<='", "GE": "'>='",
}

_prev = {"tok": None}


def p_error(tok):
    esperados = tokens_esperados(_parser, NOMBRES)
    anterior = _prev["tok"]

    if tok is None:
        raise ErrorSintactico("la consulta está incompleta; se esperaba "
                              + esperados, LENGUAJE)

    # Mensajes específicos para los casos más comunes
    if anterior is not None and anterior.type == "SELECT":
        raise ErrorSintactico("se esperaba una lista de columnas después de "
                              "SELECT", LENGUAJE)
    if anterior is not None and anterior.type == "WHERE":
        raise ErrorSintactico("se esperaba una condición después de WHERE",
                              LENGUAJE)

    raise ErrorSintactico(f"se encontró '{tok.value}' pero se esperaba "
                          + esperados, LENGUAJE)


class _LexerConMemoria(LexerDeLista):
    """Recuerda el token anterior para mejorar los mensajes de error."""

    def __init__(self, toks):
        super().__init__(toks)
        self._ultimo = None

    def token(self):
        _prev["tok"] = self._ultimo
        tok = super().token()
        self._ultimo = tok
        return tok


_parser = yacc.yacc(debug=False, write_tables=False)

# ------------------------------- API ------------------------------------


def analizar_sql(texto):
    """
    Lexer -> autómata de pila -> parser.
    Regresa el AST o lanza ErrorLexico / ErrorSintactico.
    """
    toks = tokenizar_sql(texto)                       # 1. léxico

    if not toks:
        raise ErrorSintactico("la consulta está vacía", LENGUAJE)

    ok, _traza, msg = validar_anidamiento([t.type for t in toks])
    if not ok:                                        # 2. autómata de pila
        raise ErrorSintactico(msg, LENGUAJE)

    _prev["tok"] = None
    return _parser.parse(lexer=_LexerConMemoria(toks))  # 3. sintáctico


if __name__ == "__main__":
    if "--debug" in sys.argv:
        # Genera sql_parser.out con la tabla LALR y los conflictos resueltos
        yacc.yacc(debug=True, debugfile="sql_parser.out", write_tables=False)
        print("Tabla LALR escrita en sql_parser.out")
    else:
        import pprint
        pprint.pprint(analizar_sql(
            "SELECT * FROM pagos WHERE (monto > 1000 AND estado = 'pendiente') "
            "OR urgente = 1;"))
