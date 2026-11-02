"""AI-free code tools: a real Python line tracer (run inside Judge0) and a rule-based reviewer."""

import ast
import json
import re

from fastapi import HTTPException

from .judge0 import run_code

MAX_STEPS = 200

# Runs inside the Judge0 sandbox. Traces only the user's module, captures stdout per step, prints JSON at the end.
_TRACER = r'''
import io, json, sys
SRC = json.loads(%s)
REAL_OUT = sys.stdout
buf = io.StringIO()
steps = []
mark = [0]

def snap(frame):
    out = {}
    for k, v in list(frame.f_locals.items()):
        if k.startswith("__") or callable(v) or type(v).__name__ == "module":
            continue
        try:
            r = repr(v)
        except Exception:
            r = "<?>"
        out[k] = r if len(r) <= 120 else r[:117] + "..."
    return out

def flush(step):
    text = buf.getvalue()
    if len(text) > mark[0]:
        if step is None:
            step = next((s for s in reversed(steps) if "ret" not in s), None)
        if step is not None:
            step["output"] = (step["output"] or "") + text[mark[0]:]
    mark[0] = len(text)

current = {}

def tracer(frame, event, arg):
    if frame.f_code.co_filename != "<main>":
        return None
    fid = id(frame)
    if event == "call":
        # Output printed before this call belongs to the caller's current line.
        flush(current.get(id(frame.f_back)) if frame.f_back else None)
    elif event == "line" and len(steps) < %d:
        flush(current.get(fid))
        step = {"line": frame.f_lineno, "fn": frame.f_code.co_name, "fid": fid, "variables": snap(frame), "output": None}
        steps.append(step)
        current[fid] = step
    elif event == "return" and steps:
        flush(current.pop(fid, None))
        try:
            value = repr(arg)
        except Exception:
            value = "<?>"
        steps.append({"ret": True, "fid": fid, "variables": snap(frame), "value": value[:120]})
    return tracer

error = None
sys.stdout = buf
sys.settrace(tracer)
try:
    exec(compile(SRC, "<main>", "exec"), {"__name__": "__main__"})
except SystemExit:
    pass
except BaseException as e:
    error = "%%s: %%s" %% (type(e).__name__, e)
finally:
    sys.settrace(None)
    flush(None)
    sys.stdout = REAL_OUT
REAL_OUT.write(json.dumps({"steps": steps, "output": buf.getvalue(), "error": error, "truncated": len(steps) >= %d}))
'''


async def trace_python(code: str, stdin: str) -> dict:
    program = _TRACER % (json.dumps(json.dumps(code)), MAX_STEPS, MAX_STEPS)
    result = await run_code("python", program, stdin)
    try:
        data = json.loads(result.get("stdout") or "")
    except ValueError:
        raise HTTPException(422, result.get("stderr") or result.get("compile_output") or result.get("status") or "Trace failed")

    raw = data["steps"]
    steps = []
    for k, s in enumerate(raw):
        if s.get("ret"):
            continue
        # State after this line = state at the next event in the same frame.
        nxt = next((n for n in raw[k + 1:] if n["fid"] == s["fid"]), None)
        after = nxt["variables"] if nxt else s["variables"]
        scope = "" if s["fn"] == "<module>" else f" in {s['fn']}()"
        changed = [f"{name} = {v}" for name, v in after.items() if s["variables"].get(name) != v]
        text = f"Line {s['line']}{scope} ran."
        if changed:
            text += " Now " + ", ".join(changed[:4]) + ("…" if len(changed) > 4 else "") + "."
        if nxt and nxt.get("ret") and s["fn"] != "<module>":
            text += f" {s['fn']}() returned {nxt['value']}."
        if s["output"]:
            text += f" Printed {s['output'].rstrip()!r}."
        steps.append({"line": s["line"], "variables": after, "output": s["output"], "explanation": text})
    if data.get("error") and steps:
        steps[-1]["explanation"] = f"Line {steps[-1]['line']} raised {data['error']}."
    if data.get("truncated") and steps:
        steps[-1]["explanation"] += f" (Trace stopped after {MAX_STEPS} steps.)"
    return {"steps": steps, "final_output": data.get("output"), "mode": "traced"}


def _loop_depth_python(tree: ast.AST) -> int:
    def depth(node: ast.AST, d: int) -> int:
        here = d + isinstance(node, (ast.For, ast.While, ast.comprehension))
        return max([here, *(depth(c, here) for c in ast.iter_child_nodes(node))])
    return depth(tree, 0)


