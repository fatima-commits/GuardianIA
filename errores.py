"""
Tipos de error del Guardián.

Separar los errores por clase permite que el reporte distinga en qué capa
falló una acción:

- ErrorLexico     -> el texto contiene símbolos que no pertenecen al lenguaje
                     (carácter no válido, cadena sin cerrar, herramienta
                     no reconocida, esquema no permitido...).
- ErrorSintactico -> todos los símbolos son válidos, pero están en un orden
                     que la gramática no acepta (incluye paréntesis sin
                     cerrar, detectados por el autómata de pila).
- ErrorSemantico  -> la estructura es correcta, pero un valor está fuera del
                     rango que las expresiones regulares no pueden controlar
                     (octeto IPv4 > 255, puerto > 65535).

Los RIESGOS (reglas R1 a R8) no son errores: la acción está bien formada y
recibe un dictamen. Esos se manejan en semantic.py.
"""


class ErrorGuardian(Exception):
    """Clase base. `lenguaje` indica en qué lenguaje ocurrió el error."""

    categoria = "Error"

    def __init__(self, mensaje, lenguaje=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.lenguaje = lenguaje

    def __str__(self):
        donde = f" ({self.lenguaje})" if self.lenguaje else ""
        return f"{self.categoria}{donde}: {self.mensaje}"


class ErrorLexico(ErrorGuardian):
    categoria = "Error léxico"


class ErrorSintactico(ErrorGuardian):
    categoria = "Error sintáctico"


class ErrorSemantico(ErrorGuardian):
    categoria = "Error semántico"
