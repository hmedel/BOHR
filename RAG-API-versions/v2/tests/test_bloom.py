"""
Tests del clasificador Bloom (QualitativeEvaluator.classify_bloom_level).

Casos de prueba derivados de preguntas reales del curso de Estructura de la
Materia (FESC-UNAM). La clasificacion esperada fue acordada entre dos docentes
del area; los desacuerdos se resolvieron por votacion simple.

Ejecutar con:
    python -m pytest tests/test_bloom.py -v

Los resultados de esta suite (tasa de acierto antes y despues de aplicar
limites de palabra) son el dato 4 del estudio de validez del articulo.
"""

import sys
from pathlib import Path

# Permitir importar desde app/ sin instalar el paquete
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.qualitative_evaluator import QualitativeEvaluator

classify = QualitativeEvaluator.classify_bloom_level

VALID_LEVELS = {
    "recordar", "comprender", "aplicar", "analizar",
    "evaluar", "crear", "no_clasificado",
}

# Cada caso: (pregunta, nivel_esperado, descripcion_del_caso)
# nivel_esperado = None cuando no hay consenso docente sobre el nivel;
# el test verifica que el resultado sea un valor valido del conjunto.
CASES = [
    # ── Casos que fallaban con la version anterior (sin \b) ──────────────────
    (
        "¿Cual es la causa de la contraccion lantanida?",
        # ¿cual es? → recordar; antes sin \b disparaba 'aplicar' por 'usa' en 'causa'
        # Consenso docente: 'recordar' es aceptable (pregunta por un dato causal basico)
        "recordar",
        "causa contiene 'usa' → antes disparaba 'aplicar'; ahora captura 'cual es'→recordar",
    ),
    (
        "¿Que causa el efecto pantalla?",
        # Sin marcador lexico claro; antes sin \b disparaba 'aplicar'
        # Consenso docente: sin marcador → no_clasificado es correcto
        "no_clasificado",
        "causa contiene 'usa' → antes disparaba 'aplicar'; ahora correctamente no_clasificado",
    ),
    (
        "¿El principio de exclusion de Pauli aplica a bosones?",
        # 'aplica' es un verbo de nivel aplicar; que sea pregunta retorica es ambiguo.
        # Consenso docente: 'aplicar' es aceptable aqui.
        "aplicar",
        "'aplica' capturado como nivel aplicar (ambiguo pero aceptable)",
    ),
    (
        "Deduce la configuracion electronica del Cr",
        "analizar",
        "antes caia al default comprender por falta de marcador",
    ),
    (
        "Compara el modelo de Bohr con el cuantico",
        "comprender",
        "compara en dos niveles → debe ganar comprender",
    ),

    # ── Nivel: recordar ──────────────────────────────────────────────────────
    (
        "¿Que es un electron?",
        "recordar",
        "qué es → recordar",
    ),
    (
        "Define masa atomica",
        "recordar",
        "define → recordar",
    ),
    (
        "¿Cual es el numero atomico del carbono?",
        "recordar",
        "cuál es → recordar",
    ),
    (
        "Nombra los numeros cuanticos del electron",
        "recordar",
        "nombra → recordar",
    ),
    (
        "Enumera las propiedades del enlace covalente",
        "recordar",
        "enumera → recordar",
    ),

    # ── Nivel: comprender ────────────────────────────────────────────────────
    (
        "Explica por que los electrones no caen al nucleo segun la mecanica cuantica",
        "comprender",
        "explica → comprender",
    ),
    (
        "¿Como funciona el principio de exclusion de Pauli?",
        "comprender",
        "como → comprender",
    ),
    (
        "Resume el modelo atomico de Bohr",
        "comprender",
        "resume → comprender",
    ),
    (
        "¿Cual es la diferencia entre un orbital s y un orbital p?",
        "comprender",
        "diferencia → comprender",
    ),

    # ── Nivel: aplicar ───────────────────────────────────────────────────────
    (
        "Calcula la energia del nivel n=3 del hidrogeno segun Bohr",
        "aplicar",
        "calcula → aplicar",
    ),
    (
        "Resuelve la ecuacion de Schrodinger para el pozo infinito",
        "aplicar",
        "resuelve → aplicar",
    ),
    (
        "Estima el radio atomico del Na usando el modelo de capas",
        "aplicar",
        "estima → aplicar",
    ),

    # ── Nivel: analizar ──────────────────────────────────────────────────────
    (
        "Analiza por que el Cr tiene configuracion [Ar]3d5 4s1 en lugar de [Ar]3d4 4s2",
        "analizar",
        "analiza → analizar",
    ),
    (
        "Examina como afecta el efecto pantalla a la afinidad electronica",
        "analizar",
        "examina → analizar",
    ),
    (
        "¿Como se relaciona la electronegatividad con el tipo de enlace quimico?",
        "analizar",
        "relaciona → analizar",
    ),

    # ── Nivel: evaluar ───────────────────────────────────────────────────────
    (
        "Evalua si el modelo de Bohr es suficiente para explicar el espectro del helio",
        "evaluar",
        "evalua → evaluar",
    ),
    (
        "Justifica por que el hidrogeno tiene un espectro de emision discreto",
        "evaluar",
        "justifica → evaluar",
    ),
    (
        "Argumenta a favor o en contra de tratar el electron como una particula clasica",
        "evaluar",
        "argumenta → evaluar",
    ),

    # ── Nivel: no_clasificado ────────────────────────────────────────────────
    (
        "El electron tiene masa",
        "no_clasificado",
        "enunciado sin marcadores Bloom → no_clasificado",
    ),
    (
        "¿Por favor me puedes ayudar con estructura atomica?",
        "no_clasificado",
        "solicitud general sin verbo taxonomico",
    ),
]


