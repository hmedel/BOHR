# Manual de codificación Bloom y SOLO, y banco de reactivos abiertos

Proyecto BOHR — Estructura de la Materia, FESC-UNAM  
Versión 1.1. Documento de trabajo para dos codificadores docentes.

*Cambios v1.1 (2026-08-14): reactivos R5.1, R6.1 y R7.1 completados con elementos esperados, anclas relacionales/abstracto extendido y techo. Sin cambios en protocolo, reglas de desempate ni reactivos R1–R4.*

Este manual tiene dos usos independientes:

- **Parte A y B**: codificar consultas reales de estudiantes con la taxonomía revisada de Bloom, para estimar la validez del clasificador automático.
- **Parte C y D**: codificar respuestas abiertas de estudiantes con SOLO, y el banco de enunciados que las produce.

Las dos partes se codifican por separado y no deben mezclarse en la misma sesión de trabajo.

---

# PARTE A — Protocolo de muestreo (Bloom)

## A.1 Población

Todas las filas de `messages` con `role = 'user'` generadas hasta la fecha de corte. La fecha de corte se fija antes de extraer y no se modifica después.

## A.2 Criterios de exclusión

Se definen antes de mirar los datos y se aplican automáticamente. Se reporta el número de exclusiones por categoría.

| Código | Criterio |
|---|---|
| E1 | Menos de 15 caracteres tras eliminar espacios |
| E2 | Saludo, agradecimiento o despedida sin contenido químico |
| E3 | Petición de examen, cancelación, o interacción con el sistema |
| E4 | Duplicado exacto o con distancia de edición menor a 5 respecto de otra consulta del mismo usuario |
| E5 | Sin ningún contenido químico identificable |

No se excluye por estar mal escrita, por tener faltas de ortografía ni por ser vaga. Esas son parte del fenómeno.

## A.3 Diseño de muestra

Dos muestras, reportadas por separado:

- **Muestra principal**: 150 consultas por aleatorización simple sobre la población depurada. Es la que produce la estimación de acuerdo. El muestreo aleatorio garantiza que el estimador sea representativo del uso real.
- **Muestra complementaria**: hasta 60 consultas seleccionadas al azar dentro de los estratos que el clasificador automático asigna a `analizar`, `evaluar` y `crear`, hasta un máximo de 20 por estrato. Sirve para tener casos suficientes en niveles poco frecuentes.

La muestra complementaria **no se agrega** a la principal para calcular el acuerdo global. Se reporta aparte, y se advierte explícitamente que está estratificada por la variable que se está evaluando.

Con 150 ítems y seis categorías, el intervalo de confianza del kappa será amplio. Es aceptable y hay que reportarlo, no ocultarlo.

## A.4 Condiciones de codificación

- Los dos codificadores trabajan de forma independiente y no comparan resultados hasta terminar.
- La columna con la salida del clasificador automático no aparece en el archivo de codificación.
- El orden de los ítems se aleatoriza de forma distinta para cada codificador.
- Se codifica solo el texto de la consulta. No se consulta la respuesta que dio el sistema ni el turno anterior, salvo en el caso previsto en la regla R7.
- Sesiones de máximo 50 ítems para evitar deriva por fatiga.

**Cómo obtener los archivos de codificación:**

```
GET /admin/export/bloom-coding?seed=42    # codificador 1
GET /admin/export/bloom-coding?seed=99    # codificador 2
```

El endpoint devuelve un ZIP con el CSV principal, el complementario y un JSON de estadísticas de muestreo. Requiere token de administrador.

---

# PARTE B — Manual de codificación Bloom

Cada consulta recibe dos códigos: **proceso cognitivo** y **tipo de conocimiento**. Son dimensiones independientes; toda combinación es posible.

## B.1 Principio rector

**Se codifica lo que la consulta solicita, no lo que haría falta para responderla bien.**

Una pregunta puede requerir análisis sofisticado para ser contestada y aun así estar solicitando una explicación. La taxonomía se aplica a la demanda expresada, no a la dificultad del contenido. Este principio resuelve la mayoría de las discrepancias y hay que tenerlo presente en cada ítem.

## B.2 Dimensión de proceso cognitivo

**Recordar.** Solicita un dato, valor, nombre, definición o enunciado que puede recuperarse de una fuente sin transformarlo.
*Ejemplo:* «¿Cuál es el valor de la constante de Rydberg?»

