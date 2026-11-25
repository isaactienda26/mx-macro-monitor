# P08 · Exchange-rate pass-through to producer and consumer prices

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 28-ene-2027 (8:00–9:30, centro de México) | vie 22-ene-2027, 17:00 | Pendiente |

## Encargo

Traspaso del FIX al INPP y al INPC (mercancías y servicios subyacentes), ene-2018 al último mes: diferencias logarítmicas, rezagos distribuidos 0–6, control por energía (serie oficial), efecto acumulado a 3 y 6 meses con intervalos robustos. Robustez: submuestra post-2021 o asimetría. Literatura: Capistrán, Ibarra y Ramos-Francia (2012); Ángeles, Cortés y Sámano (2019), Banxico WP 2019-10. Hallazgo en MXN por cada MXN 1 million de insumos ante una depreciación de 10%. Página final «Policy takeaway» sobre la reacción de Banxico. Siguiente: «If steel fails», Thu Feb 4.

## Estructura de esta carpeta

```
P08-fx-pass-through/
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
