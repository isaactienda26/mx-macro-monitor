# P10 · Statistical auditor for compensation surveys

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 11-feb-2027 (8:00–9:30, centro de México) | vie 5-feb-2027, 17:00 | Pendiente |

## Encargo

Módulo de Python: atípicos por IQR y Mahalanobis (con MCD robusto), faltantes por tamaño de empresa, consistencias lógicas (incluye salario menor al mínimo de la CONASAMI), winsorización con bitácora y reporte HTML. Base sintética de 2,000 registros con errores sembrados, pytest, tasa de detección y falsos positivos; nada de datos de clientes. Hallazgo: cambio en mediana y p90 antes y después. Marco de calidad de datos del FMI u OCDE. Página final «How to use it». Siguiente: «Who creates the jobs?», Thu Feb 18.

## Estructura de esta carpeta

```
P10-survey-auditor/
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
