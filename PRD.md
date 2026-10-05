# PRD-001: Procesamiento de facturas — Software para el procesamiento de facturas en formato PDF

## Contexto y Problema
En un estudio contable o empresa es necesario cargar las facturas a un sistema que posteriormente calcule los impuestos.
Dada la gran cantidad de comprobantes y complejidad de estos, es necesario reducir el tiempo y errores de tipeo.
Es muy común que en las áreas contables las personas afectadas destinen gran parte de su tiempo a esta tarea, en lugar de destinar el tiempo al control, análisis y asesoramiento profesional.

Personas:
- Mariela administrativa contable, carga mensualmente 5000 comprobantes de diferentes clientes y quiere reducir este tiempo para poder aportarle mas valor al análisis de los gastos de sus clientes.
- Juan Manuel: analista financiero, ingresa al mes 800 comprobantes de compras de una empresa agropecuaria con sus respectivos detalles de productos, le lleva mucho tiempo por los errores en la carga de cada producto.

## Objetivos
Proporcionar una aplicación capaz de leer los documentos de factura en formato PDF nativo y que los mismos sean retornados en un formato estándar (Json) para que cualquier aplicación pueda utilizarlo para su importación y posterior procesamiento.

## Requerimientos Funcionales
- RF-01: Debe leer el encabezado de la factura.
- RF-02: Debe leer el detalle del cuerpo del comprobante.
- RF-03: Debe obtener la cantidad de cada producto detectado en el detalle.
- RF-04: Debe diferenciar, en el pie del comprobante, los totales, subtotales e impuestos.
- RF-05: Debe aislar la interacción de cada usuario dentro de su propia sesión.
- RF-06: Movido a RNF-06.
- RF-07: Debe devolver como archivo descargable el JSON con los campos validados por el usuario.
- RF-08: Movido a RNF-07.
- RF-09: Debe rechazar toda petición de procesamiento de un usuario sin sesión iniciada.
- RF-10: Debe solicitar el consentimiento del usuario mostrándole una advertencia de que el contenido de la factura se enviará a la API de Claude.
- RF-11: Debe cancelar el proceso si el usuario rechaza el consentimiento; cancelar el proceso significa volver a la pantalla de carga sin entregar ningún JSON.
- RF-12: Debe mostrar al usuario los campos extraídos para que los valide.
- RF-13: Debe permitir al usuario corregir los campos extraídos antes de descargar el JSON.
- RF-14: Debe cancelar el proceso si el usuario cancela la validación.
- RF-15: Debe indicar al usuario qué campos no pudo obtener del comprobante.
- RF-16: Debe permitir al usuario completar los campos que no se pudieron obtener antes de descargar el JSON.
- RF-17: Debe mostrar al usuario un mensaje aclarando que no se pudo leer el comprobante cuando la extracción no obtiene ningún campo.
- RF-18: Debe rechazar, antes de enviarlo a la API de Claude, todo PDF que contenga más de una factura o cuyo tipo de comprobante no pueda identificar como factura A, M o FCE MiPyME A.
- RF-19: Debe autenticar al usuario con las credenciales definidas en un archivo .env.
- RF-20: Debe enviar el contenido de la factura a la API de Claude solo si el usuario dio su consentimiento.
- RF-21: Debe habilitar la descarga del JSON solo después de que el usuario valida los campos mostrados; validar significa confirmarlos de forma explícita.
- RF-22: Debe mostrar al usuario un mensaje con el motivo del rechazo cuando rechaza un PDF según RF-18.
- RF-23: Debe cancelar el proceso cuando rechaza un PDF según RF-18.

