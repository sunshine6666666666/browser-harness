# Gemini 网页版高强度测试与 Domain Skill 强化实施计划

> **Executor:** 低能力自主执行模型，预期运行数小时。它没有本对话上下文，只能逐字执行本文件。禁止自行扩大范围、禁止在共享 `main` 工作区改代码、禁止向离席用户索要权限或常规决策。

**Goal:** 在独立 Git worktree 中高强度吃透当前登录态 Gemini 网页版的普通聊天、长会话读取、折叠内容展开、精确会话切换、公开分享与分享页读取流程；把真实验证过的最小 Helper 和操作规范固化到 Gemini Domain Skill，完成本地与真实浏览器验收后推送功能分支并通过本机 `gh` CLI 创建一个只请求合并、绝不自动合并的 PR。

**Done when:** 以下条件全部成立：独立分支 `codex/gemini-web-audit-20260826` 中只包含本计划允许的 Gemini Helper、Markdown 和测试改动；普通聊天发送不存在重复提交；同一合成会话的完整读取至少连续通过 3 次；长用户消息可展开；公开分享只包含合成内容，同一会话重复取链接 3 次得到同一 URL；分享页能按顺序读回首尾标记；精确 URL 会话切换连续 5 次正确；当前模型与临时 UI 状态已恢复；全量 278 个基线测试及新增测试全部通过；Domain registry 校验通过；Agent Pool 最终 `leases=[]` 且 `write_locks={}`；共享主工作区的分支、HEAD 和原有未跟踪文件与任务前一致；功能分支已推送；GitHub 上存在一个目标为 `main` 的打开状态 PR；没有执行本地合并、远端合并、删除、付费、反馈、Drive、媒体生成或凭证操作。

**Workspace root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Repository root:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Isolated worktree:** `/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826`

**Feature branch:** `codex/gemini-web-audit-20260826`

**Plan file:** `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-08-26-gemini-web-high-intensity-audit.md`

**Evidence file:** `/tmp/browser-harness-gemini-audit-20260826.json`

**Target environment:** 本机开发环境；macOS Darwin 24.6.0 arm64；zsh 5.9；Python 3.12.13；uv 0.11.7；受管 Chrome `AgentPool-共享主浏览器-9223`；Gemini 中文 UI。

**Execution mode:** `unattended`。用户会离开电脑。任何步骤都不得让用户授权、扫码、输入密码、输入验证码、确认继续或选择常规方案。

**Live permission contract:** 计划作者于 2026-08-26 08:16–08:17 CST 核验：执行者预期为 `workspace-write` + `on-request` + `approvals_reviewer=auto_review`；主仓库与 `/tmp` 可写，网络和主仓库外路径需要精确范围的 Auto Review；Auto Review 不等于 Full Access。`./browser-harness agent-pool run`、Browser Fleet `audit` 和 `git fetch origin main` 的精确只读调用已在当前合同下获批并成功。执行者必须在启动时重新核验，不得假定此合同永久不变。

**Architecture/approved approach:** 共享 `main` 只作为只读基线，不承载弱模型的中间态。先从 `origin/main` 创建固定兄弟 worktree 和 `codex/` 功能分支，全部代码、测试、提交都在 worktree 内完成。浏览器操作统一通过 Agent Pool 的 9223 默认入口串行执行；先发现 Domain Skill，再读完所有返回的 Markdown，之后才进行网站操作。Ponytail 原则是复用 ChatGPT 已验证的分享、分页和折叠模式，但只把 Gemini 真实页面连续验证通过的最小能力写入代码。

**Tech stack:** Python 3.12；`cdp-use==1.4.5`、`fetch-use==0.4.0`、`websockets==15.0.1`；pytest 由 `uv run --with pytest` 临时提供；Browser Harness 当前 checkout 的 `./browser-harness`；无新增依赖。

## Required Skills

- `writing-plans`
  - SKILL.md: `/Users/yelin/.codex/skills/writing-plans/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/writing-plans/references/lessons.md`
  - Use for: Goal、权限预检、进度账本、失败恢复和最终验收。
- `openai-docs`
  - SKILL.md: `/Users/yelin/.codex/skills/.system/openai-docs/SKILL.md`
  - Lessons: `none found`
  - Use for: 执行开始时刷新 Auto Review、sandbox 和 Goal 的官方契约。
- `ponytail:ponytail`
  - SKILL.md: `/Users/yelin/.codex/plugins/cache/devkeeper-ponytail-local/ponytail/4.8.4/skills/ponytail/SKILL.md`
  - Lessons: `none found`
  - Use for: 先复用、后最小实现，不为未验证页面预留抽象或依赖。
- `browser-fleet-manager`
  - SKILL.md: `/Users/yelin/.codex/skills/browser-fleet-manager/SKILL.md`
  - Lessons: `/Users/yelin/.codex/skills/browser-fleet-manager/references/lessons.md`
  - Use for: 只读核验 9223 的名称、端口、Profile 与运行状态；不得启动、停止、迁移或删除浏览器。
- `browser-harness`
  - SKILL.md: `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`
  - Lessons: `none found`
  - Use for: Agent Pool、页面发现、后台标签、CDP、租约与 Domain Skill 规范。

## Official contract evidence

计划作者于 2026-08-26 获取并打开以下官方页面：

- `https://learn.chatgpt.com/docs/sandboxing`：sandbox 决定自主可操作的文件、网络与命令边界；越界才进入 approval 流程。
- `https://learn.chatgpt.com/docs/sandboxing/auto-review`：Auto Review 只替换审批者，不扩大可写根、网络或权限；拒绝后不得绕过，只能使用实质更安全的路径。
- `https://learn.chatgpt.com/docs/long-running-work`：长任务必须定义结果、约束与可验证完成标准。
- `https://developers.openai.com/api/docs/guides/latest-model`：多步任务要明确授权边界和成功标准，外部、破坏性、付费或扩展范围动作需要额外边界。

## Applicable Rules

