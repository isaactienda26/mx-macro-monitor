# Sistema de diseño · MX Macro Monitor

Reglas para todo material visual de la marca personal de Isaac Tienda en LinkedIn (carrusel semanal, gráficas sueltas, portadas). Los valores viven en código en `src/carousel.py`; este archivo y ese módulo deben mantenerse sincronizados.

## 1. Principios

1. **Una idea por lámina.** Titular-hallazgo + una gráfica + una lectura + por qué importa. Máximo ~35 palabras de texto narrativo por lámina (sin contar fuente ni pie).
2. **El dato primero.** El titular dice qué pasó con cifra y dirección ("El peso se deprecia 4.9% en la semana"), no el tema ("Tipo de cambio").
3. **Legible en el teléfono.** LinkedIn muestra el documento a ~390 px de ancho (escala ≈ 0.36 sobre 1080 px). Ningún texto menor a 21 px en el lienzo de 1080.
4. **Sin opinión, con respaldo.** Se describe dirección y magnitud; toda afirmación interpretativa lleva una referencia académica o institucional.
5. **Fuentes oficiales y trazables.** Cada gráfica cierra con "Fuente: Elaboración propia con datos de [institución] ([sistema], serie [clave])."

## 2. Formato

| Elemento | Valor |
| :--- | :--- |
| Lienzo | 1080 × 1350 px (4:5), PDF multipágina para publicación de documento |
| Láminas | 5: portada · tema principal · tablero · segundo tema · agenda + método + referencias |
| Margen exterior | 80 px |
| Encabezado | `MX MACRO MONITOR · SEMANA nn` (22 px, azul, negritas) + `n/5` a la derecha |
| Pie | línea 1.2 px `#DCE1E8`; fuente (21 px, máx. 2 líneas) a la izquierda; autor y rol a la derecha |

## 3. Color

| Token | Hex | Uso | Contraste |
| :--- | :--- | :--- | :---: |
| `navy` | `#0B1F33` | Fondo de portada, titulares, cifras, etiquetas de datos | 16.7:1 |
| `text` | `#1B2533` | Texto de cuerpo | 15.5:1 |
| `muted` | `#566070` | Texto secundario, kicker, fuentes | 6.4:1 |
| `faint` | `#6B7585` | Etiquetas de ejes | 4.7:1 |
| `rule` | `#DCE1E8` | Líneas divisorias, eje x | — |
| `panel` | `#F3F6FA` | Recuadro "por qué importa" | — |
| `blue` | `#2A78D6` | Serie 1, acento de marca | 4.4:1 |
| `blue_dk` | `#1C5CAB` | Último dato resaltado (punto o barra) | 6.6:1 |
| `blue_lt` | `#A9CBF3` | Barras de contexto | — |
| `orange` | `#EB6834` | Serie 2 (solo comparación: subyacente, Fed) | 3.2:1 → nunca como texto |
| `band` | `#E6EDF6` | Bandas de referencia (intervalo de Banxico, rango neutral) | — |
| `gold` | `#F2B84B` | Cifra protagonista de la portada (solo sobre navy) | 9.3:1 |
| `on_navy` | `#C9D4E3` | Texto secundario sobre navy | 11.1:1 |
| `status.atypical` | `#B42318` + ▲ | Señal atípica (siempre con ícono y palabra) | 6.6:1 |
| `status.unusual` | `#B54708` + ● | Señal inusual (siempre con ícono y palabra) | 5.4:1 |

Reglas: el par azul/naranja pasa la validación para daltonismo (ΔE CVD 24.7; visión normal 33.6). Los colores de estado no se usan para series. No se usan rojo/verde para "bueno/malo": una depreciación no se colorea como pérdida. El dorado no entra en gráficas.

## 4. Tipografía

Inter (OFL), incluida en `assets/fonts/`. Inter Display para titulares y cifras.

| Rol | Tamaño (px @1080) | Peso | Interlineado |
| :--- | :---: | :---: | :---: |
| Cifra de portada | 210 | Display Bold | — |
| Titular de portada | 60 | Display Bold | 1.10 |
| Titular de lámina | 58 (máx. 2 líneas) | Display Bold | 1.10 |
| Cifra de tablero | 44 | Display Bold | — |
| Lectura | 32 | Medium | 1.30 |
| Kicker / subtítulo | 28 | Regular | 1.30 |
| Por qué importa | 27 | Regular | 1.32 |
| Etiquetas, leyenda, ejes, sección | 22 | Regular / Semibold | 1.30 |
| Fuente y referencias | 21 | Regular | 1.30 |

## 5. Gráficas

