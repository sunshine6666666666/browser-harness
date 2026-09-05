# ChatGPT Domain Skill 真实复测与强化实施计划

> **Executor:** 低能力自主执行模型。它没有本对话上下文，必须从头逐字执行本文件；不得自行扩大范围、并行委派、猜测页面状态或操作既有会话。

**Goal:** 在当前受管 Agent Chrome 的真实已登录 ChatGPT 页面上，逐项复测 ChatGPT Domain Skill 已声明的全部能力；以可观察状态和最终结果修正最小必要代码、测试和文档，形成状态感知、安全重试、可恢复且声明与行为一致的 Domain Skill。

**Done when:** 当前声明的每项能力都有本轮真实页面结论和脱敏证据；普通会话“新建—设置—发送一次—等待—读取—长会话操作—精确切换—精确重命名—公开分享—分享页读取—精确删除”闭环通过；Deep Research 最多消耗一次配额并完成“启用—发送一次—状态监控—完成—读取—Markdown 导出—精确删除”；所有未知提交均未重放；原模型、推理强度、页签状态和任务标签已恢复；单元测试、全量测试、Domain Skill 校验和完整 diff 审计全部通过；不存在对既有会话、个人浏览器、其他受管浏览器、Git 分支或远端仓库的修改。

**Workspace root:** `/Users/yelin/orca/workspaces/browser-harness/main`

**Repository root:** `/Users/yelin/orca/workspaces/browser-harness/main`

**Plan file:** `/Users/yelin/orca/workspaces/browser-harness/main/docs/plans/2026-09-04-chatgpt-domain-skill-live-audit.md`

**Evidence file:** `/tmp/browser-harness-chatgpt-audit-20260904.json`

**Target environment:** 本机开发环境；macOS Darwin 24.6.0 arm64；zsh；Python 3.14.6；`browser-harness==0.1.9`；`cdp-use==1.4.5`；`websockets==15.0.1`；当前 checkout 的 `./browser-harness`；受管 Chrome `AgentPool-共享主浏览器-9223`；ChatGPT 当前实际 UI Variant。

**Execution mode:** `unattended`。用户会通过 Goal 启动执行，执行者不得把常规判断、测试选择或安全恢复重新抛给离席用户。

**Live permission contract:** 计划作者于 2026-09-04 21:29 CST 核验：`sandbox_mode=danger-full-access`、`approval_policy=never`、网络可用、文件系统 unrestricted。当前运行时暴露 `create_goal`、`get_goal`、`update_goal`；计划作者的 Goal 状态为空。执行者必须在启动时重新读取自己的真实权限与 Goal schema；作者权限不能转移给执行者。

**Architecture/approved approach:** 不新建框架、Page Object、依赖、分支或 worktree。先只读盘点和真实页面发现，再复用现有 `basic_ops.py`、`deep_research.py` 与同仓 Gemini 已验证的精确身份、单击一次、完整会话和精确关标签模式；只修真实失败或源码已证明违反安全边界的共享根因。每个动作都执行“重新观察—验证前置条件—单次动作—验证后置条件”，非幂等动作结果未知时终止该路径。

**Tech stack:** Python 3.11+；当前解释器 3.14.6；标准库 `re`、`time`、`pathlib`、`urllib.parse`；Browser Harness CDP helpers；pytest 通过 `uv run --with pytest` 临时提供；不新增依赖。

## Required Skills

- `writing-plans`
  - SKILL.md: `/Users/yelin/.agents/skills/writing-plans/SKILL.md`
  - Lessons: `/Users/yelin/.agents/skills/writing-plans/references/lessons.md`
  - Use for: Goal、权限预检、进度账本、失败恢复和完成证明。
- `openai-docs`
  - SKILL.md: `/Users/yelin/.codex/skills/.system/openai-docs/SKILL.md`
  - Lessons: `none found`
  - Use for: 执行开始时刷新 Goal、权限、sandbox 与 Auto-review 的官方契约。
- `ponytail:ponytail`
  - SKILL.md: `/Users/yelin/.codex/plugins/cache/devkeeper-ponytail-local/ponytail/4.8.4/skills/ponytail/SKILL.md`
  - Lessons: `none found`
  - Use for: 复用现有实现、修共享根因、保持最小 diff 和最少测试。
- `browser-fleet-manager`
  - SKILL.md: `/Users/yelin/.agents/skills/browser-fleet-manager/SKILL.md`
  - Lessons: `/Users/yelin/.agents/skills/browser-fleet-manager/references/lessons.md`
  - Use for: 核验浏览器名称、端口、Profile、进程和冲突；只允许 `audit` 与 `resolve`。
- `browser-harness`
  - SKILL.md: `/Users/yelin/orca/workspaces/browser-harness/main/SKILL.md`
  - Lessons: `none found`
  - Use for: Agent Pool 租约、页面发现、标签安全、CDP 与 Domain Skill 规则。
- Browser Harness interaction references
  - `/Users/yelin/orca/workspaces/browser-harness/main/interaction-skills/tabs.md`
  - `/Users/yelin/orca/workspaces/browser-harness/main/interaction-skills/iframes.md`
  - `/Users/yelin/orca/workspaces/browser-harness/main/interaction-skills/cross-origin-iframes.md`
  - `/Users/yelin/orca/workspaces/browser-harness/main/interaction-skills/downloads.md`
  - `/Users/yelin/orca/workspaces/browser-harness/main/interaction-skills/dialogs.md`
  - `/Users/yelin/orca/workspaces/browser-harness/main/interaction-skills/scrolling.md`
  - Lessons: `none found`
  - Use for: 精确关闭自建标签、iframe 状态、下载新鲜度、对话框和虚拟化滚动。

## Official Contract Evidence

计划作者于 2026-09-04 读取当前 Codex Manual，缓存路径为 `/var/folders/fv/pc2rnjn13jb5qg08n12xp8rr0000gn/T/openai-docs-cache/codex-manual.md`。执行者不得依赖该临时缓存长期存在，启动时重新获取以下官方页面：

- `https://learn.chatgpt.com/docs/long-running-work.md`：Goal 必须描述结果、约束和可验证完成条件；相关长任务保持在同一会话。
- `https://learn.chatgpt.com/docs/sandboxing/auto-review.md`：Auto-review 只替换审批者，不扩大 sandbox、网络或可写根；`approval_policy=never` 时没有 review。
- `https://learn.chatgpt.com/docs/permission-modes.md`：sandbox 决定可访问边界，approval 决定越界时如何处理。
- `https://learn.chatgpt.com/docs/permissions.md`：权限配置仍在演进，执行时以实时合同为准。
- `https://learn.chatgpt.com/docs/sandboxing.md`：命令继承同一 sandbox 边界，允许范围内才可自主继续。

