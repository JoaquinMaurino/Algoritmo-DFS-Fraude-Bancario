import streamlit as st
import streamlit.components.v1 as components

from src.data.graph_builder import get_graph_stats, load_graph_from_csv
from src.algorithms.chain_analysis import (
    buscar_cadena_mas_larga,
    buscar_cadena_sospechosa_mas_larga,
    buscar_todas_las_cadenas_sospechosas,
    buscar_cadenas_sospechosas_desde_cuenta,
)
from src.algorithms.cycle_detection import detectar_ciclos, detectar_ciclos_desde_cuenta
from src.algorithms.smurfing import detectar_smurfing
from src.algorithms.graph_renderer import render_path, render_smurfing, render_full_graph
from src.reports.pdf_report import generar_reporte_pdf
from src.config import DEFAULT_MIN_AMOUNT, DEFAULT_MIN_TRANSACTIONS, DEFAULT_MAX_TRANSACTIONS


st.set_page_config(page_title="Analisis de Fraude Bancario", layout="wide")
st.title("🏦 Analisis de Fraude Bancario")
st.caption("Taller de Programacion III — UNAHUR")


@st.cache_data
def cargar_grafo_desde_path(path: str):
    return load_graph_from_csv(path)


@st.cache_data
def cargar_grafo_desde_bytes(file_bytes: bytes):
    import io

    buffer = io.BytesIO(file_bytes)
    return load_graph_from_csv(buffer)


def mostrar_resultado(resultado, grafo, es_ciclo=False):
    nodos_str = " → ".join(resultado["nodes"])
    prefijo = "Ciclo: " if es_ciclo else ""
    titulo = f"{prefijo}{nodos_str[:80]}... | {resultado['num_hops']} hops | ${resultado['total_amount']:,.2f}"

    with st.expander(titulo):
        pasos = [
            {
                "De": paso["from"],
                "A": paso["to"],
                "Monto": f"${paso['amount']:,.2f}",
            }
            for paso in resultado["steps"]
        ]
        st.table(pasos)

        html = render_path(grafo, resultado)
        components.html(html, height=450, scrolling=False)


# --- Carga del grafo ---
st.sidebar.header("Carga de datos")
archivo = st.sidebar.file_uploader("Subir CSV", type="csv")

try:
    if archivo is not None:
        grafo = cargar_grafo_desde_bytes(archivo.getvalue())
    else:
        grafo = cargar_grafo_desde_path("Transacciones.csv")
except Exception as exc:
    st.error(f"No se pudo cargar el CSV: {exc}")
    st.stop()


st.sidebar.divider()
st.sidebar.header("Reportes")
if st.sidebar.button("📄 Generar Reporte PDF"):
    with st.spinner("Generando reporte... esto puede tardar un momento"):
        stats = get_graph_stats(grafo)
        cadena_larga = buscar_cadena_mas_larga(grafo)
        cadena_sospechosa = buscar_cadena_sospechosa_mas_larga(
            grafo, DEFAULT_MIN_AMOUNT, DEFAULT_MIN_TRANSACTIONS
        )
        todas_cadenas = buscar_todas_las_cadenas_sospechosas(
            grafo, DEFAULT_MIN_AMOUNT, DEFAULT_MIN_TRANSACTIONS, DEFAULT_MAX_TRANSACTIONS
        )
        ciclos = detectar_ciclos(grafo)
        smurfing = detectar_smurfing(grafo)
        
        pdf_bytes = generar_reporte_pdf(
            stats, cadena_larga, cadena_sospechosa, 
            todas_cadenas, ciclos, smurfing
        )
        
        st.sidebar.download_button(
            label="⬇️ Descargar Reporte PDF",
            data=pdf_bytes,
            file_name="reporte_fraude_bancario.pdf",
            mime="application/pdf"
        )


# --- Tabs principales ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Grafo",
    "🔗 Cadenas",
    "🔄 Ciclos",
    "🎯 Smurfing",
    "👤 Por cuenta",
])


# TAB 1: Estadisticas del grafo
with tab1:
    stats = get_graph_stats(grafo)

    col1, col2, col3 = st.columns(3)
    col1.metric("Nodos (cuentas)", stats["total_nodes"])
    col2.metric("Aristas (transacciones)", stats["total_edges"])
    col3.metric("Monto promedio", f"${stats['avg_amount']:,.2f}")

    col4, col5 = st.columns(2)
    with col4:
        st.subheader("Top emisores")
        st.dataframe(stats["top_senders"], use_container_width=True)
    with col5:
        st.subheader("Top receptores")
        st.dataframe(stats["top_receivers"], use_container_width=True)

    st.divider()
    st.subheader("Red completa de transacciones")
    with st.spinner("Renderizando grafo completo..."):
        html_grafo = render_full_graph(grafo)
        components.html(html_grafo, height=620, scrolling=True)


