"""T2a, RF-05: the administrator registers clients and anyone with a session reads them.

Runs on both adapters (fixture `backend`).
"""

from support import ADMIN, COLLECTOR


def _register(flow, actor: str = ADMIN, name: str = "Cliente nuevo", route_id: str = "ruta-1"):
    return flow._post("/v1/clients", actor, {"name": name, "route_id": route_id})


def test_t2a_administrator_registers_a_client_and_reads_it_back(flow):
    response = _register(flow)

    assert response.status_code == 201
    created = response.json()
    assert (created["name"], created["route_id"]) == ("Cliente nuevo", "ruta-1")
    assert created["id"]
    assert flow._get(f"/v1/clients/{created['id']}", COLLECTOR).json() == created
    listed = flow._get("/v1/clients", COLLECTOR).json()
    assert created in listed


def test_t2a_the_demonstration_clients_are_listed_with_the_new_one_last(flow):
    created = _register(flow).json()

    listed = flow._get("/v1/clients", ADMIN).json()

    assert [client["id"] for client in listed][:4] == [
        "cliente-1",
        "cliente-2",
        "cliente-3",
        "cliente-4",
    ]
    assert listed[-1] == created


def test_t2a_a_collector_cannot_register_a_client(flow):
    response = _register(flow, actor=COLLECTOR)

    assert response.status_code == 403
    assert [c["name"] for c in flow._get("/v1/clients").json()].count("Cliente nuevo") == 0


def test_t2a_an_unknown_route_is_rejected(flow):
    response = _register(flow, route_id="ruta-9")

    assert response.status_code == 404
    assert response.json()["type"].endswith("/ruta-no-encontrada")


def test_t2a_a_blank_name_is_rejected(flow):
    for name in ("", "   "):
        response = _register(flow, name=name)
        assert response.status_code == 422, name


def test_t2a_an_unknown_client_is_not_found(flow):
    response = flow._get("/v1/clients/no-existe")

    assert response.status_code == 404
    assert response.json()["type"].endswith("/cliente-no-encontrado")


def test_t2a_a_registered_client_can_receive_a_disbursement(flow):
    created = _register(flow).json()

    requested = flow.request(client=created["id"])

    assert requested.status_code == 201
    assert requested.json()["client_id"] == created["id"]