- `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`：当前 checkout 只能用 `./browser-harness`；Agent 只修改 `agent-workspace/` 内的 Helper/Domain Skill；保持最小 diff。
- `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`：遵循 `AGENTS.md`，Browser Harness 必须使用当前 source wrapper。
- 本任务宿主提供的 Browser Harness 规则：CLI 不支持 `-c`；多行脚本只可经 stdin heredoc/pipe；第一次打开网站只打印 `page_info()`，结束调用后读取全部 `domain_skill_files`，之后才能做网站特定操作；改 Domain Skill 后运行 `python3 scripts/verify_domain_skills.py`。
- RTK 规则：普通搜索、Git、测试在原命令前加 `rtk`；安全审计、完整 diff、重复/竞态异常必须用 `RTK_DISABLED=1` 或 `rtk proxy` 原始复核。
- 文件编辑：使用 `apply_patch`；保存无关用户改动；禁止 `git reset --hard`、`git checkout --`、`git clean`、`rm -rf`。
- Git 隔离：共享主工作区只读。用户在本任务中明确授权创建独立 worktree、功能分支、局部提交、推送功能分支和创建 PR；未授权任何本地/远端合并、强推、删分支、删 worktree或修改 `main`。

## Scope

- In scope:
  - 当前 Gemini 普通聊天：新聊天、合成消息发送、稳定等待、回复动作控件、长用户消息展开、虚拟化会话分页与完整读取。
  - 精确会话身份：只接受当前合成会话的精确 `https://gemini.google.com/app/{conversation_id}` URL 或 conversation ID，不按模糊标题修改/切换。
  - 普通会话分享：创建合成会话的公开链接、重复复制同一链接、打开自建分享链接并读取首尾内容。
  - 最新首页入口的只读/可逆清单：临时对话、Spark、笔记本、视频、库、模型选择器、上传和工具；只固化与聊天主流程直接相关且真实通过的能力。
  - 一个 1 KB 以内、无敏感信息的本地 `.txt` 文件的“附加后移除”循环；文件不得随消息发送。
  - Gemini `basic_ops.py`、`basic_ops.md` 与对应单元测试的最小修复。
  - 单线程串行真实测试；每次浏览器调用使用 Agent Pool 租约。
- Out of scope:
  - 读取、分享、重命名、归档或删除任何已有私人聊天。
  - 删除合成聊天、撤销公开链接、清空历史。删除/撤销不是本次验收要求。
  - Google Drive、导出到 Google Docs、账号设置、订阅升级、支付、验证码、密码、MFA。
  - 图片、视频、音乐生成；发送反馈、踩/赞、举报；任何可能对第三方产生通知的操作。
  - 新 Deep Research 配额任务。只允许对当前 UI 做入口清单；若本任务自建会话未包含完成报告，不做真实 DR。
  - Spark、笔记本、视频、库的业务功能实现；本轮只记录入口与是否影响聊天主流程。
  - Browser Harness Core、Agent Pool、Daemon、registry、依赖或 lockfile 改造。
- Allowed side effects:
  - 创建一个或极少量标题自动生成的合成 Gemini 普通聊天；发送下文规定的无敏感测试提示。
  - 为该合成聊天创建公开分享链接。链接内容只能是测试标记与合成文本。
  - 在合成聊天中切换模型后恢复原模型；开关菜单、临时对话后恢复普通新聊天。
  - 上传后移除 `/tmp/bh-gemini-attachment-20260826.txt`，不随消息发送。
  - 创建 worktree/功能分支、修改 3 个允许文件、提交、推送功能分支、创建一个 PR。
- Human-gated side effects:
  - 本计划没有需要执行期人类批准的必做动作。若页面突然要求密码、MFA、付费、账号选择或验证码，禁止向用户提问、禁止输入或绕过；按“失败恢复”处理，不得把这些动作升级为本计划范围。

## Permission Feasibility

| 资源/动作 | 实时能力 | 授权 | 无监督路径 |
| --- | --- | --- | --- |
| 读共享主仓库 | sandbox 内允许 | 用户允许 | 直接读；只记录基线 |
| 创建兄弟 worktree | 需要精确 Auto Review | 用户本轮明确要求 | `git worktree add` 精确路径；不得扩大到其他目录 |
| 写 worktree | 可能需要 Auto Review | 用户本轮明确要求 | 只用绝对路径和 `apply_patch`；不得写共享 main 文件 |
| `/tmp` 证据 | sandbox 可写 | 用户允许 | 固定两个测试文件，不含账号/邮箱/聊天隐私 |
| Browser Fleet `audit` | `ps` 需要 Auto Review | 只读核验已授权 | 精确脚本 `audit`；不调用 lifecycle 子命令 |
| 9223 Agent Pool | 需要 Auto Review 执行本机进程/CDP | 用户明确授权真实测试 | 每次 `agent-pool run`；同一浏览器自动串行 |
| Gemini 外部写入 | 浏览器登录态可用 | 仅合成聊天、合成分享、合成附件已授权 | write lease；任何非合成内容立即拒绝 |
| Git fetch/push | Git credential helper 可用；fetch 已验证 | 功能分支 push 已授权 | 只推 `codex/gemini-web-audit-20260826`，无 force |
| GitHub PR | 本机 `gh` 已通过 keyring 登录，真实网络复核具有 `repo` scope | 创建 PR 已授权 | `gh pr list/create/view`；9223 只用于 Gemini，禁止访问 GitHub |
| 合并 PR / 改 main | 技术上可能可用 | 未授权 | 永远不执行 |

## Goal Contract

- 启动时先重读 `openai-docs`，刷新上述 4 个官方页面并把获取时间、URL、实时 permission profile 与 Goal 工具 schema 写入 Progress Ledger。官方页面不可达时可使用本计划已记录契约完成本地预检，但不得降低 sandbox 或打开 Full Access。
- 检查执行运行时实际暴露的 Goal 工具。若存在 `create_goal`，第一次只调用一次，目标文本必须与本文件 **Goal** 完全一致，不设置 token budget。若已有 Goal，调用 `get_goal` 并恢复，不创建重复 Goal。
- 不把 `/goal` 当作工具调用。只按运行时真实 schema 调用 `create_goal`、`get_goal`、`update_goal`。
- 每次恢复：读取 Goal、从头重读本计划和所有 Required Skills/Lessons、读取 Progress Ledger、检查共享主仓库和 worktree 状态，再从第一个未完成且前置条件满足的步骤继续。
- 任何常规失败都按本计划既定 fallback 处理，不问用户。只有所有必做真实路径因外部登录/权限变化不可执行时才保留 Goal 和完整证据；不得伪报完成。`blocked` 只在当前运行时 Goal 工具规则允许时使用。
- 只有最终验收全部通过且 PR 已打开，才调用 `update_goal(status="complete")`。

## Current-State Evidence