**Comprender.** Solicita que se reformule, ejemplifique, resuma, clasifique, compare o explique el significado de algo. Incluye la petición de una explicación causal estándar y la de un procedimiento descrito en abstracto.
*Ejemplo:* «Explícame qué significa que un orbital sea una función de onda.»

**Aplicar.** Solicita ejecutar un procedimiento conocido sobre un caso concreto que la consulta especifica.
*Ejemplo:* «Determina la configuración electrónica del Cr.»

**Analizar.** Solicita descomponer, distinguir lo relevante de lo irrelevante, atribuir una causa entre varias posibles, o determinar cómo se relacionan las partes dentro de una estructura. Incluye pedir explicación de una excepción respecto de una regla general.
*Ejemplo:* «¿Por qué la primera energía de ionización del oxígeno es menor que la del nitrógeno si la carga nuclear es mayor?»

**Evaluar.** Solicita un juicio contra criterios: validez, adecuación, superioridad, corrección de un razonamiento.
*Ejemplo:* «¿Sigue siendo válido el modelo de Bohr para algo, o está completamente superado?»

**Crear.** Solicita generar algo que no está dado: un modelo, un experimento, una hipótesis, una analogía propia.
*Ejemplo:* «Propón una forma de comprobar experimentalmente que los electrones tienen comportamiento ondulatorio.»

**Indeterminable.** Se usa cuando la consulta es un fragmento, depende de un turno anterior no disponible, o admite dos niveles con igual plausibilidad sin que ninguna regla lo resuelva.

Esta categoría **debe usarse**. Forzar un nivel en casos ambiguos infla artificialmente el acuerdo. Si un codificador nunca la usa, hay que revisar si está adivinando.

## B.3 Reglas de desempate

Se aplican en orden. La primera que resuelve el caso decide.

**R1 — Demanda expresada.** Codificar lo solicitado, no lo requerido para responder. (Principio rector, B.1.)

**R2 — Preguntas con "¿por qué?".** Por defecto, **comprender**: piden una explicación causal estándar. Se codifica **analizar** solo si concurre alguna de estas condiciones:
- pide contrastar o jerarquizar dos o más factores posibles;
- pide explicar una anomalía o excepción respecto de una regla que la propia consulta enuncia;
- pide atribuir cuál de varios componentes es responsable del efecto.

*Comprender:* «¿Por qué disminuye el radio atómico a lo largo de un periodo?»  
*Analizar:* «¿Por qué disminuye el radio atómico a lo largo de un periodo si también se están agregando electrones que deberían repelerse?»

**R3 — Preguntas de diferencia o comparación.** Por defecto, **comprender**. Se codifica **analizar** si pide identificar qué factor produce la diferencia, o discriminar cuál de los dos aplica en un caso dado.

*Comprender:* «¿Cuál es la diferencia entre un orbital y una órbita?»  
*Analizar:* «¿Qué característica del modelo cuántico es la que impide hablar de órbitas definidas?»

**R4 — Procedimiento con o sin caso.** Si la consulta especifica un caso concreto sobre el que ejecutar el procedimiento, **aplicar**. Si pide el procedimiento en abstracto, **comprender**.

*Aplicar:* «Calcula la longitud de onda de la transición n=3 a n=2 en el hidrógeno.»  
*Comprender:* «¿Cómo se calculan las longitudes de onda de la serie de Balmer?»

**R5 — Consultas de varias partes.** Codificar el nivel más alto solicitado. Marcar `multiparte = 1` en columna aparte.

**R6 — Verificación de un razonamiento propio.** Si el estudiante expone un razonamiento y pide juicio sobre su validez, **evaluar**. Si solo pide confirmación de un dato o de una definición, codificar según el contenido (recordar o comprender).

*Evaluar:* «Si digo que el 4s se llena antes que el 3d porque tiene menor energía, ¿es correcto ese argumento?»  
*Recordar:* «¿Es cierto que el cromo tiene configuración 3d⁵4s¹?»

**R7 — Dependencia del contexto.** Si la consulta es incomprensible sin el turno anterior («¿y en el caso del cobre?»), codificar **indeterminable** y marcar `dependiente_contexto = 1`. No recuperar el turno anterior: el clasificador tampoco lo hace, y la comparación debe ser justa.

**R8 — Cortesía y preámbulo.** Ignorar fórmulas de cortesía y expresiones de dificultad («no entiendo nada, pero...») para la codificación del proceso cognitivo. Marcarlas en `expresion_dificultad` si están presentes.

