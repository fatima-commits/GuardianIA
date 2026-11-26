"""
Utilidades compartidas por los tres analizadores PLY.
"""


class LexerDeLista:
    """
    Entrega a yacc una lista de tokens ya generada.

    Cada acción se tokeniza una sola vez: la lista se usa primero para el
    autómata de pila y después para el parser.
    """

    def __init__(self, tokens):
        self._tokens = list(tokens)
        self._i = 0

    def token(self):
        if self._i < len(self._tokens):
            tok = self._tokens[self._i]
            self._i += 1
            return tok
        return None


def tokens_esperados(parser, nombres):
    """
    Lista legible de los tokens que el parser LALR aceptaba en el estado
    donde ocurrió el error (se lee de la tabla ACTION de yacc).
    """
    try:
        estado = parser.statestack[-1]
        esperados = [t for t in parser.action[estado].keys() if t != "$end"]
    except (AttributeError, IndexError, KeyError):
        return ""
    legibles = sorted({nombres.get(t, t) for t in esperados})
    if not legibles:
        return ""
    if len(legibles) == 1:
        return legibles[0]
    return ", ".join(legibles[:-1]) + " o " + legibles[-1]


class LogSinTokensNoUsados:
    """
    Logger para yacc que oculta solo el aviso "Token ... defined, but not
    used". En la gramática de la llamada COMMA e ID existen a propósito
    para producir errores sintácticos claros; cualquier otro aviso
    (por ejemplo, conflictos shift/reduce) sí se muestra.
    """

    def __init__(self):
        import sys
        self._f = sys.stderr

    def _ignorar(self, msg):
        return "defined, but not used" in msg or "unused token" in msg

    def warning(self, msg, *args, **kwargs):
        texto = msg % args
        if not self._ignorar(texto):
            self._f.write("WARNING: " + texto + "\n")

    def error(self, msg, *args, **kwargs):
        self._f.write("ERROR: " + (msg % args) + "\n")

    def info(self, *a, **k):
        pass

    debug = critical = info
