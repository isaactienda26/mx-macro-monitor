---
description: Construye un proyecto de la serie (P01–P12) con su carrusel 4:5, código y post de LinkedIn en inglés primero
argument-hint: P01
---

Construye el proyecto **$ARGUMENTS** de la serie de portafolio de Isaac Tienda (Economista Senior, isaac.tienda01@gmail.com). La carpeta del proyecto es `projects/$ARGUMENTS-*/` (índice en `projects/README.md`); el encargo está en su `BRIEF.md` y el calendario y las reglas de la serie en `docs/PLAN_CONTENIDO.md`. Tú construyes y redactas; Isaac revisa y publica. No publiques ni hagas push.

## Audiencia e idioma
- La red son sobre todo economistas senior y directivos del BID, Banco Mundial, FMI, BIS y banca privada. Escribe para pares: precisión técnica, sin explicar lo básico, sin adjetivos de marketing.
- Inglés primero: láminas, post y ficha en inglés; versión en español condensada para el primer comentario (máximo 1,250 caracteres).
- Formato internacional (1,234.5; MXN 1.9 million; USD 100,000; «Dec 2026»); instituciones con nombre oficial y sigla; al pie de cada gráfica «Source: Own elaboration with [institution] data ([series]).»

## Forma de trabajo
- Trabaja de principio a fin sin preguntar y sin narrar el avance. Si un dato falta, anótalo y sigue. Siempre entrega.
- Solo fuentes oficiales (INEGI, Banxico, IMSS, CONASAMI, Secretaría de Economía, CNBV, BMV, BIS, Reserva Federal, FMI, Banco Mundial, OCDE). Nunca inventes cifras; lo no localizado va como null y se declara.
- Tokens de Banxico e INEGI: solo desde variables de entorno (`.env`), sin imprimirlos ni escribirlos en archivos.
- Diseño: skill `mx-macro-monitor-design` si está disponible, más `src/brand.py`, `assets/fonts` y `assets/logo`. Portada con banda negra #111418, kicker azul «PROJECT NN · MX MACRO SERIES» y marca cuadrada; titular de 2–3 palabras en inglés; una idea por página (~25 palabras); Newsreader justificado; gráficas sin cuadrícula y un solo eje; firma y correo en cada página; contraportada negra con el siguiente proyecto, «Follow» y correo.

## Entregables (en la carpeta del proyecto, con la estructura que indica su `BRIEF.md`)
1. Código en `src/`, datos o script de descarga en `data/`, `requirements.txt` y `README.md` público en inglés (question, method, assumptions, sources, how to run); conserva `BRIEF.md`.
2. `output/carousel_en.pdf` y un PNG por página en `output/slides/`: Cover · The question · The method · Finding 1 · Finding 2 · página final del encargo · Back cover.
3. `output/linkedin_post.md`: (a) post en inglés ≤3,000 caracteres con gancho, líneas «→», How I calculate it, Robustness, Limitations, References verificadas, Policy takeaway neutral sin pronóstico, siguiente proyecto con fecha, «Versión en español en el primer comentario.», correo y 3 hashtags; (b) comentario en español ≤1,250 caracteres; (c) texto alternativo en inglés por página; (d) «Author's note — DRAFT» en inglés y español; (e) hora sugerida: jueves 8:00–9:30 del centro de México. Sin emojis ni enlaces a GitHub.
4. `output/linkedin_ficha.md`: ficha para la sección Projects en inglés y en español (título, descripción ≤2,000 caracteres, 5 habilidades).
5. Si el encargo pide nombres reales de emisoras, van solo en `fuentes_privado.md` dentro de la carpeta del proyecto (ignorado por git).

## Antes de entregar
Renderiza y revisa cada página (nada fuera de su caja ni sobre el pie, sin ríos, fuente al pie, correo visible), corre el agente `lector-scroll` sobre los PNG, cuenta los caracteres del post y del comentario, y lee la portada como un economista senior que decide en 2 segundos si sigue deslizando. Actualiza el estado del proyecto en `projects/README.md` y en su `BRIEF.md` a «En revisión». Cierra con el titular propuesto, tres cifras clave con su fuente y lo que requiere a Isaac.
