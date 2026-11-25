"""Anuncio del costo antes de una tarea cara (``REG-LIM-004``).

La regla dice: una tarea que va a tardar se anuncia antes de empezarla. Cuando
el anuncio depende de la memoria del agente, no se cumple; cuando lo hace el
motor, sí. Aquí el motor mide lo que va a procesar, cuenta lo que costó antes
(la bitácora tiene los tiempos reales) y **se detiene** si falta
``--confirmar``.

Tres decisiones:

1. **El costo se mide, no se inventa.** Se cuentan archivos y bytes del objetivo
   y se cita la mediana de duración de ejecuciones anteriores del mismo comando.
   Sin historial se dice «sin referencia», no se estima en segundos al azar.
2. **Sin ``--confirmar`` no se ejecuta.** Un aviso que se puede ignorar no es una
   puerta. La ejecución rechazada termina con :data:`CODIGO_RECHAZO`, así que no
   hace nada y la bitácora deja constancia del intento sin castigar al agente que
   se detuvo — se detuvo, que es justo lo que se le pedía.
3. **Solo las tareas caras de verdad.** ``ingest`` (documentos) y ``enrich``
   (una llamada al modelo por unidad) anuncian. ``scan``, ``build`` y ``refresh``
   son recorridos locales que se miden solos en la bitácora; exigirles bandera
   habría convertido la puerta en ruido en el flujo normal de verificación.
"""

from __future__ import annotations

import os
from statistics import median
from typing import Any, Iterable

from context_map.core.audit.bitacora import CODIGO_RECHAZO, leer

#: Extensiones que ``ingest`` procesa como documentos.
EXTENSIONES_DOCUMENTO: frozenset[str] = frozenset({
    ".pdf", ".docx", ".doc", ".odt", ".pptx", ".xlsx", ".csv",
    ".md", ".txt", ".rst", ".html", ".htm", ".epub", ".json",
})

#: Extensiones que ``enrich`` analiza (una unidad por función).
EXTENSIONES_CODIGO: frozenset[str] = frozenset({".py"})

#: Primera línea del anuncio.
AVISO = "[coste] Tarea cara: {comando} · {archivos} archivo(s) · {mb:.1f} MB{referencia}"


def _opcion(args: Any, nombre: str, defecto: Any = None) -> Any:
    """Lee una opción de un ``dict`` o de un ``Namespace``."""
    if isinstance(args, dict):
        return args.get(nombre, defecto)
    return getattr(args, nombre, defecto)


def _extensiones(comando: str) -> frozenset[str]:
    """Extensiones que ese comando procesa."""
    return EXTENSIONES_CODIGO if comando == "enrich" else EXTENSIONES_DOCUMENTO


def medir(objetivo: str, comando: str) -> tuple[int, int]:
    """Cuenta archivos y bytes que el comando va a tocar.

    Args:
        objetivo (str): Archivo o carpeta objetivo.
        comando (str): ``ingest`` o ``enrich``.

    Returns:
        Tuple[int, int]: Número de archivos y su tamaño total en bytes.
    """
    extensiones = _extensiones(comando)
    if os.path.isfile(objetivo):
        try:
            return 1, os.path.getsize(objetivo)
        except OSError:
            return 1, 0
    archivos = 0
    total = 0
    for base, _dirs, nombres in os.walk(objetivo):
        for nombre in nombres:
            if os.path.splitext(nombre)[1].lower() not in extensiones:
                continue
            archivos += 1
            try:
                total += os.path.getsize(os.path.join(base, nombre))
            except OSError:
                continue
    return archivos, total


def referencia_historica(comando: str, project_dir: str = ".") -> float | None:
    """Mediana de duración de ese comando según la bitácora.

    Args:
        comando (str): Nombre del comando.
        project_dir (str): Raíz del proyecto (donde vive la bitácora).

    Returns:
        Optional[float]: Segundos de referencia, o ``None`` si no hay historial.
    """
    duraciones = [
        float(entrada["duracion_s"])
        for entrada in leer(project_dir)
        if entrada.get("comando") == comando
        and isinstance(entrada.get("duracion_s"), (int, float))
        and float(entrada["duracion_s"]) > 0
    ]
    return median(duraciones) if duraciones else None


def estimar(comando: str, objetivo: str, project_dir: str = ".") -> dict[str, Any]:
    """Costo medido del trabajo pendiente.

    Args:
        comando (str): ``ingest`` o ``enrich``.
        objetivo (str): Archivo o carpeta objetivo.
        project_dir (str): Raíz del proyecto.

    Returns:
        dict: ``comando``, ``objetivo``, ``archivos``, ``mb`` y
        ``referencia_s`` (``None`` si no hay historial).
    """
    archivos, bytes_totales = medir(objetivo, comando)
    return {
        "comando": comando,
        "objetivo": objetivo,
        "archivos": archivos,
        "mb": bytes_totales / (1024 * 1024),
        "referencia_s": referencia_historica(comando, project_dir),
    }


def anunciar(
    args: Any,
    comando: str,
    objetivo: str,
    project_dir: str = ".",
) -> dict[str, Any]:
    """Imprime el costo medido y dice si se puede seguir.

    Args:
        args (Any): Argumentos del comando (dict o Namespace), con ``confirmar``.
        comando (str): ``ingest`` o ``enrich``.
        objetivo (str): Archivo o carpeta objetivo.
        project_dir (str): Raíz del proyecto.

    Returns:
        dict: La estimación, con ``puede_seguir`` añadido.
    """
    costo = estimar(comando, objetivo, project_dir)
    referencia = costo["referencia_s"]
    texto_referencia = (
        f" · referencia: {referencia:.1f} s (mediana de lo que tardó antes)"
        if referencia
        else " · sin historial de tiempos"
    )
    confirmado = bool(_opcion(args, "confirmar", False))
    nombre = os.path.basename(os.path.normpath(objetivo)) or objetivo

    print(AVISO.format(
        comando=f"{comando} {nombre}",
        archivos=costo["archivos"],
        mb=costo["mb"],
        referencia=texto_referencia,
    ))
    if confirmado:
        print("[coste] Confirmado con `--confirmar`: se ejecuta (REG-LIM-004).")
    else:
        print(
            f"[coste] Falta `--confirmar`: no se ejecuta "
            f"(código {CODIGO_RECHAZO}, REG-LIM-004)."
        )
    costo["puede_seguir"] = confirmado
    return costo


def detener() -> None:
    """Termina la ejecución con el código de rechazo (nada se ejecutó).

    Raises:
        SystemExit: Siempre, con :data:`CODIGO_RECHAZO`.
    """
    raise SystemExit(CODIGO_RECHAZO)


def extensiones_de(comando: str) -> Iterable[str]:
    """Extensiones procesadas por el comando (para documentar y testear)."""
    return sorted(_extensiones(comando))
