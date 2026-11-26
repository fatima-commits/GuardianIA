
def validar_parentesis(cadena):
    pila = []

    estado = "q0"

    for caracter in cadena:

        if caracter == '(':
            pila.append('(')
            estado = "q1"

        elif caracter == ')':

            if not pila:
                return False

            pila.pop()

            if not pila:
                estado = "q0"

    return len(pila) == 0


# Pruebas
pruebas = [
    "(a AND b)",
    "((a OR b) AND c)",
    "(a AND b",
    "a AND b)",
    "((a OR b))"
]

for prueba in pruebas:
    resultado = validar_parentesis(prueba)
    print(prueba, "ACEPTADA" if resultado else "RECHAZADA")
