---
name: disenador-de-motores-de-clasificacion-deterministica
description: Utiliza esta habilidad para construir clasificadores por reglas y scoring simple, sin ML pesado. Se enfoca en prefijos, heuristicas explicables, manejo de ambiguedad y fallbacks limpios.
---

# Disenador de Motores de Clasificacion Deterministica

Usa esta skill cuando debas asignar tareas a categorias o listas con reglas explicables y bajo costo.

## Enfoque
1. Priorizar reglas exactas y faciles de auditar.
2. Agregar scoring ligero solo cuando varias reglas compiten.
3. Mantener trazabilidad: cada decision debe poder explicarse.

## Componentes
- Reglas de alta prioridad para prefijos exactos.
- Normalizacion de texto antes de comparar.
- Scoring pequeno para aliases y coincidencias parciales.
- Resultado con categoria, puntaje y razon.

## Manejo de ambiguedad
- Si hay empate o baja diferencia, marcar como ambiguo.
- Nunca auto-confirmar casos dudosos sin vista previa humana.
- Definir una categoria fallback segura.

## Antipatrones
- Mezclar reglas de negocio con efectos secundarios.
- Umbrales ocultos o arbitrarios sin documentar.
- Introducir ML pesado para un problema estable y pequeno.
