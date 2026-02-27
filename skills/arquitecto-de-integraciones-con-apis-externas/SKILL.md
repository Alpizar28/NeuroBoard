---
name: arquitecto-de-integraciones-con-apis-externas
description: Utiliza esta habilidad para integrar APIs externas de forma robusta y barata. Se enfoca en timeouts, retries con backoff, validacion estricta de JSON, token refresh y manejo defensivo de errores como los de Google Tasks.
---

# Arquitecto de Integraciones con APIs Externas

Usa esta skill cuando el sistema dependa de servicios remotos y debas evitar cuelgues, respuestas corruptas o estados inconsistentes.

## Reglas
1. Cada llamada externa debe tener timeout explicito.
2. Reintentar solo errores transitorios y con backoff acotado.
3. Validar payloads de entrada y salida antes de usarlos.
4. Separar autenticacion, transporte y logica de negocio.
5. Refrescar tokens de manera controlada y persistir el nuevo estado.

## Para Google Tasks y APIs similares
- Manejar 401 con refresh una sola vez por intento.
- Diferenciar errores de permisos, cuota, formato y timeout.
- Registrar contexto minimo util sin exponer secretos.
- Nunca asumir que una respuesta parcial significa exito total.

## Resultado esperado
- Cliente pequeno y reusable.
- Errores tipados o al menos clasificados.
- Reintentos seguros y observables.
