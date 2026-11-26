
from lexer import crear_lexer

lexer = crear_lexer()

consulta = "SELECT nombre FROM empleos WHERE ciudad = 'GDL';"

lexer.input(consulta)

while True:
    token = lexer.token()

    if not token:
        break

    print(token.type, token.value)
