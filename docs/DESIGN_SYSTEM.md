# Sistema de diseño · MX Macro Monitor (v5, «revista económica de autor»)

Referentes: portadas de *Bloomberg Businessweek* (titular condensado que ocupa el ancho, color de marca saturado),
*The Economist* (gráfica protagonista con anotaciones, texto justificado y voz de autor). La v4 era un boletín
institucional correcto pero sin identidad; la v5 se lee como una publicación con nombre, número y firma.

## 1. Principios

1. **Una portada que se detiene en el feed.** Banda azul con logo y número, titular de 2–3 palabras en display
   condensado, gráfica protagonista con anotaciones a mano.
2. **Valor propio en cada número**: termómetro con regla pública, comparación con pares, traducción a pesos para
   empresas y un cálculo propio de la semana. Nada de esto está en los comunicados oficiales.
3. **Texto justificado** en todos los párrafos (última línea a la izquierda). Si una línea quedaría con espacios
   mayores a 3.2 veces el normal, se alinea a la izquierda para evitar «ríos».
4. **Toda gráfica sin cuadrícula** y con la línea «Fuente: Elaboración propia con datos de …».
5. **Firma y contacto** en cada página: Isaac Tienda · isaac.tienda01@gmail.com.

## 2. Estructura (v7: 6 páginas, títulos con el dato)

Lector de referencia: persona con atención corta, TDAH y TOC que decide en 2 segundos si sigue deslizando
(agente `.claude/agents/lector-scroll.md`). Reglas:

- **Una idea por página**, máximo ~25 palabras de lectura; kicker, titular, fuente y pie en la misma posición.
- **El titular dice el hecho con su cifra** y se entiende solo (EL PESO CAE 4.9%, 2 DE 6 SEÑALES EN ROJO,
  MÉXICO, TERCERO EN TASA REAL). Va en una línea siempre que quepa a 124 px; si no, dos líneas equilibradas.
- **Firma de columnista**: «Por Isaac Tienda, Economista Senior» en portada; pie con nombre y número de edición;
  correo una sola vez, en la contraportada.
- Método, cuentas, fuentes completas y la nota del autor («Mi lectura») van en el texto del post.
- Sin enlaces al repositorio en piezas públicas. La versión en inglés se redacta en inglés, no se traduce literal.

| # | Página | Titular (ejemplo Nº 1) |
|---|---|---|
| 1 | Portada | EL PESO CAE 4.9% + «Solo 5 de 416 semanas desde 2018 fueron peores» + gráfica anotada |
| 2 | Termómetro MX Macro | 2 DE 6 SEÑALES EN ROJO |
| 3 | México frente a sus pares | MÉXICO, TERCERO EN TASA REAL |
| 4 | ¿Peso o dólar? | NO FUE EL DÓLAR |
| 5 | Para tu empresa | IMPORTAR CUESTA MÁS ($89,910 por cada USD 100,000) |
| 6 | Contraportada | Lo que viene, siguiente número, autor y correo |

Las páginas 3 y 4 se omiten solas si no hay datos; la barra de progreso se ajusta.

**Composición tipográfica.** Todo el texto se compone con HarfBuzz (`src/typeset.py`): respeta el kerning de las
fuentes y el espaciado entre letras (tracking) de los kickers. Matplotlib solo dibuja los contornos; así el
espaciado es uniforme y el mismo en PDF y PNG.

## 3. Logo

Marca: cuadrado azul cobalto con una «M» trazada como serie de tiempo; el último trazo sube y termina en un
**punto verde** (el dato más reciente). Se lee como M (Monitor, México) y como gráfica. Palabra: «MX MACRO» en
negro y «MONITOR» en azul, Archivo Expanded ExtraBold. Archivos en `assets/logo/` (SVG y PNG):

- `mxmm-lockup-paper` (fondo papel), `mxmm-lockup-ink` (fondo negro), `mxmm-lockup-blue` (fondo azul)
- `mxmm-mark` (cuadrado; avatar o ícono)

