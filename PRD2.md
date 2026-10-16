# PRD-001: Procesamiento de facturas — Software para el procesamiento de facturas en formato PDF

## Contexto y Problema
En un estudio contable o empresa es necesario cargar las facturas a un sistema que posteriormente calcule los impuestos.
Dada la gran cantidad de comprobantes y complejidad de estos, es necesario reducir el tiempo y errores de tipeo.
Es muy común que en las áreas contables las personas afectadas destinen gran parte de su tiempo a esta tarea, en lugar de destinar el tiempo al control, análisis y asesoramiento profesional.

Personas:
- Mariela administrativa contable, carga mensualmente 5000 comprobantes de diferentes clientes y quiere reducir este tiempo para poder aportarle mas valor al análisis de los gastos de sus clientes.
- Juan Manuel: analista financiero, ingresa al mes 800 comprobantes de compras de una empresa agropecuaria con sus respectivos detalles de productos, le lleva mucho tiempo por los errores en la carga de cada producto.

## Objetivos
Proporcionar una aplicación capaz de leer los documentos de factura en formato PDF nativo y que los mismos sean retornados en un formato estándar (JSON) para que cualquier aplicación pueda utilizarlo para su importación y posterior procesamiento.
Se considera logrado cuando cada factura A se convierte en un JSON validado por el usuario, con la extracción lista en menos de 30 segundos p95 (RNF-02) y una precisión de al menos 90% por campo (RNF-03).

## Requerimientos Funcionales
- RF-01: El sistema debe leer el encabezado de la factura.
- RF-02: El sistema debe leer el detalle del cuerpo del comprobante.
- RF-03: El sistema debe obtener la cantidad de cada producto detectado en el detalle.
- RF-04: El sistema debe diferenciar, en el pie del comprobante, los totales, subtotales e impuestos.
- RF-05: El sistema debe aislar la interacción de cada usuario dentro de su propia sesión.
- RF-06: Movido a RNF-06.
- RF-07: El sistema debe devolver como archivo descargable el JSON con los campos validados por el usuario.
- RF-08: Movido a RNF-07.
- RF-09: El sistema debe rechazar toda petición de procesamiento de un usuario sin sesión iniciada.
- RF-10: El sistema debe solicitar el consentimiento del usuario mostrándole una advertencia de que el contenido de la factura se enviará a la API de Claude.
- RF-11: El sistema debe cancelar el proceso si el usuario rechaza el consentimiento; cancelar el proceso significa volver a la pantalla de carga sin entregar ningún JSON.
- RF-12: El sistema debe mostrar al usuario los campos extraídos para que los valide.
- RF-13: El sistema debe permitir al usuario corregir los campos extraídos antes de descargar el JSON.
- RF-14: El sistema debe cancelar el proceso si el usuario cancela la validación.
- RF-15: El sistema debe indicar al usuario qué campos no pudo obtener del comprobante.
- RF-16: El sistema debe permitir al usuario completar los campos que no se pudieron obtener antes de descargar el JSON.
- RF-17: El sistema debe mostrar al usuario un mensaje aclarando que no se pudo leer el comprobante cuando la extracción deja en `null` todos los campos del Esquema de salida, salvo items e impuestos, que pueden quedar en `null` o como lista vacía.
- RF-18: El sistema debe rechazar, antes de enviarlo a la API de Claude, todo PDF que contenga más de una factura; las copias ORIGINAL, DUPLICADO y TRIPLICADO de una misma factura cuentan como una sola factura.
- RF-19: El sistema debe autenticar al usuario con las credenciales definidas en un archivo .env.
- RF-20: El sistema debe enviar el contenido de la factura a la API de Claude solo si el usuario dio su consentimiento.
- RF-21: El sistema debe habilitar la descarga del JSON solo después de que el usuario valida los campos mostrados; validar significa confirmarlos de forma explícita.
- RF-22: El sistema debe mostrar al usuario un mensaje con el motivo del rechazo cuando rechaza un PDF según RF-18, RF-24 o RF-28.
- RF-23: El sistema debe cancelar el proceso cuando rechaza un PDF según RF-18, RF-24 o RF-28.
- RF-24: El sistema debe rechazar, antes de enviarlo a la API de Claude, todo PDF cuyo tipo de comprobante no pueda identificar como factura A.
- RF-25: El sistema debe devolver el resultado de la extracción con la estructura y los tipos definidos en el Esquema de salida.
- RF-26: El sistema debe mostrar al usuario un mensaje indicando que no se pudo completar la extracción cuando la API de Claude falla; la API de Claude falla cuando devuelve un error, cuando no responde dentro de 60 segundos o cuando su respuesta no se puede leer o no cumple el Esquema de salida.
- RF-27: El sistema debe cancelar el proceso cuando la API de Claude falla según RF-26.
- RF-28: El sistema debe rechazar, antes de enviarlo a la API de Claude, todo PDF de más de 3 páginas.
- RF-29: El sistema debe rechazar todo archivo que no sea un PDF.

