"""Contrato de los chequeos del contenido del vault.

Se construyen vaults reales en ``tmp_path`` con la estructura que genera el
motor (`7.0-MANUAL/`, `8.0-KNOWLEDGE/`, `templates/`). Cada chequeo se prueba en
sus dos caras: avisar cuando falta algo y callar cuando está.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from context_map.domain.health import reglas_vault as vault_reglas
from context_map.domain.health.doctor import DoctorReport

VAULT = ".context-map/vault-Demo"


def _estado(chequeo, raiz: Path) -> tuple[str, str]:
    report = DoctorReport()
    chequeo(report, project_dir=str(raiz))
    return report.checks[0].status, report.checks[0].message


def _escribir(raiz: Path, archivos: dict[str, str]) -> Path:
    for ruta, contenido in archivos.items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    return raiz


# ── DOC-005 dominio documentado ───────────────────────────────────────────

def test_dominio_documentado_en_verde(tmp_path):
    _escribir(tmp_path, {
        "context_map/domain/servicio.py": "x = 1\n",
        f"{VAULT}/7.0-MANUAL/DOMINIO.md": "# Dominio\n\n" + ("Explica la lógica. " * 60),
    })
    estado, mensaje = _estado(vault_reglas.check_dominio_documentado, tmp_path)
    assert estado == "OK"
    assert "DOMINIO.md" in mensaje


def test_dominio_sin_documento_avisa(tmp_path):
    _escribir(tmp_path, {
        "context_map/domain/servicio.py": "x = 1\n",
        f"{VAULT}/00-INDICE.md": "# Índice\n",
    })
    estado, mensaje = _estado(vault_reglas.check_dominio_documentado, tmp_path)
    assert estado == "WARN"
    assert "REG-DOC-005" in mensaje


def test_dominio_esqueleto_avisa(tmp_path):
    _escribir(tmp_path, {
        "context_map/domain/servicio.py": "x = 1\n",
        f"{VAULT}/7.0-MANUAL/DOMINIO.md": "# Dominio\n",
    })
    estado, mensaje = _estado(vault_reglas.check_dominio_documentado, tmp_path)
    assert estado == "WARN"
    assert "esqueleto" in mensaje


def test_sin_dominio_no_aplica(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/00-INDICE.md": "# Índice\n"})
    estado, mensaje = _estado(vault_reglas.check_dominio_documentado, tmp_path)
    assert estado == "OK"
    assert "no hay lógica nuclear" in mensaje


# ── DOC-006 / MEM-001 fuentes procesadas ──────────────────────────────────

def test_sin_fuentes_pendientes_en_verde(tmp_path):
    _escribir(tmp_path, {
        ".context-map/CONTEXT.md": "# brief\n",
        ".context-map/raw/docs/fuente.md": "texto\n",
        ".context-map/chats/chat.md": "chat\n",
    })
    # `refresh` escribe el brief al final: eso es lo que deja las fuentes al día.
    brief = tmp_path / ".context-map/CONTEXT.md"
    futuro = time.time() + 60
    os.utime(brief, (futuro, futuro))

    estado, mensaje = _estado(vault_reglas.check_fuentes_procesadas, tmp_path)
    assert estado == "OK"
    assert "Sin fuentes pendientes" in mensaje


def test_fuente_mas_nueva_que_el_brief_avisa(tmp_path):
    _escribir(tmp_path, {
        ".context-map/CONTEXT.md": "# brief\n",
        ".context-map/raw/docs/vieja.md": "texto\n",
    })
    brief = tmp_path / ".context-map/CONTEXT.md"
    vieja = tmp_path / ".context-map/raw/docs/vieja.md"
    os.utime(brief, (1_000_000, 1_000_000))
    os.utime(vieja, (2_000_000, 2_000_000))

    estado, mensaje = _estado(vault_reglas.check_fuentes_procesadas, tmp_path)
    assert estado == "WARN"
    assert "refresh" in mensaje
    assert "vieja.md" in mensaje


def test_sin_context_map_no_aplica(tmp_path):
    estado, mensaje = _estado(vault_reglas.check_fuentes_procesadas, tmp_path)
    assert estado == "OK"
    assert "Sin `.context-map/`" in mensaje


# ── MEM-003 lecciones completas ───────────────────────────────────────────

LECCION_COMPLETA = """# Lección

## Lección
Algo aprendido.

## Cómo se resolvió
Se hizo así.

## Prompt
Un prompt.

## Instrucción
Una instrucción.

