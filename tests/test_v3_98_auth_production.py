"""V3-98 security contracts: fail-closed production and same-origin session guard."""
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
import pytest

from app.auth.single_admin import AdminGuard, csrf_token, password_hash, router
from app.config import Settings
from app.main import validate_production_settings

SECRET="A"*48
ORIGIN="http://testserver"


def production_config(**changes):
    values=dict(environment="production",pipeline_mode="real",
        database_url="postgresql://u:p@localhost:5432/learnflow",
        auth_enabled=True,admin_username="admin",
        admin_password="long-secret-password-test",
        auth_secret_key=SECRET,public_origin="https://learnflow.example",
        planner_provider="openrouter",openrouter_api_key="test-key-not-a-real-key-0001",
        openrouter_planner_model="openai/gpt-6-luna")
    values.update(changes)
    return Settings(_env_file=None,**values)


@pytest.mark.parametrize("patch",[
    {"database_url":""},{"database_url":"sqlite:///db.sqlite"},
    {"pipeline_mode":"demo"},{"pipeline_mode":"fake"},{"auth_enabled":False},
    {"admin_password":"short"},{"auth_secret_key":"short"},{"public_origin":"http://learnflow.example"},
    {"openrouter_api_key":""},{"openrouter_planner_model":"openrouter/free"},
])
def test_production_fails_closed(patch):
    with pytest.raises((RuntimeError,ValueError)):
        validate_production_settings(production_config(**patch))


def test_production_with_paid_provider_and_pg_contract():
    validate_production_settings(production_config())
    validate_production_settings(production_config(
        planner_provider="gemini",gemini_api_key="test-paid-gemini-key-aaaa"))


def test_password_salted_and_csrf_bound_to_session():
    assert password_hash("password",b"a"*16)!=password_hash("password",b"b"*16)
    assert csrf_token("one-session",SECRET)!=csrf_token("other-session",SECRET)


class FakeStore:
    def __init__(self):
        self.token="test-valid-admin-session-token-"+"X"*35
        self.allowed=2
        self.rejected=False
        self.revoked=False
    def authenticate(self,username,password):
        if username=="admin" and password=="correct-secret":
            return self.token
        return None
    def verify(self,token):
        return token==self.token and not self.revoked
    def revoke(self,token):
        self.revoked=True
    def reserve_paid_job(self,limit):
        if self.allowed<=0:return False
        self.allowed-=1
        return True


def build_client():
    store=FakeStore()
    app=FastAPI()
    app.state.auth_store=store
    app.state.auth_key=SECRET
    app.state.auth_secure=False
    app.state.settings=SimpleNamespace(admin_username="admin")
    app.include_router(router)
    @app.get("/")
    def home():return {"private":"yes"}
    @app.get("/api/jobs")
    def jobs():return {"jobs":[]}
    @app.post("/api/jobs")
    def make():return JSONResponse({"id":"created"},status_code=202)
    @app.get("/api/jobs/private-id/video")
    def video():return JSONResponse({"video":"private"})
    app.add_middleware(AdminGuard,key=SECRET,origin=ORIGIN,store=store,secure=False,daily_limit=2)
    return TestClient(app,base_url=ORIGIN),store


def test_auth_login_middleware_cookie_csrf_video_and_quota():
    client,store=build_client()
    assert client.get("/api/jobs").status_code==401
    assert client.get("/api/jobs/private-id/video").status_code==401
    assert client.post("/api/auth/login",json={"username":"admin","password":"correct-secret"}).status_code==403
    denied=client.post("/api/auth/login",headers={"Origin":ORIGIN},
                       json={"username":"admin","password":"wrong-secret"})
    assert denied.status_code==401
    okay=client.post("/api/auth/login",headers={"Origin":ORIGIN},
                    json={"username":"admin","password":"correct-secret"})
    assert okay.status_code==200
    assert "httponly" in okay.headers["set-cookie"].lower()
    me=client.get("/api/auth/session")
    assert me.status_code==200
    token=me.json()["csrf_token"]
    assert len(token)==64
    assert client.get("/api/jobs/private-id/video").status_code==200
    assert client.post("/api/jobs",headers={"Origin":ORIGIN}).status_code==403
    assert client.post("/api/jobs",headers={"Origin":"https://evil.example",
         "X-CSRF-Token":token}).status_code==403
    headers={"Origin":ORIGIN,"X-CSRF-Token":token}
    assert client.post("/api/jobs",headers=headers).status_code==202
    assert client.post("/api/jobs",headers=headers).status_code==202
    assert client.post("/api/jobs",headers=headers).status_code==429
    assert client.post("/api/auth/logout",headers=headers).status_code==200
    assert client.get("/api/jobs").status_code==401


