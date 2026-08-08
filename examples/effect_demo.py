from aasm import AASMEngine, EffectSpec, ProblemSpec, RetryPolicy, SQLiteStore

store = SQLiteStore("aasm-effects.db")
engine = AASMEngine(ProblemSpec("Perform one durable external operation"), store=store)

effect = engine.propose_effect(
    EffectSpec(
        effect_type="example.write",
        payload={"message": "hello"},
        idempotency_key="example-write-001",
        retry_policy=RetryPolicy(max_attempts=2, retry_on_failure=True),
    )
)
engine.authorize_effect(effect.spec.effect_id, authority="example-controller")


def executor(spec, idempotency_key):
    # Forward idempotency_key to an external provider when supported.
    return {"written": spec.payload["message"], "idempotency_key": idempotency_key}


result = engine.execute_effect(effect.spec.effect_id, executor)
print(result.status, result.result)
store.close()
