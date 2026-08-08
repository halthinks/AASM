from aasm import AASMRemoteClient, TaskDemand, WorkerRecord

CONTROL="http://127.0.0.1:8787"
TOKEN="CHANGE_ME"
MACHINE_ID="replace-me"

client=AASMRemoteClient(CONTROL,TOKEN)
client.register_worker(MACHINE_ID,WorkerRecord("host-a","cpu-worker"))
client.heartbeat(MACHINE_ID,"host-a")
lease=client.claim(MACHINE_ID,"host-a",TaskDemand("compile",["code"],demand=1),lease_seconds=60)
# do real work here
client.complete(MACHINE_ID,lease["lease_id"],{"artifact":"build/output.bin"})
