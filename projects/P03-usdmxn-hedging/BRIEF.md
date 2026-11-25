# P03 · USD/MXN hedging simulator

| Publicación en LinkedIn | Construcción (tarea programada) | Estado |
| :--- | :--- | :--- |
| jue 17-dic-2026 (8:00–9:30, centro de México) | vie 11-dic-2026, 17:00 | Pendiente |

## Encargo

Libro de Excel (openpyxl) para una manufacturera ilustrativa con ingresos en pesos y costos en dólares a 12 meses: coberturas de 0%, 50%, 75% y 100% con forwards (paridad cubierta con CETES/TIIE frente a T-Bills o fondos federales) y calls (Garman-Kohlhagen con volatilidad histórica del FIX); tres trayectorias y VaR 95% por simulación histórica. Pares: costo anual de cubrir MXN frente a BRL, CLP y COP. Hallazgo en MXN por USD 100,000 entre 0% y 75% cubierto. Página final «Policy takeaway» sobre el costo del carry para la gestión de riesgo cambiario corporativo. Ejercicio ilustrativo, no recomendación. Siguiente: «State tax incentives: when do they pay back?», Thu Dec 24.

## Estructura de esta carpeta

```
P03-usdmxn-hedging/
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
