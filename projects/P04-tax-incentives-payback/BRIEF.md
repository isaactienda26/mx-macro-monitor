# P04 · State tax incentives: fiscal payback calculator

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 24-dic-2026 (8:00–9:30, centro de México) | vie 18-dic-2026, 17:00 | Pendiente |

## Encargo

Aplicación web en inglés, un solo HTML autocontenido: periodo de recuperación fiscal de incentivos estatales a una planta manufacturera (años de exención de ISN, subsidios, empleos, salario base de cotización, tasa e indirectos). Valores por defecto de Nuevo León con fuente y aviso de modelo simplificado. Literatura verificada de Banco Mundial u OCDE sobre incentivos y qué deja fuera el modelo. Carrusel de 5 páginas (Cover · The question · How it works · An illustrative case · Back cover); el Policy takeaway va en el post. Siguiente: «Covenants under the lens», Thu Jan 7.

## Estructura de esta carpeta

```
P04-tax-incentives-payback/
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
