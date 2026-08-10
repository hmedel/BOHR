from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import requests
import hashlib
import time
import json
import re
import logging
from typing import List, Dict, Optional
from collections import defaultdict
from .config import settings

logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.EMBEDDINGS_MODEL
        )
        
        self.vectorstore = Chroma(
            persist_directory=settings.CHROMA_PATH,
            embedding_function=self.embeddings,
            collection_name="documents"
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self.available_docs = self._get_available_docs()
        logger.info(f"RAG Engine: {len(self.available_docs)} docs, temp={settings.LLM_TEMPERATURE}")
    
    def _get_available_docs(self) -> List[str]:
        collection = self.vectorstore._collection
        results = collection.get()
        sources = set()
        for m in results['metadatas']:
            if 'source' in m:
                source = m['source']
                if not source.startswith('test_'):
                    sources.add(source)
        return sorted(list(sources))
    
    async def process_document(self, file_path: str, filename: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = hashlib.md5(filename.encode()).hexdigest()
        texts = self.text_splitter.split_text(content)
        
        logger.info(f"Total chunks: {len(texts)}")
        
        BATCH_SIZE = 20
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min((batch_num + 1) * BATCH_SIZE, len(texts))
            batch_texts = texts[start_idx:end_idx]
            
            documents = [
                Document(
                    page_content=text,
                    metadata={"source": filename, "doc_id": doc_id, "chunk_id": start_idx + i}
                )
                for i, text in enumerate(batch_texts)
            ]
            
            try:
                self.vectorstore.add_documents(documents)
                logger.info(f"Batch {batch_num + 1}/{total_batches} OK")
                time.sleep(0.5)
            except Exception as e:
                logger.info(f"Batch {batch_num + 1}/{total_batches} ERROR: {str(e)[:100]}")
        
        logger.info(f"Documento completo: {len(texts)} chunks")
        return doc_id
    
    def _call_llm(self, prompt: str, temperature: float = None) -> str:
        """Llamada al LLM con temperatura configurable"""
        temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
        
        try:
            response = requests.post(
                f"{settings.DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": temp
                },
                timeout=60
            )
        except requests.Timeout:
            raise Exception("El servicio de IA tardó demasiado en responder. Intenta de nuevo en unos momentos.")
        except requests.ConnectionError:
            raise Exception("No se pudo conectar al servicio de IA. Verifica la conexión e intenta de nuevo.")

        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")

        return response.json()["choices"][0]["message"]["content"]
    
    def _remove_unicode_math_duplicates(self, text: str) -> str:
        """
        Limpia expresiones matemáticas Unicode fuera de delimitadores LaTeX.
        DeepSeek a veces duplica ecuaciones: una vez en LaTeX y otra en Unicode plano.

        Estrategia:
        1. Corregir $...$ multilínea → $$...$$
        2. Eliminar expresiones Unicode math inline (secuencias de símbolos math)
        3. Eliminar líneas que son solo ecuaciones Unicode
        """
        # Paso 0: Corregir bloques $\n...\n$ → $$...$$ (display mode)
        text = re.sub(
            r'(?<!\$)\$\n((?:.*\n)*?)\$(?!\$)',
            lambda m: '$$\n' + m.group(1) + '$$',
            text
        )
        # $ seguido de \begin → $$
        text = re.sub(
            r'(?<!\$)\$\s*\n\s*(\\begin\{)',
            r'$$\n\1',
            text
        )
        text = re.sub(
            r'(\\end\{[^}]+\})\s*\n\s*\$(?!\$)',
            r'\1\n$$',
            text
        )

        # Paso 1: Proteger contenido dentro de $...$ y $$...$$
        # Reemplazar con placeholders para no tocarlos
        latex_blocks = []
        def protect_latex(m):
            latex_blocks.append(m.group(0))
            return f'%%LATEXBLOCK_{len(latex_blocks)-1}%%'

        # Proteger $$...$$ (incluyendo multilínea)
        text = re.sub(r'\$\$[\s\S]*?\$\$', protect_latex, text)
        # Proteger $...$
        text = re.sub(r'\$[^$\n]+?\$', protect_latex, text)

        # Paso 2: Regex para detectar expresiones Unicode math
        # Secuencias de 2+ caracteres math/operadores/subíndices/superíndices
        # que parecen ecuaciones (ej: ∇⋅E=ρ/ε₀, ∑i=1Z, ℏ²/2m∇i²)
        unicode_math_expr = re.compile(
            r'[∑∫∂∇√∞≈≠≤≥±×÷∏πΔΣΠΩαβγδεζηθλμρστφψωℏ⋅'
            r'⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉'
            r'⟨⟩→←↑↓⟶⟵'
            r'A-Za-z0-9=+\-/()^_,.\s]*'
            r'[∑∫∂∇√∞≈≠≤≥±×÷∏πΔΣΠΩαβγδεζηθλμρστφψωℏ⋅'
            r'⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉'
            r'⟨⟩→←↑↓⟶⟵]'
        )

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Si tiene placeholder de LaTeX, conservar sin tocar
            if '%%LATEXBLOCK_' in line:
                cleaned_lines.append(line)
                continue

            # Buscar expresiones Unicode math en la línea
            matches = list(unicode_math_expr.finditer(line))
            if not matches:
                cleaned_lines.append(line)
                continue

            # Calcular cuánto de la línea es Unicode math
            math_chars = sum(m.end() - m.start() for m in matches)
            total_chars = len(line.strip())

            if total_chars == 0:
                cleaned_lines.append(line)
                continue

            math_ratio = math_chars / total_chars

            if math_ratio > 0.6:
                # La línea es mayoritariamente ecuación Unicode → eliminar
                logger.debug(f"[POST-PROC] Eliminando línea ({math_ratio:.0%} math): {line[:80]}")
                continue
            else:
                # La línea tiene texto + ecuaciones Unicode inline → limpiar las ecuaciones
                cleaned = line
                for m in reversed(matches):  # reversed para no afectar índices
                    expr = m.group(0).strip()
                    if len(expr) > 3:  # Solo limpiar expresiones significativas
                        logger.debug(f"[POST-PROC] Eliminando expr inline: {expr[:60]}")
                        cleaned = cleaned[:m.start()] + cleaned[m.end():]

                # Limpiar espacios dobles y paréntesis vacíos que queden
                cleaned = re.sub(r'\(\s*\)', '', cleaned)
                cleaned = re.sub(r'\s{2,}', ' ', cleaned)
                cleaned = cleaned.strip()

                if cleaned and len(cleaned) > 5:
                    cleaned_lines.append(cleaned)
                else:
                    logger.debug(f"[POST-PROC] Línea vacía después de limpiar, eliminando")

        # Paso 3: Restaurar bloques LaTeX protegidos
        result = '\n'.join(cleaned_lines)
        for i, block in enumerate(latex_blocks):
            result = result.replace(f'%%LATEXBLOCK_{i}%%', block)

        return result
    
    def _detect_exam_mode(self, query: str) -> bool:
        """Detectar si el usuario solicita un examen"""
        exam_triggers = [
            "terminé", "termine", "listo para examen", "haz el examen",
            "quiero un examen", "evaluame", "hazme un examen", "test", "quiz"
        ]
        query_lower = query.lower()
        return any(trigger in query_lower for trigger in exam_triggers)
    async def query_multi_source_with_synthesis(
        self,
        query: str,
        sources_count: int = 3,
        chunks_per_source: int = 10,
        conversation_history: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict:
        """
        Búsqueda multi-fuente CON SÍNTESIS del LLM para respuestas claras y ordenadas
        
        Args:
            query: Consulta del usuario
            sources_count: Número de fuentes diferentes a usar (default: 3)
            chunks_per_source: Chunks por fuente para contexto (default: 20)
        
        Returns:
            {
                "synthesized_answer": "explicación clara y ordenada del LLM",
                "sources_used": ["fuente1", "fuente2", "fuente3"],
                "raw_context": "contexto combinado de todas las fuentes",
                "response_time": 1.23
            }
        """
        from datetime import datetime
        
        start_time = time.time()
        
        # Obtener documentos disponibles
        available_docs = self.available_docs
        
        if not available_docs:
            return {
                "synthesized_answer": "No hay documentos indexados en el sistema.",
                "sources_used": [],
                "raw_context": "",
                "response_time": 0
            }
        
        # FORZAR DIVERSIDAD: Buscar explícitamente en CADA documento
        contexts_by_source = []
        sources_used = []
        results_by_source = {}
        
        logger.info(f"🔍 Búsqueda multi-fuente con síntesis: {len(available_docs)} docs disponibles")
        
        # PASO 1: Buscar EN CADA FUENTE por separado para garantizar diversidad
        for doc in available_docs:
            try:
                # WORKAROUND: ChromaDB ignora k con filter, buscar más y limitar manualmente
                doc_results = self.vectorstore.similarity_search(
                    query,
                    k=50,  # Solicitar más de lo necesario
                    filter={"source": doc}
                )
                
                # FORZAR límite manualmente (ChromaDB bug con filter+k)
                doc_results = doc_results[:chunks_per_source]
                
                if doc_results:
                    results_by_source[doc] = doc_results
                    logger.debug(f"  ✓ {doc[:40]}: {len(doc_results)} chunks")
                    
            except Exception as e:
                logger.warning(f"  ✗ {doc[:40]}: Error - {str(e)[:50]}")
        
        logger.info(f"  📚 Fuentes con resultados: {len(results_by_source)}")
        
        # PASO 2: Ordenar fuentes por SCORE DE RELEVANCIA (suma de distancias)
        # Cada chunk tiene una distancia implícita - ChromaDB retorna los más cercanos primero
        # Calculamos score: más chunks + mejor posición = mayor score
        source_scores = {}
        for doc, results in results_by_source.items():
            # Score = número de chunks * factor de posición promedio
            # Chunks en posiciones tempranas tienen más peso
            position_weights = [(chunks_per_source - i) for i in range(len(results))]
            avg_position = sum(position_weights) / len(results) if results else 0
            source_scores[doc] = len(results) * avg_position
        
        sorted_sources = sorted(
            results_by_source.items(),
            key=lambda x: source_scores[x[0]],
            reverse=True
        )
        
        # PASO 3: Tomar las TOP N fuentes
        sources_to_use = min(sources_count, len(sorted_sources))
        top_sources = sorted_sources[:sources_to_use]
        
        logger.info(f"  🎯 Usando {sources_to_use} fuentes:")
        
        # PASO 4: Combinar contextos de las fuentes seleccionadas
        for rank, (source, results) in enumerate(top_sources, 1):
            try:
                # Combinar chunks de esta fuente
                combined_content = "\n\n".join([
                    result.page_content for result in results
                ])
                
                source_name = source.replace('.md', '').replace('_', ' ')
                contexts_by_source.append(f"**[Fuente {rank}: {source_name}]**\n{combined_content}")
                sources_used.append(source_name)
                
                logger.debug(f"     {rank}. {source[:45]}: {len(results)} chunks")
                
            except Exception as e:
                logger.warning(f"  ✗ {source[:40]}: Error - {str(e)[:50]}")
        
        # Combinar contextos
        full_context = "\n\n---\n\n".join(contexts_by_source)
        
        # PROMPT OPTIMIZADO: IR DIRECTO AL GRANO
        # Construir lista de fuentes con nombres reales
        sources_list_str = ", ".join([f"[{name}]" for name in sources_used])
        
        # Construir bloque de historial si existe
        history_block = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-6:]:  # últimos 3 intercambios
                role = "Estudiante" if msg["role"] == "user" else "Tutor"
                # Truncar respuestas largas del tutor para no saturar el contexto
                content = msg["content"]
                if msg["role"] == "assistant" and len(content) > 400:
                    content = content[:400] + "…"
                lines.append(f"{role}: {content}")
            history_block = "## CONVERSACIÓN PREVIA\n" + "\n\n".join(lines) + "\n\n"

        # Usar raw string para preservar backslashes de LaTeX
        synthesis_prompt = rf"""Eres un tutor experto en química/física atómica. Proporciona respuestas completas y educativas.

{history_block}## PREGUNTA ACTUAL
{query}

## CONTEXTO DISPONIBLE
{full_context}

## REGLAS CRÍTICAS

1. **RESPUESTA DIRECTA Y COMPLETA:**
   - Responde la pregunta INMEDIATAMENTE en las primeras 2-3 líneas
   - Si piden una ecuación, muéstrala PRIMERO en $$...$$ antes de cualquier explicación
   - Si piden una definición, da la definición PRIMERO antes de contexto histórico

2. **ESTRUCTURA OBLIGATORIA (en este orden):**
   
   **PRIMERO - Respuesta Directa:**
   - Si pregunta ecuación → mostrar $$ecuación$$ INMEDIATAMENTE
   - Si pregunta concepto → definición clara
   - Si pregunta "qué es" → responder "es..." sin rodeos
   
   **SEGUNDO - Explicación Completa:**
   - Explica TODOS los términos de la ecuación (si aplica)
   - Desarrolla el significado físico completamente
   - Conecta con conceptos relacionados del contexto
   - Si hay información histórica o experimental relevante, inclúyela
   
   **TERCERO - Elaboración Contextual:**
   - Ejemplos específicos del contexto
   - Aplicaciones prácticas mencionadas en las fuentes
   - Relaciones con otros conceptos del material
   - Implicaciones o consecuencias teóricas

3. **ELABORACIÓN RESPONSABLE:**
   - Desarrolla COMPLETAMENTE toda la información disponible en el contexto
   - Si el contexto menciona derivaciones, desarróllalas paso a paso
   - Si hay múltiples perspectivas en las fuentes, preséntalas todas
   - Conecta conceptos entre fuentes cuando sea apropiado
   - **NUNCA inventes información** - solo elabora lo que está en el contexto
   - Si falta información, dilo explícitamente

4. **FORMATO LaTeX ULTRA-ESTRICTO (NO NEGOCIABLE):**
   
   **REGLA DE ORO: CERO UNICODE EN TEXTO**
   - ❌ PROHIBIDO ABSOLUTO: ∑, ℏ, ∇, ², ₂, π, ε, cualquier símbolo matemático fuera de $...$
   - ✅ OBLIGATORIO: TODO símbolo matemático DEBE estar dentro de delimitadores LaTeX
   
   **Delimitadores permitidos:**
   - Display (ecuaciones completas): $$ecuación$$
   - Inline (símbolos aislados): $símbolo$
   
   **CÓMO REFERENCIAR ECUACIONES EN EXPLICACIONES:**
   
   ✅ **CORRECTO - Usar nombres descriptivos:**
   - "el primer término representa la energía cinética"
   - "la atracción coulómbica entre el electrón y el núcleo"
   - "el operador Hamiltoniano total"
   - "la suma sobre todos los electrones"
   
   ✅ **CORRECTO - Referencias inline con LaTeX:**
   - "el término $-\frac{{\hbar^2}}{{2m}}\nabla^2$ es la energía cinética"
   - "donde $\hat{{H}}$ es el Hamiltoniano"
   - "para Z=47 en el caso de la plata"
   
   ❌ **PROHIBIDO - Repetir ecuaciones en texto plano:**
   - "Energía cinética: ∑ᵢ(-ℏ²/2m)∇²ᵢ" ← NUNCA HAGAS ESTO
   - "El potencial: -Ze²/4πε₀r" ← NUNCA HAGAS ESTO
   - "Repulsión: ∑ᵢ﹤ⱼ e²/4πε₀rᵢⱼ" ← NUNCA HAGAS ESTO
   
   **SI NECESITAS MOSTRAR UNA ECUACIÓN:**
   1. Primera vez: Usa $$ecuación completa$$
   2. En explicaciones posteriores: USA NOMBRES, NO REPITAS LA ECUACIÓN
   3. Si DEBES referenciar partes: Usa inline LaTeX ($...$)

   **BLOQUES MULTILÍNEA:**
   - SIEMPRE usa $$ (doble dólar) para bloques con \begin{{aligned}}, \begin{{equation}}, etc.
   - NUNCA uses $ (un solo dólar) para ecuaciones multilínea
   - ✅ CORRECTO: $$\begin{{aligned}} ... \end{{aligned}}$$
   - ❌ INCORRECTO: $\begin{{aligned}} ... \end{{aligned}}$

   **EN EXPLICACIONES DE TÉRMINOS (CRÍTICO):**
   - Cuando expliques cada término de una ecuación, usa SOLO texto descriptivo
   - ❌ PROHIBIDO: "Ley de Gauss (∇⋅E = ρ/ε₀):" ← Unicode duplicado
   - ❌ PROHIBIDO: "donde ∇⋅E es la divergencia" ← Unicode suelto
   - ✅ CORRECTO: "**Ley de Gauss para el campo eléctrico:** El flujo del campo eléctrico..."
   - ✅ CORRECTO: "donde $\nabla \cdot \mathbf{{E}}$ es la divergencia" ← inline LaTeX

5. **SI NO HAY INFORMACIÓN SUFICIENTE:**
   - Responder: "Las fuentes contienen [lo disponible] pero no mencionan [lo faltante]"
   - Desarrolla completamente lo que SÍ está disponible

6. **IDIOMA:** Español, traduciendo del inglés si es necesario

7. **CITAS:** Terminar con "Fuentes: {sources_list_str}"
   - USA EXACTAMENTE LOS NOMBRES DE FUENTES PROPORCIONADOS
   - NO inventes nombres ni uses genéricos como "Fuente 1"

**EJEMPLO COMPLETO DE RESPUESTA CORRECTA:**

Usuario: "¿Cuál es el Hamiltoniano del átomo de plata?"

Respuesta CORRECTA:
"$$\hat{{H}} = \sum_{{i=1}}^{{47}} \left(-\frac{{\hbar^2}}{{2m}}\nabla_i^2 - \frac{{Ze^2}}{{4\pi\varepsilon_0 r_i}}\right) + \sum_{{i<j}} \frac{{e^2}}{{4\pi\varepsilon_0 r_{{ij}}}} + \hat{{H}}_{{rel}} + \hat{{H}}_{{SO}}$$

El Hamiltoniano tiene cuatro términos principales:

1. **Energía cinética de los 47 electrones:** El primer término en la sumatoria describe el movimiento cuántico de cada electrón.

2. **Atracción nuclear-electrón:** El segundo término en la primera suma representa la atracción coulómbica entre el núcleo (con $Z=47$) y cada electrón.

3. **Repulsión interelectrónica:** La doble sumatoria captura las interacciones repulsivas entre pares de electrones.

4. **Correcciones relativistas:** Los términos $\hat{{H}}_{{rel}}$ y $\hat{{H}}_{{SO}}$ incluyen efectos de masa variable y acoplamiento espín-órbita, críticos para átomos pesados.

Fuentes: {sources_list_str}"

**EJEMPLO DE RESPUESTA INCORRECTA (PROHIBIDA - NO IMITAR):**

❌ "$$\hat{{H}} = ...$$

Términos:

Energía cinética: ∑ᵢ(-ℏ²/2m)∇²ᵢ  ← PROHIBIDO: Unicode fuera de LaTeX
Potencial: -Ze²/4πε₀rᵢ  ← PROHIBIDO: Unicode fuera de LaTeX
"

**CHECKLIST ANTES DE RESPONDER:**
- [ ] ¿Usé $$...$$ para la ecuación principal?
- [ ] ¿Expliqué términos con NOMBRES DESCRIPTIVOS en lugar de repetir ecuaciones?
- [ ] ¿Revisé que NO hay ∑, ℏ, ∇, ², ₂, π, ε fuera de delimitadores LaTeX?
- [ ] ¿Usé $...$ inline solo cuando es estrictamente necesario?

**RESPONDE AHORA (RECUERDA: DIRECTO AL GRANO, ECUACIÓN PRIMERO SI LA PIDEN):"""

        # Modo streaming: devolver el prompt para que el caller haga la llamada LLM
        if stream:
            return {
                "synthesis_prompt": synthesis_prompt,
                "sources_used": sources_used,
                "raw_context": full_context[:500] + "...",
            }

        try:
            # Llamar al LLM para síntesis con temperatura moderada-alta (más elaboración sin alucinar)
            synthesized_answer = self._call_llm(synthesis_prompt, temperature=0.5)

            # POST-PROCESAMIENTO: Eliminar líneas con Unicode matemático
            synthesized_answer = self._remove_unicode_math_duplicates(synthesized_answer)
        except Exception as e:
            synthesized_answer = f"Error al sintetizar la respuesta: {str(e)}"

        response_time = time.time() - start_time

        logger.info(f"✅ Síntesis completada: {len(sources_used)} fuentes, {response_time:.2f}s")

        return {
            "synthesized_answer": synthesized_answer,
            "sources_used": sources_used,
            "raw_context": full_context[:500] + "...",
            "response_time": response_time
        }

    
    async def query(
        self, 
        query: str, 
        top_k: int = 5, 
        max_context: int = 3000,
        filter_source: Optional[str] = None
    ) -> Dict:
        """
        RAG con prompt estricto anti-alucinación y modo examen
        """
        start_time = time.time()
        
        # Detectar modo examen
        is_exam_mode = self._detect_exam_mode(query)
        
        if filter_source:
            results = self.vectorstore.similarity_search(
                query, 
                k=top_k,
                filter={"source": filter_source}
            )
        else:
            # Búsqueda multi-libro
            all_results = []
            chunks_per_book = 2
            
            logger.info(f"🔍 Búsqueda multi-libro: {len(self.available_docs)} docs")
            
            for doc in self.available_docs:
                try:
                    doc_results = self.vectorstore.similarity_search(
                        query,
                        k=chunks_per_book,
                        filter={"source": doc}
                    )
                    all_results.extend(doc_results)
                    logger.debug(f"  • {doc[:40]}: {len(doc_results)} chunks")
                except Exception as e:
                    logger.warning(f"  ✗ {doc[:40]}: Error - {str(e)[:50]}")
            
            results = all_results
        
        if not results:
            return {
                "answer": "**No se encontró información relevante.** Por favor, reformula tu pregunta con términos más específicos o indica el capítulo/sección del material.",
                "sources": [],
                "context_used": "",
                "response_time": time.time() - start_time,
                "relevance_scores": []
            }
        
        results = results[:top_k]
        
        # Construir contexto con citas explícitas
        contexts = []
        sources = []
        
        for i, result in enumerate(results):
            source = result.metadata.get("source", "unknown")
            source_name = source.replace('.md', '').replace('_', ' ')
            
            content = result.page_content
            contexts.append(f"**[Fuente {i+1}: {source_name}]**\n{content}\n")
            sources.append(source)
        
        combined_context = "\n---\n".join(contexts)
        
        # PROMPT ESTRICTO
        if is_exam_mode:
            prompt = self._build_exam_prompt(combined_context, query, sources)
        else:
            prompt = f"""# ROL
Eres un tutor de química universitaria. Tu ÚNICA fuente de verdad es el contexto proporcionado.

# REGLAS RAG (ESTRICTAS)
1. **Relevancia**: Usa SOLO fragmentos que respondan DIRECTAMENTE la pregunta. Descarta el resto.
2. **Suficiencia**: Si el contexto NO alcanza para una respuesta completa, dilo explícitamente.
3. **No alucinar**: NO completes con conocimiento externo. SOLO usa el contexto.
4. **Contradicciones**: Si hay choques entre fuentes, enuméralos y cita ambos.
5. **Citas**: Cada afirmación debe rastrearse a un fragmento específico.

# CHEQUEO PREVIO (interno)
- ¿Es relevante el contexto? ¿Es suficiente? ¿Es citable?
- Si alguna es "no", indícalo al usuario.

# CONTEXTO
{combined_context}

# PREGUNTA
{query}

# FORMATO DE RESPUESTA (Modo Consulta)

## Respuesta
[2-4 líneas, directa, SOLO con el contexto]

## Conceptos Clave
- [Definición/ecuación del contexto]
- [Otra definición relevante]

## Ejemplo
[Solo si está en el contexto o es derivación inmediata]

## Fuentes Utilizadas
[Lista solo los fragmentos usados con [Fuente X]]

# ECUACIONES
- Inline: Use $ecuación$ 
- Display: Use $$ecuación$$
- Ejemplo: La energía es $E = mc^2$ o en display $$E = mc^2$$

# PLANTILLAS DE FALLO
- **Parcial**: "Con base en lo disponible: [respuesta parcial]. **Falta información sobre [X]**. Se requiere [cap/sección] del material."
- **Vacío**: "El contexto recuperado NO cubre [tema]. Sugiero refinar con: [palabras clave] o indicar capítulo/sección."
- **Contradictorio**: "**Conflicto detectado**: [Fuente A] dice [X] vs [Fuente B] dice [Y]. Ambos son válidos en contextos diferentes."

RESPONDE:"""
        
        try:
            answer = self._call_llm(prompt)
        except Exception as e:
            answer = f"Error al procesar: {str(e)}"
        
        response_time = time.time() - start_time
        unique_sources = list(set(sources))
        
        logger.info(f"✅ Respuesta: {len(unique_sources)} fuentes, {response_time:.2f}s")
        
        return {
            "answer": answer,
            "sources": unique_sources,
            "context_used": combined_context[:300] + "...",
            "response_time": response_time,
            "relevance_scores": []
        }
    
    def _build_exam_prompt(self, context: str, query: str, sources: List[str]) -> str:
        """Construir prompt para modo examen"""
        return f"""# MODO EXAMEN

Genera un examen basado EXCLUSIVAMENTE en el siguiente contexto.

# CONTEXTO
{context}

# CONDICIONES
- Solo sobre temas cubiertos en el contexto
- 2-5 preguntas
- Al menos 1 de cálculo si hay fórmulas
- TODO debe ser citable al contexto

# FORMATO JSON
{{
  "tipo_examen": "Evaluación de [temas del contexto]",
  "instrucciones": "Responde todo. Muestra procedimiento.",
  "preguntas": [
    {{
      "num": 1,
      "tipo": "opcion_multiple",
      "enunciado": "...",
      "opciones": ["A) ...","B) ...","C) ...","D) ..."],
      "respuesta_correcta": "B",
      "justificacion": "Cita específica del contexto",
      "fuente": "[Fuente X]"
    }}
  ],
  "distribucion": "40% recuerdo, 30% aplicación, 30% análisis",
  "tiempo_sugerido": "20-30 min",
  "temas_excluidos": "[si aplica]"
}}

GENERA EL EXAMEN:"""
    
    async def list_documents(self) -> List[Dict]:
        collection = self.vectorstore._collection
        results = collection.get()
        
        source_stats = {}
        for metadata in results['metadatas']:
            if 'source' in metadata:
                source = metadata['source']
                if not source.startswith('test_'):
                    if source not in source_stats:
                        source_stats[source] = {
                            "filename": source,
                            "doc_id": hashlib.md5(source.encode()).hexdigest(),
                            "chunks": 0
                        }
                    source_stats[source]["chunks"] += 1
        
        return list(source_stats.values())
    
    async def delete_document(self, doc_id: str):
        self.vectorstore._collection.delete(where={"doc_id": doc_id})
