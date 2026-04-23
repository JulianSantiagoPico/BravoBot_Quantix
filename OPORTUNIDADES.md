# BravoBot — Oportunidades de Producto y Escalabilidad

Análisis de oportunidades para escalar BravoBot más allá de su alcance actual como chatbot institucional de la I.U. Pascual Bravo.

---

## Contexto: ¿Qué tenemos hoy?

BravoBot es actualmente un **RAG conversacional institucional** con:
- Pipeline de scraping + indexación propio y reutilizable.
- Arquitectura modular que separa ingesta, retrieval y generación.
- Frontend embebible como widget flotante.
- Bot de Telegram.
- Despliegue en Docker.

Todo esto es infraestructura genérica que no está acoplada a Pascual Bravo en el código base — solo los datos (URLs scrapeadas, mallas, documentos manuales) son específicos de la institución.

---

## Oportunidad 1 — Plataforma Multi-Institución (SaaS)

### La idea

Convertir BravoBot en un **producto blanco** (white-label) que cualquier institución de educación superior pueda adoptar configurando únicamente sus datos, sin tocar el código.

### Cómo funciona hoy vs. cómo funcionaría

| Hoy | Con modelo SaaS |
|-----|----------------|
| URLs hardcodeadas en `urls.py` | Configuración por YAML/JSON por institución |
| Una colección en ChromaDB | Colección aislada por institución (`{slug}_bravobot`) |
| Un dominio | Subdominio por cliente (`pascualbravo.bravobot.co`, `eafit.bravobot.co`) |
| Despliegue manual | Panel de onboarding: pegar URLs → el sistema indexa automáticamente |

### Mercado objetivo en Colombia

Colombia tiene más de **300 Instituciones de Educación Superior** registradas ante el Ministerio de Educación (universidades, instituciones tecnológicas, escuelas tecnológicas). La mayoría no tiene chatbot propio. Las que lo tienen usan soluciones genéricas (Tidio, Intercom) que no conocen su oferta académica.

### Modelo de negocio posible

- **Suscripción mensual** por institución (SaaS): indexación, hosting, actualizaciones.
- **Setup fee** por onboarding inicial (configuración de URLs, revisión de mallas, pruebas).
- **Tier premium** con analytics, integración con sistema de admisiones (SICAU-like), soporte dedicado.

### Qué habría que construir adicionalmente

1. Panel de administración web: gestión de URLs, visualización de métricas, re-ingesta manual.
2. Sistema de tenancy: aislamiento de datos entre instituciones en la misma instancia.
3. Personalización de branding: logo, colores, nombre del bot.
4. Documentación de onboarding para equipos no técnicos.

---

## Oportunidad 2 — Asistente de Orientación Vocacional Nacional

### La idea

El wizard de 4 pasos ya existe en BravoBot (área → nivel → modalidad → disponibilidad). Eso es el núcleo de un **orientador vocacional** que cruce el perfil del aspirante con la oferta académica de múltiples instituciones, no solo una.

### Visión ampliada

Un aspirante entra al bot sin saber qué estudiar. Le hace las 4 preguntas (o más: intereses, habilidades, ciudad, presupuesto) y en lugar de mostrar solo los programas de Pascual Bravo, muestra un ranking de programas de **múltiples instituciones afiliadas** con información comparativa: costos, modalidad, duración, acreditación.

### Referentes existentes

- **SNIES** (Ministerio de Educación Colombia): tiene datos de todos los programas acreditados del país pero no tiene interfaz conversacional.
- **Buscando Carrera** (Icetex): orientación vocacional básica, sin RAG ni conversación natural.

BravoBot podría integrarse con la API del SNIES para enriquecer el corpus con datos oficiales de programas de todo el país.

### Propuesta de valor diferencial

Los buscadores de programas actuales son formularios de filtros. BravoBot proporciona una **conversación**: el aspirante puede preguntar *"¿qué diferencia hay entre Ingeniería de Software en Pascual Bravo y en la UdeA?"* y obtener una respuesta contextualizada, no una tabla de resultados.

---