## Requerimientos No Funcionales
- RNF-01: La cantidad de archivos PDF por petición debe ser = 1.
- RNF-02: El tiempo de cada petición de un usuario sobre un PDF que contiene una sola factura, medido desde que acepta el consentimiento hasta que se le muestran los campos extraídos para validar, debe ser < 30 segundos p95, calculado sobre las 50 facturas del conjunto de pruebas de RNF-03 procesadas de a una, con un solo usuario con sesión activa.
- RNF-03: La extracción de datos debe tener una precisión >= 90% en cada uno de los campos Punto de venta, Número de comprobante, CUIT emisor, CUIT receptor, Subtotal, Impuestos y Total, evaluada sobre un conjunto de pruebas estándar de 50 facturas en PDF nativo. Un campo se considera correcto solo si su valor coincide exactamente con el del JSON esperado. El campo Impuestos es una lista de pares concepto e importe, y coincide exactamente si contiene los mismos pares que el JSON esperado, sin importar el orden. El conjunto de pruebas se compone de 50 facturas reales y sus 50 JSON esperados, cada JSON nombrado `<CUIT emisor>_<punto de venta>_<número de factura>.json`.
- RNF-04: El sistema debe admitir hasta 5 usuarios registrados en el archivo .env, todos con sesión activa y procesando un PDF cada uno al mismo tiempo.
- RNF-05: La cantidad de facturas por archivo PDF debe ser = 1.
- RNF-06: La cantidad de peticiones necesarias para obtener los campos extraídos de un PDF, una vez aceptado el consentimiento, debe ser = 1.
- RNF-07: La cantidad de archivos con el contenido del PDF o del JSON que quedan almacenados en el servidor al finalizar el proceso debe ser = 0.

