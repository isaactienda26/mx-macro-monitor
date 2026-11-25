# P01 · Output gap and Taylor rule for Mexico

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 3-dic-2026 (8:00–9:30, centro de México) | vie 27-nov-2026, 17:00 | Pendiente |

## Encargo

PIB potencial con filtros de Hodrick-Prescott (λ = 1600) y Hamilton sobre el PIB trimestral desestacionalizado del INEGI (2005 al último trimestre). Regla de Taylor inercial con rezago de la tasa (statsmodels, errores robustos) con brecha del producto y brecha de inflación frente a la meta de 3%; tasa implícita contra tasa objetivo observada con bandas de ±50 pb. Robustez: inflación subyacente o expectativas a 12 meses (encuesta de Banxico). Referencia: tasa neutral real de Banxico (Informe Trimestral abr–jun 2024, Recuadro 7: 1.8%–3.6%). Pares: tasa real ex post frente a Brasil, Chile, Colombia y Perú (BIS). Página final «Policy takeaway»: distancia en pb entre tasa implícita y observada, sin pronóstico. Siguiente: «Minimum wage 2027 and cash flow», Thu Dec 10.

## Estructura de esta carpeta

```
P01-taylor-rule/
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
