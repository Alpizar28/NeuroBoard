---
name: disenador-de-pipelines-de-procesamiento-de-imagen
description: Utiliza esta habilidad para definir pipelines ligeros de procesamiento de imagen orientados a OCR sobre fotos reales. Se enfoca en preprocesamiento, correccion de perspectiva, binarizacion y robustez ante fotos imperfectas sin exigir hardware pesado.
---

# Disenador de Pipelines de Procesamiento de Imagen

Usa esta skill para disenar el flujo que convierte una foto irregular en una entrada confiable para OCR o Vision API.

## Objetivos
1. Mejorar legibilidad sin introducir artefactos.
2. Mantener el pipeline barato en CPU y memoria.
3. Manejar fotos torcidas, con sombras, ruido o contraste pobre.

## Secuencia base
1. Validar formato y abrir la imagen con protecciones basicas.
2. Corregir orientacion y, si aplica, perspectiva solo cuando la mejora sea clara.
3. Redimensionar a una resolucion util para OCR sin exceder ancho objetivo.
4. Ajustar contraste e iluminar de forma conservadora.
5. Reducir ruido con filtros suaves.
6. Aplicar binarizacion ligera solo si aumenta legibilidad real.
7. Exportar en un formato compacto y estable.

## Criterios
- Nunca aplicar todos los filtros por costumbre; cada paso debe justificar su costo.
- Preservar trazos finos de escritura manual.
- Preferir heuristicas simples antes que CV pesada.
- Si la estructura de la foto es demasiado mala, devolver rechazo claro en vez de inventar datos.

## Salidas esperadas
- Imagen preprocesada lista para OCR.
- Metadatos utiles: tamano final, rotacion aplicada, calidad percibida, motivo de rechazo.
