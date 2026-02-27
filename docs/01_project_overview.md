# Project Overview: Handwritten Board → Telegram → Google Tasks Automation

## 1. Project Purpose
Build a lightweight, reliable automation system that:
- Receives a handwritten to-do list photo via Telegram.
- Preprocesses the image to improve OCR reliability.
- Uses an external low-cost vision model to extract structured tasks.
- Automatically classifies each task into the correct Google Tasks list.
- Interprets natural language dates & supports subtasks via indentation.
- Always asks for user confirmation before creating tasks.
- Prevents duplicate processing.
- Logs processing events.

## 2. User Behavior Model
User writes tasks:
- Mixed categories in the same photo.
- One task per line, prefixed by dash `-`.
- Subtasks with circular bullet `•` and indentation.

**Example:**
-JOKEM OS: Fix deploy issue
-SUPERIOR: Exam viernes
• tema 1
• tema 2
-Lavar ropa
-JP: Rutina gym mañana

Photos will always contain mixed categories.
User will NOT mark tasks as completed on board, use priorities, or pre-sort tasks by category.
