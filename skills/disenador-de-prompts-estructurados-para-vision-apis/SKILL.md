---
name: disenador-de-prompts-estructurados-para-vision-apis
description: Utiliza esta habilidad para crear prompts de Vision APIs que devuelvan JSON estricto y confiable. Se enfoca en reducir alucinaciones, pedir confidence scores, extraer fechas correctamente y definir jerarquia de tareas y subtareas.
---

# Disenador de Prompts Estructurados para Vision APIs

Usa esta skill cuando una Vision API deba leer imagenes y devolver estructura usable sin postprocesamiento fragil.

## Reglas de prompt
1. Exigir una sola salida JSON valida, sin texto extra.
2. Declarar un esquema fijo con campos obligatorios, opcionales y tipos esperados.
3. Pedir arrays vacios o `null` validos en vez de inventar contenido.
4. Solicitar `confidence` por tarea y para la interpretacion global.
5. Separar tarea principal, subtareas, fecha detectada, fecha normalizada y notas de ambiguedad.

## Estrategia anti-alucinacion
- Indicar que no complete texto ilegible.
- Marcar elementos dudosos como baja confianza.
- Si la jerarquia no es clara, pedir que preserve orden y marque ambiguedad.
- Pedir normalizacion de fechas y mantener tambien el texto original detectado.

## Esquema minimo sugerido
- `tasks[]`
- `tasks[].text`
- `tasks[].category_hint`
- `tasks[].due_text`
- `tasks[].due_iso`
- `tasks[].subtasks[]`
- `tasks[].confidence`
- `tasks[].warnings[]`
- `global_confidence`

## Validacion posterior
- Parsear JSON de forma estricta.
- Rechazar respuestas con campos fuera de contrato si rompen el flujo.
- Aplicar fallback seguro cuando la confianza global sea baja.