## Conexiones
- Otra nota.
"""


def test_leccion_completa_en_verde(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/8.0-KNOWLEDGE/Buena.md": LECCION_COMPLETA})
    estado, mensaje = _estado(vault_reglas.check_lecciones_completas, tmp_path)
    assert estado == "OK"
    assert "1 lecciones" in mensaje


def test_leccion_sin_secciones_avisa(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/8.0-KNOWLEDGE/Coja.md": "# Lección\n\nAlgo.\n"})
    estado, mensaje = _estado(vault_reglas.check_lecciones_completas, tmp_path)
    assert estado == "WARN"
    assert "Coja.md" in mensaje
    assert "REG-MEM-003" in mensaje


def test_los_acentos_no_rompen_la_deteccion(tmp_path):
    leccion = LECCION_COMPLETA.replace("Cómo se resolvió", "Cómo se resolvió").replace(
        "Instrucción", "Instrucción"
    )
    _escribir(tmp_path, {f"{VAULT}/8.0-KNOWLEDGE/Acentos.md": leccion})
    estado, _ = _estado(vault_reglas.check_lecciones_completas, tmp_path)
    assert estado == "OK"


def test_una_leccion_de_diseno_tambien_vale(tmp_path):
    """Una lección sin solución cerrada puede contar cómo se diseñó."""
    _escribir(tmp_path, {
        f"{VAULT}/8.0-KNOWLEDGE/Diseno.md": (
            "# Diseño\n\n## Lección\nAlgo.\n\n## Diseño (Fase 1)\nCómo se planteó.\n\n"
            "## Prompt\nUno.\n\n## Instrucción\nUna.\n\n## Conexiones\n- Otra.\n"
        ),
    })
    estado, _ = _estado(vault_reglas.check_lecciones_completas, tmp_path)
    assert estado == "OK"


def test_el_indice_de_knowledge_no_es_una_leccion(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/8.0-KNOWLEDGE/8.0-KNOWLEDGE.md": "# Índice\n\n- [[Buena]]\n"})
    estado, _ = _estado(vault_reglas.check_lecciones_completas, tmp_path)
    assert estado == "OK"


# ── HUM-001 / HUM-005 notas redactadas ────────────────────────────────────

def test_notas_redactadas_en_verde(tmp_path):
    _escribir(tmp_path, {
        f"{VAULT}/7.0-MANUAL/Diario/2026-11-25.md": "# Diario\n\nSe hizo el trabajo.\n",
    })
    estado, mensaje = _estado(vault_reglas.check_notas_sin_plantilla, tmp_path)
    assert estado == "OK"
    assert "redactadas" in mensaje


def test_nota_con_marcador_de_plantilla_avisa(tmp_path):
    _escribir(tmp_path, {
        f"{VAULT}/7.0-MANUAL/Nota.md": "# Nota\n\n[Completar] cuando haya datos.\n",
    })
    estado, mensaje = _estado(vault_reglas.check_notas_sin_plantilla, tmp_path)
    assert estado == "WARN"
    assert "Nota.md" in mensaje
    assert "REG-HUM-001" in mensaje


def test_la_carpeta_templates_no_se_juzga(tmp_path):
    _escribir(tmp_path, {
        f"{VAULT}/templates/nota-pkm.md": "# {{title}}\n\ncuerpo\n",
    })
    estado, _ = _estado(vault_reglas.check_notas_sin_plantilla, tmp_path)
    assert estado == "OK"


def test_una_plantilla_por_nombre_no_se_juzga(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/Plantilla-Idea.md": "# {{title}}\n"})
    estado, _ = _estado(vault_reglas.check_notas_sin_plantilla, tmp_path)
    assert estado == "OK"


def test_marcador_dentro_de_codigo_no_cuenta(tmp_path):
    _escribir(tmp_path, {
        f"{VAULT}/8.0-KNOWLEDGE/Plantillas.md": (
            "# Plantillas\n\nEl motor escribe:\n\n```\ntitle: \"{{title}}\"\n```\n"
        ),
    })
    estado, _ = _estado(vault_reglas.check_notas_sin_plantilla, tmp_path)
    assert estado == "OK"


def test_signos_de_admiracion_dobles_avisan(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/7.0-MANUAL/Nota.md": "# Nota\n\nEsto es genial!!\n"})
    estado, mensaje = _estado(vault_reglas.check_notas_sin_plantilla, tmp_path)
    assert estado == "WARN"
    assert "REG-HUM-005" in mensaje


# ── LIM-001 vault acotado ─────────────────────────────────────────────────

def test_vault_acotado_en_verde(tmp_path):
    _escribir(tmp_path, {f"{VAULT}/00-INDICE.md": "# Índice\n"})
    estado, mensaje = _estado(vault_reglas.check_vault_acotado, tmp_path)
    assert estado == "OK"
    assert "MB" in mensaje


def test_vault_pesado_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_reglas, "LIMITE_MB", 0.001)
    _escribir(tmp_path, {f"{VAULT}/00-INDICE.md": "# Índice\n" + ("x" * 5000)})
    estado, mensaje = _estado(vault_reglas.check_vault_acotado, tmp_path)
    assert estado == "WARN"
    assert "REG-LIM-001" in mensaje
