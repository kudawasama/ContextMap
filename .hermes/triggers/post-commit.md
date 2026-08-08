# Post-Commit — ContextMap

Después de cada commit:

1. Verifica que `python -m context_map.cli build --clean --brief` se ejecutó (hook pre-commit).
2. Si el commit tocó dependencias: actualiza el lockfile del gestor de paquetes.
3. Si el commit tocó arquitectura: revisa que el vault 4.0-RIESGOS no marcó nueva deuda.
