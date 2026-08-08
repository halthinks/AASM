from __future__ import annotations
import hashlib,json,time

class DPMemory:
    def __init__(self): self._cache={}
    @staticmethod
    def signature(problem_class:str, inputs, constraints=None):
        raw=json.dumps({"class":problem_class,"inputs":inputs,"constraints":constraints or {}},sort_keys=True,separators=(",",":"),default=str).encode()
        return hashlib.sha256(raw).hexdigest()
    def put(self,key,value,*,scope=None,proof=None):
        self._cache[key]={"value":value,"scope":scope or {},"proof":proof or [],"created_at":time.time(),"valid":True}
    def get(self,key,*,scope=None):
        item=self._cache.get(key)
        if not item or not item["valid"]: return None
        required=item["scope"]
        if scope is not None and any(scope.get(k)!=v for k,v in required.items()): return None
        return item["value"]
    def invalidate(self,key,reason=""):
        if key in self._cache: self._cache[key]["valid"]=False; self._cache[key]["invalidated_reason"]=reason
    def dump(self): return self._cache.copy()