## Criterios de Aceptación
- AC-01 (RF-12): Dado un archivo PDF de prueba de cada tipo admitido (factura A, M y FCE MiPyME A), Cuando el sistema termina la extracción, antes de que el usuario edite ningún campo, Entonces la respuesta JSON de la extracción cumple estrictamente con la estructura y tipos definidos en el esquema Pydantic (punto_venta, numero_comprobante, cuit_emisor, razon_social_emisor, domicilio_emisor, localidad_emisor, condicion_iva_emisor, cuit_receptor, razon_social_receptor, domicilio_receptor, localidad_receptor, condicion_iva_receptor, fecha_comprobante, condicion_venta, subtotal, impuestos, total, items).
- AC-02 (RNF-01): Dado un usuario autenticado en la pantalla de carga, Cuando intenta seleccionar más de un archivo PDF, Entonces el selector solo le permite elegir uno.
- AC-03 (RNF-03): Dado el conjunto de pruebas estándar de 50 facturas en PDF nativo y sus JSON esperados, Cuando el sistema ejecuta la extracción sobre cada factura y compara el JSON obtenido con el JSON esperado del mismo CUIT emisor, punto de venta y número de factura, Entonces el porcentaje de valores que coinciden exactamente es >= 90% en cada uno de los campos Punto de venta, Número de comprobante, CUIT emisor, CUIT receptor, Subtotal, Impuestos y Total.
- AC-04 (RF-05): Dado los usuarios autenticados A y B con sesiones activas simultáneas, Cuando A procesa un PDF, Entonces el JSON resultante se entrega solo en la sesión de A y la sesión de B no muestra ni permite descargar ningún dato de ese proceso.
- AC-05 (RF-09): Dado un usuario sin sesión iniciada, Cuando intenta procesar un PDF, Entonces el sistema rechaza la petición con un código HTTP 401 Unauthorized y no procesa el archivo.
- AC-06 (RF-10, RF-20): Dado un usuario autenticado en la pantalla de carga, Cuando sube un PDF con una sola factura A, M o FCE MiPyME A, Entonces el sistema muestra la advertencia y no se realiza ninguna llamada a la API de Claude mientras el usuario no acepta.
- AC-07 (RF-11, RF-20): Dado un usuario al que se le mostró la advertencia, Cuando rechaza el consentimiento, Entonces el sistema vuelve a la pantalla de carga sin entregar ningún JSON y no se realiza ninguna llamada a la API de Claude.
- AC-08 (RF-12, RF-20): Dado un usuario que aceptó el consentimiento, Cuando termina la extracción, Entonces el sistema le muestra todos los campos del esquema definido en AC-01, con los valores extraídos.
- AC-09 (RF-13): Dado un usuario al que se le muestran los campos extraídos, Cuando corrige el valor de un campo y descarga el JSON, Entonces el JSON contiene el valor corregido.
- AC-10 (RF-14): Dado un usuario en el paso de validación, Cuando cancela la validación, Entonces el sistema vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-11 (RF-15): Dado un PDF de factura de prueba que no incluye algunos campos del esquema y su JSON esperado con esos campos vacíos, Cuando el sistema termina la extracción, Entonces muestra al usuario los campos obtenidos e indica como no obtenidos exactamente los campos vacíos del JSON esperado.
- AC-12 (RF-16): Dado un usuario al que se le indicaron campos no obtenidos, Cuando los completa y descarga el JSON, Entonces el JSON contiene los valores completados.
- AC-13 (RF-17): Dado un PDF de factura de prueba cuyo tipo se puede identificar como factura A, M o FCE MiPyME A pero que no incluye ninguno de los campos del esquema, Cuando el sistema termina la extracción, Entonces muestra un mensaje aclarando que no se pudo leer el comprobante junto con todos los campos vacíos para que el usuario los complete.
- AC-14 (RNF-05, RF-18, RF-22, RF-23): Dado un PDF que contiene dos o más facturas, Cuando el usuario lo sube, Entonces el sistema lo rechaza sin enviar su contenido a la API de Claude, muestra un mensaje explicando que el PDF contiene más de una factura y vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-15 (RF-02): Dado un PDF de factura de prueba con N ítems en el detalle y su JSON esperado conocido, Cuando el sistema ejecuta la extracción, Entonces el campo items del JSON contiene exactamente N ítems.
- AC-16 (RF-03): Dado un PDF de factura de prueba y su JSON esperado conocido, Cuando el sistema ejecuta la extracción, Entonces la cantidad de cada ítem coincide exactamente con la del JSON esperado.
- AC-17 (RNF-06): Dado un usuario que aceptó el consentimiento, Cuando el sistema procesa el PDF, Entonces los campos extraídos se devuelven en la respuesta de esa misma petición, sin requerir consultas posteriores.
- AC-18 (RF-18, RF-22, RF-23): Dado un PDF de cada uno de estos comprobantes: nota de crédito, nota de débito, recibo, remito, liquidación, factura B, factura C, factura E, comprobante tipo X y un comprobante cuyo tipo no se puede identificar, Cuando el usuario lo sube, Entonces el sistema lo rechaza sin enviar su contenido a la API de Claude, muestra un mensaje indicando que el tipo de comprobante no es factura A, M o FCE MiPyME A y vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-19 (RNF-01): Dado un usuario autenticado, Cuando envía a la API una petición con más de un archivo, Entonces el sistema la rechaza con un código HTTP 422 Unprocessable Entity y no procesa ningún archivo.
- AC-20 (RF-01): Dado un PDF de factura de prueba y su JSON esperado conocido, Cuando el sistema ejecuta la extracción, Entonces los campos punto_venta, numero_comprobante, cuit_emisor, razon_social_emisor, domicilio_emisor, localidad_emisor, condicion_iva_emisor, cuit_receptor, razon_social_receptor, domicilio_receptor, localidad_receptor, condicion_iva_receptor, fecha_comprobante y condicion_venta coinciden exactamente con los del JSON esperado.
- AC-21 (RF-04): Dado un PDF de factura de prueba y su JSON esperado conocido, Cuando el sistema ejecuta la extracción, Entonces los campos subtotal, impuestos y total coinciden exactamente con los del JSON esperado, según el criterio de coincidencia de RNF-03.
- AC-22 (RNF-07): Dado un proceso finalizado por descarga del JSON, cancelación o rechazo, Cuando se inspecciona el sistema de archivos del servidor, Entonces no existe ningún archivo creado durante el proceso que contenga el PDF o el JSON.
- AC-23 (RF-07, RF-21): Dado un usuario que validó los campos extraídos, Cuando pide descargar el JSON, Entonces recibe un archivo con extensión .json cuyos valores coinciden con los campos validados.
- AC-24 (RF-19): Dado un usuario definido en el archivo .env, Cuando ingresa su usuario y contraseña correctos, Entonces el sistema inicia su sesión y le muestra la pantalla de carga.
- AC-25 (RF-19): Dado un usuario en la pantalla de inicio de sesión, Cuando ingresa un usuario o una contraseña que no coinciden con los del archivo .env, Entonces el sistema no inicia la sesión y no le muestra la pantalla de carga.
- AC-26 (RF-21): Dado un usuario al que se le muestran los campos extraídos y que todavía no los validó, Cuando intenta descargar el JSON, Entonces la descarga no está disponible.
- AC-27 (RNF-02): Dado el conjunto de pruebas de RNF-03 y un solo usuario con sesión activa, Cuando el sistema procesa las 50 facturas de a una y se mide el tiempo desde que el usuario acepta el consentimiento hasta que se le muestran los campos extraídos, Entonces el percentil 95 de los 50 tiempos es < 30 segundos.
- AC-28 (RNF-04): Dado un archivo .env con 5 usuarios, Cuando los 5 inician sesión al mismo tiempo, Entonces los 5 ven la pantalla de carga.
- AC-29 (RNF-04): Dados 5 usuarios con sesión activa, Cuando cada uno sube al mismo tiempo un PDF distinto con una sola factura A, M o FCE MiPyME A y acepta el consentimiento, Entonces cada uno ve en su sesión los campos extraídos de su propio PDF.
- AC-30 (RF-05): Dados los usuarios autenticados A y B con sesiones activas simultáneas, Cuando A procesa un PDF y B envía peticiones a la API con su propia sesión, Entonces ninguna respuesta a B contiene datos del proceso de A.

