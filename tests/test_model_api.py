"""模型元数据 4 个只读端点：字段、鉴权与错误码。"""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from dsh_onto_base import Settings, create_token
from dsh_ontology.app import create_app

MODEL_PATHS = (
    "/api/model/manifest",
    "/api/model/aggregates",
    "/api/model/aggregates/{alias}",
    "/api/model/integrity",
)


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture(scope="module")
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


def _headers(settings: Settings, role_level: int = 1) -> dict[str, str]:
    token = create_token(
        settings.jwt_secret,
        user_id=1,
        user_name="tester",
        role_level=role_level,
        tenant_id=1,
        expiration_ms=settings.jwt_expiration_ms,
    )
    return {"Authorization": f"Bearer {token}"}


def test_openapi_contains_four_model_paths(client: TestClient) -> None:
    paths = client.app.openapi()["paths"]
    assert set(MODEL_PATHS).issubset(paths)


def test_manifest_fields(client: TestClient, settings: Settings) -> None:
    response = client.get("/api/model/manifest", headers=_headers(settings))

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["platform"] == "dsh-onto-base"
    assert data["baseVersion"] == "3.0"
    assert data["projectVersion"] is None
    assert len(data["baseModels"]) == 7
    assert data["projectModelCount"] == 0
    assert data["aggregateCount"] == 25
    assert data["attributeCount"] == 200
    assert data["enumCount"] == 16
    assert data["projectLayerPresent"] is False
    assert "/Users/" not in response.text


def test_aggregates_grouped_by_tag(client: TestClient, settings: Settings) -> None:
    response = client.get("/api/model/aggregates", headers=_headers(settings))

    assert response.status_code == 200
    groups = response.json()["data"]
    assert groups
    assert all(set(group) == {"tag", "aggregateCount", "aggregates"} for group in groups)
    assert all(group["aggregateCount"] == len(group["aggregates"]) for group in groups)

    ontology_group = next(group for group in groups if group["tag"] == "本体域")
    aliases = [item["alias"] for item in ontology_group["aggregates"]]
    assert "OntologyCountry" in aliases
    assert len(aliases) == len(set(aliases)), "同一 tag 下 alias 不得重复"

    country = next(item for item in ontology_group["aggregates"] if item["alias"] == "OntologyCountry")
    assert set(country) == {"alias", "name", "category", "attributeCount"}
    assert country["attributeCount"] == 9


def test_aggregate_detail_fields(client: TestClient, settings: Settings) -> None:
    response = client.get(
        "/api/model/aggregates/OntologyCountry", headers=_headers(settings)
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["alias"] == "OntologyCountry"
    assert data["name"] == "国家"
    assert data["category"] == "country"
    assert data["sourceFile"] == "ontology-models/m1-object-model.yaml"
    assert data["subEntities"] == []
    assert set(data) == {
        "id",
        "name",
        "alias",
        "category",
        "lifecycle",
        "tags",
        "attributes",
        "subEntities",
        "sourceFile",
    }
    attribute = data["attributes"][0]
    assert set(attribute) == {
        "name",
        "label",
        "type",
        "required",
        "unique",
        "enumValues",
        "defaultValue",
        "description",
    }
    assert "sourcePath" not in response.text
    assert "source_path" not in response.text
    assert "/Users/" not in response.text


def test_aggregate_detail_supports_nested_entities(
    client: TestClient, settings: Settings
) -> None:
    response = client.get("/api/model/aggregates/OntologyI18n", headers=_headers(settings))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["alias"] == "OntologyI18n"
    assert data["category"] == "i18n"
    assert data["attributes"]


def test_integrity_fields(client: TestClient, settings: Settings) -> None:
    response = client.get("/api/model/integrity", headers=_headers(settings))

    assert response.status_code == 200
    data = response.json()["data"]
    assert set(data) == {
        "aggregateCount",
        "attributeCount",
        "enumCount",
        "duplicateAliases",
        "danglingRefs",
        "hasErrors",
        "issues",
    }
    assert data["aggregateCount"] == 25
    assert data["attributeCount"] == 200
    assert data["enumCount"] == 16
    assert data["duplicateAliases"] == 0
    assert data["danglingRefs"] == 2
    assert data["hasErrors"] is False
    assert all(
        set(issue) == {"severity", "code", "message", "sourceFile", "path"}
        for issue in data["issues"]
    )
    assert "/Users/" not in response.text


def test_unknown_alias_returns_404(client: TestClient, settings: Settings) -> None:
    response = client.get(
        "/api/model/aggregates/NotAnAggregate", headers=_headers(settings)
    )

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "未知聚合根: NotAnAggregate", "data": None}


def test_missing_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/model/manifest")

    assert response.status_code == 401
    assert response.json() == {"code": 401, "msg": "未登录", "data": None}


def test_guest_role_returns_403(client: TestClient, settings: Settings) -> None:
    response = client.get("/api/model/manifest", headers=_headers(settings, role_level=2))

    assert response.status_code == 403
    assert response.json()["code"] == 403


def test_disabled_engine_returns_503(settings: Settings) -> None:
    disabled = replace(settings, model_enabled=False)
    with TestClient(create_app(disabled)) as client:
        response = client.get("/api/model/manifest", headers=_headers(settings))

    assert response.status_code == 503
    assert response.json() == {
        "code": 503,
        "msg": "模型引擎未启用（dsh.ontology.model.enabled=false）",
        "data": None,
    }