## Oportunidad 3 — Herramienta de Inteligencia para Admisiones

### La idea

BravoBot registra qué preguntan los aspirantes. Esa data es extremadamente valiosa para los departamentos de admisiones de las instituciones.

### Qué insights se pueden extraer

| Insight | Valor para la institución |
|---------|--------------------------|
| Programas más consultados | Dónde enfocar publicidad |
| Preguntas sin respuesta (NO_INFO_FALLBACK) | Gaps de información en el sitio web |
| Consultas pico por fecha | Predecir demanda antes de cada ciclo |
| Términos más usados por aspirantes | Lenguaje real vs. lenguaje institucional |
| Tasa de abandono en el wizard | Qué paso genera más fricción |
| Distribución geográfica (si se captura) | Dónde están los aspirantes potenciales |

### Producto derivado

Un **dashboard de analítica de admisiones** que transforma las conversaciones del chatbot en reportes accionables para el equipo de mercadeo y admisiones de la institución. Esto se puede vender como add-on del SaaS o como módulo independiente.

---

## Oportunidad 4 — Integración con Sistemas de Admisión

### La idea

Hoy BravoBot responde preguntas sobre el proceso de admisión, pero el aspirante igual tiene que ir al SICAU (o sistema equivalente) a hacer la inscripción. La fricción de ese salto hace que muchos no completen el proceso.

### Propuesta

Conectar BravoBot directamente con el sistema de inscripciones:
- *"¿Quieres iniciar tu proceso de inscripción ahora?"* → el bot genera un link personalizado o pre-llena datos.
- Verificación de requisitos: *"¿Tienes grado de bachiller?"* → el bot guía al aspirante paso a paso antes de enviarlo al formulario.
- Seguimiento: *"Tu inscripción está en estado Pendiente de documentos"* (consultando la API del sistema de admisiones).

### Impacto

Convierte el chatbot de un **canal de información** a un **canal de conversión**. La tasa de inscripción completada es la métrica principal de admisiones.

---

## Oportunidad 5 — Extensión a Otros Perfiles de Usuario

### Hoy: solo aspirantes

El corpus y los prompts están diseñados para aspirantes. Pero la misma arquitectura sirve para otros perfiles:

| Perfil | Datos necesarios | Preguntas típicas |
|--------|-----------------|------------------|
| **Estudiantes activos** | Reglamento académico, horarios, trámites | "¿Cómo solicito una certificación?", "¿Cuántos créditos me faltan?" |
| **Docentes** | Normativa, plataformas institucionales, formatos | "¿Cuál es el proceso para solicitar permiso?" |
| **Egresados** | Actualización de datos, certificados, red de alumni | "¿Cómo obtengo mi diploma?" |
| **Padres de familia** | Costos, becas, proceso de admisión | "¿Qué incluye el valor de la matrícula?" |

Cada perfil tendría su propio corpus y sistema prompt, pero compartirían la misma infraestructura RAG.

---

## Oportunidad 6 — Bot para Colegios y Orientadores

### La idea

Los orientadores de colegios de bachillerato en Colombia ayudan a los estudiantes de grado 10 y 11 a elegir carrera. Hoy lo hacen con folletos y visitas a ferias universitarias.

### Propuesta

Un bot especializado para **orientadores escolares** que:
- Puede configurarse con la oferta académica de las universidades de la región.
- Responde preguntas de bachilleres sobre qué estudiar, qué aptitudes necesitan, qué salidas laborales tienen los programas.
- Se despliega como link compartible (no requiere instalación): el orientador lo comparte por WhatsApp con los estudiantes de su colegio.

### Por qué es viable

El wizard de orientación vocacional ya está construido. Solo habría que ampliar el corpus con información de salidas laborales y perfiles de ingreso de cada programa, y adaptar el sistema prompt para el público de 16-18 años.

---

## Oportunidad 7 — Certificación y Alianza con MinEducación / Icetex

### La idea

Si BravoBot se convierte en un orientador vocacional de alcance nacional, tiene sentido buscar alianzas con:

