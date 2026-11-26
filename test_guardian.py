"""
Pruebas automáticas del Guardián.

    python -m unittest -v

Cubre los 13 casos de la tabla del enunciado, el corpus semilla y casos
extra (precedencia, modo congelado, falsos positivos).
"""

import unittest

from errores import ErrorLexico, ErrorSintactico, ErrorSemantico
from guardian import analizar_accion
from sql_parser import analizar_sql
from sql_lexer import tokenizar_sql
from automata import validar_anidamiento


def dictamen(linea, modo="normal"):
    return analizar_accion(linea, modo)


def reglas(res):
    return sorted({r.regla for r in res.riesgos})


class CasosDelEnunciado(unittest.TestCase):
    """Tabla 'Ejemplos de acciones bien y mal escritas'."""

    def esperar(self, linea, esperado, tipo_error=None, reglas_esp=None):
        res = dictamen(linea)
        self.assertEqual(res.dictamen, esperado, f"{linea} -> {res.error or res.riesgos}")
        if tipo_error:
            self.assertIsInstance(res.error, tipo_error)
        if reglas_esp:
            self.assertEqual(reglas(res), reglas_esp)

    def test_01(self):
        self.esperar("""[usuario] consultar_bd("SELECT nombre FROM empleos WHERE ciudad = 'GDL';")""", "PERMITIR")

    def test_02(self):
        self.esperar("""[usuario] consultar_bd("SELECT * FROM pagos WHERE (monto > 1000 AND estado = 'pendiente') OR urgente = 1;")""", "PERMITIR")

    def test_03(self):
        self.esperar("""[usuario] abrir_enlace("https://www.iteso.mx/web/general/detalle?id=24")""", "PERMITIR")

    def test_04(self):
        self.esperar("""[usuario] consultar_bd("SELECT nombre FROM empleos WHERE ciudad = 'GDL;")""", "ERROR", ErrorLexico)

    def test_05(self):
        self.esperar("""[usuario] consultar_bd("SELECT nombre FROM empleos WHERE ciudad # 'GDL';")""", "ERROR", ErrorLexico)

    def test_06(self):
        self.esperar("""[usuario] consultar_bd("SELECT nombre empleos WHERE;")""", "ERROR", ErrorSintactico)

    def test_07(self):
        self.esperar("""[usuario] consultar_bd("SELECT * FROM pagos WHERE (monto > 1000 AND estado = 'pendiente';")""", "ERROR", ErrorSintactico)

    def test_08(self):
        self.esperar("""[usuario] abrir_enlace("https//bbva.mx")""", "ERROR", ErrorSintactico)

    def test_09(self):
        self.esperar("""[usuario] consultar_bd("DELETE FROM clientes;")""", "BLOQUEAR", reglas_esp=["R1"])

    def test_10(self):
        self.esperar("""[usuario] consultar_bd("SELECT * FROM usuarios WHERE id = 7 OR 1 = 1;")""", "BLOQUEAR", reglas_esp=["R2"])

    def test_11(self):
        self.esperar("""[usuario] consultar_bd("SELECT nombre FROM empleos WHERE id = 7 UNION SELECT usuario, clave FROM admins;")""", "BLOQUEAR", reglas_esp=["R3"])

    def test_12(self):
        self.esperar("""[usuario] abrir_enlace("https://bbva.mx@acceso-seguro.xyz/login")""", "BLOQUEAR", reglas_esp=["R5", "R6"])

    def test_13(self):
        self.esperar("""[usuario] abrir_enlace("http://187.23.4.11:8081/banco")""", "CONFIRMAR", reglas_esp=["R7"])


class Extras(unittest.TestCase):

    def test_r4_varias_sentencias(self):
        res = dictamen("""[usuario] consultar_bd("SELECT a FROM b; DROP TABLE b;")""")
        self.assertEqual(res.dictamen, "BLOQUEAR")
        self.assertIn("R4", reglas(res))

    def test_r4_no_cuenta_punto_y_coma_dentro_de_cadena(self):
        res = dictamen("""[usuario] consultar_bd("SELECT * FROM clientes WHERE nota = 'a;b';")""")
        self.assertEqual(res.dictamen, "PERMITIR")

    def test_r2_columna_igual_a_cadena_no_es_tautologia(self):
        res = dictamen("""[usuario] consultar_bd("SELECT * FROM e WHERE ciudad = 'ciudad';")""")
        self.assertEqual(res.dictamen, "PERMITIR")

    def test_r8_origen_externo(self):
        res = dictamen("""[mensaje] abrir_enlace("https://www.iteso.mx/")""")
        self.assertEqual(res.dictamen, "CONFIRMAR")
        self.assertEqual(reglas(res), ["R8"])

    def test_modo_congelado(self):
        res = dictamen("""[usuario] consultar_bd("UPDATE e SET a = 1 WHERE id = 2;")""", "congelado")
        self.assertEqual(res.dictamen, "BLOQUEAR")
        res = dictamen("""[usuario] consultar_bd("SELECT a FROM e;")""", "congelado")
        self.assertEqual(res.dictamen, "PERMITIR")

    def test_r6_subdominio(self):
        res = dictamen("""[usuario] abrir_enlace("https://bbva.mx.verificacion.com")""")
        self.assertIn("R6", reglas(res))

    def test_r6_sufijo_doble_no_es_falso_positivo(self):
        res = dictamen("""[usuario] abrir_enlace("https://www.bbva.com.mx/")""")
        self.assertEqual(res.dictamen, "PERMITIR")

    def test_herramienta_no_reconocida(self):
        res = dictamen("""[usuario] borrar_todo("x")""")
        self.assertIsInstance(res.error, ErrorLexico)

    def test_llamada_anidada(self):
        res = dictamen("""[usuario] consultar_bd(abrir_enlace("https://a.com"))""")
        self.assertIsInstance(res.error, ErrorSintactico)

    def test_rangos(self):
        res = dictamen("""[usuario] abrir_enlace("http://256.1.1.1/")""")
        self.assertIsInstance(res.error, ErrorSemantico)
        res = dictamen("""[usuario] abrir_enlace("http://a.com:65536/")""")
        self.assertIsInstance(res.error, ErrorSemantico)

    def test_palabras_reservadas_sin_mayusculas(self):
        tipos = [t.type for t in tokenizar_sql("select Selection FROM t")]
        self.assertEqual(tipos, ["SELECT", "ID", "FROM", "ID"])

    def test_precedencia_not_and_or(self):
        ast = analizar_sql("SELECT * FROM e WHERE NOT a = 1 AND b = 2 OR c = 3")
        cond = ast["sentencias"][0]["partes"][0]["condicion"]
        self.assertEqual(cond["tipo"], "OR")
        self.assertEqual(cond["izq"]["tipo"], "AND")
        self.assertEqual(cond["izq"]["izq"]["tipo"], "NOT")

    def test_automata(self):
        self.assertTrue(validar_anidamiento(["LPAREN", "LPAREN", "ID", "RPAREN", "RPAREN"])[0])
        self.assertFalse(validar_anidamiento(["LPAREN", "ID"])[0])
        self.assertFalse(validar_anidamiento(["RPAREN"])[0])


if __name__ == "__main__":
    unittest.main()
