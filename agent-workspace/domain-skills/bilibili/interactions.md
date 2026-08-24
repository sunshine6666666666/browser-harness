# Bilibili — Background-safe read-only interactions (gray release)

Use this helper for read-only Bilibili navigation and filters while the gray
release is active. It first uses a DOM click, which does not send macOS-facing
CDP mouse input. The caller must provide an observable completion check. If
that check fails, the helper activates the tab and falls back to the existing
coordinate click so task completion remains the priority.

Load it inside Browser Harness:

```python
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/interactions.py").read())
```

Example — navigate from the Bilibili home page to Popular:

```python
result = bilibili_click_readonly(
    text="热门",
    verify=lambda: any("/v/popular/" in tab["url"] for tab in list_tabs()),
)
print(result)  # mode is silent or fallback
```

For a page-local tab or filter, narrow with `selector` and verify the selected
state directly:

```python
result = bilibili_click_readonly(
    selector="[role=tab]",
    text="每周必看",
    verify=lambda: bool(js("document.querySelector('[role=tab][aria-selected=true]')?.textContent.includes('每周必看')")),
)
```

Rules:

- Read-only controls only. Never use it for like, coin, favorite, follow,
  publish, send, delete, checkout, or account-setting changes.
- A click is successful only when `verify` becomes true.
- `mode="silent"` means no legacy mouse input was needed.
- `mode="fallback"` means the task completed through the focus-taking legacy
  path; never report it as silent success.
- Keep the existing core `click_at_xy()` behavior unchanged during this gray
  release.
