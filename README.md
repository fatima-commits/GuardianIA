# GuardianIA — Guardián de Seguridad para un Agente de IA

Proyecto 2 de Lenguajes Formales (ITESO). 

El Guardián es un **analizador estático**:
lee las acciones que propone el agente *AgenteDev* (`consultar_bd` y `abrir_enlace`),
las analiza en tres capas (**léxica, sintáctica y semántica**) y emite un dictamen
explicado: **PERMITIR**, **CONFIRMAR** o **BLOQUEAR**. No ejecuta nada.

## Integrantes de Equipo
Fátima Vélez
Karlos Acosta
Alejandro Ortega

## Instalación

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

## Uso

```bash
python main.py tests/corpus_semilla.txt
python main.py tests/casos_pdf.txt tests/pruebas_propias.txt
python main.py tests/corpus_semilla.txt --salida resultados/corpus_semilla.txt
python -m unittest -v          # pruebas automáticas
python automata.py             # trazas del autómata de pila (para el reporte)
python sql_parser.py --debug   # genera sql_parser.out (tabla LALR)
```

### Formato de entrada

```
# modo: normal
[usuario]    consultar_bd("SELECT nombre FROM empleos WHERE ciudad = 'GDL';")
[mensaje]    abrir_enlace("https://bbva.mx@acceso-seguro.xyz/login?id=8821")
```

* La primera línea es el encabezado `# modo: normal` o `# modo: congelado`. Si falta o
  el modo no es válido, se avisa y se usa `congelado` (la opción más restrictiva).
* Después del encabezado, las líneas que empiezan con `#` son comentarios.

### Ejemplo de salida

```
Analizando: corpus_semilla.txt  (modo: normal)
----------------------------------------------------------------------
[1]  ✓ PERMITIR   consultar_bd: SELECT nombre, salario FROM empleos WHERE ciudad = 'GDL' ...
[2]  ✓ PERMITIR   consultar_bd: SELECT * FROM pagos WHERE (monto > 1000 AND estado = 'pe ...
[3]  ✗ BLOQUEAR   abrir_enlace: https://bbva.mx@acceso-seguro.xyz/login?id=8821
      R5: usuario con '@' antes del host; el sitio real es acceso-seguro.xyz
      R6: la marca 'bbva' aparece fuera del dominio principal (acceso-seguro.xyz)
      R8: origen externo [mensaje]
[4]  ✗ BLOQUEAR   consultar_bd: DELETE FROM clientes WHERE 1 = 1;
      R2: tautología 1 = 1 en la condición
[5]  ✗ BLOQUEAR   consultar_bd: SELECT nombre FROM empleos WHERE id = 7 UNION SELECT usu ...
      R3: UNION hacia la tabla no permitida 'admins'
      R8: origen externo [documento]
[6]  ✓ PERMITIR   abrir_enlace: https://www.iteso.mx/web/general/detalle?id=24
Resumen: 3 permitidas, 0 por confirmar, 3 bloqueadas, 0 con error
```

## Arquitectura

```
 archivo .txt
     │  main.py  ─ lee el encabezado de modo y cada línea por separado
     ▼
 guardian.py  ─ orquesta el análisis de UNA acción
     │
     ├─► llamada.py      lexer + autómata de pila + parser de la llamada
     │                   → {origen, herramienta, argumento}
     │
     ├─► según la herramienta se elige la gramática del argumento:
     │     consultar_bd ─► sql_lexer.py → automata.py → sql_parser.py   → AST SQL
     │     abrir_enlace ─► url_lexer.py → url_parser.py (+ rangos)       → estructura URL
     │
     ├─► semantic.py     R1–R4 (SQL) / R5–R7 (URL) / R8 (origen) + modo
     │                   → lista de riesgos → dictamen más severo
     ▼
 reporte.py   ─ formato de consola y resumen
```

| Módulo | Responsabilidad |
|---|---|
| `main.py` | Línea de comandos, lectura del archivo y del encabezado de modo. |
| `guardian.py` | Flujo de una acción; atrapa los errores para que una acción con error no detenga las demás. |
| `errores.py` | `ErrorLexico`, `ErrorSintactico`, `ErrorSemantico` (rangos). |
| `llamada.py` | Lenguaje 1: `[origen] herramienta("argumento")` con PLY. |
| `sql_lexer.py` / `sql_parser.py` | Lenguaje 2: SQL con PLY, precedencia NOT > AND > OR. |
| `url_lexer.py` / `url_parser.py` | Lenguaje 3: URL con PLY (lexer con dos estados) y validación de rangos. |
| `automata.py` | Autómata de pila para paréntesis (SQL y llamada). |
| `semantic.py` | Reglas R1–R8 sobre la estructura reconocida y combinación del dictamen. |
| `reporte.py` | Salida en consola con el formato del enunciado. |
| `ply_comun.py` | Utilidades compartidas (alimentar yacc con una lista de tokens, mensajes de error). |

Cada acción se tokeniza **una sola vez**: la lista de tokens pasa primero por el autómata
de pila y después por yacc. Los errores de cada capa se lanzan como excepción, `guardian.py`
los convierte en un resultado `ERROR` y `reporte.py` arma el reporte final.

## Clasificación de los resultados

| Resultado | Cuándo |
|---|---|
| Error léxico | carácter no válido, cadena sin cerrar, herramienta u origen no reconocidos, esquema no permitido, `%XX` inválido |
| Error sintáctico | símbolos válidos en orden inválido, paréntesis sin cerrar (autómata de pila), varios argumentos, llamadas anidadas |
| Error semántico (rango) | octeto IPv4 fuera de 0–255, puerto fuera de 0–65535 |
| BLOQUEAR | R1–R4 (SQL) o R5–R6 (URL, riesgo alto) |
| CONFIRMAR | R7 (URL, riesgo medio) o R8 (origen `[documento]`/`[mensaje]`) |
| PERMITIR | sin reglas |

Las reglas se aplican sobre el AST/estructura, nunca buscando texto en la cadena original
(por eso `WHERE nota = 'a;b'` no dispara R4 y `ciudad = 'ciudad'` no dispara R2).

## Pruebas

| Archivo | Contenido |
|---|---|
| `tests/corpus_semilla.txt` | Corpus del enunciado. |
| `tests/casos_pdf.txt` | Los 13 casos de la tabla del enunciado. |
| `tests/pruebas_propias.txt` | 25 acciones propias: legítimas, errores léxicos, sintácticos, de rango, peligrosas, inyecciones y falsos positivos evitados. |
| `tests/modo_congelado.txt` | Comportamiento en modo congelado. |
| `resultados/` | Salida del Guardián para cada archivo de prueba. |
| `test_guardian.py` | 26 pruebas automáticas (`python -m unittest -v`). |