## Applicable Rules

- `/Users/yelin/orca/workspaces/browser-harness/main/AGENTS.md`：只使用当前 checkout 的 `./browser-harness`；先读后写；保持最小 diff；未经要求禁止分支、提交和推送。
- `/Users/yelin/orca/workspaces/browser-harness/main/CLAUDE.md`：遵循 `AGENTS.md`；浏览器工作使用当前 source wrapper。
- 用户本轮附带规则：Browser Harness 不支持 `-c`；脚本必须通过 stdin heredoc 或管道；`new_tab(url)` 或 `goto_url(url)` 后第一件事打印并检查 `page_info()`；如果返回 `domain_skill_files`，先读完其中全部 Markdown，再做网站特定动作。
- RTK：普通搜索、Git、测试使用 `rtk`；同一失败两次、输出被截断或安全/删除审计时改用 `RTK_DISABLED=1` 或 `rtk proxy` 获取完整原始输出。
- 文件编辑：只用 `apply_patch`；保存所有无关改动；禁止 `git reset --hard`、`git checkout --`、`git clean` 和递归删除。
- 浏览器身份：个人浏览器只识别不操作；不得直接设置 `BU_CDP_URL`，不得复制 Profile；不得调用 Browser Fleet 的 `start`、`stop`、`adopt`、`update`、`retire`、`restore`、`delete`。
- 共享标签：只关闭本次 `new_tab()` 返回的 target ID；绝不按 URL 扫描或批量关闭；任务标签应 `protect_tab`，完成后 `unprotect_tab` 再精确关闭。
- 单 Agent 执行：不得 spawn 子 Agent，不得并行占用同一 ChatGPT 账号或浏览器；所有真实网页操作经一个 9223 Agent Pool 租约串行执行。

## Scope

- In scope:
  - `basic_ops.md` 当前声明的全部普通会话、模型、推理强度、消息、回复、滚动、分页、Markdown block、长消息展开、Header tab、分享、分享页读取、切换、重命名、删除和标签关闭能力。
  - `deep_research.py` 当前声明的启用、取消、iframe 状态、完整运行与 Markdown 导出能力。
  - 当前 UI Variant 的状态定义、确定性定位、后置条件、错误分类、重试边界、Known-Good State、候选路径评分和剪枝。
  - 仅对上述三个 Domain Skill 文件和两个现有单元测试文件做最小改动。
- Out of scope:
  - ChatGPT 设置、个性化、工作区管理、既有项目和既有会话内容。
  - 密码、Cookie、Token、MFA、验证码、授权同意、付费升级、账号选择。
  - Browser Harness Core、Daemon、Agent Pool、registry、依赖、包版本、浏览器 Profile 或 Fleet 生命周期修改。
  - Git 分支、worktree、commit、push、PR、发布、部署。
  - 随机点击、固定坐标、无限重试、未知提交自动重发、为未出现 UI 预留推测性 fallback。
- Allowed side effects:
  - 创建少量带唯一合成标记的 ChatGPT 测试会话；发送最小普通测试消息和为长会话能力所需的有限合成消息。
  - 最多消耗一次最小 Deep Research 配额。
  - 为本轮普通测试会话创建一个只含合成内容的公开分享链接。
  - 临时切换模型、推理强度和 Header tab 后恢复原状态。
  - 重命名并删除本轮创建、精确 ID 匹配的测试会话。
  - 下载一个本轮新生成的 Deep Research Markdown 报告到当前账号的 Downloads。
- Human-gated side effects:
  - 用户已在需求单中明确回答“是”：允许最小普通消息、一次最小 Deep Research、一个非敏感公开分享、测试会话重命名，以及仅删除本次创建且身份明确的测试数据。此授权不覆盖任何既有会话或其他账号状态。
  - 若执行时出现密码、MFA、验证码、账号选择、付费确认、配额购买或授权同意，立即停止外部动作；没有已授权的绕过路径。

## Permission Feasibility

| 资源或动作 | 作者运行时能力 | 用户授权 | 无监督路径 |
| --- | --- | --- | --- |
| 读取和修改当前仓库 | unrestricted | 仅本计划列出的文件 | `apply_patch`，保留无关改动 |
| `/tmp` 脱敏证据 | unrestricted | 允许 | 固定 Evidence path，不含私人会话内容 |
| `~/Downloads` 新 DR 文件 | unrestricted；浏览器可下载 | 允许一个本轮新报告 | 下载前后快照文件名、mtime、size，只接受新建或变更文件 |
| Browser Fleet audit/resolve | 可执行 | 只读允许 | 固定脚本，输出白名单字段 |
| 9223 Agent Pool | 可执行 | 真实测试允许 | 精确 browser name、`--mode write --account default`、单租约串行 |
| ChatGPT 普通发送 | 登录态可用性待执行确认 | 合成消息允许 | 每条消息发送按钮最多触发一次；unknown 禁止重发 |
| Deep Research | 配额待执行确认 | 最多一次 | 发送前只做 arm/disarm；正式运行只提交一次 |
| 公开分享 | 登录态可用性待执行确认 | 一个合成会话允许 | 首次创建一次，后续只读取同一 URL；actual URL 只存 `/tmp` |
| 精确重命名与删除 | 登录态可用性待执行确认 | 仅本轮测试 ID | 写入 ledger 的 ID、run marker 和 exact URL 三者一致才操作 |
| Git/远端 | 技术上可用 | 未授权 | 不执行 |

## Goal Contract

- 执行开始先读取 `openai-docs`，刷新 Official Contract Evidence 中的页面，记录获取时间、URL、实时 permission profile 和 Goal 工具 schema 到 Evidence file。
- 第一条 Goal 操作先调用实时暴露的 `get_goal`。若用户已建立与本文件 Goal 一致的 active Goal，直接恢复；不得创建重复 Goal。仅当没有 Goal 且实时存在 `create_goal` 时，用本文件 Goal 原文创建一次，不设置 token budget。
- 不把用户界面的 `/goal` 当作 callable tool。Goal 工具名、参数和状态规则以执行运行时 schema 为准。
- 每次恢复：调用 `get_goal`，重读本计划、Required Skills、Lessons 和 Evidence file，检查 `git status --short`、目标浏览器 audit/status、当前 task-owned tabs，再从第一个未完成且前置条件成立的步骤继续。
- 只有 Final Acceptance Gate 全部通过且没有剩余必做工作时才调用 `update_goal(status="complete")`。登录、配额或不可恢复页面变化导致无法完成时，保存证据并按实时 Goal 规则继续或最终标 blocked；不得伪造通过。

## Current-State Evidence

