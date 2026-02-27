---
name: disenador-de-sistemas-idempotentes
description: Utiliza esta habilidad para evitar duplicados y efectos repetidos en bots y automatizaciones. Se enfoca en deduplicacion, reintentos seguros, control de estado y creacion unica de registros externos.
---

# Disenador de Sistemas Idempotentes

Usa esta skill cuando una misma entrada pueda llegar varias veces por reintentos, duplicados de webhook o fallos parciales.

## Objetivos
1. Detectar si una entrada ya fue procesada.
2. Evitar doble creacion en servicios externos.
3. Permitir reintentos seguros despues de fallos transitorios.

## Patrones
- Derivar una llave idempotente estable por evento o contenido.
- Persistir estados como `received`, `processing`, `confirmed`, `completed`, `failed`.
- Validar antes de crear y registrar despues de crear.
- Si el paso remoto puede fallar a mitad, guardar evidencia suficiente para reanudar.

## Riesgos a evitar
- Marcar como completado antes de tiempo.
- Reintentar ciegamente sin verificar estado previo.
- Usar memoria volatil como unica fuente de deduplicacion.