### Esquema de salida
| Campo | Tipo | Formato |
|---|---|---|
| punto_venta | entero | sin ceros a la izquierda |
| numero_comprobante | entero | sin ceros a la izquierda |
| cuit_emisor | texto | 11 dígitos, sin guiones |
| razon_social_emisor | texto | libre, tal como figura en el PDF |
| domicilio_emisor | texto | libre, tal como figura en el PDF |
| localidad_emisor | texto | libre, tal como figura en el PDF |
| condicion_iva_emisor | texto | libre, tal como figura en el PDF |
| cuit_receptor | texto | 11 dígitos, sin guiones |
| razon_social_receptor | texto | libre, tal como figura en el PDF |
| domicilio_receptor | texto | libre, tal como figura en el PDF |
| localidad_receptor | texto | libre, tal como figura en el PDF |
| condicion_iva_receptor | texto | libre, tal como figura en el PDF |
| fecha_comprobante | texto | `AAAA-MM-DD` (ISO 8601) |
| condicion_venta | texto | libre, tal como figura en el PDF |
| subtotal | decimal | redondeado a 2 decimales, punto como separador decimal |
| impuestos | lista de pares descripcion_impuesto e importe | descripcion_impuesto: texto libre, tal como figura en el PDF; importe: decimal, redondeado a 2 decimales, punto como separador decimal |
| total | decimal | redondeado a 2 decimales, punto como separador decimal |
| items | lista de ítems | cada ítem tiene los campos de la tabla "Campos de cada ítem" |

#### Campos de cada ítem
| Campo | Tipo | Formato |
|---|---|---|
| codigo | texto | libre, tal como figura en el PDF |
| descripcion | texto | libre, tal como figura en el PDF |
| cantidad | decimal | sin redondeo, punto como separador decimal |
| precio_unitario | decimal | redondeado a 2 decimales, punto como separador decimal |
| subtotal_item | decimal | redondeado a 2 decimales, punto como separador decimal |

Todo importe del esquema es decimal, redondeado a 2 decimales, con punto como separador decimal.

Todo campo que no se pudo obtener del comprobante se representa con el valor `null`. Los campos items e impuestos se representan con `null` cuando no se pudieron obtener y con una lista vacía (`[]`) cuando el comprobante no tiene ninguno.