- 共享仓库当前分支：`main`。
- `HEAD` 与 `origin/main`：`3474847b45828992d414a4536310056e2c3941e8`。
- 原有未跟踪路径：`.understand-anything/`、`agent-workspace/recordings/`；二者属于用户，禁止修改、暂存或删除。
- Worktree 基线：只有主工作区；`codex/gemini-web-audit-20260826` 分支不存在。
- CodeGraph：68 files、1644 nodes、3937 edges，索引最新。
- 测试：`rtk uv run --with pytest pytest -q` 为 `278 passed in 0.77s`。
- Domain registry：`PASS registry=102 skills`，runtime symlink 指向当前仓库 Domain Skill。
- Browser Fleet：9223 为 `AgentPool-共享主浏览器-9223`，running/health ok；9224/9225/9226 属于其他任务，禁止选择。
- Agent Pool：`leases=[]`，`write_locks={}`。
- Gemini 最新只读首页：`https://gemini.google.com/app`，中文 UI，已登录；当前可见普通聊天 composer、Flash 模型、临时对话、Spark、笔记本、视频、库等入口。此计划不保存账号名或邮箱。
- `page_info()` 为 Gemini 返回：
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/gemini/basic_ops.md`
  - `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/google/search.md`
- 当前 Gemini Helper 缺口：`conversation_text()` 只读当前渲染正文；没有普通聊天公开链接 helper；没有完整虚拟化 transcript reader；`ensure_gemini_tab()` 会扫描并切换到任意既有 Gemini 标签，不符合共享浏览器“只操作自建标签”原则。
- ChatGPT 可复用模式位于 `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/chatgpt/basic_ops.py`：`export_share_link`、`read_shared_conversation`、`page_conversation`、`toggle_user_message_expand`、`expand_all_user_messages`。只复用状态机和安全原则，不复制 ChatGPT 选择器。
- Git：`git fetch origin main` 已成功；Git credential helper 可读远端。
- GitHub：本机 `gh auth status` 已在真实网络权限下复核为已登录，HTTPS Git 协议，具有 `repo` scope。沙箱内曾因网络受限产生假失败；执行时必须用同一只读命令在真实网络权限下核验。禁止让 9223 访问 GitHub。

## Requirement Traceability

| Requirement | Source | Implemented by | Verified by |
| --- | --- | --- | --- |
| 不影响共享 main | 用户本轮明确要求 | Task 1、Task 8 | 主工作区前后 HEAD/branch/status 字节级对比 |
| 高强度测试最新 Gemini 网页版 | 用户要求 | Task 2、Task 6 | 控件矩阵 + 重复次数 + 真实 E2E 证据 |
| 聊天发送稳定、不重复 | 用户目标与现有安全规则 | Task 3、Task 6 | unknown 不重试测试 + 唯一 turn 标记 |
| 长会话完整读取与折叠展开 | 用户重点 | Task 3、Task 6 | 三次完整 transcript 哈希一致，首尾/顺序/turn 数一致 |
| 普通聊天分享与分享页读取 | 用户重点 | Task 4、Task 6 | 单次创建、三次同 URL、分享页首尾标记 |
| 弱模型可无人监督执行 | 用户要求 | 全计划 | Goal、Progress Ledger、明确 fallback、无执行期提问 |
| 形成更好的 Helper 文档 | 用户要求 | Task 5 | Python/Markdown 同步、最新验证日期与能力边界 |
| 只请求合并 | 用户本轮明确要求 | Task 8 | 功能分支 push + 打开 PR；main 未改变；无 merge |

## File Map

| Action | Absolute path | Repository-relative path | Responsibility | Depends on / consumed by |
| --- | --- | --- | --- | --- |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826/agent-workspace/domain-skills/gemini/basic_ops.py` | `agent-workspace/domain-skills/gemini/basic_ops.py` | 共享标签安全、确定发送、分页/展开、完整会话、普通分享、分享页读取 | Browser Harness 执行脚本、`basic_ops.md`、单元测试 |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826/agent-workspace/domain-skills/gemini/basic_ops.md` | `agent-workspace/domain-skills/gemini/basic_ops.md` | 当前 UI、最优路径、调用示例、限制、真实验证证据 | Domain discovery 返回给后续 Agent |
| Modify | `/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826/tests/unit/test_gemini_domain_skill.py` | `tests/unit/test_gemini_domain_skill.py` | 点击次数、unknown、标签所有权、分页、去重、分享 URL 与关闭精确标签回归 | pytest |
| Create temporary | `/tmp/browser-harness-gemini-audit-20260826.json` | none | 可恢复的脱敏运行证据 | Tasks 2–8 |
| Create temporary | `/tmp/bh-gemini-attachment-20260826.txt` | none | 1 KB 内合成附件 | Task 6 |
| Create temporary | `/tmp/browser-harness-gemini-pr-body-20260826.md` | none | GitHub PR 正文 | Task 8 |
| Preserve | `/Users/yelin/Developer/agent-tools/browser-harness` 除本计划文件外全部内容 | none | 多 Agent 共享 main 工作区 | 不得编辑/切换/提交 |

## Interface Contracts

以下是必须达到的接口，不得另建类、框架、依赖或配置层。若真实 UI 已由现有函数满足，修现有函数，不新增同义 helper。

- `ensure_gemini_tab(url: str = GEMINI_HOME) -> dict[str, Any]`
  - Inputs: 只允许 `https://gemini.google.com/app` 或其 `/app/{conversation_id}` 子路径；`conversation_id` 必须由当前 Gemini URL 实际读取。
  - Output: 当前 task-owned Gemini target 的 `target_id`、`url` 和 `opened`。
  - Errors: 非 Gemini URL、登录墙、无法得到可用 composer。
  - Side effects: 当前附着标签已是 Gemini 时复用；否则只 `new_tab(url)`。禁止扫描并切换到其他已有 Gemini 标签。

- `send_message(text: str, evidence_timeout: float = 10.0) -> dict[str, Any]`
  - Inputs: 非空文本；composer 初始为空。
  - Output: `status` 只能是 `definitely_sent` 或 `unknown`；成功时含 canonical URL、composer_empty、匹配的 user turn 证据。
  - Errors: 发送前 selector/文本不匹配直接 raise。
  - Side effects: 发送按钮最多点击一次；`unknown` 永不自动重发。

- `page_conversation(direction: str = "down", steps: int = 1, wait_s: float = 0.8) -> dict[str, Any]`
  - Inputs: direction 仅 `up|down`，steps >= 1。
  - Output: before/after scroll position、rendered turn count、`moved`。
  - Side effects: 只聚焦主会话 scroller 并发送 PageUp/PageDown；不激活 Chrome 可见标签。