## B.4 Dimensión de tipo de conocimiento

**Factual.** Datos aislados, terminología, valores numéricos, nombres, símbolos.  
**Conceptual.** Modelos, principios, clasificaciones, relaciones entre elementos, teorías.  
**Procedimental.** Métodos, algoritmos, criterios para decidir cuándo usar un procedimiento.  
**Metacognitivo.** Sobre el propio conocimiento o la estrategia de estudio. «¿Qué me conviene repasar antes del examen?»

Regla: si la consulta mezcla factual y conceptual, codificar **conceptual** cuando lo solicitado es la relación o el modelo, y **factual** cuando lo solicitado es el dato aunque esté enmarcado en un modelo.

## B.5 Formato del archivo de codificación

CSV, una fila por ítem, columnas:

```
id_item, texto_consulta, proceso_cognitivo, tipo_conocimiento,
multiparte, dependiente_contexto, expresion_dificultad,
confianza, nota
```

`confianza`: 1 = segura, 2 = dudosa. Sirve para analizar si el desacuerdo se concentra en los ítems que los propios codificadores marcaron como dudosos.  
`nota`: texto libre, solo cuando la regla aplicada no fue obvia.

---

# PARTE C — Manual de codificación SOLO

## C.1 Qué codifica SOLO y qué no

SOLO describe la **estructura** de una respuesta en relación con una tarea. No describe a la persona, no mide corrección química y no depende de la extensión.

**El enunciado fija el techo alcanzable.** Una respuesta no puede ser relacional si la tarea no admite relacionar. Por eso SOLO solo se codifica sobre respuestas a los reactivos abiertos de la Parte D, nunca sobre conversación libre.

> **Nota metodológica — Bloom y SOLO son escalas independientes.**  
> El sistema BOHR registra el nivel Bloom de la *pregunta* (inferido del verbo
> de la consulta) y el nivel SOLO de la *respuesta* (codificado manualmente sobre
> los reactivos de la Parte D). Cualquier mapeo entre ambas escalas —por ejemplo,
> asumir que una pregunta de nivel *analizar* espera una respuesta *relacional*—
> es un **supuesto de los autores de este sistema**, no una correspondencia
> establecida por Anderson y Krathwohl (2001) ni por Biggs y Collis (1982).
> Los datos de este estudio no permiten concluir que ambas taxonomías estén
> correlacionadas. Esa hipótesis requeriría un diseño de investigación separado.

## C.2 Los cinco niveles, operacionalizados

**Preestructural.** No aborda la tarea. Repite el enunciado, usa elementos irrelevantes, o es incoherente. Incluye «no sé» y equivalentes.

**Uniestructural.** Identifica **un** elemento relevante y correcto de la tarea, y se detiene ahí.

**Multiestructural.** Identifica **dos o más** elementos relevantes, pero los presenta yuxtapuestos o enumerados, sin establecer una relación explícita entre ellos.

**Relacional.** Integra los elementos mediante una relación explícita —causal, condicional, jerárquica o de dependencia— que responde a la tarea como un todo.

**Abstracto extendido.** Además de integrar, generaliza a un caso no contenido en la tarea, formula un principio, transfiere el razonamiento a otro contexto, o identifica los límites de validez del modelo empleado.

## C.3 Reglas de codificación

**S1 — La extensión no es evidencia.** Tres líneas que enuncian una relación causal correcta son relacionales. Doscientas palabras enumerando sin integrar son multiestructurales. Si un codificador se descubre usando la longitud como pista, debe detenerse y releer.

**S2 — Los conectores no bastan.** La presencia de «porque», «por lo tanto» o «debido a» no establece relación si lo que sigue es una reafirmación del mismo elemento. «El radio disminuye porque se hace más pequeño» no es relacional.

**S3 — Estructura y corrección se codifican en columnas separadas.** Una respuesta puede integrar coherentemente los elementos bajo un modelo equivocado: eso es relacional e incorrecto. La columna `correccion` toma los valores: correcta, parcialmente correcta, incorrecta, no evaluable.

**S4 — Nivel sostenido, no destello.** Si la respuesta es mayoritariamente una lista y contiene una sola frase relacional aislada, se codifica el nivel que la estructura principal sostiene. Registrar en `nota` cuando esta regla decidió el caso.