## Requerimientos No Funcionales
- RNF-01: La cantidad de archivos PDF por petición debe ser = 1.
- RNF-02: El tiempo de cada petición de un usuario sobre un PDF que contiene una sola factura, medido desde que acepta el consentimiento hasta que se le muestran los campos extraídos para validar, debe ser < 30 segundos p95, calculado sobre las 20 facturas del Conjunto de referencia procesadas de a una, con un solo usuario con sesión activa.
- RNF-03: La extracción de datos debe tener una precisión >= 90% en cada uno de los campos del Esquema de salida, salvo items, en la cantidad de ítems, en la cantidad de cada ítem y en los campos codigo, descripcion, precio_unitario y subtotal_item de cada ítem, evaluada sobre el Conjunto de referencia. La precisión es el porcentaje de facturas del Conjunto de referencia en las que el valor obtenido coincide exactamente con el del JSON esperado; para la cantidad de cada ítem, una factura cuenta como correcta solo si coinciden las cantidades de todos sus ítems; para los campos de cada ítem, una factura cuenta como correcta en un campo solo si ese campo coincide en todos sus ítems. Los ítems se comparan por posición: el primer ítem obtenido con el primer ítem del JSON esperado, y así sucesivamente. Si la cantidad de ítems obtenidos no coincide con la del JSON esperado, la factura cuenta como incorrecta en la cantidad de cada ítem y en los campos codigo, descripcion, precio_unitario y subtotal_item. El campo impuestos es una lista de pares descripcion_impuesto e importe, y coincide exactamente si contiene los mismos pares que el JSON esperado, sin importar el orden.
- RNF-04: El sistema debe admitir hasta 5 usuarios registrados en el archivo .env, todos con sesión activa y procesando un PDF cada uno al mismo tiempo; con los 5 procesando a la vez, el tiempo de cada petición, medido desde que el usuario acepta el consentimiento hasta que se le muestran los campos extraídos para validar, debe ser < 30 segundos para cada uno de los 5.
- RNF-05: La cantidad de facturas por archivo PDF debe ser = 1.
- RNF-06: La cantidad de peticiones necesarias para obtener los campos extraídos de un PDF, una vez aceptado el consentimiento, debe ser = 1.
- RNF-07: La cantidad de archivos con el contenido del PDF o del JSON que se escriben en el sistema de archivos del servidor durante el proceso debe ser = 0.

## Criterios de Aceptación
Conjunto de referencia: 20 facturas A reales en PDF nativo, cada una con su JSON esperado, contra el cual se valida el resultado de la extracción. Las facturas y sus JSON esperados no se suben al repositorio. Cada JSON esperado se nombra igual que su PDF, con extensión .json.

Los PDF de AC-11, AC-13, AC-14, AC-18 y AC-33 no forman parte del Conjunto de referencia: son PDF armados para la prueba. Estos PDF y el JSON esperado de AC-11 no se suben al repositorio.

El PDF de AC-36 es una factura A real descargada con sus copias ORIGINAL, DUPLICADO y TRIPLICADO, y no forma parte del Conjunto de referencia.

