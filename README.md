# devops_taller_2

## Grupo: The Last One

- Integrante: Breitner Enrique Gonzalez Angarita

Taller 2: Integración Continua (CI)

Continuacion del microservicio de la Entrega 1, esta vez con un pipeline de **Integracion Continua** sobre AWS CodeBuild que se dispara con cada commit en `master`/`main`, ejecuta las pruebas unitarias y genera el artefacto desplegable.

## Componentes principales del CI

| Archivo | Proposito |
|---|---|
| `buildspec.yml` | Receta que CodeBuild ejecuta (install -> pre_build -> build -> post_build). |
| `tests/` | Tests unitarios con `pytest` (un escenario por endpoint + casos de error). |
| `requirements.txt` | Incluye `pytest` y `pytest-cov` ademas de las libs de la app. |
| `pytest.ini` | Configuracion de descubrimiento de pruebas. |

## Estructura

```
devops_taller_2/
|-- application.py
|-- Procfile
|-- requirements.txt
|-- buildspec.yml             # <-- AWS CodeBuild
|-- pytest.ini
|-- .ebextensions/01_env.config
|-- src/
|   |-- main.py
|   |-- models/blacklist.py
|   |-- schemas/blacklist_schema.py
|   `-- views/blacklist_view.py
`-- tests/
    |-- conftest.py            # fixtures comunes
    |-- test_health.py
    |-- test_blacklist_post.py
    `-- test_blacklist_get.py
```

## Ejecutar las pruebas localmente

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest --cov=src --cov-report=term-missing
```

Resultado esperado: todas las pruebas en verde y cobertura > 80% sobre `src/`.

## Flujo del Pipeline de CI

1. Push a `master` -> webhook de GitHub dispara CodeBuild.
2. `install` -> instala Python 3.11 + dependencias.
3. `pre_build` -> corre `pytest` y publica reportes JUnit y de cobertura.
4. `build` -> empaqueta `blacklist-service.zip` listo para desplegar.
5. `post_build` -> marca el fin.
6. Artefacto zip se sube al bucket S3 configurado en CodeBuild.

> No se incluye etapa de Deploy: la entrega es solamente CI.

## Forzar un build fallido (para evidencia)

Edita `tests/test_blacklist_post.py` y cambia un `assert` para que falle, haz commit y push. Documenta los logs y luego revierte el cambio:

```bash
git revert HEAD
git push origin master
```

## Configuracion en AWS (resumen)

Sigue `../PASO-A-PASO-Entrega-2.md`. Pasos clave:

1. CodeBuild -> Create build project `blacklist-ci`.
2. Source: GitHub App + repo + filtro `^refs/heads/master$`.
3. Webhook: `Rebuild every time a code change is pushed`.
4. Environment: Ubuntu, runtime Standard, imagen `aws/codebuild/standard:7.0`.
5. Buildspec: usar `buildspec.yml` del repo (no cargar inline).
6. Artifacts: bucket S3 propio (`blacklist-artifacts-...`).
7. Logs: CloudWatch group `/aws/codebuild/blacklist-ci`.