# TAB 2: Cadenas
with tab2:
    st.subheader("Cadena mas larga")
    if st.button("Buscar cadena mas larga", key="btn_larga"):
        resultado = buscar_cadena_mas_larga(grafo)
        if resultado:
            mostrar_resultado(resultado, grafo)

    st.divider()
    st.subheader("Cadena sospechosa mas larga")
    col1, col2 = st.columns(2)
    monto_min = col1.number_input("Monto minimo", value=10000.0, step=1000.0)
    trans_min = col2.number_input("Transacciones minimas", value=3, min_value=1, step=1)

    if st.button("Buscar cadena sospechosa mas larga", key="btn_sospechosa_larga"):
        resultado = buscar_cadena_sospechosa_mas_larga(grafo, monto_min, int(trans_min))
        if resultado:
            mostrar_resultado(resultado, grafo)
        else:
            st.info("No se encontraron cadenas sospechosas.")

    st.divider()
    st.subheader("Todas las cadenas sospechosas")
    col1, col2, col3 = st.columns(3)
    monto_min_all = col1.number_input("Monto minimo (todas)", value=10000.0, step=1000.0)
    trans_min_all = col2.number_input("Transacciones minimas (todas)", value=3, min_value=1, step=1)
    trans_max_all = col3.number_input("Transacciones maximas (todas)", value=10, min_value=1, step=1)

    if st.button("Buscar todas", key="btn_todas"):
        resultados = buscar_todas_las_cadenas_sospechosas(
            grafo,
            float(monto_min_all),
            int(trans_min_all),
            int(trans_max_all),
        )
        if resultados:
            st.success(f"Se encontraron {len(resultados)} cadenas. (Mostrando top 20)")
            for res in resultados[:20]:
                mostrar_resultado(res, grafo)
        else:
            st.info("No se encontraron cadenas sospechosas.")


# TAB 3: Ciclos
with tab3:
    st.subheader("Ciclos en el grafo")
    if st.button("Detectar ciclos", key="btn_ciclos"):
        ciclos = detectar_ciclos(grafo)
        if ciclos:
            st.success(f"Se encontraron {len(ciclos)} ciclos. (Mostrando top 20)")
            for ciclo in ciclos[:20]:
                mostrar_resultado(ciclo, grafo, es_ciclo=True)
        else:
            st.info("No se detectaron ciclos en el grafo.")


# TAB 4: Smurfing
with tab4:
    st.subheader("Deteccion de Smurfing")
    st.caption(f"Umbral: {int(0.80 * 100)}% o mas de lo recibido al destino.")

    if st.button("Detectar smurfing", key="btn_smurfing"):
        patrones = detectar_smurfing(grafo)
        if patrones:
            st.success(f"Se encontraron {len(patrones)} patrones. (Mostrando top 20)")
            for patron in patrones[:20]:
                titulo = (
                    f"Origen: {patron['origen']} → Destino: {patron['destino']}"
                    f" | {len(patron['intermediarios'])} intermediarios"
                )
                with st.expander(titulo):
                    filas = [
                        {
                            "Intermediario": i["cuenta"],
                            "Recibido": f"${i['monto_recibido']:,.2f}",
                            "Enviado": f"${i['monto_enviado']:,.2f}",
                            "Ratio": f"{i['ratio']:.0%}",
                        }
                        for i in patron["intermediarios"]
                    ]
                    st.table(filas)
                    html = render_smurfing(patron)
                    components.html(html, height=450, scrolling=False)
        else:
            st.info("No se detectaron patrones de smurfing.")


# TAB 5: Por cuenta
with tab5:
    st.subheader("Analisis por cuenta")
    nodos = sorted(grafo.nodes())
    cuenta = st.selectbox("Seleccionar cuenta", nodos)

    sub1, sub2 = st.tabs(["Cadenas sospechosas", "Ciclos"])

    with sub1:
        col1, col2, col3 = st.columns(3)
        monto_min_acc = col1.number_input("Monto minimo (cuenta)", value=10000.0, step=1000.0)
        trans_min_acc = col2.number_input("Transacciones minimas (cuenta)", value=3, min_value=1, step=1)
        trans_max_acc = col3.number_input("Transacciones maximas (cuenta)", value=10, min_value=1, step=1)

        if st.button("Buscar cadenas sospechosas", key="btn_cadenas_cuenta"):
            resultados = buscar_cadenas_sospechosas_desde_cuenta(
                grafo,
                cuenta,
                float(monto_min_acc),
                int(trans_min_acc),
                int(trans_max_acc),
            )
            if resultados:
                st.success(f"Se encontraron {len(resultados)} cadenas. (Mostrando top 20)")
                for res in resultados[:20]:
                    mostrar_resultado(res, grafo)
            else:
                st.info("No se encontraron cadenas sospechosas.")

    with sub2:
        if st.button("Detectar ciclos desde esta cuenta", key="btn_ciclos_cuenta"):
            ciclos = detectar_ciclos_desde_cuenta(grafo, cuenta)
            if ciclos:
                st.success(f"Se encontraron {len(ciclos)} ciclos. (Mostrando top 20)")
                for ciclo in ciclos[:20]:
                    mostrar_resultado(ciclo, grafo, es_ciclo=True)
            else:
                st.info("No se detectaron ciclos para esta cuenta.")