- 作者仓库分支：`sunshine6666666666/main`；HEAD `5f449bc03343bc57af77007de3420f0e272a364f`；`git status --short` 为空。
- `.codegraph/` 路径虽由宿主声明存在，但 `codegraph status` 实际返回 `Not initialized`。执行者不得为本任务初始化或修改 CodeGraph；若执行时已可用，先 query/impact 再以源码复核。
- Browser Fleet audit：`AgentPool-共享主浏览器-9223` 在端口 9223 运行、health ok、Profile `/Users/yelin/Desktop/ManagedBrowsers/active/AgentPool-共享主浏览器-9223--9223/profile`；9224、9225、9226 属于其他受管任务；另有个人 Chrome，只识别不操作。
- `./browser-harness agent-pool status --browser "AgentPool-共享主浏览器-9223"`：selected browser alive；目标资源 `leases=[]`、`write_locks={}`。
- ChatGPT Domain registry 已包含 `chatgpt.com` 和 `*.chatgpt.com`。
- 当前文档真实验证日期为普通会话 2026-08-04、Deep Research 2026-08-05；它们只能作为历史基线。
- 计划作者按用户要求没有执行本轮 ChatGPT 页面复测，也没有运行测试套件。
- 源码已知安全缺口：`switch_chat` 和 `delete_chat` 依赖标题 fragment；`close_extra_tab` 和 `read_shared_conversation` 会扫描标签；`send_and_wait` 未证明返回的是本次发送后的新 assistant turn；`run_deep_research` 绕过 `send_message` 的 unknown 保护；DR connector 已存在但 nested iframe 不可读时会误判 idle；DR 导出未排除旧下载文件。
- 同仓可复用模式位于 `/Users/yelin/orca/workspaces/browser-harness/main/agent-workspace/domain-skills/gemini/basic_ops.py`：精确会话 URL、单击一次发送、new reply 计数、完整虚拟化会话、精确关闭新建分享标签。只能复用状态机和安全原则，不复制 Gemini selector。

## Existing Capability Inventory

| 能力 | 声明/入口 | 当前自动测试 | 本轮真实结论初始值 |
| --- | --- | --- | --- |
| 打开 ChatGPT | `basic_ops.md`; `open_chatgpt` | 无专门测试 | pending |
| 新建空会话 | `new_chat` | fresh home 三项 | pending |
| 切换会话 | `switch_chat` | 无 exact identity 测试 | unsafe until hardened |
| 删除会话 | `delete_chat` | options 子路径，非完整删除 | unsafe until hardened |
| 选择模型 | `select_model` | direct/advanced/checked | pending |
| 推理强度 | `set_reasoning_effort` | 双标签/checked | pending |
| 单次发送 | `send_message` | canonical URL、长 prompt、unknown、多异常 | pending |
| 等待并读回复 | `send_and_wait` | 仅 unknown 不重试 | incomplete until hardened |
| 当前会话读取 | `conversation_text` | 无 | pending |
| 普通滚动 | `scroll_conversation` | 无 | pending |
| 虚拟化分页 | `page_conversation` | Page key 与 moved | pending |
| Markdown block 读取 | `read_markdown_block_summary` | editor full text | pending; variant may not expose block |
| 长消息单个展开 | `toggle_user_message_expand` | 无 | pending |
| 长消息全部展开 | `expand_all_user_messages` | 无 | pending |
| 关闭额外标签 | `close_extra_tab` | 无 | unsafe until hardened |
| 创建公开分享 | `export_share_link` | 无 | pending |
| 读取分享页 | `read_shared_conversation` | 无 | unsafe close until hardened |
| 精确重命名 | `rename_chat` | exact URL、persistence、bounded retry | pending |
| Header 聊天/工作切换 | `switch_header_tab` | 无 | pending |
| DR 启用/取消 | `arm_deep_research` / `disarm_deep_research` | pill 成功/失败/取消 | pending |
| DR 状态识别 | `deep_research_progress` | idle/planning/running/done | mounted-unreadable gap |
| DR 完整运行 | `run_deep_research` | 无 | unsafe send until hardened |
| DR Markdown 导出 | `export_deep_research_markdown` | 旧 fixture 中 newest nonempty | stale-download gap |

## State and Error Contract

`observe_chatgpt_state()` 是唯一新增的共享页面观察入口，返回 dict，至少包含 `state`、`url`、`conversation_id`、`composer_visible`、`composer_empty`、`generating`、`auth_required`、`paywall_or_quota`、`dialog`。`state` 只能是：

- `ready_home`：exact `https://chatgpt.com/`，可见空 unified composer。
- `ready_conversation`：canonical `/c/{id}`，composer 可用且未生成。
- `generating`：canonical conversation，存在停止生成/研究中的可观察信号。
- `auth_required`：登录、密码、MFA、验证码、授权或账号选择界面。
- `paywall_or_quota`：升级、付款、配额不足或购买界面。
- `dialog`：`page_info()` 或 DOM 证明有阻塞对话框。
- `unknown`：以上均无法充分证明。

错误分类使用稳定前缀写入 RuntimeError 或 result reason，不新增异常类：`precondition`、`not_found`、`ambiguous`、`auth_required`、`paywall_or_quota`、`transient_rerender`、`result_unknown`、`timeout`、`postcondition_failed`、`destructive_scope_violation`、`external_blocked`。

Known-Good States：

- `KGS-HOME`：task-owned tab，ready_home，composer empty，无菜单/弹层。
- `KGS-CONVERSATION`：task-owned exact canonical URL，run marker 存在，composer empty，未生成。
- `KGS-RESTORED`：原模型、原推理强度、Header 聊天 tab 恢复，无弹层。
- `KGS-DR-DONE`：exact DR conversation，connector state done，report text 非空，停止研究信号消失。
- `KGS-CLEAN`：所有本轮测试会话的 exact sidebar rows 均不存在；task-owned tabs 已关闭；9223 本任务 lease/write lock 为空；其他端口状态未触碰。

每次 DOM/AX 动作必须在动作当下重新查询元素和 rect；等待、导航、菜单开合或 React 重渲染后的旧 element、backendNodeId、坐标均失效。同步使用 bounded polling 和后置条件，固定等待只允许短暂让 UI settle，不能作为成功证明。

## File Map