def _review_python(code: str) -> tuple[list[dict], list[str], int, bool]:
    issues: list[dict] = []
    tips: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [{"line": e.lineno, "severity": "error", "message": f"Syntax error: {e.msg}"}], [], 0, False

    funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    recursive = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({"line": node.lineno, "severity": "warning", "message": "Bare `except:` hides real errors — catch specific exceptions."})
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append({"line": node.lineno, "severity": "warning",
                                   "message": f"Mutable default argument in {node.name}() is shared between calls — use None."})
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == node.name for c in ast.walk(node)):
                recursive = True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "pop" and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                issues.append({"line": node.lineno, "severity": "info", "message": "list.pop(0) is O(n) — use collections.deque.popleft()."})
            if node.func.attr == "index" or node.func.attr == "count":
                tips.append(f"Line {node.lineno}: .{node.func.attr}() scans the whole list (O(n)); a dict/Counter may be faster inside loops.")
        if isinstance(node, (ast.For, ast.While)):
            for inner in ast.walk(node):
                if isinstance(inner, ast.AugAssign) and isinstance(inner.op, ast.Add) and isinstance(inner.value, (ast.JoinedStr, ast.Constant)) \
                        and isinstance(getattr(inner.value, "value", ""), str):
                    tips.append(f"Line {inner.lineno}: building a string with += in a loop is O(n²) — collect parts and ''.join() them.")
                    break
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and getattr(node.iter.func, "id", "") == "range" \
                    and node.iter.args and isinstance(node.iter.args[0], ast.Call) and getattr(node.iter.args[0].func, "id", "") == "len":
                tips.append(f"Line {node.lineno}: prefer `for i, x in enumerate(items)` over range(len(items)).")
        if isinstance(node, ast.Compare) and any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops) \
                and any(isinstance(c, ast.Constant) and c.value is not None and not isinstance(c.value, bool) for c in node.comparators):
            issues.append({"line": node.lineno, "severity": "error", "message": "`is` compares identity — use == for values."})
    if not funcs and len(code.splitlines()) > 40:
        tips.append("Split long scripts into small functions so each piece can be tested.")
    return issues, list(dict.fromkeys(tips)), _loop_depth_python(tree), recursive


def _review_braces(language: str, code: str) -> tuple[list[dict], list[str], int, bool]:
    issues: list[dict] = []
    tips: list[str] = []
    depth, best, stack = 0, 0, []
    for line in code.splitlines():
        stripped = line.strip()
        is_loop = bool(re.match(r"(for|while)\b", stripped))
        for ch in stripped:
            if ch == "{":
                stack.append(is_loop)
                depth += is_loop
                best = max(best, depth)
                is_loop = False
            elif ch == "}" and stack:
                depth -= stack.pop()
    for n, line in enumerate(code.splitlines(), 1):
        if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
            issues.append({"line": n, "severity": "warning", "message": "Empty catch block swallows errors."})
        if language in ("cpp", "java") and re.search(r"\bint\b[^;]*\*[^;]*;", line) and "long" not in line:
            tips.append(f"Line {n}: multiplying ints can overflow — consider long / long long.")
        if language == "cpp" and re.search(r"\bendl\b", line) and re.search(r"\b(for|while)\b", code):
            tips.append("Prefer '\\n' over endl inside loops — endl flushes every time.")
        if language == "javascript" and re.search(r"\.sort\(\)", line):
            tips.append(f"Line {n}: Array.sort() without a comparator sorts numbers as strings.")
    names = set(re.findall(r"\b(\w+)\s*\([^;{]*\)\s*\{", code)) - {"if", "for", "while", "switch", "catch", "main"}
    recursive = any(len(re.findall(rf"\b{re.escape(f)}\s*\(", code)) > 1 for f in names)
    return issues, list(dict.fromkeys(tips)), best, recursive


def review(language: str, code: str) -> dict:
    issues, tips, loops, recursive = _review_python(code) if language == "python" else _review_braces(language, code)
    if loops == 0:
        time = "O(1) per input (no loops)" if not recursive else "Depends on recursion depth/branching"
    else:
        time = "O(n)" if loops == 1 else f"O(n^{loops})"
        if recursive:
            time += " plus recursion"
    tips.append("Test with: empty input, a single element, duplicates, negatives and the largest allowed size.")
    if loops >= 2:
        tips.append("Nested loops: check whether a hash map, sorting + two pointers, or prefix sums can remove one level.")
    summary = (f"Rule-based review: {'no obvious problems found' if not issues else f'{len(issues)} issue(s) found'}; "
               f"deepest loop nesting = {loops}{', uses recursion' if recursive else ''}. "
               "Add an AI key in backend/.env for a full AI review.")
    return {"summary": summary, "time_complexity": f"~{time} (estimated from loop nesting)",
            "space_complexity": "Depends on data structures used" if not recursive else "Includes recursion stack",
            "issues": issues, "suggestions": tips[:8]}
