from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer

from aasm import AASMEngine, DecisionRecord, ProblemSpec, SQLiteStore, __version__
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


def test_remote_v25_observability_and_backend_views(tmp_path):
    database = str(tmp_path / "v25-remote.db")
    store = SQLiteStore(database)
    engine = AASMEngine(ProblemSpec("remote observability"), store=store)
    engine.register_decision(DecisionRecord("D1", "method", "A"))
    machine_id = engine.snapshot.machine_id
    store.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(database, "secret"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        health = client.health()
        assert health["version"] == "0.19.0"
        assert health["runtime_version"] == __version__
        contract = client._request("GET", "/adoption-contract")
        assert contract["valid"] is True
        assert contract["contract"]["contract_id"] == "aasm.adoption.v1"
        assert contract["contract"]["reference_application"]["id"] == "research-synthesis"
        assert contract["contract"]["local_stack"]["entry_point"] == (
            "docker compose up --build"
        )
        assert "unknown-effect" in contract["contract"]["operator_runbooks"]
        report = client._request("GET", f"/v1/machines/{machine_id}/inspect/summary")
        assert report["machine_id"] == machine_id
        assert report["decision_graph"]["nodes"][0]["id"] == "D1"
        causal = client._request("GET", f"/v1/machines/{machine_id}/inspect/causal")
        assert causal["kind"] == "CAUSAL"
        backends = client._request("GET", f"/v1/machines/{machine_id}/backends")
        assert any(row["backend_id"] == "aasm.finite-domain" for row in backends["registered_backends"])
        assurance = client._request("GET", f"/v1/machines/{machine_id}/assurance")
        assert assurance["certificate_count"] == 0
    finally:
        server.shutdown()
        server.server_close()
