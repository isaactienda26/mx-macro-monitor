# Metodología de las métricas propias (`src/valueadd.py`)

Todas las entradas provienen de fuentes oficiales del pipeline; ninguna cifra se captura a mano.

## 1. La semana en la historia (cálculo de la semana)

- Cambio semanal del FIX (Banxico, SF43718): cierre del viernes contra el viernes previo. La semana en curso se
  mide de punto a punto contra el dato de 7 días naturales antes.
- Rango: número de semanas completas con un movimiento igual o mayor en la misma dirección, más uno.
  Percentil = 100 × (1 − semanas mayores / semanas totales).

## 2. Efecto en pesos para empresas

Costo de una importación de USD 100,000 al FIX de hoy menos el costo al FIX de hace una semana. Es una cuenta
mecánica: no incluye coberturas, comisiones ni el tipo de cambio pactado de cada empresa.

## 3. Termómetro MX Macro

| Señal | Fuente | Estable | Vigilancia | Tensión |
|---|---|---|---|---|
| Inflación general, subyacente y expectativas a 12 meses (media) | INEGI, Banxico | a ±0.5 pp de la meta de 3% | dentro de 2%–4% | fuera de 2%–4% |
| Tasa real ex ante (tasa objetivo − expectativa media a 12 meses) | Banxico | dentro de 1.8%–3.6% | hasta 0.5 pp fuera | más de 0.5 pp fuera |
| Tipo de cambio, cambio semanal | Banxico | z < 1.5 | 1.5 ≤ z < 2 | z ≥ 2 |
| Actividad (IGAE), cambio mensual | INEGI | z < 1.5 | 1.5 ≤ z < 2 | z ≥ 2 |

z = valor absoluto del z-score del último cambio frente a su historia previa (60 meses; 260 semanas para el tipo
de cambio), sin incluir el dato más reciente. Índice MX Macro = 100 × suma de puntos / 12, con Estable = 0,
Vigilancia = 1, Tensión = 2. Es un resumen descriptivo, no un modelo de probabilidad de crisis.

## 4. México frente a sus pares

Tasa real ex post = tasa de política vigente − inflación anual del último mes disponible para todos los países.
Tasas: BIS, Central bank policy rates (diaria); para México, Banxico (SF61745). Inflación: BIS, Consumer prices
(serie 771, variación anual). Muestra: Brasil, Chile, Colombia, México, Perú y Estados Unidos.

## 5. ¿Fue el peso o el dólar?

Variación de MXN, BRL e índice amplio del dólar (Reserva Federal, H.10, vía FRED: DEXMXUS, DEXBZUS, DTWEXBGS)
entre la última fecha común y siete días antes. Se usa H.10 para que las tres series tengan la misma hora de
cierre; por eso la ventana puede diferir del FIX de la portada.

## 6. Convención de signos

En todo el número, el signo sigue a la moneda: **negativo = la moneda se debilita frente al dólar**. La magnitud
es la variación del tipo de cambio (USD/MXN, FIX), la misma que reportan Banxico y la prensa (19.37 contra 18.47 =
el peso −4.9%). El índice amplio del dólar va con su propio signo: positivo = el dólar se fortalece. Los datos se
guardan en `data/` como tipo de cambio (positivo = más pesos por dólar); el cambio de signo es solo de presentación.
