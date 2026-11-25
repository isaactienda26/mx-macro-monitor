# P06 · A tone index for Banxico's minutes

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 14-ene-2027 (8:00–9:30, centro de México) | vie 8-ene-2027, 17:00 | Pendiente |

## Encargo

Minutas de los últimos 24 meses (incluye diciembre de 2026 si ya se publicó). Esquema JSON estricto con evidencia literal (votación, balance de riesgos, tipo de cambio, actividad; null si no aparece). Índice hawkish–dovish con diccionario público y referencias verificadas de text-as-data en bancos centrales; índice contra tasa objetivo y prueba simple de si anticipa la siguiente decisión. Cada valor con cita y página. Página final «Policy takeaway» sobre la comunicación de Banxico. Siguiente: «Industrial investment radar», Thu Jan 21.

## Estructura de esta carpeta

```
P06-banxico-tone-index/
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
