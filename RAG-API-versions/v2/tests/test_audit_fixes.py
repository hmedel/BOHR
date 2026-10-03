"""
Tests de las correcciones de la auditoría de octubre de 2026:
detección de solicitud/confirmación de examen y migración de hashes legacy.

Ejecutar con:
    python -m unittest tests.test_audit_fixes -v
"""

import hashlib
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.exam_engine import is_exam_request, is_exam_confirmation


class ExamRequestTests(unittest.TestCase):
    def test_solicitudes_explicitas(self):
        for q in [
            "Quiero un examen",
            "quiero otro examen",
            "Evalúame",
            "evaluame por favor",
            "hazme una prueba",
            "quiero una evaluación",
            "más preguntas",
        ]:
            self.assertTrue(is_exam_request(q), q)

    def test_consultas_de_quimica_no_disparan_examen(self):
        for q in [
            "¿Qué es la prueba a la flama?",
            "¿Cómo se hace la evaluación de la integral radial?",
            "Ya terminé de leer el capítulo, ¿qué es el espín?",
            "¿Qué prueba experimental confirmó la dualidad onda-partícula?",
        ]:
            self.assertFalse(is_exam_request(q), q)


class ExamConfirmationTests(unittest.TestCase):
    def test_confirmaciones(self):
        for q in ["Sí, comenzar", "si comenzar", "Sí, empezar", "sí, iniciar el examen"]:
            self.assertTrue(is_exam_confirmation(q), q)

    def test_subcadena_si_no_confirma(self):
        # "posible" contiene "si"; antes esto arrancaba un examen
        for q in [
            "¿Es posible iniciar una reacción sin energía de activación?",
            "comenzar",
            "¿Qué pasa si quiero iniciar la configuración electrónica desde el orbital 2s en lugar del 1s?",
        ]:
            self.assertFalse(is_exam_confirmation(q), q)


class PasswordHashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # auth.py lee JWT_SECRET_KEY y DEEPSEEK_API_KEY del entorno/.env al importar
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
        os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
        from app import auth
        cls.auth = auth

    def test_hash_legacy_se_detecta_y_verifica(self):
        legacy = hashlib.sha256(b"clave-de-prueba").hexdigest()
        self.assertTrue(self.auth.is_legacy_hash(legacy))
        self.assertTrue(self.auth.verify_password("clave-de-prueba", legacy))
        self.assertFalse(self.auth.verify_password("otra", legacy))

    def test_hash_nuevo_es_bcrypt(self):
        new = self.auth.get_password_hash("clave-de-prueba")
        self.assertFalse(self.auth.is_legacy_hash(new))
        self.assertTrue(new.startswith("$2"))
        self.assertTrue(self.auth.verify_password("clave-de-prueba", new))
        self.assertFalse(self.auth.verify_password("otra", new))


if __name__ == "__main__":
    unittest.main()
