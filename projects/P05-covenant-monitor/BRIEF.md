# P05 · Covenant monitor for BMV-listed issuers

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 7-ene-2027 (8:00–9:30, centro de México) | mié 30-dic-2026, 17:00 | Pendiente |

## Encargo

Tres emisoras industriales de la BMV de sectores distintos: EBITDA 12 meses, deuda, efectivo e intereses de reportes oficiales; deuda neta/EBITDA y cobertura frente a umbrales hipotéticos (3.0x y 1.5x) con semáforo Low/Medium/High de regla publicada; Python + SQLite. Pares: deuda corporativa no financiera / PIB frente a Brasil, Chile, Colombia y Perú (BIS). Públicamente «Issuer A, B and C»; nombres solo en `fuentes_privado.md` (no se sube al repositorio). No es recomendación ni calificación. Página final «Policy takeaway» macroprudencial. Siguiente: «Banxico's tone, measured», Thu Jan 14.

## Estructura de esta carpeta

```
P05-covenant-monitor/
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