| Action | Absolute path | Responsibility |
| --- | --- | --- |
| Modify | `/Users/yelin/orca/workspaces/browser-harness/main/agent-workspace/domain-skills/chatgpt/basic_ops.py` | 页面状态、精确身份、单次发送、回复完成、标签安全和普通会话原子能力 |
| Modify | `/Users/yelin/orca/workspaces/browser-harness/main/agent-workspace/domain-skills/chatgpt/deep_research.py` | DR 单次发送、iframe 状态、超时证据和新鲜下载 |
| Modify | `/Users/yelin/orca/workspaces/browser-harness/main/agent-workspace/domain-skills/chatgpt/basic_ops.md` | 当前状态机、能力表、路径证据、限制、恢复和真实验证结论 |
| Modify | `/Users/yelin/orca/workspaces/browser-harness/main/tests/unit/test_chatgpt_domain_skill.py` | 普通会话安全边界和状态回归 |
| Modify | `/Users/yelin/orca/workspaces/browser-harness/main/tests/unit/test_chatgpt_deep_research.py` | DR unknown、单次发送、iframe 与下载回归 |
| Create temporary | `/tmp/browser-harness-chatgpt-audit-20260904.json` | 可恢复的脱敏事实账本；actual share URL 只保存在这里 |
| Preserve | 其他全部 tracked/untracked 文件、全部既有 ChatGPT 会话、9224/9225/9226 和个人 Chrome | 禁止修改 |

## Interface Contracts

- `observe_chatgpt_state() -> dict[str, Any]`
  - 每次实时读取，不缓存元素；按 State contract 返回；不产生网页副作用。
- `open_chatgpt(url: str = "https://chatgpt.com/") -> dict[str, Any]`
  - 只接受 chatgpt.com home 或 exact canonical conversation URL；返回本次 `new_tab` 的 `target_id` 和最终 state；把 target 注册为本模块 task-owned。
- `switch_chat(conversation: str) -> dict[str, Any]`
  - 只接受 exact URL/path/ID；精确导航或精确 sidebar href；后置条件 URL ID 完全相等且 conversation 可读。删除标题 fragment 语义。
- `delete_chat(conversation: str, confirm: bool = False) -> dict[str, Any]`
  - 只接受 ledger 中本轮创建的 exact ID，`confirm` 必须显式 True；只打开 exact row 的 options；成功需 exact row 消失，返回 deleted ID。
- `close_extra_tab(target_id: str) -> int`
  - 只接受本模块 task-owned 集合中的 exact target ID；protected by another owner 或未知 ID 直接 `destructive_scope_violation`；不扫描 tabs。
- `export_share_link(conversation: str | None = None) -> dict[str, Any]`
  - conversation 为空时只允许当前 canonical chat；非空只接受 exact ID；当前 turns 必须包含本轮 run marker；第一次最多创建一次，结果未知时缓存 unknown 并禁止再次触发；返回 `status`、`url`、`created`、`conversation_id`。
- `read_shared_conversation(url: str, close_after: bool = True) -> dict[str, Any]`
  - 仅允许官方 `https://chatgpt.com/share/` 或已真实确认的官方 message-share path；只关闭该调用 `new_tab` 返回的 target；返回结构化 visible text 和 final URL。
- `send_message(text: str, evidence_timeout: float = 8.0) -> dict[str, Any]`
  - 发送前 composer visible/empty；发送按钮最多激活一次；成功需 canonical URL、composer empty、新 user message ID/turn 和完整或安全折叠前缀同时成立；否则返回 non-retryable unknown。
- `send_and_wait(text: str, timeout: int = 180) -> dict[str, Any]`
  - 记录发送前 assistant IDs/count；仅在 `send_message=definitely_sent` 后等待；新 assistant turn 存在、停止生成信号消失、完整文本长度/尾部连续两次稳定才返回；返回 status、text、message ID 和 URL。
- `deep_research_progress() -> dict[str, Any]`
  - connector 不存在才是 idle；connector 存在但 nested root 缺失、不可读或空白是 unknown 并携带 reason；planning/running/done 使用当前真实 markers。
- `run_deep_research(question, poll_interval=8, timeout=900, export=True) -> dict[str, Any]`
  - 要求已加载 `basic_ops.py`；通过同一个 `send_message` 提交一次；unknown 禁止重发；timeout 返回 unknown、reason、last observation；done 后才允许 export。
- `export_deep_research_markdown(timeout=30) -> str`
  - 点击前快照 `deep-research-report*.md` 的 path、mtime_ns、size；只返回点击后新建或发生变化且非空的文件；旧文件不得冒充本轮产物。

## Requirement Traceability

| 验收 | 实施任务 | 通过证据 |
| --- | --- | --- |
| AC1 完整能力清单 | Task 1、6 | Inventory 每行有声明、入口、测试、真实结论 |
| AC2 每项本轮真实结论 | Task 2、4、5 | Evidence capabilities 无 pending |
| AC3 前后置/中间/未知/失败 | Task 3、6 | State/Error contract 与 tests |
| AC4 成功有目标状态 | 全部真实任务 | before/action/after 证据 |
| AC5 当前 UI Variant | Task 2 | ui_variant 与结构摘要 |
| AC6 重渲染后重新定位 | Task 3、4、5 | query count tests 与 live rerender |
| AC7 备用定位确定性 | Task 2、6 | candidate path matrix 无随机/坐标 fallback |
| AC8 候选路径比较 | Task 2、6 | result/actions/failure/state/side-effect 五列 |
| AC9 正确与安全优先 | Task 6 | selected path rationale |
| AC10 淘汰无价值动作 | Task 6 | pruned paths |
| AC11 条件同步 | Task 3 | monotonic bounded polling tests |
| AC12 重试边界 | Task 3、6 | idempotency table |
| AC13 unknown 不重发 | Task 3、4、5 | click count=1 tests/live evidence |
| AC14 状态化恢复 | Task 3、7 | Recovery matrix 与 ledger resume |
| AC15 Known-Good State | Task 4、5 | KGS assertions |
| AC16 普通消息闭环 | Task 4 | definite send + new final assistant text |
| AC17 DR 闭环 | Task 5 | done + report + fresh Markdown |
| AC18 DR 最小配额 | Task 5 | submission_count=1 |
| AC19 非敏感公开分享 | Task 4 | run marker only；URL 在 `/tmp` |
| AC20 只删本轮测试数据 | Task 4、5 | exact IDs 与 rows absent |
| AC21 文档行为一致 | Task 6 | Function table 与 live matrix |
| AC22 全部路径可审查 | Task 6、7 | Evidence hashes、tests、raw diff |

## Progress Ledger

| Task | Status | Completion evidence |
| --- | --- | --- |
| Task 1 启动与基线 | pending | — |
| Task 2 页面状态与路径发现 | pending | — |
| Task 3 最小安全强化 | pending | — |
| Task 4 普通会话完整闭环 | pending | — |
| Task 5 Deep Research 完整闭环 | pending | — |
| Task 6 文档、路径剪枝与一致性 | pending | — |
| Task 7 最终验收 | pending | — |

