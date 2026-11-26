"""
Orquestador del Guardián: analiza UNA acción y regresa su Resultado.

Flujo de una acción
-------------------
  línea del archivo
     │
     ▼
  llamada.py      lexer + autómata de pila + parser de la llamada
     │            -> {origen, herramienta, argumento}
     ▼
  ¿herramienta?   AQUÍ se decide con qué gramática se analiza el argumento:
     ├─ consultar_bd -> sql_parser.analizar_sql   (lexer, PDA, yacc)
     └─ abrir_enlace -> url_parser.analizar_url   (lexer, yacc, rangos)
     │
     ▼
  semantic.py     R1-R4 (SQL) o R5-R7 (URL), R8 (origen), modo
     │
     ▼
  Resultado       dictamen + riesgos  |  ERROR + mensaje clasificado

Cualquier ErrorLexico / ErrorSintactico / ErrorSemantico se atrapa aquí y se
convierte en un Resultado con dictamen 'ERROR'; así un error en una acción
no detiene el análisis de las demás.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from errores import ErrorGuardian
from llamada import analizar_llamada
from sql_parser import analizar_sql
from url_parser import analizar_url
import semantic


@dataclass
class Resultado:
    texto: str                       # línea original
    dictamen: str = "PERMITIR"       # PERMITIR | CONFIRMAR | BLOQUEAR | ERROR
    herramienta: Optional[str] = None
    argumento: Optional[str] = None
    origen: Optional[str] = None
    riesgos: List[semantic.Riesgo] = field(default_factory=list)
    error: Optional[ErrorGuardian] = None


def analizar_accion(linea, modo):
    res = Resultado(texto=linea)
    try:
        llamada = analizar_llamada(linea)
        res.origen = llamada["origen"]
        res.herramienta = llamada["herramienta"]
        res.argumento = llamada["argumento"]

        if res.herramienta == "consultar_bd":
            ast = analizar_sql(res.argumento)
            riesgos = semantic.reglas_sql(ast, modo)
        else:  # abrir_enlace
            datos = analizar_url(res.argumento)
            riesgos = semantic.reglas_url(datos)

        riesgos += semantic.regla_origen(res.origen)
        res.riesgos = riesgos
        res.dictamen = semantic.dictamen(riesgos)

    except ErrorGuardian as e:
        res.dictamen = "ERROR"
        res.error = e

    return res