## Fuera de Alcance
- No se procesan PDF escaneados (no nativos). No se escanean comprobantes desde la aplicación.
- No se reciben facturas por email ni se envía el JSON resultante por email.
- No se procesan notas de crédito, notas de débito, recibos, remitos ni liquidaciones.
- No se procesan comprobantes tipo B, C, E y X.
- No se cargan comprobantes por lotes.
- No se procesan PDF que contengan más de una factura.
- No se integra con sistema contable.
- No se validan los datos corregidos o completados manualmente por el usuario.
- No se gestionan usuarios desde la aplicación (alta, baja, cambio o recuperación de contraseña); se definen solo en el archivo .env.

## Riesgos y Dependencias
- Riesgo: la IA obtenga valores inventados, mitigación mostrar los resultados al usuario para que decida.
- Riesgo: Hay diferentes formatos de comprobantes, mitigación informar cuando no se pueden obtener los datos.
- Riesgo: Compartir información sensible con los modelos de IA, mitigación advertir al usuario esta situación y en caso de no aceptar cancelar el proceso.
- Riesgo: Las contraseñas de los usuarios y la API key de Claude se guardan en texto plano en un archivo .env, mitigación el archivo queda fuera del repositorio.
- Riesgo: Los datos corregidos o completados manualmente por el usuario no se validan, por lo que el JSON descargado puede no cumplir el esquema Pydantic, mitigación se acepta el riesgo en el MVP.
- Riesgo: La API de Claude puede no responder o demorarse e impedir cumplir RNF-02, mitigación se acepta el riesgo en el MVP.
- Riesgo: El campo Impuestos se compara por coincidencia exacta de cada par concepto e importe, y no está definido cómo se escribe el concepto, por lo que una diferencia de formato (por ejemplo, "IVA 21%" contra "IVA 21 %") cuenta como error en RNF-03 y AC-21, mitigación se acepta el riesgo en el MVP y se resuelve en la versión 2.
- Riesgo: El conjunto de pruebas de RNF-03 usa facturas reales con datos de terceros, mitigación no se suben al repositorio, se copian manualmente solo para la prueba y se borran al finalizarla.
- Dependencias: Python con FastApi, pdfplumber, Streamlit, Validación con Pydantic, API de Claude para la extracción de datos.
- Configuración: la configuración general de la aplicación se define en archivos .ini; los usuarios, las contraseñas y la API key de Claude se definen en un archivo .env.