### Task 1: 启动门与本地基线

**Purpose:** 建立 Goal、权限、浏览器身份、仓库和测试基线，避免弱模型在错误浏览器或脏状态下继续。

**Working directory:** `/Users/yelin/orca/workspaces/browser-harness/main`

**Risk level:** safe/read-only；只创建 Evidence file。

- [ ] 重读全部 Required Skills、Lessons、AGENTS.md、CLAUDE.md 和本计划；刷新官方合同并记录实际时间、URL、权限和 Goal schema。
- [ ] 调用 `get_goal` 并按 Goal Contract 创建或恢复唯一 Goal。
- [ ] 运行 Browser Fleet audit：
  - Command: `python3 "/Users/yelin/.agents/skills/browser-fleet-manager/scripts/browser_fleet.py" audit`
  - Success: 9223 exact name/profile/port 均一致，health ok，无 conflict。
  - Failure: conflict、unmanaged、stopped 均停止浏览器操作；不得自行 start/stop/adopt。
- [ ] 运行 Fleet resolve 和 Agent Pool status：
  - Commands:
    - `python3 "/Users/yelin/.agents/skills/browser-fleet-manager/scripts/browser_fleet.py" resolve --name "AgentPool-共享主浏览器-9223"`
    - `./browser-harness agent-pool status --browser "AgentPool-共享主浏览器-9223"`
  - Success: CDP URL 为 `http://127.0.0.1:9223`、alive；只按 9223 资源过滤 leases/write_locks，其他端口活动不属于本任务。
- [ ] 原始记录仓库状态：`RTK_DISABLED=1 git status --short && git branch --show-current && git rev-parse HEAD && git diff --check`。保存现有输出，后续不得覆盖其他人的改动。
- [ ] 用 `apply_patch` 创建 Evidence JSON，写入真实 run metadata、Progress Ledger、capabilities、side_effects、ui_variant、candidate_paths、errors、tests 和 cleanup 顶层对象。不得写账号名、邮箱、既有会话标题/正文、Cookie、Token 或完整 page body。
- [ ] 运行本地基线：
  - `rtk uv run --with pytest pytest -q "tests/unit/test_chatgpt_domain_skill.py" "tests/unit/test_chatgpt_deep_research.py"`
  - `rtk python3 "scripts/verify_domain_skills.py"`
  - Expected: exit 0。失败原样记录，不先改代码；同一失败第二次才 raw rerun。

**Task acceptance:** 9223 身份无冲突、Goal 唯一、Evidence file 可读、仓库基线与两项本地基线均已记录。

### Task 2: 当前页面状态、UI Variant 与候选路径发现

**Purpose:** 在任何 ChatGPT 特定动作前取得本轮页面事实，并形成可剪枝的路径矩阵。

**Risk level:** read-only browser discovery；只打开并精确关闭本次标签。

- [ ] 第一次浏览器调用只做页面发现：

  ```bash
  ./browser-harness agent-pool run --browser "AgentPool-共享主浏览器-9223" --site chatgpt.com --mode read --account default <<'PY'
  tid = new_tab("https://chatgpt.com/")
  print(page_info())
  close_tab(tid)
  PY
  ```

  Success: page_info 的 URL 属于 chatgpt.com，并返回 `domain_skill_files`。如果出现 auth/paywall/dialog，只记录分类并按 Failure Recovery 处理。
- [ ] 在第二次网站调用之前，读取 page_info 返回的全部 Markdown 绝对路径；至少应包含当前 checkout 的 `agent-workspace/domain-skills/chatgpt/basic_ops.md`。如果路径指向其他 checkout，停止并记录 wiring conflict，不混用代码。
- [ ] 第二次调用使用一个 write lease，`new_tab` 后 `protect_tab`。只输出脱敏结构事实：URL path、语言、composer 是否存在/为空、可见稳定 `data-testid`、role、aria-label、checked radios、iframe target 是否存在；禁止输出 sidebar 既有标题和 body 全文。
- [ ] 对每个候选定位路径打分并记入 Evidence：stable testid/exact href=5，role+aria=4，结构+exact visible text=3，动态 class=1，固定坐标=0。每行必须记录 goal、path、precondition、postcondition、actions、result、failure mode、side effect、score。
- [ ] 只读/可逆探索以下路径：home、新聊天、composer、send button、模型 picker 两种 variant、推理强度、Header tabs、exact sidebar href/options、分享入口、长消息 toggle、主 scroller、Markdown editor selector、DR plus row、connector iframe 和 export 控件。菜单每次 Escape 后验证关闭；不得提交消息、创建分享、删除或启动 DR。
- [ ] 每次菜单或导航重渲染后重新查询元素。对核心定位进行 3 次开合/观察；出现率低于 3/3 不可作为唯一保留路径。
- [ ] 结束时恢复 `KGS-HOME`，unprotect 并只关闭本次 target。Agent Pool 9223 的本任务租约/锁应为空。

**Task acceptance:** `ui_variant` 已记录；全部当前能力都有可执行候选或明确缺失状态；没有私人内容或外部副作用。

### Task 3: 最小安全强化与单元测试

**Purpose:** 修复源码已知根因，并只为真实页面确认的 selector drift 增加确定性 fallback。

**Risk level:** reversible repository mutation。

- [ ] 在两个现有测试文件先增加最小失败测试，覆盖：
  1. State contract 的 home/conversation/generating/auth/paywall/dialog/unknown；
  2. switch/delete/share 只接受 exact ID，missing/ambiguous 不点击；
  3. close 只接受 task-owned exact target，read_shared 只关闭 new_tab 返回值；
  4. send button click count 最多 1，unknown 不重发；
  5. send_and_wait 必须看到本次发送后的新 assistant turn，旧回复不能误判完成；
  6. 每次 attempt 重新查询，旧 element/rect 不复用；
  7. DR connector absent=idle，mounted unreadable/empty=unknown；
  8. run_deep_research 调用共享 send_message 一次，unknown 立即停止；
  9. export 只接受快照后新建或变化的 non-empty Markdown。
