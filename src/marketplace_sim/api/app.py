"""Local FastAPI app (thin layer over marketplace_sim.api.service). Binds to loopback only; see __main__.py.

Every response carries source levels per number and ``is_private`` for the data it was built from.
"""

from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from marketplace_sim.api import game as gm
from marketplace_sim.api import service as svc

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"]


def create_app(session: svc.Session | None = None) -> FastAPI:
    app = FastAPI(title="mpsim local API", version="1", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])
    state = session or svc.Session()

    def guarded(fn: Any, *args: Any) -> Any:
        try:
            with state.lock:
                return fn(*args)
        except (svc.ApiError, ValueError, KeyError, FileNotFoundError, NotImplementedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, **svc.pack_info(state)}

    @app.get("/api/pack")
    def get_pack() -> dict[str, Any]:
        return dict(svc.pack_info(state))

    @app.post("/api/pack")
    def post_pack(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.load_pack_into, state, str(body.get("source", "synthetic")), body.get("path")))

    @app.get("/api/levels")
    def get_levels() -> dict[str, Any]:
        return svc.levels()

    @app.get("/api/modules")
    def get_modules() -> dict[str, Any]:
        return svc.modules_catalog()

    @app.get("/api/explain/{metric}")
    def get_explain(metric: str) -> dict[str, Any]:
        return dict(guarded(svc.explain, metric))

    @app.get("/api/game")
    def get_game() -> dict[str, Any]:
        return svc.game(state)

    @app.post("/api/game/new")
    def post_new(body: dict[str, Any] = Body(default={})) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.new_game, state, int(body.get("quarter", 1))))

    @app.post("/api/game/load")
    def post_load(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.load_save, state, str(body["path"])))

    @app.post("/api/game/save")
    def post_save() -> dict[str, Any]:
        return dict(guarded(svc.save_game, state))

    @app.post("/api/game/play")
    def post_play(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.play, state, body))

    @app.post("/api/game/preview")
    def post_preview(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.preview, state, body))

    @app.get("/api/plans")
    def get_plans() -> dict[str, Any]:
        return dict(guarded(svc.plan_presets, state))

    @app.post("/api/compare")
    def post_compare(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.compare, state, list(body.get("plans", []))))

    @app.get("/api/game-mode/setup")
    def get_game_mode() -> dict[str, Any]:
        return dict(guarded(gm.setup, state))

    @app.post("/api/game-mode/start")
    def post_game_mode(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(gm.start, state, body))

    @app.get("/api/scenarios")
    def get_scenarios() -> dict[str, Any]:
        return dict(guarded(svc.scenario_templates, state))

    @app.get("/api/events")
    def get_events() -> dict[str, Any]:
        return svc.event_types()

    @app.post("/api/scenario/run")
    def post_scenario(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.run_scenario, state, body))

    @app.get("/api/sweeps")
    def get_sweeps() -> dict[str, Any]:
        return dict(guarded(svc.sweep_files, state))

    @app.post("/api/sweep/run")
    def post_sweep(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.run_sweep, state, body))

    @app.get("/api/sweep/worst")
    def get_worst(top: int = 10) -> dict[str, Any]:
        return dict(guarded(svc.sweep_worst, state, top))

    @app.get("/api/packs")
    def get_packs() -> dict[str, Any]:
        return dict(guarded(svc.pack_snapshots, state))

    @app.post("/api/diff")
    def post_diff(body: dict[str, Any] = Body(...)) -> dict[str, Any]:  # noqa: B008
        return dict(guarded(svc.params_diff, str(body["old"]), str(body["new"])))

    @app.post("/api/export-demo")
    def post_export(body: dict[str, Any] = Body(default={})) -> dict[str, Any]:  # noqa: B008
        from marketplace_sim.api.export import export_demo

        return dict(guarded(export_demo, body.get("out")))

    return app
