ABRE = "LPAREN"
CIERRA = "RPAREN"


def validar_anidamiento(tipos_tokens):
    """
    Ejecuta el PDA sobre una lista de tipos de token.

    Regresa (aceptada: bool, traza: list[str], mensaje: str | None)
    """
    estado = "q0"
    pila = ["Z0"]
    traza = []

    def foto(simbolo, tope, apila):
        pila_txt = "".join(reversed(pila))  # tope a la izquierda
        traza.append(f"δ({estado}, {simbolo}, {tope}) -> ({estado}, {apila})"
                     f"   pila: {pila_txt}")

    for tipo in tipos_tokens:
        if tipo == ABRE:
            tope = pila[-1]
            pila.append("P")
            foto("(", tope, "P" + tope)
        elif tipo == CIERRA:
            if pila[-1] != "P":
                traza.append("δ(q0, ), Z0) no definida -> RECHAZA")
                return False, traza, "se cierra un paréntesis que nunca se abrió"
            pila.pop()
            foto(")", "P", "ε")
        else:
            # transiciones 4 y 5: no se modifica la pila (se omiten de la
            # traza para que sea legible)
            pass

    if pila[-1] == "Z0":
        traza.append("δ(q0, ε, Z0) -> (qf, Z0)   ACEPTA")
        return True, traza, None

    abiertos = pila.count("P")
    traza.append(f"fin de entrada con P en el tope ({abiertos} sin cerrar) -> RECHAZA")
    return False, traza, "se abre un paréntesis que nunca se cierra"


if __name__ == "__main__":
    # Trazas para el reporte: una cadena aceptada y una rechazada
    from sql_lexer import tokenizar_sql

    ejemplos = [
        "SELECT * FROM pagos WHERE (monto > 1000 AND (estado = 'pendiente')) OR urgente = 1;",
        "SELECT * FROM pagos WHERE (monto > 1000 AND estado = 'pendiente';",
    ]
    for sql in ejemplos:
        tipos = [t.type for t in tokenizar_sql(sql)]
        ok, traza, msg = validar_anidamiento(tipos)
        print(sql)
        for paso in traza:
            print("   ", paso)
        print("   =>", "ACEPTADA" if ok else f"RECHAZADA ({msg})")
        print()