- [ ] 运行 focused tests，确认新增测试因缺失行为失败，而非 fake 错误：`rtk uv run --with pytest pytest -q "tests/unit/test_chatgpt_domain_skill.py" "tests/unit/test_chatgpt_deep_research.py"`。
- [ ] 用 `apply_patch` 按 Interface Contracts 修改现有函数。复用 `_norm`、`_is_canonical_conversation_url`、`_conversation_id`、`_open_exact_conversation_options` 和同仓 Gemini 状态机；不得新增 class、dependency、配置文件或同义 public helper。
- [ ] `switch_chat`、`delete_chat`、`export_share_link` 共同复用 exact conversation normalizer；把 operation-specific 错误改成通用精确身份错误。`run()` smoke dispatch 同步新签名。
- [ ] task-owned tab 集合只记录本模块自己 `new_tab` 的返回值；`read_shared_conversation` 使用 try/finally 精确关闭自己的 share target；不得扫描 list_tabs 关闭。
- [ ] 所有 bounded loops 使用 `time.monotonic()`；固定 wait 仅用于渲染 settle，成功判断必须读取后置状态。
- [ ] DR runner 依赖已加载的 `send_message`；若 callable 不存在，在任何输入/发送前以 `precondition` 失败。
- [ ] focused tests 至 green，再运行：
  - `rtk python3 -m py_compile "agent-workspace/domain-skills/chatgpt/basic_ops.py" "agent-workspace/domain-skills/chatgpt/deep_research.py"`
  - `rtk python3 "scripts/verify_domain_skills.py"`
- [ ] 若同一错误两次不清楚，用 `rtk proxy uv run --with pytest pytest -vv "tests/unit/test_chatgpt_domain_skill.py" "tests/unit/test_chatgpt_deep_research.py"`；修根因，不放宽断言。

**Task acceptance:** focused tests/compile/registry 全绿；raw diff 只含五个允许文件；不存在 fragment mutation、tab scan close 或 DR 直接 click-send。

### Task 4: 普通会话全部能力真实闭环

**Purpose:** 在一个合成会话中用最终 Helper 逐项验证所有普通能力并保存可恢复证据。

**Risk level:** 用户已授权的真实账号写入；一个 write lease 串行。

- [ ] 生成 `run_id = "BH-CHATGPT-AUDIT-" + time.strftime("%Y%m%d-%H%M%S")`，立即写 Evidence。所有新会话、标题、消息和匹配都必须含该 exact run_id；不得读取或打印其他会话正文。
- [ ] 在一个 `agent-pool run --mode write` heredoc 中加载当前 checkout 的 `basic_ops.py`，创建并 protect task-owned tab，证明 `KGS-HOME`。不得设置 `BU_CDP_URL`。
- [ ] 记录 picker 中原模型和原推理强度的 exact checked radio。选择一个当前可见、无升级/付款提示的不同项并重新打开验证 checked，再精确恢复原项并验证。没有安全替代项时记录 `blocked_by_entitlement`，不点击价格或升级入口。
- [ ] Header tab 执行“聊天→工作→聊天”一次，每一步重新定位 exact radio 并验证 aria-checked；不进入任何工作区管理页面。
- [ ] 普通消息使用 `f"{run_id}-TURN-001。只回复：{run_id}-ACK-001"`。只调用一次 `send_and_wait`；验证返回 exact canonical URL、新 user turn、新 assistant turn，ACK 仅出现一次。unknown 时按恢复规则检查一次，不重发。
- [ ] 长消息使用由 `run_id`、`LONG-START`、700 个字母 `A`、`LONG-END` 拼成的纯合成文本，要求只回复 `f"{run_id}-ACK-LONG"`。发送一次后验证 toggle；`toggle_user_message_expand` 只切换目标消息，`expand_all_user_messages` 不收起已展开项。
- [ ] 为滚动/分页制造的最后一条消息要求输出从 `f"{run_id}-LINE-001"` 到 `f"{run_id}-LINE-080"` 的 80 行列表。只发送一次。验证普通 scrollTop 变化；PageUp/PageDown 后 `moved` 与当前真实边界一致；conversation_text 含首尾 marker 且角色顺序正确。
- [ ] Markdown block 能力只做一次最小尝试：要求 ChatGPT “在可用的写作/Canvas Markdown 编辑区创建标题为 run_id 的三行 Markdown；若界面不支持则直接文字回复 UNSUPPORTED”。如果真实页面生成已声明 editor selector，`read_markdown_block_summary` 必须读取完整标题和第三行；若只返回 UNSUPPORTED 或没有 block，记录 `not_available_in_current_variant`，文档不得宣称本轮通过。
- [ ] 用 exact canonical ID 重命名为 `f"{run_id}-RENAMED"`，离开并回到 exact URL，验证 sidebar exact href 的标题持久化。再用 `switch_chat(exact_url)` 循环 3 次，每次 exact URL、run marker、composer 可用。
- [ ] 创建公开分享前验证 current exact ID 和全部 turns 只含合成内容。`export_share_link(exact_url)` 第一次最多触发一次创建；再调用一次只能返回同一 URL 且 `created=False`。actual URL 只写 Evidence；Domain Markdown 只写 SHA-256 与已验证时间。
- [ ] `read_shared_conversation` 连续两次读取同一 share URL；每次只关闭自己的 new target；验证 TURN-001、ACK、LONG-START/LONG-END、LINE-001/LINE-080 顺序和 run_id，不要求打印全文。
- [ ] `close_extra_tab` 单独用一个本轮新建的 `about:blank` task-owned target 验证；未知 target 和其他 owner protected target 必须在 close 前失败。
- [ ] 删除前把 exact conversation ID、canonical URL、renamed title、run marker、share URL hash 写入 Evidence。

> [!DANGER]
> **Human approval required — approval already recorded; do not widen scope.**
> Action: 调用 Domain Skill 的精确会话删除能力，仅删除本步骤 Evidence 中的普通测试 conversation ID。
> Why required: 验证当前已声明的删除能力和普通会话完整生命周期。
> Blast radius: 一个本轮创建且只含合成内容的 ChatGPT 测试会话；不涉及既有会话、分享链接撤销或账号设置。
> Preconditions/backups: exact ID、canonical URL、run marker、renamed title 四项一致；分享内容已读回；证据已保存。
> Rollback or irreversibility: ChatGPT 会话删除可能不可恢复；公开分享链接是否随源会话失效必须按真实结果记录，不能假设。
> Approval request: 是否仅删除本轮创建、精确 ID 匹配的普通测试会话？已答：是，用户在原始需求“已确认的副作用授权”中明确授权。

- [ ] 只在上述四项一致时执行 `delete_chat(exact_url, confirm=True)`；验证 exact sidebar row 消失。任一项不一致则禁止删除，记录 `destructive_scope_violation`，普通闭环不通过。
- [ ] 恢复 `KGS-RESTORED`，unprotect 并只关闭本次自建主标签。检查 9223 本任务 lease/write lock 为空。

**Task acceptance:** 所有普通能力都有 pass、fail 或 current-variant unavailable 的事实结论；普通发送/等待/读取、exact rename/switch、分享/read 和 exact delete 必须 pass；模型/强度/header 已恢复；无重复发送和无既有数据接触。

### Task 5: Deep Research 一次配额完整闭环

