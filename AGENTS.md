# AGENTS.md

## Propósito
App que lee facturas A en PDF nativo (encabezado, ítems, totales/impuestos) y devuelve
un JSON estandarizado, validado por el usuario antes de descargarlo, para que otros
sistemas contables lo importen.

Los IDs de requerimientos y criterios (RF, RNF, AC) se refieren a `PRD.md`.

## Stack
- Python 3.13
- FastAPI (backend/API), Streamlit (UI), pdfplumber (parseo de PDF), Pydantic v2 (validación de esquema)
- Anthropic Claude (API) para la extracción de datos de la factura
- Gestor de dependencias: uv

## Configuración
- Configuración general de la aplicación: archivos `.ini`.
- Usuarios, contraseñas y API key de Claude: archivo `.env` (fuera del repositorio).

## Cómo correr
- Instalar dependencias: `uv sync`
- Levantar la app (backend + UI): `make dev`
- Correr tests: `pytest`

## Qué NO hacer
- No procesar más de un archivo PDF por petición ni un PDF con más de una factura
  (RNF-01, RNF-05): nada de lotes. Si la API recibe 0 archivos o más de uno, responder
  HTTP 422 (AC-19). Las copias ORIGINAL, DUPLICADO y TRIPLICADO de una misma factura
  cuentan como una sola factura (RF-18, AC-36).
- No procesar comprobantes fuera de alcance: solo se admiten facturas tipo A; nada de
  facturas M ni FCE MiPyME A, notas de crédito/débito, recibos, remitos, liquidaciones,
  ni comprobantes tipo B, C, E o X. Los comprobantes fuera de alcance, los PDF con más
  de una factura y los PDF de más de 3 páginas se rechazan antes de enviarlos a la API
  de Claude (RF-18, RF-24, RF-28, AC-14, AC-18, AC-33).
- No aceptar archivos que no sean PDF: el selector solo permite `.pdf` y la API
  responde HTTP 422 (RF-29, AC-34, AC-35).
- No enviar el contenido de la factura a la API de Claude sin antes advertir al usuario
  y obtener su consentimiento (riesgo de datos sensibles); si no acepta, cancelar el
  proceso y volver a la pantalla de carga (RF-10, RF-11, RF-20).
- No devolver campos extraídos por la IA sin mostrárselos al usuario para que los valide
  (riesgo de valores inventados/alucinados) (RF-12, RF-21).
- No permitir procesar comprobantes sin sesión iniciada (RF-09, AC-05).
- No entregar a un usuario datos del proceso de otro, ni en la UI ni por la API
  (RF-05, AC-04, AC-30).
- No asumir un solo usuario a la vez: hasta 5 usuarios pueden procesar un PDF cada uno
  al mismo tiempo (RNF-04, AC-29).
- No escribir el PDF ni el JSON en el sistema de archivos del servidor en ningún momento
  del proceso: todo se procesa en memoria (RNF-07, AC-22). Ojo: FastAPI guarda en un
  archivo temporal en disco los archivos subidos de más de 1 MB.
- No reintentar la llamada a la API de Claude: si devuelve un error, no responde en
  60 segundos o su respuesta no se puede leer o no cumple el Esquema de salida, mostrar
  un mensaje y cancelar el proceso (RF-26, RF-27, AC-32).
- No hardcodear la API key de Claude ni las credenciales de los usuarios en el código
  fuente: se cargan desde el archivo `.env`.
- No commitear el archivo `.env`: las contraseñas de los usuarios y la API key de Claude
  están en texto plano.
- No commitear las facturas reales del Conjunto de referencia ni el PDF de AC-36, ni
  sus JSON esperados: se copian manualmente en `tests/data/` (ignorada en `.gitignore`)
  solo para la prueba y se borran al finalizarla.
- No commitear los PDF armados para la prueba (AC-11, AC-13, AC-14, AC-18 y AC-33) ni
  el JSON esperado de AC-11: también van en `tests/data/`.
- No agregar funcionalidades fuera del alcance del MVP: validación de los datos
  corregidos o completados por el usuario, recepción o envío por email, integración
  con sistemas contables, gestión de usuarios desde la aplicación (alta, baja, cambio o
  recuperación de contraseña), cierre o vencimiento de sesión, reintentos automáticos de
  la API de Claude, límite de tamaño en bytes del PDF, y los campos de ítem reservados
  para la versión 2 (unidad de medida, bonificación, alícuota de IVA, subtotal con IVA).