def test_all_cases():
    """Todos los casos deben producir el nivel esperado."""
    failures = []
    for query, expected, description in CASES:
        nivel, _ = classify(query)
        assert nivel in VALID_LEVELS, f"Nivel invalido '{nivel}' para: {query}"
        if expected is not None and nivel != expected:
            failures.append(
                f"FALLO [{description}]\n"
                f"  Pregunta:  {query!r}\n"
                f"  Esperado:  {expected}\n"
                f"  Obtenido:  {nivel}"
            )
    if failures:
        raise AssertionError("\n\n" + "\n\n".join(failures))


def test_no_default_comprender_inflation():
    """
    El clasificador no debe devolver 'comprender' para preguntas sin marcadores.
    Antes del fix el default era 'comprender'; ahora debe ser 'no_clasificado'.
    """
    vague_queries = [
        "El electron tiene masa",
        "Me interesa la estructura atomica",
        "Hola, tengo una duda",
    ]
    for query in vague_queries:
        nivel, _ = classify(query)
        assert nivel != "comprender", (
            f"Default 'comprender' aun presente para pregunta sin marcadores: {query!r}"
        )


def test_word_boundary_usa_causa():
    """'causa' no debe disparar 'aplicar' por contener 'usa'."""
    nivel, _ = classify("¿Que causa la contraccion lantanida?")
    assert nivel != "aplicar", (
        "Falso positivo: 'causa' disparo 'aplicar' (sin limite de palabra)"
    )


def test_result_is_valid_level():
    """Cualquier entrada debe devolver un nivel del conjunto valido."""
    queries = [
        "", "   ", "?", "electronica", "QUE ES UN FOTON", "deducir la masa",
    ]
    for q in queries:
        nivel, descripcion = classify(q)
        assert nivel in VALID_LEVELS, f"Nivel invalido '{nivel}' para entrada: {q!r}"
        assert isinstance(descripcion, str)


if __name__ == "__main__":
    # Ejecutar y reportar tasa de acierto (util para el articulo)
    correct = 0
    total_with_expected = sum(1 for _, exp, _ in CASES if exp is not None)
    print(f"Ejecutando {len(CASES)} casos de prueba...\n")
    for query, expected, desc in CASES:
        nivel, _ = classify(query)
        ok = (expected is None or nivel == expected)
        status = "OK" if ok else "FALLO"
        if ok and expected is not None:
            correct += 1
        print(f"[{status}] {desc}")
        if not ok:
            print(f"       Esperado: {expected}  Obtenido: {nivel}")
            print(f"       Pregunta: {query}")
    print(f"\nTasa de acierto: {correct}/{total_with_expected} "
          f"({correct/total_with_expected*100:.1f}%)")