**Purpose:** 用最多一次真实提交验证最终 DR 状态机、报告读取和新鲜下载。

**Risk level:** 用户已授权的一次付费配额型外部动作和一个测试会话删除。

- [ ] 先在 fresh task-owned ChatGPT tab 加载 `basic_ops.py` 和 `deep_research.py`，证明 KGS-HOME；记录已有 `deep-research-report*.md` 的 path、mtime_ns、size 元数据，不读取旧报告内容。
- [ ] 先做 arm→验证 pill→disarm→验证 pill 消失的可逆测试。再重新 arm 一次准备正式提交；不得通过再次点 menu row 取消。
- [ ] 正式问题固定为：`f"{run_id}-DR：请用深度研究说明 Python 标准库 functools.lru_cache 的 maxsize=None 与 maxsize=128 在缓存淘汰行为上的差异；不超过 5 条要点，并附来源。"`。只调用一次 `run_deep_research`，禁止任何外层重试。
- [ ] 每个 poll 保存 state、len、marker booleans、elapsed，不保存报告全文。必须实际观察 planning、running、done 中页面出现的状态；某状态过快跳过时记录 `not_observed`，不能补造。
- [ ] connector absent 才记 idle；mounted 但 nested iframe 不可读为 unknown。unknown 或 timeout 时检查当前 conversation 和 connector 一次，禁止再次提交；保存最后观察并终止 DR mutation。
- [ ] done 必须满足当前真实 completion markers、停止研究信号消失、report non-empty。随后导出一次 Markdown；新文件必须相对 pre-snapshot 为新建或发生变化、size>0，并包含 run_id 或问题主题及非空正文。
- [ ] 记录 DR exact conversation ID、canonical URL、submission_count=1、配额/付费 UI 是否出现、状态序列、report text SHA-256、download absolute path/mtime_ns/size。actual report content 不写 Domain Markdown。
- [ ] 删除前确认 exact ID、URL、run marker 和 DR done/export evidence 四项一致。

> [!DANGER]
> **Human approval required — approval already recorded; do not widen scope.**
> Action: 调用 Domain Skill 的精确会话删除能力，仅删除本步骤 Evidence 中的 Deep Research 测试 conversation ID。
> Why required: 清理本轮测试数据并验证删除能力对 DR 测试会话同样遵守精确身份边界。
> Blast radius: 一个本轮创建且只含合成问题和研究报告的 ChatGPT 测试会话；已下载 Markdown 文件保留。
> Preconditions/backups: exact ID、canonical URL、run marker、done/export evidence 四项一致；下载产物已记录。
> Rollback or irreversibility: ChatGPT 会话删除可能不可恢复；本地 Markdown 报告保留作为结果证据。
> Approval request: 是否仅删除本轮创建、精确 ID 匹配的 DR 测试会话？已答：是，用户在原始需求“已确认的副作用授权”中明确授权。

- [ ] 只在四项一致时执行精确删除并验证 row 消失；否则不删除并记录安全失败。
- [ ] unprotect 并关闭自己的 DR tab；检查 9223 本任务 lease/write lock 为空。

**Task acceptance:** `submission_count` 精确为 1；DR done、报告读取、新鲜 Markdown 导出和 exact delete 通过；若账号配额不足或出现付费/认证墙，记录 external blocker，绝不伪造闭环或消费第二次。

### Task 6: 路径剪枝、文档与行为一致性

**Purpose:** 把真实事实固化到 Domain Skill，删除无价值动作和未经验证的声明。

**Risk level:** reversible repository mutation。

- [ ] 更新 `basic_ops.md` verified date 为实际最终 E2E 日期；只有 Task 4/5 已通过的能力可标 verified。current-variant unavailable 或 external blocker 必须原样声明。
- [ ] Invocation 全部使用当前 checkout 的 `./browser-harness agent-pool run`、stdin heredoc、managed browser name；删除全局 binary、显式 `BU_CDP_URL` 和 `-c` 示例。
- [ ] 写入 State/Error contract、每个原子能力的 input/precondition/intermediate/success/unknown/failure/retry/recovery、Known-Good States、exact identity、task-owned tab 和 unknown-no-retry 规则。
- [ ] 写入能力验证矩阵，包含实际时间、UI Variant、结果、最小证据和测试覆盖；不得写 actual share URL、账号标识、私人内容或报告全文。
- [ ] 写入候选路径表。保留路径必须有成功结果和后置条件；淘汰固定坐标、模糊标题 mutation、global first options、tab URL scan、Return send、重复设置、无条件 sleep、main-page DR 文本判断、旧下载复用和非幂等重放。
- [ ] 对每个目标按 correctness、side-effect safety、success、verifiability、adaptability、actions 顺序评价；动作少不能覆盖前五项。
- [ ] 删除代码里未被最终 E2E、文档或测试使用的新增 helper/fallback；安全验证、unknown 状态、exact ID、download freshness 和 tab ownership 不得为追求短代码删除。
- [ ] 运行 focused tests、compile、Domain verifier。检查 Markdown 的 function signatures 与 Python 一致。

**Task acceptance:** 文档声明与 Evidence/代码一致；所有 capability 不再 pending；保留与淘汰路径都有事实依据；无推测性能力。

### Task 7: 最终验收与 Goal 完成

**Purpose:** 证明实现、真实行为、安全边界和文档同时满足要求。

**Risk level:** safe/read-only verification。

- [ ] 重新运行 Test Matrix 全部命令并把 fresh exit code/test count 写入 Evidence。
- [ ] 原始审计：
  - `RTK_DISABLED=1 git diff --check`
  - `RTK_DISABLED=1 git diff --stat`
  - `RTK_DISABLED=1 git diff -- "agent-workspace/domain-skills/chatgpt/basic_ops.py" "agent-workspace/domain-skills/chatgpt/deep_research.py" "agent-workspace/domain-skills/chatgpt/basic_ops.md" "tests/unit/test_chatgpt_domain_skill.py" "tests/unit/test_chatgpt_deep_research.py"`
  - `RTK_DISABLED=1 git status --short`
- [ ] Scope check：除计划文件和五个允许实现文件外，本任务没有新 diff；若启动前已有无关改动，它们保持不变且不归因于本任务。
- [ ] 搜索并排除：固定坐标 fallback、global first options、fragment mutation、tab URL scan close、第二次 send、无界循环、禁用测试、调试输出、secret/credential/account/private content、未完成占位语和生成垃圾。
- [ ] Requirement Traceability 的 AC1–AC22 每行都有 passing evidence；普通闭环和 DR 闭环是 mandatory，不得用单元测试或历史记录替代。
- [ ] 最终 Fleet audit 无 conflict；9223 本任务 leases/write locks 为空；9224/9225/9226 和个人 Chrome 未触碰；本轮 task tabs 全部精确关闭。
- [ ] 确认没有分支、commit、push、PR、发布或依赖变化；保留 Evidence JSON、actual share URL 和 DR download path 供用户复核。
- [ ] 更新 Progress Ledger。全部通过后才调用实时 `update_goal(status="complete")`，最终报告只列变更文件、真实能力结果、测试数、Evidence path、share artifact、DR download path 和残余限制。

