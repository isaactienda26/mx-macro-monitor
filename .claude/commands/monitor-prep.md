---
description: Prepara el número del MX Macro Monitor de esta semana (inglés primero) y lo deja listo para revisión
---

Prepara el número del MX Macro Monitor que sale el martes. El Nº 2 sale el 1-dic-2026 y sale uno por semana. Isaac revisa y publica; no publiques ni hagas push.

1. Carga el skill `mx-macro-monitor-design` si está disponible y aplica sus reglas.
2. Verifica en los calendarios oficiales de INEGI y Banxico qué se publicó desde el martes pasado y qué se publica hasta el lunes siguiente (Reserva Federal si hay decisión o dato clave). Nunca inventes cifras.
3. Revisa que `config/nota_autor.yml` tenga la semana ISO actual y los campos `es`, `en`, `cita_es` y `cita_en`. Si faltan, redacta un borrador marcado `estado: borrador` y avísale a Isaac; el inglés no es traducción literal.
4. Corre `python src/macro_monitor.py` (tokens desde `.env`). Corre el agente `lector-scroll` sobre `bulletins/slides_en/` y atiende lo que marque.
5. Revisa `bulletins/linkedin_post.md`: post en inglés (≤3,000 caracteres) con `carousel_en.pdf`, comentario en español ≤1,250 caracteres, medidas parecidas etiquetadas (FIX vs H.10, tasa real ex ante vs ex post).
6. Propón tres candidatos para «Chart of the week / El cálculo de la semana» con cifra, cuenta y fuente oficial; uno compara a México con pares emergentes si aplica.
7. Recuerda qué proyecto sale el jueves según `docs/PLAN_CONTENIDO.md`.

Hora sugerida: martes 8:00–9:30 del centro de México; pegar el comentario en español en los primeros minutos.