- AC-01 (RF-25): Dado cada PDF del Conjunto de referencia, Cuando el sistema termina la extracción, antes de que el usuario edite ningún campo, Entonces la respuesta JSON de la extracción de cada uno de los 20 PDF cumple con la estructura y los tipos definidos en el Esquema de salida.
- AC-02 (RNF-01): Dado un usuario autenticado en la pantalla de carga, Cuando intenta seleccionar más de un archivo PDF, Entonces el selector solo le permite elegir uno.
- AC-03: Eliminado, cubierto por AC-15, AC-16, AC-20 y AC-21.
- AC-04 (RF-05): Dado los usuarios autenticados A y B con sesiones activas simultáneas, Cuando A procesa un PDF, Entonces el JSON resultante se entrega solo en la sesión de A y la sesión de B no muestra ni permite descargar ningún dato de ese proceso.
- AC-05 (RF-09): Dado un usuario sin sesión iniciada, Cuando intenta procesar un PDF, Entonces el sistema rechaza la petición con un código HTTP 401 Unauthorized y no procesa el archivo.
- AC-06 (RF-10, RF-20): Dado un usuario autenticado en la pantalla de carga, Cuando sube un PDF con una sola factura A, Entonces el sistema muestra una advertencia que indica que el contenido de la factura se enviará a la API de Claude, con una opción para aceptar y otra para rechazar, y no se realiza ninguna llamada a la API de Claude mientras el usuario no acepta.
- AC-07 (RF-11, RF-20): Dado un usuario al que se le mostró la advertencia, Cuando rechaza el consentimiento, Entonces el sistema vuelve a la pantalla de carga sin entregar ningún JSON y no se realiza ninguna llamada a la API de Claude.
- AC-08 (RF-12, RF-20): Dado un usuario que aceptó el consentimiento, Cuando termina la extracción, Entonces el sistema le muestra todos los campos definidos en el Esquema de salida, con los valores extraídos.
- AC-09 (RF-13): Dado un usuario al que se le muestran los campos extraídos, Cuando corrige el valor de un campo y descarga el JSON, Entonces el JSON contiene el valor corregido.
- AC-10 (RF-14): Dado un usuario en el paso de validación, Cuando cancela la validación, Entonces el sistema vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-11 (RF-15): Dado un PDF de factura A armado para la prueba que no incluye algunos campos del Esquema de salida y su JSON esperado con esos campos en `null`, Cuando el sistema termina la extracción, Entonces muestra al usuario los campos obtenidos e indica como no obtenidos exactamente los campos en `null` del JSON esperado; un campo con lista vacía no se indica como no obtenido.
- AC-12 (RF-16): Dado un usuario al que se le indicaron campos no obtenidos, Cuando los completa y descarga el JSON, Entonces el JSON contiene los valores completados.
- AC-13 (RF-17): Dado un PDF de factura A armado para la prueba, cuyo tipo se puede identificar como factura A pero que no incluye ninguno de los campos del Esquema de salida, Cuando el sistema termina la extracción, Entonces muestra un mensaje aclarando que no se pudo leer el comprobante junto con todos los campos vacíos para que el usuario los complete.
- AC-14 (RNF-05, RF-18, RF-22, RF-23): Dado un PDF que contiene dos o más facturas, Cuando el usuario lo sube, Entonces el sistema lo rechaza sin enviar su contenido a la API de Claude, muestra un mensaje explicando que el PDF contiene más de una factura y vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-15 (RF-02, RNF-03): Dado el Conjunto de referencia, Cuando el sistema ejecuta la extracción sobre cada factura, Entonces la cantidad de ítems del campo items coincide exactamente con la del JSON esperado en al menos el 90% de las facturas, según RNF-03.
- AC-16 (RF-03, RNF-03): Dado el Conjunto de referencia, Cuando el sistema ejecuta la extracción sobre cada factura, Entonces las cantidades de todos los ítems coinciden exactamente con las del JSON esperado en al menos el 90% de las facturas, según RNF-03.
- AC-17 (RNF-06): Dado un usuario que aceptó el consentimiento, Cuando el sistema procesa el PDF, Entonces los campos extraídos se devuelven en la respuesta de esa misma petición, sin requerir consultas posteriores.
- AC-18 (RF-24, RF-22, RF-23): Dado un PDF de cada uno de estos comprobantes: nota de crédito, nota de débito, recibo, remito, liquidación, factura M, FCE MiPyME A, factura B, factura C, factura E, comprobante tipo X, un PDF protegido con contraseña, un PDF escaneado y un comprobante cuyo tipo no se puede identificar, Cuando el usuario lo sube, Entonces el sistema lo rechaza sin enviar su contenido a la API de Claude, muestra un mensaje indicando que no se pudo identificar el comprobante como factura A y vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-19 (RNF-01): Dado un usuario autenticado, Cuando envía a la API una petición con 0 archivos o con más de un archivo, Entonces el sistema la rechaza con un código HTTP 422 Unprocessable Entity y no procesa ningún archivo.
- AC-20 (RF-01, RNF-03): Dado el Conjunto de referencia, Cuando el sistema ejecuta la extracción sobre cada factura, Entonces cada uno de los campos punto_venta, numero_comprobante, cuit_emisor, razon_social_emisor, domicilio_emisor, localidad_emisor, condicion_iva_emisor, cuit_receptor, razon_social_receptor, domicilio_receptor, localidad_receptor, condicion_iva_receptor, fecha_comprobante y condicion_venta coincide exactamente con el del JSON esperado en al menos el 90% de las facturas, según RNF-03.
- AC-21 (RF-04, RNF-03): Dado el Conjunto de referencia, Cuando el sistema ejecuta la extracción sobre cada factura, Entonces cada uno de los campos subtotal, impuestos y total coincide exactamente con el del JSON esperado en al menos el 90% de las facturas, según RNF-03.
- AC-22 (RNF-07): Dado un usuario que procesa un PDF, Cuando se inspecciona el sistema de archivos del servidor después de la carga del PDF, durante la validación y después de que el proceso termina por descarga del JSON, cancelación o rechazo, y después de que el usuario cierra el navegador sin terminar el proceso, Entonces en ninguna de esas inspecciones existe un archivo escrito durante el proceso que contenga el PDF o el JSON.
- AC-23 (RF-07, RF-21): Dado un usuario que validó los campos extraídos, Cuando pide descargar el JSON, Entonces recibe un archivo con extensión .json cuyos valores coinciden con los campos validados.
- AC-24 (RF-19): Dado un usuario definido en el archivo .env, Cuando ingresa su usuario y contraseña correctos, Entonces el sistema inicia su sesión y le muestra la pantalla de carga.
- AC-25 (RF-19): Dado un usuario en la pantalla de inicio de sesión, Cuando ingresa un usuario o una contraseña que no coinciden con los del archivo .env, Entonces el sistema no inicia la sesión y no le muestra la pantalla de carga.
- AC-26 (RF-21): Dado un usuario al que se le muestran los campos extraídos y que todavía no los validó, Cuando intenta descargar el JSON, Entonces la descarga no está disponible.
- AC-27 (RNF-02): Dado el Conjunto de referencia y un solo usuario con sesión activa, Cuando el sistema procesa las 20 facturas de a una y se mide el tiempo desde que el usuario acepta el consentimiento hasta que se le muestran los campos extraídos, Entonces el percentil 95 de los 20 tiempos es < 30 segundos.
- AC-28 (RNF-04): Dado un archivo .env con 5 usuarios, Cuando los 5 inician sesión al mismo tiempo, Entonces los 5 ven la pantalla de carga.
- AC-29 (RNF-04): Dados 5 usuarios con sesión activa, Cuando cada uno sube al mismo tiempo un PDF distinto del Conjunto de referencia y acepta el consentimiento, Entonces cada uno ve en su sesión los campos extraídos de su propio PDF en menos de 30 segundos desde que aceptó el consentimiento, según RNF-04.
- AC-30 (RF-05): Dados los usuarios autenticados A y B con sesiones activas simultáneas, Cuando A procesa un PDF y B envía peticiones a la API con su propia sesión, Entonces ninguna respuesta a B contiene datos del proceso de A.
- AC-31 (RF-02, RNF-03): Dado el Conjunto de referencia, Cuando el sistema ejecuta la extracción sobre cada factura, Entonces cada uno de los campos codigo, descripcion, precio_unitario y subtotal_item de los ítems coincide exactamente con el del JSON esperado en al menos el 90% de las facturas, según RNF-03.
- AC-32 (RF-26, RF-27): Dado un usuario que aceptó el consentimiento, Cuando la API de Claude devuelve un error, no responde dentro del tiempo de espera de RF-26 o devuelve una respuesta que no se puede leer o no cumple el Esquema de salida, Entonces en cada uno de esos casos el sistema muestra un mensaje indicando que no se pudo completar la extracción y vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-33 (RF-28, RF-22, RF-23): Dado un usuario autenticado en la pantalla de carga, Cuando sube un PDF de 4 páginas con una sola factura A, Entonces el sistema lo rechaza sin enviar su contenido a la API de Claude, muestra un mensaje indicando que el PDF supera las 3 páginas y vuelve a la pantalla de carga sin entregar ningún JSON.
- AC-34 (RF-29): Dado un usuario autenticado en la pantalla de carga, Cuando abre el selector de archivos, Entonces el selector solo le permite elegir archivos con extensión .pdf.
- AC-35 (RF-29): Dado un usuario autenticado, Cuando envía a la API una petición con un archivo que no es un PDF, Entonces el sistema la rechaza con un código HTTP 422 Unprocessable Entity y no procesa el archivo.
- AC-36 (RF-18): Dado un usuario autenticado en la pantalla de carga y un PDF de 3 páginas con las copias ORIGINAL, DUPLICADO y TRIPLICADO de una misma factura A, una por página, con su JSON esperado, Cuando sube el PDF y acepta el consentimiento, Entonces el sistema no lo rechaza, le muestra la advertencia de consentimiento y, después de la extracción, el campo items contiene los ítems de una sola copia, en la misma cantidad que en su JSON esperado.

