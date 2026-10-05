# AGENTS.md

## Propósito
App que lee facturas en PDF nativo (encabezado, ítems, totales/impuestos) y devuelve
un JSON estandarizado, validado por el usuario antes de descargarlo, para que otros
sistemas contables lo importen.

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
  (RNF-01, RNF-05): nada de lotes. Si la API recibe más de un archivo, responder
  HTTP 422 (AC-19).
- No procesar comprobantes fuera de alcance: solo se admiten facturas tipo A, M y
  FCE MiPyME A; nada de notas de crédito/débito, recibos, remitos, liquidaciones, ni
  comprobantes tipo B, C, E o X. Los comprobantes fuera de alcance y los PDF con más
  de una factura se rechazan antes de enviarlos a la API de Claude (RF-18, AC-14, AC-18).
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
- No almacenar el PDF ni el JSON resultante (RNF-07).
- No hardcodear la API key de Claude ni las credenciales de los usuarios en el código
  fuente: se cargan desde el archivo `.env`.
- No commitear el archivo `.env`: las contraseñas de los usuarios y la API key de Claude
  están en texto plano.
- No commitear las facturas reales ni los JSON esperados del conjunto de pruebas de
  RNF-03: se copian manualmente en `tests/data/` (ignorada en `.gitignore`) solo para
  la prueba y se borran al finalizarla.
- No agregar funcionalidades fuera del alcance del MVP: validación de los datos
  corregidos o completados por el usuario, recepción o envío por email, integración
  con sistemas contables, gestión de usuarios desde la aplicación (alta, baja, cambio o
  recuperación de contraseña).
