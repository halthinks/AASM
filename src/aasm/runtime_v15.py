from __future__ import annotations

from copy import deepcopy

from .change_impact import ChangeImpactAnalyzer, ChangeKind, ChangeSignal
from .graph import PlanGraph
from .model import new_id
from .runtime_v14 import AASMEngine as V14Engine
from .team_protocol import PlannerBuilderVerifierPolicy, TeamRole


class AASMEngine(V14Engine):
    """v0.15 runtime: information-change checkpoints and selective steering."""

    def paused_tasks(self):
        return sorted(set(self.snapshot.resources.get("change_control",{}).get("paused_tasks",[]) or []))

    def _canonical_paused_tasks(self):
        snapshot=self.store.load_snapshot(self.snapshot.machine_id)
        return set(snapshot.resources.get("change_control",{}).get("paused_tasks",[]) or [])

    def impact_history(self):
        return deepcopy(self.snapshot.resources.get("change_control",{}).get("impacts",[]) or [])

    def last_impact(self):
        items=self.impact_history()
        return items[-1] if items else None

    def analyze_change(self,signal:ChangeSignal,*,pause_affected=True,reason="information change analyzed"):
        active=[x.get("task_id") for x in self.snapshot.resources.get("leases",[]) if x.get("status")=="ACTIVE"]
        analysis=ChangeImpactAnalyzer().analyze(PlanGraph.from_dict(self.snapshot.graph),signal,active)
        raw=analysis.to_dict()
        raw.update({
            "impact_id":new_id("impact"),
            "status":"OPEN",
            "remaining_nodes":list(raw["affected_nodes"]),
            "released_lease_ids":[],
            "resolutions":[],
        })
        resources=deepcopy(self.snapshot.resources); control=resources.setdefault("change_control",{}); control.setdefault("impacts",[]).append(raw)
        if pause_affected:
            paused=set(control.get("paused_tasks",[]) or []); paused.update(raw["affected_nodes"]); control["paused_tasks"]=sorted(paused)
        control["last_impact_id"]=raw["impact_id"]
        self.patch_snapshot({"resources":resources},reason)

        released=[]
        if pause_affected:
            # Use the post-pause canonical snapshot, not the pre-analysis active
            # set. This catches a concurrent claim that landed while the impact
            # checkpoint itself was being committed.
            affected=set(raw["affected_nodes"])
            for lease in list(self.snapshot.resources.get("leases",[])):
                if lease.get("status")=="ACTIVE" and lease.get("task_id") in affected:
                    self.release_lease(lease["lease_id"])
                    released.append(lease["lease_id"])
            if released:
                resources=deepcopy(self.snapshot.resources); impacts=resources.setdefault("change_control",{}).setdefault("impacts",[])
                target=next(x for x in impacts if x.get("impact_id")==raw["impact_id"]); target["released_lease_ids"]=released
                self.patch_snapshot({"resources":resources},"affected active leases released")
                raw=deepcopy(target)
        return deepcopy(raw)

    def claim_task(self,task,worker_id,**kwargs):
        # Check the authoritative store rather than trusting this process's local
        # snapshot. Re-check after claim as well to close the pause/claim race:
        # if a pause lands concurrently, the just-created lease is immediately
        # released and never returned as successful ownership.
        if task.task_id in self._canonical_paused_tasks():
            raise ValueError(f"Task paused by information-change checkpoint: {task.task_id}")
        lease=super().claim_task(task,worker_id,**kwargs)
        if task.task_id in self._canonical_paused_tasks():
            self.release_lease(lease["lease_id"])
            raise ValueError(f"Task became paused during claim: {task.task_id}")
        return lease

    def resolve_change_impact(self,planner_id:str,impact_id:str,*,resume_nodes:list[str]|None=None,retire_nodes:list[str]|None=None,plan_decision_id:str|None=None,reason="change impact resolved"):
        resources=deepcopy(self.snapshot.resources); team=resources.get("team_protocol")
        if team:
            PlannerBuilderVerifierPolicy.require_role(team["members"],planner_id,TeamRole.PLANNER.value)
            if planner_id!=team.get("planner_id"):
                raise PermissionError("only the authoritative Planner may resolve an impact checkpoint")
        control=resources.setdefault("change_control",{}); impacts=control.setdefault("impacts",[])
        target=next((x for x in impacts if x.get("impact_id")==impact_id),None)
        if target is None: raise KeyError(impact_id)
        if target.get("status") not in {"OPEN","PARTIAL"}: raise ValueError("impact checkpoint is already resolved")
        remaining=set(target.get("remaining_nodes",target.get("affected_nodes",[])) or [])
        resume=set(resume_nodes or []); retire=set(retire_nodes or [])
        if not resume.issubset(remaining) or not retire.issubset(remaining):
            raise ValueError("resume_nodes and retire_nodes must be inside the unresolved affected region")
        if resume & retire: raise ValueError("a node cannot be both resumed and retired")
        resolved_now=resume|retire; remaining.difference_update(resolved_now)
        paused=set(control.get("paused_tasks",[]) or []); paused.difference_update(resolved_now); paused.update(remaining)
        control["paused_tasks"]=sorted(paused)
        target["remaining_nodes"]=sorted(remaining)
        target["status"]="RESOLVED" if not remaining else "PARTIAL"
        target.setdefault("resolutions",[]).append({"planner_id":planner_id,"resume_nodes":sorted(resume),"retire_nodes":sorted(retire),"plan_decision_id":plan_decision_id})
        self.patch_snapshot({"resources":resources},reason)
        return deepcopy(target)

    def user_interrupt(self,note:str,*,metadata:dict|None=None):
        control=super().user_interrupt(note,metadata=metadata)
        metadata=deepcopy(metadata or {})
        if metadata.get("seed_nodes") is not None:
            signal=ChangeSignal(ChangeKind.USER_STEERING,note,seed_nodes=list(metadata.pop("seed_nodes") or []),metadata=metadata)
            impact=self.analyze_change(signal,reason="user steering impact analyzed")
            return {"control":control,"impact":impact}
        return control

    def dashboard(self):
        out=super().dashboard()
        out["change_control"]={"paused_tasks":self.paused_tasks(),"last_impact":self.last_impact(),"impact_count":len(self.impact_history())}
        return out
