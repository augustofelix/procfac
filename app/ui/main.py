import httpx
import streamlit as st

from app.core.config import cargar_config

BACKEND_URL = cargar_config()["ui"]["backend_url"]


class SesionPerdida(Exception):
    """El backend no reconoce el token, por ejemplo porque se reinició y perdió las sesiones."""


def iniciar_sesion(usuario: str, contrasena: str) -> str | None:
    """Devuelve el token de sesión, o None si las credenciales son incorrectas."""
    respuesta = httpx.post(
        f"{BACKEND_URL}/login",
        json={"usuario": usuario, "contrasena": contrasena},
        timeout=10,
    )
    if respuesta.status_code == 401:
        return None
    respuesta.raise_for_status()
    return respuesta.json()["token"]


def verificar(nombre: str, contenido: bytes) -> str | None:
    """Devuelve None si el PDF se puede procesar, o el motivo del rechazo (RF-22)."""
    respuesta = httpx.post(
        f"{BACKEND_URL}/verificar",
        files={"archivo": (nombre, contenido, "application/pdf")},
        headers={"Authorization": f"Bearer {st.session_state.token}"},
        timeout=30,
    )
    if respuesta.status_code == 401:
        raise SesionPerdida
    if respuesta.status_code == 422:
        return respuesta.json()["detail"]["mensaje"]
    respuesta.raise_for_status()
    return None


def avisar(tipo: str, mensaje: str) -> None:
    """Deja un mensaje para mostrar en la próxima pantalla."""
    st.session_state.aviso = (tipo, mensaje)


def mostrar_aviso() -> None:
    if aviso := st.session_state.pop("aviso", None):
        tipo, mensaje = aviso
        getattr(st, tipo)(mensaje)


def volver_a_carga() -> None:
    """Cancela el proceso sin entregar ningún JSON y vacía el selector de archivos."""
    st.session_state.pop("pdf", None)
    st.session_state.pop("consentimiento", None)
    st.session_state.carga_id = st.session_state.get("carga_id", 0) + 1
    st.rerun()


def perder_sesion() -> None:
    st.session_state.clear()
    avisar("warning", "La sesión se perdió. Iniciá sesión de nuevo.")
    st.rerun()


def pantalla_login() -> None:
    st.subheader("Iniciar sesión")
    mostrar_aviso()
    with st.form("login"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        enviado = st.form_submit_button("Ingresar")
    if not enviado:
        return
    try:
        token = iniciar_sesion(usuario, contrasena)
    except httpx.HTTPError:
        st.error("No se pudo conectar con el servidor.")
        return
    if token is None:
        st.error("Usuario o contraseña incorrectos.")
        return
    # session_state es propio de cada sesión del navegador (RF-05)
    st.session_state.token = token
    st.session_state.usuario = usuario
    st.rerun()


def pantalla_carga() -> None:
    st.subheader("Cargar factura")
    st.caption(f"Sesión iniciada como {st.session_state.usuario}")
    mostrar_aviso()
    # Un solo archivo y solo .pdf (RNF-01, RF-29, AC-02, AC-34)
    archivo = st.file_uploader(
        "Factura A en PDF",
        type=["pdf"],
        accept_multiple_files=False,
        key=f"pdf_{st.session_state.get('carga_id', 0)}",
    )
    if archivo is None:
        return
    contenido = archivo.getvalue()
    try:
        with st.spinner("Verificando el PDF..."):
            rechazo = verificar(archivo.name, contenido)
    except SesionPerdida:
        perder_sesion()
    except httpx.HTTPError:
        avisar("error", "No se pudo conectar con el servidor.")
        volver_a_carga()
    if rechazo:
        avisar("error", rechazo)
        volver_a_carga()
    # El PDF queda solo en memoria, en la sesión del usuario (RNF-07)
    st.session_state.pdf = (archivo.name, contenido)
    st.rerun()


def pantalla_consentimiento() -> None:
    nombre, _ = st.session_state.pdf
    st.subheader("Consentimiento")
    # Nada se envía a Claude mientras el usuario no acepte (RF-10, RF-20, AC-06)
    st.warning(
        f"El contenido de la factura **{nombre}** se enviará a la API de Claude (Anthropic) "
        "para extraer sus datos. La factura puede contener datos sensibles. "
        "¿Aceptás enviarla?"
    )
    aceptar, rechazar = st.columns(2)
    if aceptar.button("Aceptar y enviar", type="primary"):
        st.session_state.consentimiento = True
        st.rerun()
    if rechazar.button("Rechazar"):
        # Cancela el proceso sin llamar a Claude ni entregar JSON (RF-11, AC-07)
        avisar("info", "Proceso cancelado: la factura no se envió.")
        volver_a_carga()


def pantalla_extraccion() -> None:
    st.subheader("Extracción")
    st.info("La extracción con Claude se agrega en la Funcionalidad 3.")


st.set_page_config(page_title="procfac")
st.title("Procesamiento de facturas A")

if "token" not in st.session_state:
    pantalla_login()
elif "pdf" not in st.session_state:
    pantalla_carga()
elif not st.session_state.get("consentimiento"):
    pantalla_consentimiento()
else:
    pantalla_extraccion()
