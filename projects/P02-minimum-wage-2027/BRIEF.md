# P02 · Minimum wage 2027: cash-flow and labor-cost stress test

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 10-dic-2026 (8:00–9:30, centro de México) | vie 4-dic-2026, 17:00 | Pendiente |

## Encargo

Verificar si la CONASAMI publicó el salario mínimo 2027 (general y frontera); si no, escenarios +10%, +12% y +15% sobre el vigente. Libro de Excel auditable (openpyxl) para una manufacturera ilustrativa de Nuevo León con 450 empleados: Assumptions, Payroll (IMSS e ISN con fuente de cada tasa), Imported inputs (FIX), Debt (TIIE 28), Scenarios y Summary (EBITDA, margen y flujo libre); fórmulas nativas (LET, tabla de sensibilidad). Contexto: salario mínimo real desde 2018 frente a productividad (INEGI) y salario mínimo / salario medio frente a pares OCDE. Hallazgo en MXN por cada 100 trabajadores. Página final «Policy takeaway» sobre formalidad y márgenes. Video 4:5 de ~60 s opcional. Siguiente: «USD/MXN hedging», Thu Dec 17.

## Estructura de esta carpeta

```
P02-minimum-wage-2027/
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
