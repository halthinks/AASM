from aasm import (
    AASMEngine,
    KubernetesScaleAdapter,
    LocalDirectoryArtifactBackend,
    ProblemSpec,
    ResourceRecord,
    WorkerControlAction,
    WorkerControlRecord,
    WorkerRecord,
)


engine=AASMEngine(ProblemSpec("provider/artifact/control example"))
engine.register_resource(ResourceRecord("workers","agent",["code"],capacity=2))
engine.register_worker(WorkerRecord("worker-1","workers"))

# Worker lifecycle control affects AASM admission only.
engine.control_worker(WorkerControlRecord("worker-1",WorkerControlAction.DRAIN,"operator","maintenance"))
engine.control_worker(WorkerControlRecord("worker-1",WorkerControlAction.RESUME,"operator","maintenance complete"))

# External text is stored outside the machine snapshot; AASM keeps the ref.
backend=LocalDirectoryArtifactBackend("./.aasm-artifacts","local")
artifact=engine.store_text_artifact(
    backend,
    backend_name="local",
    namespace=engine.snapshot.machine_id,
    name="example-log",
    text="example log payload",
)
print(artifact)

# Concrete provider adapters are still called only through an authorized
# provisioning EffectSpec. This adapter is constructed here only to show the
# provider contract; the example deliberately does not execute kubectl.
adapter=KubernetesScaleAdapter()
print(type(adapter).__name__)