**S5 — La generalización debe ser sustantiva.** Frases de cierre como «esto es muy importante en química» o «se aplica a todos los elementos» no son abstracto extendido. Se requiere una generalización con contenido: un principio enunciado, un caso nuevo tratado, o una condición de validez identificada.

**S6 — Elementos relevantes solo cuentan si son correctos.** Un elemento mencionado pero mal atribuido no cuenta para subir de uniestructural a multiestructural. Sí se registra en `correccion`.

**S7 — Techo del reactivo.** Antes de codificar, verificar qué nivel máximo admite el enunciado según la ficha de la Parte D. Si una respuesta parece exceder ese techo, revisar: normalmente el estudiante añadió algo por su cuenta, y eso sí puede ser abstracto extendido.

## C.4 Formato del archivo

```
id_respuesta, id_reactivo, texto_respuesta, nivel_solo,
correccion, elementos_presentes, confianza, nota
```

`elementos_presentes`: lista de los identificadores de elemento de la ficha del reactivo que aparecen correctamente en la respuesta. Esta columna hace verificable la asignación de nivel y es la que permite auditar el desacuerdo.

---

# PARTE D — Banco de reactivos abiertos

Cada reactivo cumple los tres criterios: admite más de un elemento relevante, admite relación entre ellos, e invita a generalizar. Cada ficha declara los elementos esperados y qué constituye nivel relacional y abstracto extendido, para anclar la codificación.

Los temas 1 y 2 están completos. Los temas 3 a 7 llevan un reactivo de arranque y la plantilla para completarlos.

---

## Tema 1 — Estructura atómica

### R1.1
**Enunciado.** Explica por qué el radio atómico disminuye a lo largo de un periodo pero aumenta al bajar en un grupo. ¿Esperarías el mismo comportamiento en los radios de los iones que forman esos elementos?

**Elementos esperados**
- E1: la carga nuclear aumenta a lo largo del periodo
- E2: el apantallamiento de los electrones internos permanece aproximadamente constante dentro del periodo
- E3: al bajar en un grupo aumenta el número cuántico principal, y con él la distancia media del electrón externo
- E4: la carga nuclear efectiva resulta del balance entre E1 y E2

**Relacional.** Vincula E1 y E2 mediante E4 para explicar la contracción, y usa E3 para el comportamiento vertical, dejando claro que son dos causas distintas y no la misma.

**Abstracto extendido.** Extiende el razonamiento a los radios iónicos reconociendo que la pérdida o ganancia de electrones cambia el balance, por ejemplo que los cationes son menores que su átomo neutro y los aniones mayores, o que en una serie isoelectrónica el orden lo fija la carga nuclear.

**Techo.** Abstracto extendido.

### R1.2
**Enunciado.** Un compañero afirma que el litio tiene mayor primera energía de ionización que el berilio porque el litio está antes en la tabla periódica. Explica si el argumento es correcto y qué está ocurriendo realmente.

**Elementos esperados**
- E1: la primera energía de ionización aumenta, en términos generales, a lo largo del periodo
- E2: el berilio tiene mayor carga nuclear que el litio
- E3: el electrón que se retira en ambos casos ocupa el subnivel 2s
- E4: el argumento por posición en la tabla es una inversión de la tendencia real

**Relacional.** Rechaza la afirmación integrando E1, E2 y E3 en una explicación única.

**Abstracto extendido.** Generaliza señalando que la tendencia periódica presenta excepciones cuando cambia el subnivel del que se retira el electrón o cuando hay apareamiento, por ejemplo boro frente a berilio, u oxígeno frente a nitrógeno.

**Techo.** Abstracto extendido.

### R1.3
**Enunciado.** El cromo tiene configuración electrónica [Ar]3d⁵4s¹ en lugar de [Ar]3d⁴4s². Explica a qué se debe y qué te dice esto sobre el principio de construcción progresiva (Aufbau).

**Elementos esperados**
- E1: el orden de llenado del Aufbau es una regla aproximada, no una ley
- E2: las energías de 3d y 4s son muy próximas en esta región de la tabla
- E3: la configuración observada corresponde a un arreglo de menor energía total
- E4: la energía total depende también de repulsiones interelectrónicas y de energía de intercambio, no solo del orden de los subniveles

**Relacional.** Explica la anomalía integrando E1 con E2 y E3.

**Abstracto extendido.** Identifica el límite de validez del modelo: el Aufbau ordena subniveles hidrogenoides y falla cuando las diferencias energéticas son comparables a los términos de repulsión e intercambio. O extiende el caso al cobre y otras anomalías del bloque d.