- **Sin líneas de cuadrícula.** Solo línea base inferior (`rule`, 1.2 px) y 3 marcas en el eje y, sin línea de eje vertical.
- **Etiquetas directas** del último dato (y del mínimo cuando aporta contexto) en `navy`; el color de la serie identifica, el texto siempre usa tokens de texto.
- **Leyenda** en una fila arriba de la gráfica: siempre con ≥ 2 series; con una serie, la leyenda nombra la unidad ("Pesos por dólar (alza = peso más débil)").
- **Un solo eje y.** Nunca doble eje.
- **Bandas de referencia** en `band` con su nombre escrito dentro (intervalo 2%–4%, rango neutral 1.8%–3.6%).
- Líneas de 3 px con extremos redondeados; barras con separación blanca de 2 px; la barra o punto más reciente en `blue_dk`.
- Fechas del eje x: `ene 26`, `abr 26`… (inglés: `Jan 26`).
- **Fuente obligatoria:** "Fuente: Elaboración propia con datos de Banxico (SIE, serie SF43718)." / "Source: Author's elaboration with data from …".

## 6. Plantillas de lámina

| # | Lámina | Contenido |
| :---: | :--- | :--- |
| 1 | Portada (fondo navy) | Etiqueta de la cifra (28 px) · cifra en dorado (210 px) · titular blanco (≤ 3 líneas) · subtítulo · *sparkline* de la serie sin ejes · autor · "Desliza →" |
| 2 | Tema principal | Sección · titular-hallazgo · kicker · leyenda · gráfica · lectura (1 frase) · recuadro "por qué importa" + `Ref.:` · fuente |
| 3 | Tablero | 6 filas: nombre + periodo (+ señal si aplica) · *sparkline* · cifra + cambio |
| 4 | Segundo tema | Igual que la 2 |
| 5 | Cierre | Qué sigue (3 eventos) · Cómo se lee (método) · Referencias numeradas · bloque navy de seguimiento |

## 7. Redacción

- Titular: verbo de dirección + cifra + periodo; ≤ 55 caracteres. Verbos permitidos: sube, baja, se mantiene, avanza, retrocede, se deprecia, se aprecia.
- Decimales: inflación y tasas con 2; variaciones porcentuales con 1; tipo de cambio con 2; diferenciales en pb enteros. Signo menos tipográfico (−).
- Sin adjetivos valorativos ("preocupante", "fuerte"). Sin pronósticos propios.
- "Por qué importa": un mecanismo económico respaldado por la referencia citada.
- Post: gancho ≤ 140 caracteres (cabe antes de "…ver más"), 3 viñetas, pregunta de cierre de bajo compromiso, 3 *hashtags*. El enlace al repositorio va en el primer comentario.

## 8. Referencias base

| Clave | Uso | Referencia |
| :--- | :--- | :--- |
| Traspaso cambiario | Lámina de tipo de cambio | Capistrán, Ibarra y Ramos-Francia (2012), *El Trimestre Económico* 79(316); Ángeles, Cortés y Sámano (2019), Banxico WP 2019-10 |
| Tasa neutral | Postura monetaria, tablero | Banco de México (2024), Informe Trimestral abr–jun, Recuadro 7 (rango 1.8%–3.6%) |
| Diferencial de tasas | Política monetaria | Fama (1984), *Journal of Monetary Economics* 14(3) |
| Lectura de indicadores | Actividad, inflación | Heath (2012), *Lo que indican los indicadores*, INEGI |
| Expectativas | Inflación | Banxico, Encuesta sobre las Expectativas de los Especialistas en Economía del Sector Privado |

Agregar una referencia nueva exige verificar autor, año, título y publicación en la fuente original.

## 9. Auditoría de diseño (v2 → v3, noviembre de 2026)

| # | Hallazgo en v2 | Corrección en v3 |
| :---: | :--- | :--- |
| 1 | Textos de 17–19 px: ~6–7 px reales en teléfono | Mínimo 21 px; cuerpo 27–32 px |
| 2 | 60–90 palabras por lámina temática (3 viñetas + recuadro) | ≤ ~35 palabras: una lectura + por qué importa |
| 3 | Titulares de 3–4 líneas (hasta 90 caracteres) | Titular ≤ 55 caracteres; el contexto pasa al kicker |
| 4 | Sobreprecisión (4.87%, 19.3668, z = +3.39) | 1 decimal en variaciones, 2 en niveles; z solo como etiqueta |
| 5 | Cuadrícula y 6–7 marcas en el eje y | Sin cuadrícula, 3 marcas, etiquetas directas |
| 6 | Fuente sin formato académico | "Elaboración propia con datos de …" con clave de serie |
| 7 | Sin respaldo académico | `Ref.:` en cada lámina + referencias completas al cierre |
| 8 | Tasa real ex ante con la mediana de expectativas | Media (definición de Banxico) y banda del rango neutral |
| 9 | Portada con 5 focos (titular + 4 recuadros) | Una cifra protagonista + titular + *sparkline* |
| 10 | Columna "Señal" vacía en 6 de 8 filas | *Sparklines* de tendencia; señal solo cuando aplica |
| 11 | Etiquetas de datos en color de serie (naranja 3.2:1) | Etiquetas en `navy`; el color solo en la marca |
| 12 | 7 láminas con datos repetidos entre tablero y láminas temáticas | 5 láminas; el hallazgo principal en la 1 y la 2 |
| 13 | Agenda sin contexto metodológico | Sección "Cómo se lee" con la regla de señales y la definición de tasa real |
| 14 | Pie redundante en dos bloques | Pie de una línea con fuente + autor |