def test_anonymous_root_probe_is_healthy_without_exposing_private_app():
    client, _ = build_client()
    # Hosting probes generally send */* or omit Accept, unlike browser navigation.
    for accept in ("*/*", "application/json", ""):
        response = client.get("/", headers={"Accept": accept})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["vary"] == "Accept, Cookie"
    assert client.head("/", headers={"Accept": "*/*"}).status_code == 200
    # Real browser navigation still requires login.
    browser = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    assert browser.status_code == 303
    assert browser.headers["location"] == "/login"
    # The probe exception must not authorize private pages, API or media.
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/jobs/private-id/video").status_code == 401
    assert client.get("/create", headers={"Accept": "*/*"}).status_code == 401
    authenticated = client.post("/api/auth/login", headers={"Origin": ORIGIN},
                                json={"username": "admin", "password": "correct-secret"})
    assert authenticated.status_code == 200
    assert client.get("/", headers={"Accept": "text/html"}).json() == {"private": "yes"}


def test_pg_admin_real_database_when_ci_service_available():
    import os
    url=os.getenv("V398_PG_TEST_URL")
    if not url:
        pytest.skip("External PostgreSQL service needed; never fall back to SQLite")
    from app.auth.single_admin import PostgresSingleAdmin
    store=PostgresSingleAdmin(url,"admin","long-ci-admin-password-000")
    assert store.authenticate("admin","incorrect") is None
    first=store.authenticate("admin","long-ci-admin-password-000")
    assert first and store.verify(first)
    assert store.reserve_paid_job(100)
    store.revoke(first)
    assert not store.verify(first)


def test_paid_openrouter_wire_schema_and_fail_closed(monkeypatch):
    """No network calls: capture one pinned OpenRouter request and reject fallback."""
    import asyncio
    import httpx
    from app.providers.llm.openrouter_paid import OpenRouterPaidLessonPlanner
    from app.domain.lesson import LessonPlan
    from app.providers.llm.base import PlannerProviderError

    seen = []
    returned = {"model":"openai/gpt-6-luna","choices":[
        {"finish_reason":"stop","message":{"content":"{}"}}]}
    class MockResponse:
        def raise_for_status(self):pass
        def json(self):return returned
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,headers,json):
            seen.append((url,headers,json))
            return MockResponse()
    monkeypatch.setattr(httpx,"AsyncClient",FakeClient)
    sentinel=object()
    monkeypatch.setattr(LessonPlan,"model_validate_json",staticmethod(lambda raw:sentinel))
    planner=OpenRouterPaidLessonPlanner(api_key="ci-fake-provider-key-012345",tokens=4000)
    assert asyncio.run(planner._complete("A safe prompt")) is sentinel
    assert len(seen)==1
    url,headers,body=seen[0]
    assert url=="https://openrouter.ai/api/v1/chat/completions"
    assert body["model"]=="openai/gpt-6-luna"
    assert body["provider"]["allow_fallbacks"] is False
    assert body["provider"]["require_parameters"] is True
    assert body["response_format"]["type"]=="json_schema"
    assert body["max_tokens"]==4000
    assert body["stream"] is False
    returned["model"]="openrouter/free"
    with pytest.raises(PlannerProviderError):
        asyncio.run(planner._complete("A safe prompt"))
    assert len(seen)==2   # exactly one POST per call, never hidden retries
    with pytest.raises(ValueError):
        OpenRouterPaidLessonPlanner(api_key="ci-fake-provider-key-012345",model="openrouter/free")


def test_openrouter_default_strict_schema_contract():
    """This test runs inside the V3-98 gated production CI job."""
    from jsonschema import Draft202012Validator
    from app.providers.llm.openrouter_paid import build_strict_lesson_plan_schema
    from app.domain.lesson import LessonPlan

    assert Settings(_env_file=None).planner_provider == "openrouter"
    assert Settings(_env_file=None, planner_provider="gemini").planner_provider == "gemini"

    original = LessonPlan.model_json_schema()
    schema = build_strict_lesson_plan_schema()
    Draft202012Validator.check_schema(schema)
    assert "schema_version" not in original["required"]
    assert "schema_version" in schema["required"]
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["ScenePlan"]["properties"]["visual_spec"].get("anyOf")
    for item in schema["$defs"].values():
        if item.get("type") == "object":
            assert item["additionalProperties"] is False
            assert set(item["required"]) == set(item["properties"])