Se generan con `python src/brand.py`. Área de respeto: la mitad de la altura de la marca. No se deforma ni se
recolorea fuera de estas tres versiones.

## 4. Color (preferencia del autor: azul, negro y verde)

| Token | Hex | Uso | Contraste |
|---|---|---|---|
| `PAPER` | `#F4EFE6` | fondo cálido | — |
| `INK` | `#111418` | titulares, cifras, contraportada | 16.1:1 sobre papel |
| `BODY` | `#2B2B2B` | texto corrido | 12.4:1 |
| `MUTED` | `#5E5A52` | notas, fuentes | 6.0:1 |
| `BLUE` | `#1546C7` | marca: banda de portada, kickers, dato de la semana | 6.7:1; blanco sobre azul 7.7:1 |
| `GREEN` | `#12804F` | marca: punto del logo; estado «Estable» | 4.3:1 |
| `BLUE_LT` / `GREEN_LT` | `#8DADFF` / `#4FD08F` | azul y verde sobre negro | 8.4:1 / 9.5:1 |
| `CTX` | `#8C8578` | barras de contexto | 3.2:1 |
| `OCHRE` / `RED` | `#946410` / `#C62F25` | **solo estado**: Vigilancia / Tensión | 4.5:1 / 4.8:1 |

Azul y verde pasan el validador de paletas (ΔE CVD 24.9). Ocre y rojo no se distinguen para deuteranopía, por eso
**nunca** van solos: siempre con la palabra del estado y la posición en el marcador de tres casillas.

## 5. Tipografía (licencia SIL OFL, `assets/fonts/`)

| Rol | Fuente | Tamaño (px a 1080) |
|---|---|---|
| Titular | Archivo Extra Condensed ExtraBold, ajustado al ancho | 104–200 |
| Cifra grande | Archivo Extra Condensed ExtraBold | 52–200 |
| Logo | Archivo Expanded ExtraBold | — |
| Kicker | Archivo ExtraBold, mayúsculas espaciadas | 20–22 |
| Entradilla, nota del autor | Newsreader Display Medium Italic, justificada | 27–38 |
| Texto | Newsreader Text, justificado | 20–28 |
| Etiquetas, ejes, fuentes | Archivo Regular/SemiBold | 17–25 |

A escala de teléfono (≈0.36) el texto más pequeño (17 px) queda en ≈6 px de pantalla; por eso solo se usa en
fuentes y referencias, nunca en la lectura.

## 6. Gráficas

- Sin cuadrícula; solo línea de cero o eje base. Contexto en `CTX`, dato de la semana en `BLUE`.
- Título en Archivo SemiBold + subtítulo con unidades y periodo.
- Anotaciones «a mano»: Newsreader Display itálica con flecha curva al dato. Máximo tres.
- Fuente al pie: «Fuente: Elaboración propia con datos de …».

## 7. Redacción

- Titular de 2–3 palabras que nombra el hecho (SACUDIDA CAMBIARIA, DOS EN ROJO, TERCERO DE SEIS).
- La entradilla responde «¿qué tan grande es?» con una comparación histórica o entre países.
- Para empresas: siempre en pesos y con la cuenta visible.
- Sin adjetivos que la cifra no sostenga; sin pronósticos propios sin modelo publicado.

## 8. Crítica de la v4 y cambios (noviembre de 2026)

| Hallazgo en v4 | Gravedad | Cambio en v5 |
|---|---|---|
| Sin identidad: parecía comunicado institucional | Crítica | Logo, número de edición, banda de marca, titular display |
| Tipografía genérica (Source Serif / Sans) | Alta | Archivo condensada para titulares + Newsreader justificada |
| Texto alineado a la izquierda | Alta | Justificación con control de espacios |
| Solo reportaba datos oficiales | Crítica | Termómetro, pares, efecto en pesos, cálculo propio |
| Gráficas sin jerarquía | Media | Gráfica protagonista anotada en portada |
| Sin contacto | Media | Correo en cada página y en contraportada |
