import httpx
import streamlit as st

from app.core.config import cargar_config

BACKEND_URL = cargar_config()["ui"]["backend_url"]


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


def pantalla_login() -> None:
    st.subheader("Iniciar sesión")
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
    st.info("La carga del PDF se agrega en la Funcionalidad 2.")


st.set_page_config(page_title="procfac")
st.title("Procesamiento de facturas A")

if "token" in st.session_state:
    pantalla_carga()
else:
    pantalla_login()
