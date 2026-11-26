
from parser import analizar_sql

consulta = """
SELECT nombre FROM empleos
WHERE ciudad = 'GDL';
"""

try:
    resultado = analizar_sql(consulta)
    print("Consulta válida")
    print(resultado)

except ValueError as error:
    print(error)