**Techo.** Abstracto extendido.

### R1.4
**Enunciado.** La contracción lantánida hace que el hafnio y el circonio tengan radios atómicos casi idénticos pese a estar en periodos distintos. Explica el fenómeno y qué consecuencias tiene para las propiedades de esos elementos.

**Elementos esperados**
- E1: al llenarse el subnivel 4f la carga nuclear aumenta en catorce unidades
- E2: los electrones f apantallan mal, por la forma de su distribución radial
- E3: la carga nuclear efectiva sobre los electrones externos crece de forma acumulada a lo largo de la serie
- E4: el aumento de radio esperado por cambio de periodo queda compensado

**Relacional.** Vincula E1, E2 y E3 para explicar la compensación de E4.

**Abstracto extendido.** Transfiere a consecuencias no contenidas en el enunciado: dificultad de separación química de la pareja, densidades elevadas, o el paralelo con la contracción del bloque d.

**Techo.** Abstracto extendido.

---

## Tema 2 — Espectroscopía

### R2.1
**Enunciado.** El espectro de emisión del hidrógeno consiste en líneas discretas y no en un continuo. Explica por qué, y qué ocurriría si el electrón pudiera tener cualquier energía.

**Elementos esperados**
- E1: los estados de energía del electrón están cuantizados
- E2: la emisión corresponde a la transición entre dos estados permitidos
- E3: la energía del fotón emitido es la diferencia entre esos dos estados
- E4: la frecuencia se relaciona con la energía del fotón mediante la relación de Planck

**Relacional.** Encadena E1 a E4 para explicar la discretización observada.

**Abstracto extendido.** Trata el contrapositivo del enunciado: si la energía fuera continua, el espectro sería continuo. O generaliza a que todo sistema con niveles discretos produce espectros de líneas, o contrasta con la emisión térmica de un sólido incandescente.

**Techo.** Abstracto extendido.

### R2.2
**Enunciado.** Explica la diferencia entre un espectro de emisión y uno de absorción para el mismo elemento, y por qué las líneas aparecen en las mismas posiciones.

**Elementos esperados**
- E1: en emisión el electrón cae a un estado de menor energía y libera un fotón
- E2: en absorción el electrón sube a un estado de mayor energía tomando un fotón
- E3: las diferencias de energía entre los mismos dos estados son idénticas en ambos procesos
- E4: por eso la posición de las líneas coincide, y lo que cambia es si aparecen brillantes sobre fondo oscuro o como huecos sobre un continuo

**Relacional.** Integra E1 a E4 en una explicación única del origen común.

**Abstracto extendido.** Extiende a un caso no dado: identificación de elementos en atmósferas estelares, o el hecho de que la coincidencia de posiciones es lo que permite usar el espectro como huella de identidad.

**Techo.** Abstracto extendido.

### R2.3
**Enunciado.** En el efecto fotoeléctrico, aumentar la intensidad de la luz incrementa el número de electrones emitidos pero no su energía cinética máxima. Explica por qué, y qué revela esto sobre la naturaleza de la luz.

**Elementos esperados**
- E1: la energía de cada fotón depende de la frecuencia, no de la intensidad
- E2: la intensidad determina el número de fotones incidentes
- E3: cada electrón emitido interactúa con un fotón
- E4: existe una frecuencia umbral por debajo de la cual no hay emisión, independientemente de la intensidad

**Relacional.** Integra E1 a E3 para explicar la independencia observada.

**Abstracto extendido.** Generaliza a la insuficiencia del modelo ondulatorio clásico, que predeciría dependencia de la intensidad y un retardo de acumulación, o conecta con la relación lineal entre energía cinética máxima y frecuencia.

**Techo.** Abstracto extendido.

### R2.4
**Enunciado.** El modelo de Bohr predice correctamente las líneas del hidrógeno pero falla para el helio. Explica por qué funciona en un caso y no en el otro.

**Elementos esperados**
- E1: el modelo de Bohr trata un solo electrón en el campo de un núcleo
- E2: en el helio hay repulsión entre los dos electrones, no contemplada por el modelo
- E3: el acierto en el hidrógeno no valida las suposiciones del modelo, como las órbitas definidas
- E4: el modelo cuántico describe distribuciones de probabilidad, no trayectorias

