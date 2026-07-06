"""Render de grafos con pyvis para usar en Streamlit."""

from pyvis.network import Network


def _formatear_monto(monto: float) -> str:
    return f"${monto:,.2f}"


def render_path(grafo, path_report) -> str:
    """
    Visualiza un camino de transacciones como grafo interactivo.

    - Origen: rojo
    - Destino: verde
    - Intermedios: azul
    """
    net = Network(height="420px", width="100%", directed=True, bgcolor="#ffffff")

    nodos = path_report["nodes"]
    pasos = path_report["steps"]

    for i, nodo in enumerate(nodos):
        if i == 0:
            color = "#e74c3c"
            title = "Origen"
        elif i == len(nodos) - 1:
            color = "#2ecc71"
            title = "Destino"
        else:
            color = "#3498db"
            title = "Intermediario"

        net.add_node(nodo, label=nodo, color=color, title=title)

    for paso in pasos:
        etiqueta = _formatear_monto(float(paso["amount"]))
        net.add_edge(paso["from"], paso["to"], label=etiqueta, title=etiqueta)

    return net.generate_html()


def render_smurfing(patron) -> str:
    """
    Visualiza un patron de smurfing como grafo interactivo.

    - Origen: rojo
    - Destino: verde
    - Intermediarios: naranja
    """
    net = Network(height="420px", width="100%", directed=True, bgcolor="#ffffff")

    origen = patron["origen"]
    destino = patron["destino"]

    net.add_node(origen, label=origen, color="#e74c3c", title="Origen")
    net.add_node(destino, label=destino, color="#2ecc71", title="Destino")

    for inter in patron["intermediarios"]:
        cuenta = inter["cuenta"]
        monto_recibido = _formatear_monto(float(inter["monto_recibido"]))
        monto_enviado = _formatear_monto(float(inter["monto_enviado"]))
        ratio = f"{float(inter['ratio']):.0%}"

        net.add_node(cuenta, label=cuenta, color="#e67e22", title="Intermediario")
        net.add_edge(origen, cuenta, label=monto_recibido, title=monto_recibido)
        net.add_edge(cuenta, destino, label=monto_enviado, title=f"{monto_enviado} ({ratio})")

    return net.generate_html()


def render_full_graph(grafo) -> str:
    """Visualiza el grafo completo de transacciones."""
    net = Network(height="600px", width="100%", directed=True, bgcolor="#ffffff")
    
    # Añadir nodos
    for nodo in grafo.nodes():
        in_degree = grafo.in_degree(nodo)
        out_degree = grafo.out_degree(nodo)
        title = f"Cuenta: {nodo}<br>Envíos: {out_degree}<br>Recepciones: {in_degree}"
        net.add_node(str(nodo), label=str(nodo), title=title, color="#95a5a6")
        
    # Añadir aristas
    for u, v, data in grafo.edges(data=True):
        monto = data.get("amount", 0.0)
        etiqueta = _formatear_monto(float(monto))
        net.add_edge(str(u), str(v), title=etiqueta)

    return net.generate_html()
