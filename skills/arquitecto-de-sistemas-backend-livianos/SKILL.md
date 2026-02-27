---
name: arquitecto-de-sistemas-backend-livianos
description: Utiliza esta habilidad para disenar backend y flujos de procesamiento que deban correr con 2GB RAM y 1 CPU. Prioriza async no bloqueante, memoria acotada, pipelines simples y evita sobre-ingenieria como colas o servicios extra sin necesidad real.
---

# Arquitecto de Sistemas Backend Livianos

Usa esta skill cuando el sistema deba vivir en una VPS limitada, dentro de Docker y sin margen para componentes pesados.

## Principios
1. Mantener un solo proceso o un microservicio unico mientras sea suficiente.
2. Evitar dependencias persistentes extra como Redis, Kafka o workers separados si no resuelven un cuello de botella real.
3. Preferir IO async y operaciones cortas; si algo bloquea CPU, reducir su costo antes de paralelizar.
4. Diseñar por etapas claras para que cada paso use la menor memoria posible y libere datos intermedios rapido.
5. Favorecer SQLite, colas en memoria pequenas y estructuras de datos simples cuando cumplan el requerimiento.

## Checklist de diseno
- Confirmar limite de memoria y tiempo de respuesta esperado.
- Separar trabajo IO-bound de trabajo CPU-bound.
- Procesar bytes o streams en lugar de duplicar buffers grandes.
- Reusar objetos y evitar caches grandes por defecto.
- Definir fallbacks simples antes de agregar complejidad operacional.

## Patrones recomendados
- FastAPI con endpoints async y validacion estricta.
- Servicios pequenos con funciones puras para transformaciones.
- Timeouts y cancelacion explicita en llamadas externas.
- Persistencia minima para idempotencia, auditoria y reintentos.

## Antipatrones
- Multiples workers por defecto.
- Fan-out innecesario de tareas.
- Cargar modelos locales pesados.
- Mantener imagenes completas en memoria mas tiempo del necesario.