def test_paid_planner_repairs_invalid_schema_once_no_provider_fallback(monkeypatch):
    """End-to-end planning service with real Pydantic and offline fake OpenRouter."""
    import asyncio
    import copy
    import json
    import httpx
    from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
    from app.domain.lesson import LearningRequest
    from app.planning.service import PlanningService
    from app.providers.llm.openrouter_paid import OpenRouterPaidLessonPlanner

    good = DEMO_PHOTOSYNTHESIS_PLAN.model_dump(mode="json")
    bad = copy.deepcopy(good)
    bad["scenes"][0]["scene_id"] = "invalid-scene-id"

    def exercise(repaired, expected_error=None):
        seen = []
        outputs = [bad, repaired]

        class FakeClient:
            def __init__(self, **kwargs): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass

            async def post(self, url, headers, json):
                assert url == "https://openrouter.ai/api/v1/chat/completions"
                assert json["model"] == "openai/gpt-6-luna"
                assert json["provider"]["allow_fallbacks"] is False
                assert json["provider"]["require_parameters"] is True
                seen.append(json)
                data = {
                    "model": "openai/gpt-6-luna",
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {"content": __import__("json").dumps(
                            outputs.pop(0), ensure_ascii=False,
                        )},
                    }],
                }
                return httpx.Response(200, json=data, request=httpx.Request("POST", url))

        monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
        planner = OpenRouterPaidLessonPlanner(api_key="ci-fake-provider-key-012345")
        req = LearningRequest(
            topic=good["topic"], audience=good["audience"],
            language=good["language"], target_duration_seconds=90,
        )
        if expected_error:
            with pytest.raises(expected_error) as ex:
                asyncio.run(PlanningService(planner).build_valid_plan(req))
            assert ex.value.code == "plan_validation_failed" if expected_error.__name__ == "PipelineExecutionError" else ex.value.code == "paid_planner_invalid_plan"
        else:
            plan = asyncio.run(PlanningService(planner).build_valid_plan(req))
            assert plan.scenes[0].scene_id == good["scenes"][0]["scene_id"]

        # One initial request and at most one schema repair, never a third paid POST.
        assert len(seen) == 2
        assert "invalid-scene-id" in seen[1]["messages"][0]["content"]
        assert "scenes.0.scene_id" in seen[1]["messages"][0]["content"]

    exercise(good)

    # A second Pydantic-invalid response must fail closed; no more paid calls.
    from app.providers.llm.base import PlannerProviderError
    exercise(bad, PlannerProviderError)

    # A Pydantic-valid but wrong-language repair must fail semantic QA with no third call.
    from app.domain.errors import PipelineExecutionError
    semantically_bad = copy.deepcopy(good)
    semantically_bad["language"] = "en" if good["language"] == "vi" else "vi"
    exercise(semantically_bad, PipelineExecutionError)


def test_paid_planner_validation_error_reports_safe_paths(monkeypatch):
    import asyncio
    import json
    import httpx
    from app.demo.lesson_plans import DEMO_PHOTOSYNTHESIS_PLAN
    from app.providers.llm.base import PlannerOutputValidationError
    from app.providers.llm.openrouter_paid import OpenRouterPaidLessonPlanner

    bad = DEMO_PHOTOSYNTHESIS_PLAN.model_dump(mode="json")
    bad["scenes"][0]["scene_id"] = "SECRET_INVALID_PROVIDER_CONTENT"
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, json):
            return httpx.Response(200, json={
                "model": "openai/gpt-6-luna",
                "choices": [{"finish_reason": "stop", "message": {
                    "content": __import__("json").dumps(bad),
                }}],
            }, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    with pytest.raises(PlannerOutputValidationError) as ex:
        asyncio.run(OpenRouterPaidLessonPlanner(
            api_key="ci-fake-provider-key-012345",
        )._complete("test"))
    assert ex.value.code == "paid_planner_invalid_plan"
    assert "scenes.0.scene_id" in ex.value.message
    assert "SECRET_INVALID_PROVIDER_CONTENT" not in ex.value.message
