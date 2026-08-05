from typing import Any

from eduplay.core.i18n import I18n


def _norm(s: Any) -> str:
    try:
        return str(s or "").strip().lower()
    except Exception:
        return ""


def _score_item(item: dict, q: str) -> int:
    if not q:
        return 0
    title = _norm(item.get("title", ""))
    if title.startswith(q):
        return 300
    if q in title:
        return 200
    kws = item.get("keywords", [])
    if isinstance(kws, (list, tuple)):
        for kw in kws:
            k = _norm(kw)
            if not k:
                continue
            if k.startswith(q):
                return 160
            if q in k:
                return 120
    return -1


def filter_items(items: list[dict], query: str) -> list[dict]:
    q = _norm(query)
    if not items:
        return []
    if not q:
        return list(items)
    scored: list[tuple[int, int, dict]] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        s = _score_item(it, q)
        if s < 0:
            continue
        scored.append((s, i, it))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [it for _, __, it in scored]


def _label(key: str, lang: str) -> str:
    try:
        return I18n.t(key, lang)
    except Exception:
        return key


def _normalize_tags(tags: Any) -> list[str]:
    if not isinstance(tags, list):
        return []
    out: list[str] = []
    for tag in tags:
        text = str(tag or "").strip()
        if text:
            out.append(text)
    return out


def build_palette_items(
    projects: list[dict] | None,
    recent_projects: list[dict] | None,
    current_project_id: str = "",
    lang: str = "en",
) -> list[dict]:
    recent_ids = {
        str(item.get("id") or "").strip()
        for item in (recent_projects or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    current_project_id = str(current_project_id or "").strip()
    items: list[dict] = [
        {
            "id": "action:new_project",
            "title": _label("command_palette.action_new_project", lang),
            "keywords": ["new", "create", "project", "tao", "du an"],
            "kind": "action",
            "action": "new_project",
        },
        {
            "id": "action:open_projects",
            "title": _label("command_palette.action_open_projects", lang),
            "keywords": ["open", "projects", "browser", "du an", "danh sach"],
            "kind": "action",
            "action": "open_projects",
        },
        {
            "id": "action:quick_preview",
            "title": _label("command_palette.action_quick_preview", lang),
            "keywords": ["quick", "preview", "current", "xem nhanh", "cau hien tai"],
            "kind": "action",
            "action": "quick_preview",
        },
        {
            "id": "action:full_preview",
            "title": _label("command_palette.action_full_preview", lang),
            "keywords": ["full", "preview", "runtime", "run", "xem day du"],
            "kind": "action",
            "action": "full_preview",
        },
        {
            "id": "action:export_html",
            "title": _label("command_palette.action_export_html", lang),
            "keywords": ["export", "html", "publish", "xuat ban"],
            "kind": "action",
            "action": "export_html",
        },
    ]

    for project in projects or []:
        if not isinstance(project, dict):
            continue
        project_id = str(project.get("id") or "").strip()
        if not project_id:
            continue
        name = str(project.get("name") or project_id).strip() or project_id
        desc = str(project.get("description") or "").strip()
        game_type = str(project.get("game_type") or "").strip()
        tags = _normalize_tags(project.get("tags"))
        is_current = project_id == current_project_id
        is_recent = project_id in recent_ids
        keywords = [name, desc, game_type, *tags]
        if is_current:
            keywords.extend(["current", "open", "dang mo"])
        if is_recent:
            keywords.extend(["recent", "gan day"])
        items.append(
            {
                "id": f"project:{project_id}",
                "title": name,
                "subtitle": desc,
                "keywords": keywords,
                "kind": "project",
                "project_id": project_id,
                "game_type": game_type,
                "tags": tags,
                "is_current": is_current,
                "is_recent": is_recent,
            }
        )
    return items