- `conversation_turns(limit_per_turn: int = 20000) -> list[dict[str, Any]]`
  - Output 每项固定为 `{"role": "user"|"assistant", "text": str, "id": str|None}`，按当前 DOM 时间顺序。
  - 必须删除 UI action 文本，不得把“复制/分享/赞/踩”等按钮文字混进正文。

- `expand_all_user_messages() -> int`
  - 只点击当前为“展开/Show more”的控件；已展开内容不得再次收起；返回本次展开数。

- `full_conversation(max_pages: int = 120, wait_s: float = 0.8) -> dict[str, Any]`
  - 先分页到顶部，再逐页向下收集；每页先展开长用户消息，再读 turns。
  - Output: `status="complete"`、`turns`、`text`、`pages`、`url`；只有到顶/到底均有连续两次 `moved=False` 且无新 turn 才能 complete。
  - 去重优先使用页面稳定 message/turn ID。若当前 UI 没有稳定 ID，使用相邻页“最长后缀/前缀 turn 序列重叠”合并，禁止简单按文本 set 去重，因为两个合法 turn 可能文本相同。
  - 达到 max_pages 仍未到底必须 raise，不得返回伪完整结果。

- `export_share_link() -> dict[str, Any]`
  - 前置：当前 URL 必须是本任务合成会话的 canonical `/app/{conversation_id}`；正文必须包含本次 run ID。
  - Output: `status="shared"`、`url`、`created`、`conversation_url`。
  - 只接受 `https://g.co/gemini/share/{share_id}` 或真实页面证明的新 Gemini 官方分享 URL；`share_id` 必须来自本次 clipboard。若前缀变化，先在 live evidence 记录 host/path，再把精确 allowlist 写入代码和测试。
  - 创建公开链接动作最多一次；第二次及以后只复制既有链接。未知状态禁止再次点击创建。
  - 复用 `export_report_copy()` 已有 clipboard permission/read 模式，抽取一个本文件私有 `_read_clipboard_text()`，不引入 subprocess 或新依赖。

- `read_shared_conversation(url: str, close_after: bool = True) -> dict[str, Any]`
  - 先验证 HTTPS + Gemini 官方分享 allowlist，拒绝任意 URL。
  - `new_tab(url)` 的 target ID 必须保存；close_after 时只关闭该精确 target，禁止按域名批量关闭。
  - Output: 最终 URL、标题、结构化 turns、纯文本；不得返回账号信息、Cookie、Token 或页面脚本。

- `switch_chat(url_or_id: str) -> dict[str, Any]`
  - 只接受精确 Gemini `/app/{conversation_id}` URL 或严格 conversation ID；不得接受标题 fragment。
  - 使用当前 task-owned tab 的 `goto_url`，验证最终 URL 完全一致且 composer/对话正文存在。

## Test Matrix

| Layer | Requirement/risk | Preconditions/fixtures | Exact command or procedure | Expected result | Failure evidence |
| --- | --- | --- | --- | --- | --- |
| Baseline | 当前分支/测试 | worktree 创建后 | `rtk uv run --with pytest pytest -q` | 至少 278 passed | 原始 pytest 输出 |
| Unit | send 单击与 unknown | fake js/cdp states | `rtk uv run --with pytest pytest -q tests/unit/test_gemini_domain_skill.py` | 新旧 Gemini tests 全通过 | pytest 原始失败 |
| Unit | 不切换/关闭他人标签 | fake current_tab/new_tab/list_tabs | 同上 | 不调用 switch 到任意现有 Gemini target；只关闭自建 share target | mock call 断言 |
| Unit | 分页/重叠合并 | 3 页含重复边界和两个相同文本合法 turn | 同上 | 顺序与 6 个逻辑 turns 精确一致 | expected/actual turns |
| Unit | 分享 allowlist/idempotence | fake clipboard/dialog | 同上 | 创建最多一次；同链接复用；恶意 URL 拒绝 | click count/exception |
| Static | Python/Domain wiring | worktree diff | `rtk uv run python -m py_compile "agent-workspace/domain-skills/gemini/basic_ops.py"` 后运行 `rtk python3 "scripts/verify_domain_skills.py"` | 两个命令 exit 0；registry 102 | stdout/stderr |
| Full | 邻接回归 | 所有本地修改完成 | `rtk uv run --with pytest pytest -q` | 278 + 新增数全部通过 | 完整失败日志 |
| E2E | 普通发送 | 9223 write lease、自建 tab | Task 6 核心脚本 | 每个 TURN 只出现一次；无 unknown 重试 | JSON evidence |
| E2E | 完整读取 | 同一合成长会话 | 连续调用 3 次 `full_conversation()` | 哈希、顺序、首尾 marker、turn 数一致 | 3 个结果摘要 |
| E2E | 分享 | 同一合成会话 | 创建一次、复制 3 次、读分享页 | 3 URL 相同，分享页含首尾 marker 且顺序正确 | URL 哈希/turn 摘要 |
| E2E | 切换 | 精确合成 chat URL | 当前 chat ↔ fresh home 循环 5 次 | 每次只落到精确 URL，无他人 chat 内容 | 每次 URL/marker |
| E2E | 附件取消 | 合成 txt | attach/remove 3 次，不发送 | 每次 chip 出现后消失；消息 turn 不增加 | filename/chip/count |
| Operational | 租约清理 | 所有浏览器脚本结束 | `./browser-harness agent-pool status` | `leases=[]`, `write_locks={}` | 原始 JSON |
| Delivery | main 隔离 + PR | 测试通过 | Task 8 | main 不变；功能分支 pushed；PR open/base main | Git SHA/status/PR URL |

## Progress Ledger

| Task | Status | Completion evidence |
| --- | --- | --- |
| Task 1: live contract + isolated worktree | pending | — |
| Task 2: latest Gemini UI map | pending | — |
| Task 3: safe chat/read helpers | pending | — |
| Task 4: ordinary share helpers | pending | — |
| Task 5: Domain Markdown | pending | — |
| Task 6: high-intensity real E2E | pending | — |
| Task 7: full audit/regression | pending | — |
| Task 8: push feature branch + create PR | pending | — |

### Task 1: 核验实时合同并创建隔离 worktree

