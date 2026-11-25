"""Tests del registro de lecturas y del chequeo ``lecturas_previas`` (INI-006).

La regla es conducta, pero la huella sí es medible. Se prueba con repos git
reales y registros reales: un chequeo que se conforma con que «el archivo exista»
no demuestra nada.
"""

from __future__ import annotations

import io
import json
import os
import subprocess

from context_map.core.audit import lecturas
from context_map.domain.ecosystem import hooks_lectura
from context_map.domain.health import reglas_sesion


def _git(raiz: str, *args: str, fecha: str = "2030-01-01T10:00:00") -> None:
    """Ejecuta git en el repositorio de prueba con una fecha controlada."""
    entorno = dict(
        os.environ,
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
        GIT_AUTHOR_DATE=fecha,
        GIT_COMMITTER_DATE=fecha,
    )
    subprocess.run(
        ["git", *args], cwd=raiz, check=True, capture_output=True, env=entorno
    )


def _estado(chequeo, raiz: str) -> tuple[str, str]:
    """Ejecuta un chequeo y devuelve (estado, mensaje)."""
    from context_map.domain.health.doctor import DoctorReport

    reporte = DoctorReport()
    chequeo(reporte, project_dir=raiz)
    assert len(reporte.checks) == 1
    return reporte.checks[0].status, reporte.checks[0].message


def _repo(tmp_path, archivos: dict[str, str], fecha: str = "2030-01-01T10:00:00") -> str:
    """Crea un repositorio git con un primer commit."""
    raiz = str(tmp_path)
    _git(raiz, "init", "-q")
    os.makedirs(os.path.join(raiz, "paquete"), exist_ok=True)
    for nombre, contenido in archivos.items():
        ruta = os.path.join(raiz, nombre)
        os.makedirs(os.path.dirname(ruta), exist_ok=True) if os.path.dirname(ruta) else None
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "feat: base", fecha=fecha)
    return raiz


# ── El registro ───────────────────────────────────────────────────────────


def test_anota_la_ruta_relativa_y_el_origen(tmp_path) -> None:
    raiz = str(tmp_path)
    assert lecturas.registrar_lectura("paquete/modulo.py", raiz, origen="claude")

    entradas = lecturas.leer_lecturas(raiz)
    assert len(entradas) == 1
    assert entradas[0]["ruta"] == "paquete/modulo.py"
    assert entradas[0]["origen"] == "claude"
    assert entradas[0]["ts"]


def test_no_guarda_contenido_ni_rutas_absolutas(tmp_path) -> None:
    """La huella no puede convertirse en una fuga ni en un volcado de código."""
    raiz = str(tmp_path)
    lecturas.registrar_lectura(os.path.join(raiz, "a.py"), raiz)

    crudo = io.open(lecturas.ruta_lecturas(raiz), encoding="utf-8").read()
    assert raiz.lower() not in crudo.lower()
    assert crudo.count("\n") == 1


def test_una_ruta_vacia_no_se_anota(tmp_path) -> None:
    raiz = str(tmp_path)
    assert lecturas.registrar_lectura("", raiz) is False
    assert lecturas.leer_lecturas(raiz) == []


def test_una_linea_corrupta_no_tumba_el_registro(tmp_path) -> None:
    raiz = str(tmp_path)
    conector = lecturas.ruta_lecturas(raiz)
    os.makedirs(os.path.dirname(conector), exist_ok=True)
    with open(conector, "w", encoding="utf-8") as f:
        f.write("{no es json}\n")
    lecturas.registrar_lectura("ok.py", raiz)

    entradas = lecturas.leer_lecturas(raiz)
    assert [e["ruta"] for e in entradas] == ["ok.py"]


def test_registrar_nunca_lanza(tmp_path) -> None:
    """Si el registro falla se pierde la evidencia, no la sesión."""
    assert lecturas.registrar_lectura("a.py", os.path.join(str(tmp_path), "no-es-dir", "x")) in (True, False)


