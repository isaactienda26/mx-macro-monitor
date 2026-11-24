# Sistema de diseño · MX Macro Monitor (v4)

Estilo de boletín institucional para la marca personal de Isaac Tienda en LinkedIn. Los valores viven en `src/carousel.py`; este archivo y ese módulo se mantienen sincronizados.

## 1. Principios

1. **Dos capas de lectura.** Titular y entrada en lenguaje llano para cualquier lector; unidades, ajustes, fuentes y referencias en notas al pie para economistas.
2. **Convención institucional.** Cada gráfica lleva número y título descriptivo, subtítulo con unidades y frecuencia, notas, fuente y última observación, como en los informes de Banxico, el Banco Mundial o el Banco de Canadá.
3. **La gráfica es el gancho.** La página 1 es la "Gráfica de la semana": titular, entrada y gráfica. No hay cifras gigantes decorativas.
4. **Legible en el teléfono.** LinkedIn muestra la página a ~390 px (×0.36): cuerpo ≥ 34 px, notas ≥ 24 px sobre el lienzo de 1080.
5. **Datos sin adorno; opinión firmada.** El texto de datos describe dirección y magnitud con fuente. La única opinión es la *Lectura del autor*, firmada y con aviso.

## 2. Estructura (5 páginas, 1080 × 1350)

| # | Página | Contenido |
| :---: | :--- | :--- |
| 1 | Gráfica de la semana | Cabecera completa (banda navy de 14 px, nombre, fecha, descriptor) · titular serif · entrada (2–3 frases, cita en línea) · Gráfica 1 con notas y fuente |
| 2 | Indicadores clave | Tabla de 6 filas: indicador + unidad/periodo, tendencia, último dato, cambio; llamadas ¹ ² para señales; glosario y fuente |
| 3 | Gráfica 2 | Segundo tema con la misma plantilla de la página 1 y cabecera corta |
| 4 | Lectura del autor | Nota firmada (`config/nota_autor.yml`) + "Qué vigilar esta semana" |
| 5 | Notas y referencias | Metodología, referencias completas, dónde consultar datos y código |

## 3. Color

| Token | Hex | Uso | Contraste sobre blanco |
| :--- | :--- | :--- | :---: |
| `ink` | `#0B1F33` | Banda de cabecera, titulares, cifras, etiquetas de datos | 16.7:1 |
| `text` | `#1F2933` | Cuerpo | 14.8:1 |
| `muted` | `#52606D` | Subtítulos, notas, fuentes | 6.5:1 |
| `axis` | `#66717F` | Etiquetas de ejes | 5.0:1 |
| `rule` | `#D9DEE5` | Líneas divisorias y línea base | decorativo |
| `tint` | `#F4F6F9` | Encabezado de tabla | decorativo |
| `blue` | `#1F5FAD` | Serie principal, barra más reciente | 6.4:1 |
| `blue-ctx` | `#6F95C9` | Barras de contexto | 3.1:1 |
| `orange` | `#D9692B` | Segunda serie (solo comparación); nunca texto | 3.5:1 |
| `band` | `#E9EEF5` | Bandas de referencia (meta, rango neutral) | decorativo |

El par `blue`/`orange` pasa la validación para daltonismo (ΔE CVD 23.9; visión normal 32.8). Sin rojo/verde de juicio, sin degradados, sin sombras, sin color de estado: las señales estadísticas se marcan con llamadas numeradas (¹, ²) y se explican al pie.

## 4. Tipografía

Source Serif 4 (titulares y nota del autor) y Source Sans 3 (texto, datos, gráficas), ambas de Adobe con licencia OFL, incluidas en `assets/fonts/`.

| Rol | Fuente | px @1080 |
| :--- | :--- | :---: |
| Nombre en cabecera | Source Serif 4 Display Semibold | 40 (p. 1) · 28 |
| Titular | Source Serif 4 Display Semibold | 62 (p. 1) · 58 |
| Nota del autor | Source Serif 4 Regular | 38 |
| Entrada | Source Sans 3 Regular | 34 |
| Cifra de tabla | Source Sans 3 Semibold | 42 |
| Título de gráfica | Source Sans 3 Semibold | 30 |
| Subtítulo de gráfica, ejes | Source Sans 3 Regular | 26 |
| Etiquetas de datos | Source Sans 3 Semibold | 28 |
| Notas, fuente, pie | Source Sans 3 Regular | 24 |