**Relacional.** Explica el fallo integrando E1 y E2, distinguiendo el alcance del modelo de su corrección conceptual.

**Abstracto extendido.** Generaliza sobre qué significa que un modelo acierte por razones equivocadas, o identifica que el problema de muchos electrones no tiene solución analítica y exige aproximaciones.

**Techo.** Abstracto extendido.

---

## Temas 3 a 7 — Reactivo de arranque y plantilla

### Tema 3 — Mecánica cuántica

**R3.1.** El principio de incertidumbre suele enunciarse diciendo que no se puede medir la posición y la velocidad de un electrón al mismo tiempo. Explica si esa formulación es adecuada y qué establece realmente el principio.

*Elementos esperados:* la limitación no proviene de la calidad del instrumento; es una propiedad de la descripción, no del acto de medir; la relación involucra las dispersiones de las magnitudes; es incompatible con la noción de trayectoria definida.  
*Abstracto extendido:* conecta con la imposibilidad de las órbitas de Bohr, o con la necesidad de describir el electrón mediante una distribución de probabilidad.

### Tema 4 — Orbitales

**R4.1.** Explica qué representa un orbital atómico y por qué las representaciones que aparecen en los libros muestran superficies bien delimitadas si la distribución de probabilidad no lo está.

*Elementos esperados:* el orbital es una función de onda monoelectrónica; el cuadrado del módulo se interpreta como densidad de probabilidad; la superficie dibujada es una isosuperficie que contiene un porcentaje elegido de la probabilidad; el corte es una convención de representación.  
*Abstracto extendido:* identifica que la representación introduce una frontera que el modelo no tiene, o extiende a los nodos y a lo que significa que la densidad se anule.

### Tema 5 — Enlaces químicos

**R5.1.** Dos compuestos con enlaces polares pueden tener momentos dipolares muy distintos. Explica de qué depende y qué papel juega la geometría.

**Elementos esperados**
- E1: la polaridad de un enlace depende de la diferencia de electronegatividad entre los átomos enlazados
- E2: cada enlace polar tiene un momento dipolar de enlace, con magnitud y dirección
- E3: el momento dipolar molecular es la suma vectorial de los momentos de enlace individuales
- E4: en geometrías simétricas los momentos de enlace se cancelan aunque los enlaces sean polares

**Relacional.** Vincula E2, E3 y E4 para explicar que la simetría de la geometría determina si hay cancelación y, con ello, si el dipolo molecular es nulo o no, integrando polaridad de enlace con estructura espacial.

**Abstracto extendido.** Extiende el razonamiento a un caso no dado: por ejemplo, CO₂ (lineal, apolar) frente a SO₂ (angular, polar) con la misma clase de enlace, o generaliza que la polaridad molecular no puede inferirse solo de la electronegatividad sin conocer la geometría. O identifica que los pares solitarios no enlazantes también contribuyen al dipolo total.

**Techo.** Abstracto extendido.

### Tema 6 — Estructura molecular

**R6.1.** El modelo VSEPR predice correctamente la geometría de muchas moléculas sin recurrir a orbitales. Explica en qué se basa y qué limitaciones tiene.

**Elementos esperados**
- E1: el modelo asume que los pares de electrones —enlazantes y no enlazantes— se repelen y adoptan la posición de máxima separación
- E2: los pares no enlazantes ocupan más espacio angular que los enlazantes y comprimen los ángulos entre enlaces
- E3: la geometría predicha es la de los átomos, no la de todos los pares, y por eso la molécula de agua es angular y no lineal
- E4: el modelo falla cuando los efectos de enlace múltiple, la resonancia o los metales de transición dominan la distribución electrónica

**Relacional.** Integra E1, E2 y E3 en una explicación que justifica cómo el principio de repulsión de pares predice la forma observable, distinguiendo geometría electrónica de geometría molecular.

**Abstracto extendido.** Identifica el límite de validez: el modelo trata los electrones como pares localizados y no distingue entre tipos de orbital. Generaliza señalando en qué clases de moléculas VSEPR es insuficiente (complejos de coordinación, moléculas con resonancia extensa) y qué modelo adicional haría falta.

**Techo.** Abstracto extendido.

### Tema 7 — Termodinámica

**R7.1.** Un proceso puede ser endotérmico y aun así ocurrir espontáneamente. Explica cómo es posible y de qué depende.