## Fuera de Alcance
- No se procesan PDF escaneados (no nativos). No se escanean comprobantes desde la aplicación.
- No se reciben facturas por email ni se envía el JSON resultante por email.
- No se procesan notas de crédito, notas de débito, recibos, remitos ni liquidaciones.
- No se procesan comprobantes tipo B, C, E y X.
- No se procesan facturas M ni FCE MiPyME A en el MVP.
- No se cargan comprobantes por lotes.
- No se procesan PDF que contengan más de una factura.
- No se integra con sistema contable.
- No se validan los datos corregidos o completados manualmente por el usuario.
- No se gestionan usuarios desde la aplicación (alta, baja, cambio o recuperación de contraseña); se definen solo en el archivo .env.
- No se extraen de cada ítem la unidad de medida, el porcentaje de bonificación, el importe de bonificación, la alícuota de IVA ni el subtotal con IVA; se reservan para la versión 2.
- No se reintenta automáticamente la llamada a la API de Claude.
- No se ofrece cierre de sesión ni vencimiento de sesión.
- No se limita el tamaño en bytes del PDF.

## Riesgos y Dependencias
- Riesgo: la IA obtenga valores inventados, mitigación mostrar los resultados al usuario para que decida.
- Riesgo: Hay diferentes formatos de comprobantes, mitigación informar cuando no se pueden obtener los datos.
- Riesgo: Compartir información sensible con los modelos de IA, mitigación advertir al usuario esta situación y en caso de no aceptar cancelar el proceso.
- Riesgo: Las contraseñas de los usuarios y la API key de Claude se guardan en texto plano en un archivo .env, mitigación el archivo queda fuera del repositorio.
- Riesgo: Los datos corregidos o completados manualmente por el usuario no se validan, por lo que el JSON descargado puede no cumplir el Esquema de salida, mitigación se acepta el riesgo en el MVP.
- Riesgo: La detección del tipo de comprobante y de la cantidad de facturas se hace sin la API de Claude y puede fallar, rechazando facturas A válidas o enviando a la API un PDF que debía rechazarse, mitigación AC-14, AC-18 y los AC del Conjunto de referencia verifican ambos casos; se acepta el riesgo residual en el MVP.
- Riesgo: La API de Claude puede no responder o demorarse e impedir cumplir RNF-02 y RNF-04, mitigación se acepta el riesgo en el MVP.
- Riesgo: El campo impuestos se compara por coincidencia exacta de cada par descripcion_impuesto e importe, y descripcion_impuesto debe coincidir con el texto tal como figura en el PDF, por lo que si la extracción no copia ese texto exacto (por ejemplo, "IVA 21 %" en lugar de "IVA 21%") cuenta como error en RNF-03 y AC-21, mitigación se acepta el riesgo en el MVP y se resuelve en la versión 2.
- Riesgo: El Conjunto de referencia y el PDF de AC-36 usan facturas reales con datos de terceros, mitigación no se suben al repositorio, se copian manualmente solo para la prueba y se borran al finalizarla.
- Dependencias: Python con FastAPI, pdfplumber, Streamlit, Validación con Pydantic, API de Claude para la extracción de datos.
- Configuración: la configuración general de la aplicación se define en archivos .ini; los usuarios, las contraseñas y la API key de Claude se definen en un archivo .env.