## 5. Gráficas

- Bloque fijo: **"Gráfica n. Título descriptivo"** → subtítulo con unidades, frecuencia y periodo → gráfica → **Nota:** (lectura del eje, bandas, ajuste) y **Última observación** → **Fuente: Elaboración propia con datos de [institución] ([sistema], serie [clave]).**
- Sin cuadrícula; solo línea base y 3–4 marcas en el eje y; sin marcas en el eje temporal.
- Etiquetas directas con nombre y valor ("Subyacente 3.80%"); sin leyenda cuando la etiqueta directa basta.
- Un solo eje y; bandas de referencia en `band`; la observación más reciente resaltada.

## 6. Redacción

- Titular: hecho + dirección + magnitud o referencia temporal ("El peso registra su mayor depreciación semanal desde junio de 2024").
- Entrada: frase 1 = qué pasó en palabras llanas ("El dólar pasó de 18.47 a 19.37 pesos"); frase 2 = qué significa, con cita en línea (autor, año).
- Siglas explicadas en el glosario (a.e., pp, pb). Decimales: tasas e inflación 2, variaciones 1, tipo de cambio 2.
- Post: pregunta y respuesta del tema principal, tres datos más, "Mi lectura" (de la nota firmada), agenda, pregunta de cierre, 3 *hashtags*. Sin viñetas decorativas.

## 7. Benchmark institucional

| Práctica | Referente | Aplicación |
| :--- | :--- | :--- |
| Título + subtítulo con unidades y "a.e./ Cifras con ajuste estacional" | Banxico, Informe Trimestral | Bloque de gráfica y glosario |
| "Los datos son los últimos disponibles al…" y glosario de siglas | Banxico, infografía de indicadores clave | Página 2 |
| Orden notas → notas al pie → fuente | Eurostat | Pie de cada gráfica |
| Leyenda solo si no hay etiqueta directa; ~5 marcas por eje; sin marcas en eje temporal | Banco Mundial | Etiquetas directas y ejes |
| Título, subtítulo en tipo oración, notas, fuentes y última observación | Banco de Canadá | Bloque de gráfica |
| Una gráfica con historia como pieza semanal; aviso de que las opiniones son de los autores | FMI, *Chart of the Week* | Página 1 y nota firmada |

## 8. Auditoría v3 → v4

### Atención y comprensión

| Hallazgo en v3 | Corrección en v4 |
| :--- | :--- |
| Portada navy con cifra dorada de 210 px: patrón de plantilla publicitaria, compite con el dato | La gráfica es la portada; titular serif y entrada en lenguaje llano |
| Recuadro con borde izquierdo y etiqueta "Por qué importa": patrón genérico de contenido generado | Entrada en prosa con cita en línea, sin recuadros |
| Etiquetas en mayúsculas, flechas y símbolos ▲ ● | Tipo oración; señales como llamadas numeradas al pie |
| Lenguaje técnico en primer plano (tasa real, z, pb) | Primera capa en lenguaje llano; tecnicismos al pie y en el glosario |
| Sin voz del autor: poco motivo para seguir la serie | *Lectura del autor* firmada, con aviso de opinión personal |
| Inter en todo: tipografía genérica | Source Serif 4 + Source Sans 3, par editorial-institucional |

### Accesibilidad (WCAG 2.1 AA aplicado a documento PDF)

| Criterio | v3 | v4 |
| :--- | :--- | :--- |
| 1.4.3 Contraste de texto | Cumple (mín. 4.7:1) | Cumple (mín. 5.0:1) |
| 1.4.11 Contraste no textual | Barras de contexto `#A9CBF3` 1.7:1 | `#6F95C9` 3.1:1 |
| 1.4.1 Uso del color | Series identificadas por color + leyenda | Etiqueta directa con nombre de la serie |
| Legibilidad móvil | Notas de 21 px (≈ 7.6 px en teléfono) | Notas 24 px, cuerpo 34 px |
| 1.1.1 Alternativa textual | Sin texto alternativo | PDF con texto real y metadatos; texto alternativo listo en `linkedin_post.md` |
| 3.1.4 Abreviaturas | Parcial | Glosario en página 2 y notas por gráfica |
| 1.3.2 Orden de lectura | No verificable en PDF generado | Sin cambio: LinkedIn no lee PDF etiquetado; el post repite los datos clave en texto |
