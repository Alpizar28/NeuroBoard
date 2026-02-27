---
name: disenador-de-logging-minimalista-util
description: Utiliza esta habilidad para definir logging util y austero en servicios pequenos. Se enfoca en registrar solo lo necesario para depurar rapido, evitar ruido, no llenar disco y mantener contexto suficiente para incidentes.
---

# Disenador de Logging Minimalista pero Util

Usa esta skill para disenar trazas que ayuden a depurar sin convertir el disco en un basurero.

## Que si registrar
- Inicio y fin de cada flujo principal.
- Identificadores de correlacion y estado de procesamiento.
- Conteos utiles: tareas detectadas, tareas creadas, reintentos.
- Errores con causa resumida y etapa donde ocurrieron.

## Que no registrar
- Imagenes completas.
- Tokens, secretos o payloads sensibles completos.
- Mensajes repetitivos en loops o paths exitosos triviales.

## Formato recomendado
1. Logs estructurados o lineas consistentes.
2. Nivel correcto: `INFO`, `WARNING`, `ERROR`.
3. Campos compactos y comparables.

## Politica
- Favorecer logs resumidos por evento, no spam por subpaso.
- Mantener retencion pequena y rotacion simple.
- Si un dato no ayuda a depurar ni auditar, no se loggea.