**Task acceptance:** Final Acceptance Gate 全部通过且 Goal complete。

## Test Matrix

| Layer | Requirement/risk | Exact command or procedure | Expected result | Failure evidence |
| --- | --- | --- | --- | --- |
| Baseline | 当前 tests/registry | Task 1 两条命令 | exit 0 或记录真实既有失败 | raw stdout/stderr |
| Unit focused | 状态、exact ID、unknown、tab、DR | `rtk uv run --with pytest pytest -q "tests/unit/test_chatgpt_domain_skill.py" "tests/unit/test_chatgpt_deep_research.py"` | exit 0；全部 collected tests pass | 第二次用 `rtk proxy uv run --with pytest pytest -vv "tests/unit/test_chatgpt_domain_skill.py" "tests/unit/test_chatgpt_deep_research.py"` |
| Syntax | 两个 Python helper | `rtk python3 -m py_compile "agent-workspace/domain-skills/chatgpt/basic_ops.py" "agent-workspace/domain-skills/chatgpt/deep_research.py"` | exit 0，无 output | stderr |
| Wiring | Domain registry/runtime link | `rtk python3 "scripts/verify_domain_skills.py"` | `PASS` 且 chatgpt Markdown 可发现 | exact FAIL line |
| Full regression | 邻接 Browser Harness | `rtk uv run --with pytest pytest -q` | exit 0；无 failed/error | 第二次 raw verbose |
| Browser discovery | Skill discovery | Task 2 first call | page_info 返回当前 checkout 的全部 skill files | page_info 脱敏结构 |
| E2E ordinary | AC4–16、19–20 | Task 4 单租约步骤 | mandatory ordinary path 全 pass；unknown click 不重放 | Evidence capability/action records |
| E2E DR | AC4、13、17–18、20 | Task 5 单租约步骤 | one submission、done、fresh export、exact delete | state sequence、file metadata |
| Safety | 私人数据与共享浏览器 | raw diff、Fleet、tab/ID assertions | 无既有会话/其他浏览器/secret；本任务资源清空 | Evidence errors/cleanup |

## Failure Recovery and Autonomous Continuation

1. 中断或 compaction 后：`get_goal` → 重读计划/Skills/Lessons/Evidence → raw `git status`/diff → Fleet audit/status → 检查 partial external state → 从第一个未完成且前置条件满足的步骤继续。
2. 9223 busy：让 Agent Pool 排队；单次 wait timeout 后只查 status。不得切换 9224/9225/9226、不得直连 CDP、不得 `reap --apply`。
3. Fleet conflict/unmanaged/stopped：停止网页任务并记录 exact conflict；不得修 Fleet 生命周期。继续可安全完成的本地审计，但 mandatory E2E 未通过时 Goal 不 complete。
4. auth/MFA/验证码/账号选择/授权同意：关闭自己的 task tab，停止外部动作；不得输入、选择、绕过或请求离席用户即时处理。
5. paywall/quota：记录可见分类；不购买、不升级、不第二次尝试 DR。普通能力可继续，DR mandatory 未通过则 Goal 不 complete。
6. selector 失败：重新 `page_info()`，打印脱敏 compact AX/DOM；每种确定性策略最多一次，顺序为 stable testid/exact href → role/aria → exact structural text。固定坐标只可诊断，不得固化。
7. 页面重渲染：丢弃旧 element/backendNodeId/rect，重新观察 state 和重新定位。不得对旧坐标重放。
8. 发送或分享 result unknown：先只读检查 canonical URL、turn IDs、composer、toast/dialog、clipboard/已分享状态。已有结果则继续读取；仍不确定则终止该 mutation，永不再次触发。
9. rename partial：只在 exact row 仍存在且标题明确不同、现有 bounded retry 合同允许时重试一次；missing/ambiguous 不重试。
10. delete partial/unknown：只读查询 exact ID row；row absent 视为结果已发生，row present 保留失败；不得第二次点击删除。
11. DR unknown/timeout：读取 connector 一次和 exact conversation once；不再次提交。已有 done markers 可继续 export；否则保留 last observation。
12. export unknown：比较 pre/post snapshot；新鲜 non-empty file 已存在则复用；没有则不再次点击导出，记录 unknown。
13. tests 同一错误两次或 RTK 不完整：使用 Test Matrix 的 raw verbose 方式；只修任务引入或本来就在目标路径的根因，不接受红 suite。
14. 编辑器工具失败：先核验实时权限；若 exact path 可写，使用同一 authorized editing tool 重试一次。不得用 shell 重定向、Python 写文件或扩大权限规避。
15. 不得通过 reset、clean、checkout、删除文件、切分支或新 worktree 恢复。保留 partial work 和 Evidence，下一 Goal turn 继续。

## Final Acceptance Gate

- [ ] AC1–AC22 每行都有当前轮、可观察、可追踪证据。
- [ ] 普通 mandatory 闭环通过；每次非幂等 action 的 activation count 为 1。
- [ ] Deep Research mandatory 闭环通过；真实 quota submission count 为 1。
- [ ] 全部声明能力有明确结论；未出现的 Markdown block variant 被诚实标为 unavailable，不宣称 verified。
- [ ] 原模型、推理强度、Header 聊天状态、菜单和弹层已恢复。
- [ ] 仅删除两个本轮 exact test conversation；没有接触既有会话。
- [ ] 公开分享只含合成内容；actual URL 仅在 Evidence，Domain 文档只存 hash。
- [ ] DR Markdown 是 pre-snapshot 后的新鲜 non-empty file，absolute path 已记录。
- [ ] focused、syntax、registry、full regression 全部 fresh pass。
- [ ] 完整 raw diff 只含计划文件和五个允许实现文件；无 secrets、私人内容、禁用测试、调试代码或无关重构。
- [ ] Browser Fleet 无 conflict；9223 本任务 lease/write lock 为空；本轮 tabs 全部精确关闭；其他浏览器未触碰。
- [ ] 没有 Git 分支、commit、push、PR、发布、依赖或 Browser Harness Core 变化。
- [ ] Evidence 与 Progress Ledger 完整；没有仍需执行的必做动作。
- [ ] 只在以上全部成立后调用 `update_goal(status="complete")`。
