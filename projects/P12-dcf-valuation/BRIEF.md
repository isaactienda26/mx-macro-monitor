# P12 · Discounted cash flow (DCF) valuation

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 25-feb-2027 (8:00–9:30, centro de México) | vie 19-feb-2027, 17:00 | Pendiente |

## Encargo

Una industrial de la BMV con cuatro años de reportes anuales: ingresos, EBIT, D&A, CapEx y capital de trabajo (null si falta); proyección a cinco años, WACC con bono M a 10 años, prima de mercado y beta documentadas; sensibilidad tasa × crecimiento terminal. Robustez: WACC en dólares frente a pesos. Pares: rendimientos soberanos a 10 años de Brasil, Chile, Colombia y Perú. Públicamente «A BMV-listed industrial»; nombre solo en `fuentes_privado.md`. Ejercicio académico. Página final «Policy takeaway» sobre tasas, prima soberana e inversión productiva. Cierra la serie.

## Estructura de esta carpeta

```
P12-dcf-valuation/
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
