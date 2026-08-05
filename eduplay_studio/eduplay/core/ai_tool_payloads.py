def _parse_json_lenient(value):
    import json
    import ast

    try:
        raw = str(value or "").strip()
    except Exception:
        raw = ""
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
    candidates = []
    if raw:
        candidates.append(raw)
    try:
        i = raw.find("{")
        j = raw.rfind("}")
        if i != -1 and j != -1 and j > i:
            candidates.append(raw[i : j + 1])
    except Exception:
        pass
    try:
        i = raw.find("[")
        j = raw.rfind("]")
        if i != -1 and j != -1 and j > i:
            candidates.append(raw[i : j + 1])
    except Exception:
        pass
    try:
        raw2 = raw.replace("\r", "").replace("\n", " ").strip()
        if raw2 and raw2 not in candidates:
            candidates.append(raw2)
        try:
            i = raw2.find("{")
            j = raw2.rfind("}")
            if i != -1 and j != -1 and j > i:
                cand = raw2[i : j + 1]
                if cand not in candidates:
                    candidates.append(cand)
        except Exception:
            pass
        try:
            i = raw2.find("[")
            j = raw2.rfind("]")
            if i != -1 and j != -1 and j > i:
                cand = raw2[i : j + 1]
                if cand not in candidates:
                    candidates.append(cand)
        except Exception:
            pass
    except Exception:
        pass
    for cand in candidates:
        try:
            return json.loads(cand)
        except Exception:
            pass
        try:
            obj = ast.literal_eval(cand)
            if isinstance(obj, (dict, list)):
                return obj
        except Exception:
            pass
    return None


def build_updated_question(payload, current_q):
    if not isinstance(payload, dict):
        return None

    patch = payload.get("patch")
    full = payload.get("question")

    if isinstance(patch, str):
        patch_s = patch
        patch = _parse_json_lenient(patch)
        if patch is None:
            try:
                ps = str(patch_s or "").strip()
            except Exception:
                ps = ""
            if ps:
                patch = {"explanation": ps}
    if isinstance(full, str):
        full = _parse_json_lenient(full)

    if isinstance(full, dict):
        return dict(full)

    if isinstance(patch, dict) and isinstance(current_q, dict):
        new_q = dict(current_q)
        new_q.update(patch)
        return new_q

    if isinstance(current_q, dict):
        ignore = {
            "question_id",
            "questionId",
            "qid",
            "id",
            "question_index",
            "questionIndex",
            "index",
            "question_number",
            "questionNumber",
            "number",
            "q",
            "patch",
            "question",
        }
        flat_patch = {}
        for k, v in payload.items():
            if k in ignore:
                continue
            flat_patch[k] = v
        if flat_patch:
            new_q = dict(current_q)
            new_q.update(flat_patch)
            return new_q

    return None


def parse_update_question_payload(args):
    if isinstance(args, dict):
        return args
    obj = _parse_json_lenient(args)
    if isinstance(obj, dict):
        return obj
    try:
        s = str(args or "").strip()
    except Exception:
        s = ""
    if not s:
        return {}
    if ":" in s and "{" in s:
        try:
            i = s.find("{")
            j = s.rfind("}")
            if i != -1 and j != -1 and j > i:
                cand = s[i : j + 1]
                obj2 = _parse_json_lenient(cand)
                if isinstance(obj2, dict):
                    return obj2
        except Exception:
            pass
    try:
        import re

        pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\".*?\"|\'.*?\'|[^,]+)", s)
        out = {}
        for k, v in pairs:
            key = str(k or "").strip()
            val_raw = str(v or "").strip()
            if (val_raw.startswith('"') and val_raw.endswith('"')) or (val_raw.startswith("'") and val_raw.endswith("'")):
                val = val_raw[1:-1]
            else:
                val = val_raw.strip()
            if key:
                out[key] = val
        if out:
            return out
        return {"patch": {"explanation": s}}
    except Exception:
        if s:
            return {"patch": {"explanation": s}}
        return {}


def extract_question_numbers(text):
    try:
        s = str(text or "")
    except Exception:
        s = ""
    if not s:
        return []
    try:
        import re
    except Exception:
        re = None
    nums = []
    if re is not None:
        for m in re.finditer(r"(?:\b(?:câu|cau|q)\s*#?\s*)(\d{1,3})\b", s, flags=re.IGNORECASE):
            nums.append(m.group(1))
        if not nums:
            for m in re.finditer(r"\bq(\d{1,3})\b", s, flags=re.IGNORECASE):
                nums.append(m.group(1))
        try:
            if ("câu" in s.lower()) or ("cau" in s.lower()):
                for m in re.finditer(r"\b(\d{1,3})\b", s):
                    nums.append(m.group(1))
        except Exception:
            pass
    seen = set()
    out = []
    for x in nums:
        try:
            n = int(str(x))
        except Exception:
            continue
        if n <= 0 or n > 500:
            continue
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out