**Elementos esperados**
- E1: la espontaneidad no la determina la entalpía sola, sino la energía de Gibbs (ΔG = ΔH − TΔS)
- E2: un proceso endotérmico tiene ΔH > 0; si además ΔS > 0, el término −TΔS puede hacer ΔG negativo
- E3: la magnitud relativa de ΔH y TΔS depende de la temperatura
- E4: existe una temperatura de cruce por encima de la cual el proceso endotérmico pasa a ser espontáneo

**Relacional.** Integra E1 a E3 para explicar que la espontaneidad emerge del balance entre entalpía y el producto TΔS, y que ese balance depende de la temperatura.

**Abstracto extendido.** Generaliza a condiciones de frontera: calcula o estima la temperatura de cruce (ΔG = 0 → T ≈ ΔH/ΔS) para un proceso concreto, o transfiere el razonamiento a la fusión del hielo (endotérmica, espontánea por encima de 0 °C) o a reacciones de disolución de sales que enfrían la solución. O identifica que la expresión solo es válida a presión constante.

**Techo.** Abstracto extendido.

### Plantilla para completar los reactivos faltantes

```
Enunciado:
  [debe admitir al menos tres elementos relevantes]
  [debe admitir una relación causal, condicional o jerárquica entre ellos]
  [debe incluir una segunda frase que invite a transferir, generalizar
   o identificar límites de validez]

Elementos esperados:
  E1: ...
  E2: ...
  E3: ...
  E4: ...

Relacional: qué integración concreta se requiere
Abstracto extendido: qué generalización o transferencia cuenta
Techo: nivel máximo alcanzable con este enunciado
```

**Verificación antes de aprobar un reactivo.** Redactar mentalmente una respuesta uniestructural, una multiestructural y una relacional. Si no se puede distinguir la multiestructural de la relacional, el enunciado no admite relación y hay que reescribirlo.

---

# PARTE E — Entrenamiento, fiabilidad y adjudicación

## E.1 Ronda de entrenamiento

Antes de codificar la muestra definitiva, los dos codificadores trabajan un conjunto piloto de 25 ítems **que no forma parte de ninguna muestra posterior**. Se comparan resultados, se discuten las discrepancias y, si hace falta, se ajusta el manual.

Todo cambio al manual se registra con fecha. La versión usada para la codificación definitiva queda congelada y se reporta.

## E.2 Cálculo del acuerdo

Sobre la muestra principal, reportar:

- Porcentaje de acuerdo simple
- Kappa de Cohen sin ponderar
- Kappa ponderado con pesos lineales, por tratarse de una escala ordinal donde confundir niveles adyacentes no equivale a confundir extremos
- Matriz de confusión completa entre codificadores
- Distribución marginal de cada codificador

La matriz de confusión importa tanto como el kappa: muestra **dónde** está el desacuerdo, que es lo que permite mejorar el manual.

Reportar también el acuerdo restringido a los ítems que ambos marcaron con `confianza = 1`. Si el acuerdo es alto ahí y bajo en el resto, el instrumento funciona y el problema son los casos genuinamente ambiguos, lo cual es un resultado distinto y más favorable.

## E.3 Si el acuerdo es bajo

**El problema es el manual, no los codificadores ni el clasificador.** Se revisan las definiciones operativas y las reglas de desempate, se documenta el cambio, y se recodifica **una submuestra nueva**.

Recodificar los mismos ítems después de haberlos discutido y reportar ese segundo número como fiabilidad es contaminación. Es un error frecuente en la literatura y un revisor competente lo detecta.

## E.4 Adjudicación

Solo **después** de calcular y reportar el acuerdo, un tercer docente resuelve las discrepancias para producir el conjunto de referencia definitivo. Ese conjunto es contra el cual se evalúa el clasificador automático.

El orden importa: adjudicar antes de calcular el acuerdo elimina la evidencia de fiabilidad.

## E.5 Evaluación del clasificador automático

Con el conjunto de referencia definitivo, reportar para el clasificador de Bloom:

- Matriz de confusión contra la referencia
- Exactitud global y por nivel
- Proporción de casos asignados al valor por defecto, antes y después de introducir la categoría `no_clasificado`
- Análisis cualitativo de los errores sistemáticos, con los casos concretos que los ilustran

Este último punto es el que tiene mayor valor para la comunidad: no interesa tanto el porcentaje de acierto como **la estructura del error**, es decir, que el vocabulario disciplinar de la química colisiona con los marcadores léxicos de la taxonomía.