def test_rotacion_conserva_las_ultimas(tmp_path) -> None:
    raiz = str(tmp_path)
    conector = lecturas.ruta_lecturas(raiz)
    os.makedirs(os.path.dirname(conector), exist_ok=True)
    with open(conector, "w", encoding="utf-8") as f:
        for i in range(lecturas.MAX_LINEAS + 5):
            f.write(json.dumps({"ts": "2030-01-01T00:00:00", "ruta": f"f{i}.py"}) + "\n")

    lecturas.registrar_lectura("ultimo.py", raiz)

    entradas = lecturas.leer_lecturas(raiz)
    assert len(entradas) <= lecturas.MAX_LINEAS
    assert entradas[-1]["ruta"] == "ultimo.py"


def test_primera_lectura_e_hay_registro(tmp_path) -> None:
    raiz = str(tmp_path)
    assert lecturas.hay_registro(raiz) is False
    lecturas.registrar_lectura("a.py", raiz)
    assert lecturas.hay_registro(raiz) is True
    assert lecturas.primera_lectura(raiz)


def test_rutas_leidas_normaliza_separadores(tmp_path) -> None:
    raiz = str(tmp_path)
    lecturas.registrar_lectura("paquete\\modulo.py", raiz)
    assert "paquete/modulo.py" in lecturas.rutas_leidas(raiz)


# ── El receptor: formatos de los harnesses ────────────────────────────────


def test_extrae_la_ruta_de_un_pre_tool_use_anidado() -> None:
    datos = {"tool_name": "Read", "tool_input": {"file_path": "C:/x/a.py"}}
    assert lecturas.extraer_ruta(datos) == "C:/x/a.py"


def test_extrae_la_ruta_de_un_formato_plano() -> None:
    assert lecturas.extraer_ruta({"path": "b.py"}) == "b.py"


def test_extrae_la_ruta_de_una_cadena_cruda() -> None:
    assert lecturas.extraer_ruta("  c.py  ") == "c.py"


def test_sin_ruta_no_se_inventa_una() -> None:
    assert lecturas.extraer_ruta({"otra_cosa": 1}) == ""
    assert lecturas.extraer_ruta(None) == ""


def test_el_receptor_anota_desde_los_argumentos(tmp_path) -> None:
    from context_map.application.commands.hook import cmd_hook_lectura

    raiz = str(tmp_path)
    cmd_hook_lectura({"target": raiz, "ruta": "src/app.py", "quiet": True})
    assert lecturas.leer_lecturas(raiz)[0]["ruta"] == "src/app.py"


# ── Instalación del hook ──────────────────────────────────────────────────


def test_instalar_respeta_lo_que_ya_habia(tmp_path) -> None:
    """Sobrescribir la configuración de otro sería el atajo que EJE-004 prohíbe."""
    raiz = str(tmp_path)
    os.makedirs(os.path.join(raiz, ".claude"), exist_ok=True)
    previo = {"permisos": {"allow": ["Bash(*)"]}, "hooks": {"Stop": [{"hooks": []}]}}
    with open(hooks_lectura.CONFIG.replace(".claude", os.path.join(raiz, ".claude")), "w", encoding="utf-8") as f:
        json.dump(previo, f)

    resultado = hooks_lectura.instalar_hook_lectura(raiz)

    assert resultado["status"] == "OK"
    with open(os.path.join(raiz, hooks_lectura.CONFIG), encoding="utf-8") as f:
        config = json.load(f)
    assert config["permisos"] == {"allow": ["Bash(*)"]}
    assert "Stop" in config["hooks"]
    assert hooks_lectura.ya_instalado(raiz) is True


def test_instalar_dos_veces_no_duplica(tmp_path) -> None:
    raiz = str(tmp_path)
    hooks_lectura.instalar_hook_lectura(raiz)
    segundo = hooks_lectura.instalar_hook_lectura(raiz)

    assert "ya estaba instalado" in segundo["message"]
    with open(os.path.join(raiz, hooks_lectura.CONFIG), encoding="utf-8") as f:
        assert len(json.load(f)["hooks"]["PreToolUse"]) == 1


