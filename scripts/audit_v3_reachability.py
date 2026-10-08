"""Static reachability inventory: import *plus actual symbol-use*, not imports alone.

Catalogs every learnflow_v3 module/public API, production caller, integration
caller, downstream module, test and script. This is a conservative AST audit:
dynamic imports / DI reflection cannot be proven absent by static analysis.
Never delete a file solely because this reports no reachable callers.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRODUCTION_PREFIXES=("app/","lesson_pipeline/","live_evaluation/",".hermes/plugins/")
INTEGRATION_MODULES={"learnflow_v3.integration_slice","learnflow_v3.offline_lesson_source"}
IGNORE=(".git/",".venv/","venv/","node_modules/","dist/","build/","__pycache__/")
EXPLICIT_SAFETY_OFFLINE={
    "learnflow_v3.artifact_critic","learnflow_v3.artifact_refine",
    "learnflow_v3.evaluation_pilot","learnflow_v3.release_gate",
    "learnflow_v3.publication_gate",
}
ENTRYPOINTS=("app/main.py","lesson_pipeline/coordinator.py","live_evaluation/pilot.py",
             ".hermes/plugins/learnflow/tools.py")


def _mod(path:str)->str:
    return path[:-3].replace("/",".").removesuffix(".__init__")


def _parse():
    result={}
    for p in sorted(ROOT.rglob("*.py")):
        name=p.relative_to(ROOT).as_posix()
        if any(name.startswith(prefix) or "/"+prefix in name for prefix in IGNORE):
            continue
        try:result[name]=ast.parse(p.read_text(encoding="utf-8"),filename=name)
        except (SyntaxError,UnicodeError):
            continue
    return result


def build_inventory()->dict:
    parsed=_parse()
    v3=[p for p in parsed if p.startswith("learnflow_v3/")]
    modules={_mod(p):p for p in v3}
    direct={m:set() for m in modules}
    consumers={m:set() for m in modules}
    api_calls={m:{} for m in modules}
    for path,tree in parsed.items():
        loads={n.id for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
        attrs={n.value.id+"."+n.attr for n in ast.walk(tree)
               if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name)}
        ownmod=_mod(path)
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                resolved=None
                if node.level and path.startswith("learnflow_v3/"):
                    # V3 modules have flat siblings. Import from .models is a direct edge.
                    if node.level==1 and node.module:
                        resolved="learnflow_v3."+node.module
                elif node.module and node.module.startswith("learnflow_v3"):
                    resolved=node.module
                if resolved in modules:
                    for alias in node.names:
                        active=alias.asname or alias.name
                        if active in loads:
                            direct[resolved].add(path)
                            consumers[resolved].add(path)
                            api_calls[resolved].setdefault(alias.name,set()).add(path)
            elif isinstance(node,ast.Import):
                for alias in node.names:
                    if alias.name in modules:
                        used_name=alias.asname or alias.name.split(".")[0]
                        if used_name in loads and (
                            alias.asname or alias.name in attrs or
                            any(s.startswith(used_name+".") for s in attrs)
                        ):
                            direct[alias.name].add(path)
                            consumers[alias.name].add(path)
        # import from package's __init__ is intentionally indistinguishable at
        # module level; track explicitly as a lower-bound import of package.
    rows=[]
    for mod,path in sorted(modules.items()):
        tree=parsed[path]
        symbols=[n.name for n in tree.body if isinstance(
            n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)
        ) and not n.name.startswith("_")]
        actual=set(x for x in consumers[mod] if x!=path)
        production=sorted(x for x in actual if x.startswith(PRODUCTION_PREFIXES))
        integration=sorted(x for x in actual if _mod(x) in INTEGRATION_MODULES)
        demos=sorted(x for x in actual if x.startswith("scripts/"))
        tests=sorted(x for x in actual if x.startswith("tests/"))
        internal=sorted(x for x in actual if x.startswith("learnflow_v3/"))
        # No static import from production directly/indirectly into V3.
        # Treat internal code / test-only conservatively, NOT as unused/dead.
        if production:state="PRODUCTION_REFERENCED_REQUIRES_RUNTIME_PROOF"
        elif integration:state="OFFLINE_INTEGRATION_ONLY"
        elif mod in EXPLICIT_SAFETY_OFFLINE:state="INTENTIONALLY_OFFLINE_SAFETY_GATE"
        elif demos or tests:state="DEMO_OR_TEST_ONLY"
        elif internal:state="INTERNAL_LIBRARY_ONLY"
        else:state="POTENTIAL_ORPHAN_VERIFY_MANUALLY"
        rows.append({
            "module":mod,"file":path,"status":state,
            "production_callers":production,
            "integration_callers":integration,
            "downstream_v3_consumers":internal,
            "script_callers":demos,"test_callers":tests,
            "public_api":[{"name":name,"referenced_callers":sorted(api_calls[mod].get(name,())),
                            "status":"REFERENCED_IN_STATIC_AST" if api_calls[mod].get(name)
                            else "NOT_STATICALLY_REFERENCED_REQUIRES_MANUAL_AUDIT"}
                           for name in symbols],
        })
    return {
        "version":"v3-integration-closure-static-inventory-v1",
        "scope":"AST_STATIC_LOWER_BOUND_NOT_DYNAMIC_CALL_GRAPH",
        "scope_files_scanned":len(parsed),
        "production_entrypoints":list(ENTRYPOINTS),
        "uncertainties":[
            "Dynamic imports and dependency injection are not modeled",
            "Module-level access through a package re-export may be undercounted",
            "A public API without direct named call is not automatically dead code",
            "Static references do not prove successful runtime integration",
            "A script importing a module is offline evidence, not app production wiring",
        ],
        "production_v3_imports_found":sum(len(r["production_callers"]) for r in rows),
        "module_count":len(rows),
        "rows":rows,
    }


if __name__=="__main__":
    print(json.dumps(build_inventory(),ensure_ascii=False,indent=2))
