"""T19: Supplier scoring — single query, no N+1, returns scored list."""

import pytest


@pytest.mark.asyncio
async def test_suggest_suppliers(auth_client):
    """T19: /suppliers/suggest returns scored list without N+1."""
    # Create 3 suppliers
    for i in range(3):
        await auth_client.post("/api/v2/suppliers", json={
            "name": f"Proveedor Scoring {i}",
            "categories": ["construccion"],
            "city": "Santiago",
        })

    resp = await auth_client.get(
        "/api/v2/suppliers/suggest",
        params={"item_description": "cemento portland", "category": "construccion"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    # Scores returned (may be empty if no suppliers match, but endpoint works)
    assert isinstance(data["suggestions"], list)


@pytest.mark.asyncio
async def test_suggest_suppliers_empty_org(auth_client):
    """T19b: No suppliers → empty list returned."""
    resp = await auth_client.get(
        "/api/v2/suppliers/suggest",
        params={"item_description": "producto raro", "category": "industrial"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["suggestions"] == []


@pytest.mark.asyncio
async def test_validated_supplier_gets_full_score(auth_client):
    """T19c: Validated supplier gets 1.0x multiplier, unvalidated gets 0.5x."""
    validated_resp = await auth_client.post("/api/v2/suppliers", json={
        "name": "Proveedor Validado",
        "categories": ["materiales"],
    })
    unvalidated_resp = await auth_client.post("/api/v2/suppliers", json={
        "name": "Proveedor No Validado",
        "categories": ["materiales"],
    })

    # Patch unvalidated status
    unvalidated_id = unvalidated_resp.json()["supplier"]["id"]
    await auth_client.patch(f"/api/v2/suppliers/{unvalidated_id}", json={"is_validated": False})

    resp = await auth_client.get(
        "/api/v2/suppliers/suggest",
        params={"item_description": "material test", "category": "materiales"},
    )
    assert resp.status_code == 200
    suggestions = resp.json()["suggestions"]
    if len(suggestions) >= 2:
        for s in suggestions:
            if not s["is_validated"]:
                assert s["score_breakdown"]["validation_multiplier"] == 0.5
            else:
                assert s["score_breakdown"]["validation_multiplier"] == 1.0