def test_el_comando_prefiere_el_interprete_del_proyecto(tmp_path) -> None:
    """Un `ctxmap` global desactualizado saldría con 2 y bloquearía la lectura."""
    raiz = str(tmp_path)
    interprete = os.path.join(raiz, hooks_lectura.INTERPRETES[0])
    os.makedirs(os.path.dirname(interprete), exist_ok=True)
    open(interprete, "w").close()

    comando = hooks_lectura.comando(raiz)

    assert interprete in comando
    assert "-m context_map.cli hook lectura" in comando


def test_sin_venv_se_usa_el_binario_canonico(tmp_path) -> None:
    assert hooks_lectura.comando(str(tmp_path)) == hooks_lectura.COMANDO


# ── El chequeo ────────────────────────────────────────────────────────────


def test_sin_registro_se_declara_fuera_de_alcance(tmp_path) -> None:
    """Un hueco declarado es honesto; un verde silencioso no."""
    raiz = _repo(tmp_path, {"app.py": "x = 1\n"})

    estado, mensaje = _estado(reglas_sesion.check_lecturas_previas, raiz)

    assert estado == "OK"
    assert "no se puede juzgar" in mensaje


def test_commit_anterior_al_registro_no_se_juzga(tmp_path) -> None:
    """Nada se mira hacia atrás: el rojo perpetuo enseña a ignorar los avisos."""
    raiz = _repo(tmp_path, {"app.py": "x = 1\n"}, fecha="2020-01-01T10:00:00")
    lecturas.registrar_lectura("otro.py", raiz)  # la lectura es posterior al commit

    estado, mensaje = _estado(reglas_sesion.check_lecturas_previas, raiz)

    assert estado == "OK"
    assert "hacia atrás" in mensaje


def test_codigo_tocado_sin_lectura_avisa(tmp_path) -> None:
    raiz = _repo(tmp_path, {"app.py": "x = 1\n", "otros.py": "y = 2\n"})
    lecturas.registrar_lectura("app.py", raiz)
    with open(os.path.join(raiz, "otros.py"), "w", encoding="utf-8") as f:
        f.write("y = 3\n")
    _git(raiz, "commit", "-qam", "fix: cambia otros")

    estado, mensaje = _estado(reglas_sesion.check_lecturas_previas, raiz)

    assert estado == "WARN"
    assert "otros.py" in mensaje
    assert "REG-INI-006" in mensaje
    assert "app.py" not in mensaje.split(":")[-1]


def test_codigo_leido_antes_del_commit_esta_verde(tmp_path) -> None:
    raiz = _repo(tmp_path, {"app.py": "x = 1\n"})
    with open(os.path.join(raiz, "app.py"), "w", encoding="utf-8") as f:
        f.write("x = 2\n")
    _git(raiz, "commit", "-qam", "fix: cambia app")
    lecturas.registrar_lectura("app.py", raiz)

    estado, mensaje = _estado(reglas_sesion.check_lecturas_previas, raiz)

    assert estado == "OK"
    assert "registro de lecturas" in mensaje


def test_un_archivo_nuevo_no_se_juzga(tmp_path) -> None:
    """No se podía leer lo que no existía todavía."""
    raiz = _repo(tmp_path, {"app.py": "x = 1\n"})
    lecturas.registrar_lectura("app.py", raiz)
    with open(os.path.join(raiz, "nuevo.py"), "w", encoding="utf-8") as f:
        f.write("z = 9\n")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "feat: agrega nuevo")

    estado, mensaje = _estado(reglas_sesion.check_lecturas_previas, raiz)

    assert estado == "OK", mensaje


def test_la_documentacion_no_cuenta_como_codigo(tmp_path) -> None:
    raiz = _repo(tmp_path, {"app.py": "x = 1\n", "README.md": "hola\n"})
    lecturas.registrar_lectura("app.py", raiz)
    with open(os.path.join(raiz, "README.md"), "w", encoding="utf-8") as f:
        f.write("hola otra vez\n")
    _git(raiz, "commit", "-qam", "docs: readme")

    estado, _ = _estado(reglas_sesion.check_lecturas_previas, raiz)

    assert estado == "OK"


def test_el_chequeo_esta_registrado() -> None:
    assert reglas_sesion.check_lecturas_previas in reglas_sesion.CHECKS_SESION
