from copy import deepcopy

class HotReuseIndex:
    def __init__(self): self._rows=[]
    def add(self,candidate):
        if all(row.fingerprint!=candidate.fingerprint for row in self._rows): self._rows.append(deepcopy(candidate))
    def candidates(self,request):
        exact=[deepcopy(row) for row in self._rows if row.kind==request.kind and row.request_fingerprint==request.fingerprint]
        return exact or [deepcopy(row) for row in self._rows if row.kind==request.kind]
    def clear(self): self._rows.clear()
    def dump(self): return [row.to_dict() for row in sorted(self._rows,key=lambda x:x.fingerprint)]
