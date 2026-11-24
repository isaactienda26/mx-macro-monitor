# Playbook de publicación semanal · MX Macro Monitor en LinkedIn

Objetivo: una publicación cada semana con el mismo formato, construida solo con datos oficiales y en menos de 20 minutos de trabajo manual.

## Rutina de cada lunes

| Hora (centro de México) | Paso | Tiempo |
| :--- | :--- | :---: |
| 07:00 | GitHub Actions genera carrusel, texto y boletín y los sube a `bulletins/` | automático |
| 08:00 | Abrir `bulletins/linkedin_post.md` y `bulletins/carousel_es.pdf` en GitHub (o descargar el *artifact* de la corrida) | 2 min |
| 08:05 | **Control de calidad** (abajo) | 5–10 min |
| 08:30 | Publicar: *Iniciar publicación → Agregar documento → carousel_es.pdf*; pegar el texto del post; título del documento sugerido en el mismo archivo | 3 min |
| 08:35 | Pegar como primer comentario la versión en inglés (incluye el enlace al repositorio; los enlaces en el cuerpo del post reducen el alcance) | 1 min |
| 08:35–09:30 | Responder cada comentario; las respuestas en la primera hora son las que más alcance generan | 10 min |

Si el lunes es festivo o hay un dato mayor el martes (por ejemplo, decisión de Banxico el jueves), se puede correr de nuevo el flujo desde *Actions → Weekly Mexico Macro Bulletin → Run workflow* y publicar ese día.

## Control de calidad antes de publicar

1. **Titular:** ¿sigue vigente? Si después de las 07:00 h se publicó un dato relevante, vuelve a correr el flujo.
2. **Cifra principal contra el boletín oficial:** comparar el dato del titular con el comunicado de INEGI o Banxico de esa semana (redondeo a un decimal).
3. **Señales "Inusual" o "Atípico":** revisar que el movimiento no sea un error de captura de la fuente (abrir `data/raw/<serie>.csv`).
4. **Avisos de datos:** si `latest_es.md` termina con "Avisos de datos", alguna fuente falló y se usó caché; mencionarlo o posponer.
5. **Revisión visual:** abrir las 7 láminas del PDF.

## Ajustes manuales permitidos

- Agregar al texto del post un dato que el pipeline no cubre (por ejemplo, la inflación de la primera quincena), con su fuente.
- Cambiar la pregunta de cierre para dirigirla a un sector o audiencia específica.
- **No** editar cifras del carrusel a mano: si una cifra está mal, se corrige en el código o la fuente y se vuelve a generar.

## Reglas editoriales

- Solo fuentes oficiales; cada lámina cita serie y fuente.
- Describir dirección y magnitud; no atribuir causas que los datos no muestran. Si quieres agregar una causa (por ejemplo, un evento de mercado), cítala con su fuente en el texto del post.
- Sin pronósticos propios ni posturas político-partidistas.
- Pregunta de cierre de bajo compromiso, orientada a la experiencia de la audiencia.

## Indicadores de seguimiento (registrar cada viernes)

Impresiones, interacciones (reacciones + comentarios + compartidos), tasa de interacción, nuevos seguidores, visitas al perfil y clics al repositorio. Tras 8 semanas, comparar qué tipo de titular (tipo de cambio, inflación, Banxico, actividad) genera más interacción y ajustar la pregunta de cierre.

## Perfil

- Titular sugerido: *Economista | Inteligencia de mercado y análisis macroeconómico de México | Autor de MX Macro Monitor*.
- Fijar en *Destacados* la publicación más reciente y el enlace al repositorio.

## Mantenimiento

| Cuándo | Tarea |
| :--- | :--- |
| Al publicarse | Agregar el calendario 2027 de Banxico (decisiones, minutas, encuesta) a `config/agenda.yml` |
| Junio de 2027 | Agregar el calendario de INEGI del segundo semestre de 2027 (`cal_2027.pdf`) |
| Si falla una corrida | Revisar el log de Actions: token vencido (renovar en Banxico/INEGI y actualizar *Secrets*) o cambio de endpoint |
| Trimestral | Revisar en el log de la corrida que cada serie muestre un último dato reciente (si una serie se congela, la clave pudo cambiar) |