**Purpose:** 确保弱模型的任何实现中间态都不进入共享 `main` 工作区。

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness`

**Risk level:** reversible mutation；用户已明确授权固定 worktree 与分支。

- [ ] **Step 1.1: 启动 Goal 与权限门槛**
  - 依次重读所有 Required Skills/Lessons 和 4 个官方 URL。
  - 检查实时 writable roots、sandbox、approval reviewer、network、Goal schemas。
  - 禁止修改 Codex 配置、禁止 Full Access、禁止向用户索权。
  - Success means: 当前合同仍允许精确 worktree 创建、worktree 写入、Auto Review Browser Harness、功能分支 push 与本机 `gh pr create`。
  - If it fails: 只采用本表已有安全路径；同一 Auto Review 拒绝不得绕过或换壳重试。

- [ ] **Step 1.2: 记录共享主工作区不可变基线**
  - Run:
    ```bash
    RTK_DISABLED=1 bash -lc 'git branch --show-current; git rev-parse HEAD; git rev-parse origin/main; git status --short --branch'
    ```
  - Expected: branch `main`，两个 SHA 相同，原有未跟踪 `.understand-anything/` 与 `agent-workspace/recordings/`。
  - 将完整输出写入 Evidence JSON 的 `main_before`。不得暂存未跟踪路径。

- [ ] **Step 1.3: 更新远端只读基线并创建 worktree**
  - Precondition: `git worktree list --porcelain` 不含目标路径，`git branch --list codex/gemini-web-audit-20260826` 为空。
  - Run:
    ```bash
    git fetch origin main
    git worktree add -b codex/gemini-web-audit-20260826 "/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826" origin/main
    ```
  - Expected: 新 worktree HEAD 等于最新 `origin/main`；共享主工作区仍在 main。
  - If partially succeeded: 先运行 `git worktree list --porcelain`、`git -C "/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826" status --short --branch`、`git branch --list "codex/gemini-web-audit-20260826"` 判定；已正确存在则继续，禁止再 add；路径存在但不是该 worktree 时不要删除，保留证据并停止这一步。
  - Rollback: 本计划禁止自动删除 worktree/分支；保留供人工审计。

- [ ] **Step 1.4: worktree 基线**
  - Working directory 改为目标 worktree，后续 Tasks 2–8 不得回到主工作区执行编辑、测试、commit 或 push。
  - Run: `rtk git status --short --branch`, `rtk codegraph status`, `rtk uv run --with pytest pytest -q`, `rtk python3 scripts/verify_domain_skills.py`。
  - Expected: clean feature branch；CodeGraph 可用；278 passed；registry 102。

- [ ] **Task acceptance**
  - 对比共享主工作区 Step 1.2 状态；branch/HEAD/原有未跟踪状态一致。
  - Ledger 记录 worktree path、branch、base SHA、测试结果。

### Task 2: 建立当前 Gemini UI 的脱敏能力地图

**Purpose:** 先理解真实最新页面，避免把 2026-08-05 的旧 selector 当事实。

**Working directory:** `/Users/yelin/Developer/agent-tools/browser-harness-worktrees/gemini-web-audit-20260826`

**Risk level:** safe/read-only UI state。

- [ ] **Step 2.1: Fleet 与租约只读核验**
  - Run Browser Fleet `audit` 的绝对脚本；要求 9223 name/port/profile/process 四锚点一致。
  - Run `./browser-harness agent-pool status`；要求空租约/空写锁。
  - 任一 conflict 时禁止指定其他端口，禁止 9224/9225/9226。

- [ ] **Step 2.2: 单独 Domain discovery 调用**
  - 精确执行：
    ```bash
    ./browser-harness agent-pool run --owner gemini-audit-discovery-20260826 --site gemini.google.com --account default --mode read <<'PY'
    new_tab("https://gemini.google.com/app")
    wait_for_load(timeout=20)
    print(page_info())
    PY
    ```
  - 此调用打印 `page_info()` 后必须结束；禁止在同一个 heredoc 继续检查或点击。
  - 完整读取返回的每一个 Markdown 绝对路径。当前预期是 Gemini `basic_ops.md` 与 Google `search.md`，但以本次实际返回为准。

- [ ] **Step 2.3: 脱敏控件与 DOM 结构清单**
  - 新开 read lease 和 task-owned tab。
  - 浏览器内先过滤：任何含 `@`、账号、邮箱、Cookie、Token、验证码、现有 chat 标题或现有聊天正文的文本都不打印。
  - 只输出：URL path、logged_in 布尔、composer selector/placeholder、model selector、header/sidebar action 的 tag/role/aria-label/data-testid、普通分享入口候选、message container/role/id、展开控件、主 scroller、附件 input、临时对话状态。
  - 对每个候选记录评分：稳定 `data-testid`/固定 href=5；role+aria=4；结构+exact visible text=3；动态 class=1；坐标=0。选择最高分且有可观察后置条件的路径。
  - 连续 reload 10 次，确认核心候选出现率；低于 9/10 不可固化为唯一 selector，必须增加语义 fallback。

- [ ] **Step 2.4: UI 元素矩阵**
  - 逐一打开并 Escape/关闭：模型菜单 10 次、上传和工具菜单 10 次、临时对话入口 3 次、普通新聊天入口 5 次。
  - 只读记录 Spark/笔记本/视频/库，不进入业务功能。
  - 记录每个动作的 before、一次 action、after、恢复动作。任何动作无 after 证据视为失败。
  - If selector fails: 最多 3 种不同策略；每次失败都先重读 compact AX/DOM。不得重复同一 click。顺序固定：稳定 DOM/AX → JS pointer sequence → 精确 CDP center click。坐标只作为临时诊断，不能写入 Helper。

- [ ] **Task acceptance**
  - Evidence JSON 含脱敏 `ui_map`、10 次稳定率、当前官方分享 URL 前缀候选、消息/分页/展开结构。
  - 无账号标识、旧聊天标题/正文、secret。

### Task 3: 修复共享标签安全并实现聊天/完整读取 Helper

**Purpose:** 从根因修复任意 tab 切换、弱发送证据和虚拟化读取缺口。

**Prerequisites:** Task 2 当前 UI map 完成。

**Files:** 只修改 Gemini Python 和 Gemini 单元测试。

- [ ] **Step 3.1: 先写最小失败测试**
  - 扩充 `load_skill()` namespace，提供 `current_tab`、`protect_tab`、`unprotect_tab` 所需 fake；不得依赖真实浏览器。
  - 新增测试必须覆盖：
    1. 当前不是 Gemini 时只 `new_tab`，即使 `list_tabs` 有别人的 Gemini tab 也不得 `switch_tab`；
    2. send 按钮只点一次，稳定新 user turn 才 `definitely_sent`；证据不足返回 `unknown` 且没有第二 click；
    3. direction/steps 参数校验；
    4. 三个虚拟页的边界 turns 合并保持顺序，两个文本完全相同但位置不同的合法 turns 均保留；
    5. expand 只点“展开”状态；
    6. max_pages 未到底 raise。
  - Run focused pytest，确认新测试先失败且失败原因正是缺失行为，不是 fixture 错误。

- [ ] **Step 3.2: 最小实现**
  - 按 Interface Contracts 修改现有函数并只新增：`page_conversation`、`conversation_turns`、`expand_all_user_messages`、`full_conversation`、`switch_chat`。
  - 优先复用当前 `_conversation_scroller`、`_norm`、`_reply_state`；不要建立 Page/Driver 类，不新增 dependency，不新增文件。
  - `conversation_text()` 保持向前兼容，但内部改为调用结构化 `conversation_turns()`，读取当前渲染页。
  - 非平凡重叠合并留下一个 `# ponytail:` 注释，明确当前上限与升级条件。
  - Run focused pytest 至 green。

