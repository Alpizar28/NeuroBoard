---
name: disenador-de-ux-conversacional-en-telegram
description: Utiliza esta habilidad para disenar flujos conversacionales en Telegram con botones inline, mensajes compactos y validaciones claras. Se enfoca en confirmacion, edicion estructurada y manejo de errores amigable.
---

# Disenador de UX Conversacional en Telegram

Usa esta skill para modelar la experiencia del bot cuando el usuario confirma, corrige o cancela tareas.

## Principios
1. Mensajes cortos, escaneables y accionables.
2. Una decision clara por paso.
3. Botones inline antes que texto libre cuando sea posible.
4. Confirmar antes de crear acciones irreversibles.

## Flujo base
1. Acusar recibo de la foto.
2. Informar si esta procesando.
3. Mostrar vista previa agrupada y compacta.
4. Ofrecer `Confirmar`, `Editar`, `Cancelar`.
5. Si hay error, explicar en lenguaje simple y decir que hacer despues.

## Reglas de edicion
- Permitir corregir fechas y categorias sin reescribir todo.
- Preservar contexto de la foto original.
- Si la confianza es baja, pedir nueva foto en vez de una edicion caotica.

## Calidad de mensaje
- Evitar bloques largos.
- Indicar claramente que nada se crea hasta confirmar.
- Mostrar estado final resumido y verificable.
