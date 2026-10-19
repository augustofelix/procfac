---
name: conventional-commit
description: Arma y crea commits siguiendo Conventional Commits con la convención del repo (tipo(scope): descripción en español, imperativo). Se usa cuando el usuario pide commitear, hacer un commit, armar el mensaje de commit o revisar si un mensaje respeta la convención.
---

# Conventional Commit

Creás commits con mensajes que siguen Conventional Commits 1.0.0, adaptados a la
convención de este repo.

## Formato

```
<tipo>(<scope>): <descripción>

[cuerpo opcional]

[footer(s) opcional(es)]
```

- **tipo** (obligatorio, en minúsculas, en inglés):
  - `feat`: funcionalidad nueva.
  - `fix`: corrección de un bug.
  - `docs`: solo documentación (PRD.md, AGENTS.md, README, etc.).
  - `test`: agregar o corregir tests.
  - `refactor`: cambio de código que no agrega funcionalidad ni corrige bugs.
  - `perf`: mejora de rendimiento.
  - `style`: formato, espacios, imports; sin cambio de comportamiento.
  - `build`: dependencias, `pyproject.toml`, `uv.lock`, `Makefile`.
  - `ci`: configuración de integración continua.
  - `chore`: tareas de mantenimiento que no encajan en lo anterior (`.gitignore`, config).
  - `revert`: revierte un commit anterior.
- **scope** (recomendado): el área afectada, corto y estable. Ejemplos del repo:
  `PRD`, `AGENTS`, `skills`. Para código: `api`, `ui`, `parser`, `extraccion`,
  `schema`, `auth`, `config`, `tests`.
- **descripción** (obligatoria):
  - En español, en infinitivo (“agregar”, “corregir”, “quitar”, “alinear”).
  - Empieza en minúscula y no termina con punto.
  - Máximo ~72 caracteres en toda la primera línea.
  - Dice QUÉ cambia, no cómo.
- **cuerpo** (opcional): separado por una línea en blanco. Explica el POR QUÉ y el
  contexto; líneas de ~72 caracteres. Si el cambio implementa o toca requerimientos
  del PRD, citá los IDs (RF-xx, RNF-xx, AC-xx).
- **footers** (opcionales): `BREAKING CHANGE: <detalle>`, `Refs: #<issue>`, y las
  líneas de atribución que indique el entorno (p. ej. `Co-Authored-By:`).
- **Cambio incompatible**: agregá `!` antes de los dos puntos (`feat(api)!: ...`)
  y además el footer `BREAKING CHANGE:`.

## Ejemplos

```
feat(parser): extraer ítems de la tabla de la factura con pdfplumber
fix(api): responder 422 cuando se suben cero archivos

Antes devolvía 500 al no recibir archivos. Cubre AC-19.
docs(PRD): aclarar el alcance de las copias DUPLICADO y TRIPLICADO
test(extraccion): agregar test de rechazo de factura tipo B (AC-14)
build: agregar pdfplumber como dependencia
```

## Pasos

1. Mirá el estado: `git status` y `git diff` (y `git diff --staged` si ya hay algo
   en stage). Revisá `git log --oneline -10` para mantener el estilo.
2. Verificá que no se commitee nada prohibido por AGENTS.md: el archivo `.env`,
   facturas reales, PDFs o JSON de `tests/data/`. Si aparece algo así, frená y
   avisale al usuario.
3. Si el diff mezcla cambios no relacionados (p. ej. una feature y un fix, o código
   y docs sin relación), proponé dividirlo en varios commits, uno por tema.
4. Elegí tipo y scope según lo que realmente cambió y redactá el mensaje con el
   formato de arriba.
5. Agregá al stage solo los archivos del commit, por nombre (evitá `git add -A`
   o `git add .`), y creá el commit pasando el mensaje con un heredoc para
   respetar las líneas en blanco.
6. Mostrá el resultado con `git log -1 --stat`.

## Qué NO hacer

- No commitear sin que el usuario lo haya pedido.
- No usar `--no-verify` ni saltear hooks; si un hook falla, corregí el problema y
  creá un commit nuevo (no `--amend` salvo que el usuario lo pida).
- No hacer `push` salvo pedido explícito.
- No escribir descripciones vagas como “cambios varios”, “fix”, “update” o “wip”.
