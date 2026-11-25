# P07 · Industrial investment announcements radar

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 21-ene-2027 (8:00–9:30, centro de México) | vie 15-ene-2027, 17:00 | Pendiente |

## Encargo

Extractor en Python para hasta 15 comunicados (Secretaría de Economía, secretarías estatales, salas de prensa corporativas) con esquema estricto (monto USD millions, empleos, municipio, estado, subsector, arranque, URL, fecha; null si no es explícito). Primera edición con anuncios de las últimas dos semanas verificados en su fuente. Contraste con IED observada (SE y Banxico) y, si existe, UNCTAD o FMI. Página final «How to use it»; Policy takeaway en el post. Siguiente: «How much of the peso reaches prices?», Thu Jan 28.

## Estructura de esta carpeta

```
P07-investment-radar/
├── BRIEF.md             ← este encargo
├── README.md            ← README público en inglés (question, method, sources, how to run)
├── requirements.txt
├── src/                 ← código reproducible
├── data/                ← datos descargados de fuentes oficiales (o el script que los descarga)
└── output/
    ├── carousel_en.pdf  ← carrusel 4:5 en inglés
    ├── slides/          ← un PNG por página
    ├── linkedin_post.md ← post en inglés, comentario en español, alt text y nota del autor (DRAFT)
    └── linkedin_ficha.md← ficha para la sección Projects (inglés y español)
```

`fuentes_privado.md` (nombres reales de emisoras, si aplica) se guarda aquí pero git lo ignora: nunca se sube.

Reglas comunes de la serie: [`.claude/commands/proyecto.md`](../../.claude/commands/proyecto.md) · Calendario: [`docs/PLAN_CONTENIDO.md`](../../docs/PLAN_CONTENIDO.md)