- [ ] **Step 3.3: CodeGraph 与邻接影响**
  - Run `codegraph sync .`，查询所有新增/修改 symbol 的 callers/callees/impact，`codegraph affected` 检查测试覆盖。
  - 源码与 CodeGraph 冲突时以源码为准，修复索引后重跑。

- [ ] **Task acceptance**
  - Focused Gemini tests 全绿；py_compile 通过；不存在扫描/切换任意既有 Gemini tab 的代码；send 单击 invariant 有测试。

### Task 4: 实现普通分享与分享页读取 Helper

**Purpose:** 用合成会话安全完成用户最关心的普通聊天分享闭环。

**Prerequisites:** Task 3 完成；Task 2 已证明当前分享 UI 和 URL 前缀。

- [ ] **Step 4.1: 分享失败测试**
  - 覆盖当前真实 UI 对应的 dialog/toast 状态机：首次创建、已存在只复制、unknown 不重建、clipboard 读取、URL allowlist、非当前合成会话拒绝。
  - 覆盖 `read_shared_conversation` 只关闭 `new_tab` 返回的 target ID；绝不扫描/按 URL 关闭其他 tab。
  - Fake 分享页包含首尾 marker，断言结构化 turns 顺序。

- [ ] **Step 4.2: 最小分享实现**
  - 在 Gemini `basic_ops.py` 内新增私有 `_read_clipboard_text()`，让 `export_report_copy()` 和 `export_share_link()` 复用。
  - 新增且只新增 `export_share_link`、`read_shared_conversation` 两个公共 helper。
  - 分享 dialog 每次 action 前重新定位元素；每个外部 mutation 只做一次；已分享路径不得再次创建。
  - URL allowlist 来自 Task 2 真实证据，不接受任意重定向 host。

- [ ] **Task acceptance**
  - Focused tests 全绿；分享创建 click count=1；重复获取不新增外部状态；恶意 URL 在打开 tab 前被拒绝。

### Task 5: 更新 Gemini Domain Markdown

**Purpose:** 让后续弱模型无需重新摸索即可执行当前真实最优路径。

**Files:** 只修改 Gemini `basic_ops.md`。

- [ ] **Step 5.1: 同步当前能力**
  - 更新 verified date 为真实 E2E 完成日期，不得提前写“verified”。
  - Invocation 全部使用 worktree 的 `./browser-harness agent-pool run`，无 `-c`、无全局 binary、无显式 9223 端口。
  - 明确两阶段发现：首次只 page_info → 读完所有 Markdown → 第二次操作。
  - 增加新函数表、最小普通聊天脚本、完整 transcript 脚本、分享/读分享脚本。
  - 增加“只操作 task-owned tab”“unknown 不重发”“分享是公开外部状态”“长聊天 complete 判据”“精确 URL 切换”“不读私人会话”。

- [ ] **Step 5.2: 清理过期事实**
  - Task 2 未通过的 2026-08-05 selector 改为历史 fallback 或删除。
  - 不把 Spark/笔记本/视频/库写成已支持 Helper；只在 Current UI inventory 记录。
  - 保留 Deep Research 已验证能力，但注明本轮未消耗新配额；不得伪造最新 DR E2E。

- [ ] **Task acceptance**
  - `python3 scripts/verify_domain_skills.py` PASS；Markdown 中无 `9224/9225/9226`、全局 binary、`-c`、账号标识、临时绝对 worktree path。

### Task 6: 高强度真实 Gemini E2E

**Purpose:** 用少量合成外部状态反复测试所有核心路径，找到真实最优方案。

**Risk level:** 已授权的可见外部 mutation；必须 write lease 串行。

**Synthetic fixture:** 每次开始从 `time.strftime('%Y%m%d-%H%M%S')` 生成字符串 `run_id = "BH-GEMINI-AUDIT-" + time.strftime('%Y%m%d-%H%M%S')`，立即写入 Evidence JSON。所有消息必须含 run_id。禁止包含用户资料、仓库私密内容、账号、邮箱或现有聊天文本。

- [ ] **Step 6.1: 创建合成长会话，只发送一次每个 turn**
  - 在单个 Agent Pool write lease 内新建 task-owned Gemini tab并 protect。
  - TURN-001：约 3500–4500 字符的重复无敏感中文段落，首尾分别含 `{run_id}-TURN-001-START` 与 `{run_id}-TURN-001-END`，要求 Gemini 只回复 `{run_id}-ACK-001`；花括号表示使用本步骤已经生成的真实 run_id 字符串。
  - TURN-002：要求输出 80 个短编号行，第一行 `{run_id}-LIST-001`，最后一行 `{run_id}-LIST-080`，制造足够页面高度。
  - TURN-003 至 TURN-006：每次只要求回复对应唯一 ACK。
  - 每次只在 `send_message.status == definitely_sent` 后进入 wait；`unknown` 时读取当前 turns 查证，绝不重发同一 TURN。
  - Evidence 记录 canonical conversation URL、每个 turn 的唯一出现次数、reply assistant count、发送 click count。

- [ ] **Step 6.2: 展开、分页与完整读取压力测试**
  - 页面到顶部后调用 `expand_all_user_messages()`；验证 TURN-001-END 可见。
  - 连续运行 `full_conversation()` 3 次。每次保存：turn 数、首尾 marker、角色序列、normalized text SHA-256、pages。
  - Pass: 3 个哈希一致；TURN-001..006 各出现一次且顺序一致；LIST-001 在 LIST-080 前；无 action 按钮文本混入。
  - 若页面实际上未虚拟化：仍要求 top/bottom complete 判据与 3 次一致；不要为了制造虚拟化无限发送消息。

