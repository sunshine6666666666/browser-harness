# Tabs

Use **CDP for control**, **UI automation for user-visible order**.

## Pure CDP (portable: macOS / Linux / Windows)

```python
tabs = list_tabs()                    # includes chrome:// pages too
real_tabs = list_tabs(include_chrome=False)
tid = new_tab("https://example.com")  # create + attach
switch_tab(tid)                       # attach harness to tab
cdp("Target.activateTarget", targetId=tid)  # show it in Chrome
print(current_tab())
print(page_info())
```

What CDP is good at:
- attach to a tab
- open a tab
- activate a known target
- inspect URL/title/viewport
- capture the attached tab's screenshot even if another tab is visibly frontmost

What CDP is bad at:
- matching the **left-to-right tab strip order** the user sees
- telling whether the attached target is an omnibox popup / internal page without URL filtering

## Visible order (platform UI)

### macOS

```applescript
tell application "Google Chrome"
  set out to {}
  set i to 1
  repeat with t in every tab of front window
    set end of out to {tab_index:i, tab_title:(title of t), tab_url:(URL of t)}
    set i to i + 1
  end repeat
  return out
end tell
```

```applescript
tell application "Google Chrome"
  set active tab index of front window to 2
  activate
end tell
```

### Linux

No AppleScript. Same split still applies:
- use CDP for `new_tab`, attach, inspect, activate known targets
- use window-manager / browser UI automation when the user means visible order

Typical tools:
- `xdotool`
- `wmctrl`
- desktop-environment scripting (`gdbus`, KWin, GNOME Shell extensions, etc.)

## Rules that held up in practice

- `switch_tab()` is **not enough** if the user expects Chrome to visibly change.
- `Target.activateTarget` is the CDP-side "show this tab".
- `list_tabs()` includes `chrome://newtab/` by default; ask for `include_chrome=False` when you want only real pages.
- `chrome://omnibox-popup.top-chrome/` can appear as a fake page target; ignore it for user-facing tab lists.
- If a page has `w=0 h=0`, you may be attached to the wrong target or a non-window surface.
- For dynamic UIs, re-read element rects after opening dropdowns / modals before coordinate-clicking.

## Shared instance tab safety (multi-agent)

The Agent Chrome (BU_NAME=agent, port 9223) is a **shared browser**: multiple
Hermes agents (researchbot, devkeeper, ...) use it at the same time. A tab you
see is usually another agent's live work — they judge task state by "open tabs +
screenshots", so closing their tab breaks their workflow even though the session
data stays recoverable server-side.

**Safe closing conventions (mandatory):**
- Only close tabs **your own `new_tab()` returned** (keep a targetId whitelist).
- Never batch-close by URL/domain filter (e.g. `'chatgpt.com' in url`). That is
  exactly what caused issue #11 — it closed 3 other agents' work tabs.
- When you need to close a tab you did not open, check ownership first:
  `tab_owner(tid)` → returns the protection entry or `None`.

**Protection API (issue #11):**
```python
protect_tab(tid, owner="devkeeper", purpose="Issue #11 verification")  # protect a specific tab
protect_tab(owner="researchbot", purpose="Deep Research session")      # protect current tab
protect_tab(url_contains="chatgpt.com/c/6a7305c9", owner="researchbot",
            purpose="session tab")                                     # protect by URL pattern
list_tabs()        # each tab now includes protected / owner / purpose
tab_owner(tid)     # -> protection entry or None
unprotect_tab(tid) # remove protection when you are done
close_tab(tid)               # raises RuntimeError("tab_protected: ...") if protected
close_tab(tid, force=True)   # only when you own it — bypasses protection and clears the entry
```

- Protection is enforced **daemon-side**: even a raw
  `cdp("Target.closeTarget", targetId=...)` refuses protected tabs unless
  `force=True` is passed. Entries persist across daemon restarts in the config
  dir (`tab-protections-<BU_NAME>.json`).
- Protect tabs you are actively working on so other agents' cleanup cannot
  close them; unprotect when the work is done.