- **MinEducación**: integración con SNIES para datos oficiales de programas acreditados.
- **Icetex**: información sobre créditos educativos, subsidios y becas nacionales integrada en el RAG.
- **Ser Pilo Paga / Generación E** (o programas equivalentes): información sobre programas de acceso especial.

Una alianza institucional convierte a BravoBot en el canal oficial de orientación vocacional del sistema educativo colombiano — o al menos de la región.

---

## Oportunidad 8 — Monetización por Lead Generation

### La idea

Cada aspirante que interactúa con BravoBot en el contexto del SaaS multi-institución es un **lead de admisiones**. Las instituciones pagan por leads calificados.

### Modelo

- El aspirante puede dar su correo / número al final del wizard.
- La institución recibe el perfil del aspirante (área de interés, nivel buscado, modalidad) junto con el dato de contacto.
- Cobro por lead entregado (CPA) o como feature del plan premium del SaaS.

Esto convierte a BravoBot en un canal de captación de aspirantes además de un canal de atención.

---

## Oportunidad 9 — Expansión Regional (Latinoamérica)

### Contexto

El problema que resuelve BravoBot existe en toda Latinoamérica: instituciones educativas con sitios web complejos, aspirantes con dudas que no encuentran respuesta rápida, y equipos de admisiones saturados.

### Ventajas del stack actual para expansión

- El modelo de embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) ya funciona en español, portugués, e inglés sin cambios.
- El pipeline de scraping es genérico — funciona con cualquier sitio web, no solo `pascualbravo.edu.co`.
- Los prompts y el intent classifier están en español pero son adaptables a variantes regionales.

### Mercados prioritarios

| País | Tamaño del mercado | Particularidades |
|------|-------------------|-----------------|
| México | ~4,000 IES | Sistema muy diverso, alta demanda de orientación |
| Perú | ~140 universidades | Boom de nuevas universidades privadas |
| Chile | ~60 universidades | Alto nivel de digitalización, mercado más exigente |
| Brasil | ~2,600 IES | Requiere soporte en portugués (el modelo ya lo soporta) |

---

## Oportunidad 10 — BravoBot como Producto Open Source + Servicios

### La idea

Publicar el núcleo del RAG como open source en GitHub y monetizar a través de servicios:

- **Hosting administrado**: la institución no quiere mantener infraestructura propia.
- **Onboarding y personalización**: equipo que configura el corpus inicial.
- **Soporte y actualizaciones**: mantenimiento del sistema con datos vigentes.

### Por qué funciona

El open source construye comunidad y confianza, especialmente con instituciones públicas que no pueden pagar por software propietario cerrado. Los ingresos vienen de los servicios, no de la licencia del software.

Referentes: GitLab, Metabase, Posthog.

---

## Hoja de Ruta de Producto (visión a 12-24 meses)

```
Mes 1-3    Mes 4-6        Mes 7-12          Mes 13-24
─────────  ────────────   ───────────────   ─────────────────────
BravoBot   Multi-tenant   SaaS lanzado      Orientador vocacional
Pascual  → config por   → 3-5 clientes    → nacional (SNIES)
Bravo      YAML/JSON       piloto            + WhatsApp
           + branding      + analytics       + colegios
           + panel admin   dashboard         + MinEducación
```

---

## Lo que nos diferencia de soluciones genéricas

| BravoBot | Chatbots genéricos (Tidio, Intercom, ChatGPT plugins) |
|---------|------------------------------------------------------|
| Conoce exactamente la oferta académica de la institución | Responden con conocimiento general, pueden alucinar |
| Mallas curriculares estructuradas (semestre a semestre) | No tienen acceso a esos datos |
| Orientación vocacional con perfil del aspirante | Responden preguntas, no guían |
| Corpus auditado y trazable (fuentes reales) | Fuentes opacas |
| Desplegable on-premise (datos no salen de la institución) | Datos van a servidores de terceros |
| Integrable con sistemas institucionales (SICAU) | Requieren desarrollo a medida costoso |
| Costo operativo bajo (modelo local de embeddings) | Costos por token en cada operación |