- [ ] **Step 6.3: 精确会话切换**
  - 保存 canonical URL；`goto_url(GEMINI_HOME)` 与 `switch_chat(canonical_url)` 循环 5 次。
  - 每次验证最终 URL 精确相等、run_id 存在、composer 可用。
  - 禁止点击/sidebar 模糊标题；禁止读取其他历史 chat。

- [ ] **Step 6.4: 普通会话分享**
  - 首次调用 `export_share_link()`，只允许一次创建外部链接。
  - 再调用 2 次，要求 3 个 URL 完全相同；created 只能首次为 true。
  - `read_shared_conversation(url, close_after=True)` 连续 3 次，要求首尾 marker、TURN 顺序、LIST 边界一致；每次 share tab 都精确关闭且其他 tab 未变。
  - 使用无 Cookie 的 `curl -L --max-time 20` 只做状态/官方 host 检查；若 JS shell 不含内容，不把它误判为分享失败，也不得声称已证明匿名可读。Browser E2E 是功能验收，匿名性结论单独标记 unverified。

- [ ] **Step 6.5: 模型、菜单、临时对话与附件可逆循环**
  - 记录原模型。若 picker 暴露另一个无需升级/付费的模型，切过去再恢复，执行 2 轮；每次重新打开 picker 验证当前模型。出现升级/价格立即 Escape 并跳过，不问用户。
  - 上传和工具菜单打开/关闭 10 次；不得点击 Drive、图片、视频、音乐生成。
  - 创建 `/tmp/bh-gemini-attachment-20260826.txt`，内容仅为固定字符串 `BH Gemini synthetic attachment 2026-08-26`。附加后移除 3 次，每次验证 filename chip 出现再消失，且 user turn 数不增加。
  - 临时对话只做一次短合成消息测试，验证不进入普通历史和分享入口按 UI 预期不可用；随后返回普通 home。若临时模式退出方式不明确，直接 `goto_url(GEMINI_HOME)` 并验证普通 composer，不反复点击。
  - Spark/笔记本/视频/库只记录入口存在，不进入。

- [ ] **Step 6.6: 恢复与清理**
  - 恢复原模型；关闭/取消所有弹层；unprotect 并只关闭本次自建标签。
  - 不删除聊天、不撤销分享链接。合成公开链接保留为验收证据。
  - 保留 `/tmp/bh-gemini-attachment-20260826.txt` 与脱敏 Evidence 供复查；本计划不执行文件删除。
  - Run Agent Pool status，要求空租约/空写锁。

- [ ] **Task acceptance**
  - Evidence JSON 的 `e2e.status=passed`；所有次数、URL 哈希、turn 哈希、恢复状态、租约状态齐全；无私人内容。

### Task 7: 完整审计与回归

**Purpose:** 证明实现小、准、无安全回退和无偶然绿。

- [ ] **Step 7.1: 静态/Focused/Full**
  - Run:
    ```bash
    rtk uv run python -m py_compile "agent-workspace/domain-skills/gemini/basic_ops.py"
    rtk uv run --with pytest pytest -q "tests/unit/test_gemini_domain_skill.py"
    rtk python3 "scripts/verify_domain_skills.py"
    rtk uv run --with pytest pytest -q
    ```
  - Expected: 全部 exit 0；full >= 278 + 新增 tests。

- [ ] **Step 7.2: 原始 diff/安全审计**
  - Run raw `git diff --check`、`git diff --stat`、`git diff --` 三个允许文件。
  - 搜索：账号/邮箱模式、Cookie、Token、Authorization、password、验证码、`BU_CDP_URL`、9224/9225/9226、`close_extra_tab`、`activate_tab`、`git merge`、placeholder、debug print、disabled/skipped tests。
  - 允许 `9223` 只在计划 Current-State Evidence 中出现；最终 Gemini Domain 文件不得硬编码任何端口。
  - 确认无新依赖、无 registry 修改、无 Core 修改。

- [ ] **Step 7.3: CodeGraph final**
  - `codegraph sync .`；对新增公共函数运行 query/impact；`codegraph affected` 必须包含 Gemini unit test 或明确说明 Domain 文件动态 exec 的索引限制。

- [ ] **Step 7.4: Ponytail review**
  - 删除未被文档或 E2E 使用的 helper、重复 selector wrapper、推测性 fallback。
  - 保留安全验证、unknown 状态、URL allowlist、tab ownership、max_pages guard；这些不得为“简洁”删除。

- [ ] **Task acceptance**
  - 只有 3 个允许文件有 tracked diff；所有测试和真实 E2E fresh evidence 通过。

### Task 8: 提交功能分支、推送并用本机 gh 创建 PR；不合并

**Purpose:** 让共享 main 继续稳定使用，同时把已验收改动送入正常合并审查。

**Risk level:** 用户已明确授权的外部 Git/PR 写入；禁止超出功能分支与一个 PR。

- [ ] **Step 8.1: 最后检查主工作区未改变**
  - 在共享主仓库运行 Step 1.2 相同 raw 命令，与 `main_before` 对比。
  - HEAD、branch、原有 untracked 必须一致；计划文件是计划作者预先落盘的已知新增，不属于执行者代码改动。
  - 若共享 main 被其他 Agent 正常推进：不要回滚或覆盖；记录新的 HEAD，并证明本任务从未写入 main。功能分支基于启动时 origin/main，PR 交由合并端处理。

- [ ] **Step 8.2: 精确暂存与提交**
  - 在 worktree 只暂存三个允许文件，禁止 `git add .`：
    ```bash
    rtk git add "agent-workspace/domain-skills/gemini/basic_ops.py" "agent-workspace/domain-skills/gemini/basic_ops.md" "tests/unit/test_gemini_domain_skill.py"
    git diff --cached --check
    git diff --cached --name-only
    git commit -m "feat(gemini): harden web conversation operations"
    ```
  - Expected cached names 精确等于三个路径；commit 成功。

- [ ] **Step 8.3: 推送功能分支**
  - Run:
    ```bash
    git push -u origin codex/gemini-web-audit-20260826
    ```
  - 禁止 `--force`、`--force-with-lease`、push main、tag、delete。
  - Verify: `git ls-remote --heads origin codex/gemini-web-audit-20260826` SHA 等于 worktree HEAD。

- [ ] **Step 8.4: 准备 PR 正文**
  - 用 `apply_patch` 创建 `/tmp/browser-harness-gemini-pr-body-20260826.md`，正文必须包含：
    - Summary：safe task-owned tab、definite send、full transcript/expand、ordinary share/read。
    - Real verification：合成 turns 数、3 次 transcript 哈希一致、3 次 share URL 一致、5 次 exact switch、附件 3 次 attach/remove、最终空租约。
    - Tests：focused、registry、full pytest 的实际数量。
    - Safety：只分享合成内容；未读私人 chats；未删除；未消耗 DR；未自动 merge。
    - 不得包含公开分享 URL 本身、账号、邮箱、Cookie、Token 或 Evidence 全文。

- [ ] **Step 8.5: 通过本机 gh 创建 PR**
  - 9223 只允许访问 Gemini；本步骤和整个计划都禁止用 Browser Harness 打开 GitHub。
  - 先在真实网络权限下运行 `gh auth status`。Expected: active account 已登录且 token scopes 包含 `repo`；不得使用 `--show-token`，不得读取或记录完整 token。
  - 先去重：
    ```bash
    gh pr list --repo sunshine6666666666/browser-harness --state open --base main --head codex/gemini-web-audit-20260826 --json number,url,state,baseRefName,headRefName,title
    ```
  - 若返回一个 exact head/base 的打开 PR，复用该 URL，不创建重复；若返回空数组，精确执行一次：
    ```bash
    gh pr create --repo sunshine6666666666/browser-harness --base main --head codex/gemini-web-audit-20260826 --title "feat(gemini): harden web conversation operations" --body-file "/tmp/browser-harness-gemini-pr-body-20260826.md"
    ```
  - Verify:
    ```bash
    gh pr view codex/gemini-web-audit-20260826 --repo sunshine6666666666/browser-harness --json number,url,state,baseRefName,headRefName,title
    ```
  - Expected: `state=OPEN`、`baseRefName=main`、`headRefName=codex/gemini-web-audit-20260826`、title 精确一致，URL 为目标仓库 PR。
  - 禁止运行 `gh pr merge`、`gh pr close`、`gh auth login`、`gh auth refresh`，禁止启用 auto-merge 或删除分支。

- [ ] **Step 8.6: 最终状态**
  - Worktree clean，branch ahead/同步 origin；共享 main 未被本任务修改；Agent Pool 空；PR open。
  - 保留 worktree，不自动 remove；它是 PR 复查证据。

- [ ] **Task acceptance**
  - Ledger 记录 feature commit SHA、remote SHA、PR URL、main before/after、最终测试、最终空租约。
  - 所有要求满足后才 Goal complete。

## Failure Recovery and Autonomous Continuation

1. 每次中断/compaction 后先 `get_goal`，重读本计划、Required Skills/Lessons、Progress Ledger。
2. 检查共享 main、worktree list、worktree branch/status、Evidence JSON、Agent Pool status。
3. 从第一个未勾选步骤继续；先验证上次动作是否已部分成功，禁止重复发送消息、重复创建分享、重复 push 或重复 PR。
4. Selector 失败：打印脱敏 compact AX/DOM；每种不同策略最多一次，总共最多 3 种；失败后修 Helper + 单元测试，再回真实页面。不得盲点、不得重复同一 click。
5. `send_message=unknown`：检查唯一 TURN marker 和 user turn ID；存在则视为已发送并等待，缺失则保留 unknown，禁止重发该 TURN。可以继续测试其他只读能力，但 E2E 不得标 passed。
6. 分享 unknown：检查 dialog、toast、clipboard、当前分享状态；任何证据表明已创建则只复制；完全未知时禁止第二次 Create，记录并修证据读取。
7. 页面语言变化：优先 role/aria/data-testid/结构，不硬切语言；只为真实出现的中文/英文 exact labels 增加最小 fallback。
8. 9223 busy：Agent Pool 自己排队；禁止绕过租约、禁止指定其他端口、禁止手工 CDP。单次命令超时后先 status，确认租约归属；不得 reap --apply。
9. Auto Review 明确拒绝：不得换命令、间接脚本或绕过策略；仅使用计划已有更安全路径。不要向用户索权。
10. Gemini login/验证码/付费墙：关闭本次自建 tab，等待一次 5–10 分钟后重新执行独立 discovery；仍存在则停止外部 mutation，继续可完成的代码/fixture审计，但不得伪造真实验收或 Goal complete，不向用户发授权请求。
11. `gh` 网络/认证失败：先在真实网络权限下只读运行一次 `gh auth status`，避免把 sandbox 网络问题误判为 token 失效；然后重试原 `gh pr list/create/view` 流程最多一次。仍失败时保留已推送功能分支和错误证据；禁止使用 9223、禁止 `gh auth login/refresh`、禁止向用户索权；PR 未创建则 Goal 不 complete。
12. PR 提交结果未知：读取当前 URL 和仓库 open PR 列表，按 exact head branch 去重；已有则复用，未知时禁止第二次提交。
13. Gemini focused test 失败两次或 RTK 输出不足：运行 `rtk proxy uv run --with pytest pytest -vv "tests/unit/test_gemini_domain_skill.py"`；全量测试不明时运行 `rtk proxy uv run --with pytest pytest -vv`；修根因，不接受红 suite。
14. 绝不运行 reset/clean/checkout 丢改动、worktree remove、branch delete 或 main merge 作为恢复。

## Final Acceptance Gate

- [ ] 重新运行 Test Matrix 的全部命令并记录 fresh evidence。
- [ ] Requirement Traceability 每一行都有实现任务和 passing check。
- [ ] 原始完整 diff 只含 Gemini Python、Gemini Markdown、Gemini unit test。
- [ ] 无 placeholder、debug、disabled test、secret、账号、私人聊天、生成 junk、后台 watchdog。
- [ ] E2E 证明：发送不重复；完整读取 3 次一致；展开成功；分享 URL 3 次一致；分享页首尾/顺序正确；exact switch 5 次；附件 attach/remove 3 次；模型恢复。
- [ ] Browser Fleet 无 conflict；Agent Pool `leases=[]`、`write_locks={}`。
- [ ] 共享主工作区未被本任务修改；原有未跟踪内容完整。
- [ ] 功能分支 remote SHA 正确；PR open、base main、head 精确；没有 merge/auto-merge。
- [ ] Worktree 保留、clean；临时证据不在 Git diff。
- [ ] Progress Ledger 全部 complete，含测试数、commit SHA、PR URL、剩余限制。
- [ ] 只在以上全部通过后调用 `update_goal(status="complete")`，最终报告只给结果、变更文件、测试、PR URL、未覆盖项；不要要求用户继续、确认或授权。
