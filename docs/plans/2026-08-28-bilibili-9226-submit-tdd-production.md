# Bilibili 9226 投稿确认故障：TDD 复现、最小修复与生产发布计划

> 执行对象：低能力、无人监督的 Codex 执行模型  
> 工作目录：`/Users/yelin/Developer/agent-tools/browser-harness`  
> 计划日期：2026-08-28（Asia/Shanghai）  
> 用户已于 2026-08-28 明确授权：对 Bilibili 9226 账号做受控真实定时投稿、修改本仓库、提交 Git commit，并在验收成功后发布 Browser Harness 生产版本。  
> 本文是执行闭环，不是问题结论。Hermes 的诊断只能作为待验证假设。

## 1. 唯一目标

在 Bilibili 账号 `水蜜桃英语`（MID `518800384`，CDP `http://127.0.0.1:9226`）上，精确复现 Job 98 的“点击提交后无可回读证据”问题；用真实页面和脱敏网络证据确定根因；严格按 RED → GREEN → REFACTOR 做最小修复；再用不同素材完成一次真实定时投稿验收；全部测试通过后提交代码并把 Browser Harness 升为新的生产版本。

不得顺手重构，不得改变已经正确的上传、封面、标题、分区、简介、声明、排期和账号校验步骤。

## 2. 最终成功标准

只有同时满足以下条件，Goal 才能标记 `complete`：

1. 已在 9226 账号完成一次 Job 98 精确标题的真实基线测试，且每个标题最多点击一次提交。
2. 若基线复现故障，已取得足以区分点击拦截、平台拒绝、或受理后回读延迟的脱敏证据。
3. 已先添加一个能因现有缺陷而失败的最小单元测试；失败是预期断言失败，不是语法、导入或环境错误。
4. 只修复证据指向的根因；相关测试、全量测试和 Domain Skill 校验全部通过。
5. 已用第二个不同素材完成真实定时投稿验收：
   - `status == "verified"`
   - `submitted is True`
   - `submit_clicks == 1`
   - 稿件管理页能匹配精确标题和中文排期时间；若平台在审核中隐藏排期，则精确最新卡片的 `审核中` 按用户口径即为发布完成
   - 归档 API 最终只出现一条同标题记录，并取得 `aid` 或 `bvid`；若 API 暂时延迟，必须在有界只读回读窗口内补齐
6. 没有同标题重复稿件，没有遗留浏览器租约、写锁或本任务新开的标签页。
7. Git 工作树只包含允许文件的变更，已提交但未 push。
8. Browser Harness 新生产版本已发布，`verify` 成功，并保留旧生产版本用于回滚。

特殊情况：如果 Job 98 基线一次即成功且证据链完整，则视为“当前无法复现”。此时不得为了制造版本而改代码、提交或升生产版本；完成全部只读核验和现有测试后，以“无代码变更、无需发布”的证据结束 Goal。

## 3. 不可违反的边界

- 不修改、提交或推送 `/Users/yelin/Developer/linye-english-news-workflow`。
- 不使用旧目录 `/Users/yelin/Developer/agent-tools/express` 作为证据。
- 不创建分支或 worktree；直接在当前 `main` 上工作。
- 不执行 `git push`。
- 不删除素材、稿件、浏览器 Profile 或生产版本。
- 不停止 9226 浏览器；只释放自己的租约，只关闭自己创建的标签页。
- 不使用全局 `browser-harness`；必须使用 `/Users/yelin/Developer/agent-tools/browser-harness/browser-harness`。
- 不添加依赖，不修改 Browser Harness 核心代码。若证据证明核心事件采集损坏，停止扩展范围并按阻塞规则处理。
- 最多允许 **3 次真实提交点击总数**：基线 1 次、修复后验收 1 次、必要时补丁后最终验收 1 次。不得无限重试。
- 同一个精确标题最多提交一次。结果不明时只能只读回查，绝不再次点击。

## 4. 定时投稿硬性约束

这是测试，任何真实投稿都必须为定时投稿：

| 用途 | 精确排期（Asia/Shanghai） | 素材 |
|---|---|---|
| Job 98 基线 | `2026-09-03 22:00` | `videoFile-1787889530091-715515343` |
| 修复后验收 | `2026-09-04 22:00` | `videoFile-1787618151999-352662935` |
| 最终备用验收 | `2026-09-05 22:00` | `videoFile-1787709497729-601582932` |

执行每次投稿前必须检查：

1. 排期晚于 `2026-08-31 23:59:59`。
2. 排期不晚于 `2026-09-07 23:59:59`。
3. 排期距当前时间至少 5 分钟，且不超过平台允许的 15 天窗口。
4. 若目标槽位已失效，依次尝试表中的下一个槽位；不得自行改成立即发布，不得排到 9 月 7 日之后。
5. 若三个槽位均不可用，停止真实写操作并进入阻塞处理。

## 5. 必须读取的指令与事实来源

执行任何仓库修改或网站操作前，完整读取下列文件；不得只读摘要：

1. `/Users/yelin/Developer/agent-tools/browser-harness/AGENTS.md`
2. `/Users/yelin/Developer/agent-tools/browser-harness/CLAUDE.md`
3. `/Users/yelin/.codex/skills/writing-plans/SKILL.md`
4. `/Users/yelin/.codex/skills/test-driven-development/SKILL.md`
5. `/Users/yelin/.codex/skills/browser-fleet-manager/SKILL.md`
6. `/Users/yelin/.codex/skills/browser-fleet-manager/references/lessons.md`
7. `/Users/yelin/.codex/skills/production-toolchain-manager/SKILL.md`
8. `/Users/yelin/.codex/skills/production-toolchain-manager/references/lessons.md`
9. `/Users/yelin/Developer/agent-tools/browser-harness/SKILL.md`
10. `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.md`
11. `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/network-requests.md`
12. `/Users/yelin/Developer/agent-tools/browser-harness/interaction-skills/tabs.md`

Bilibili 页面发现后，如果 `page_info()` 返回 `domain_skill_files`，必须再完整读取其中列出的 **全部 Markdown 文件**。当前已知集合是：

- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/creator-dashboard.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/danmaku.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/interactions.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/navigation.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.md`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/replies.md`

## 6. Goal 与权限启动协议

先检查当前可用工具的实时 schema；不要把 `/goal` 当成 shell 命令。若存在 `create_goal`，调用：

```text
objective: 在 Bilibili 9226 账号精确复现 Job 98 投稿确认故障，按 TDD 做最小根因修复，完成真实定时投稿验收，并发布验证 Browser Harness 新生产版本。
```

不要设置 `token_budget`。随后调用 `get_goal` 记录初始状态。

Goal 不扩大权限；Auto Review 只是审批者，不是权限授予。若操作被拒绝：

- 不绕过、不改用等价隐蔽命令、不重复相同升级请求。
- 先尝试实质上更安全且仍能完成目标的方法。
- 只有同一阻塞条件连续出现至少三次、且无法继续产生有效进展时，才调用 `update_goal(status="blocked")`。
- 只有第 2 节全部成功标准满足，才调用 `update_goal(status="complete")`。

权限可行性：

| 行为 | 授权状态 | 执行要求 |
|---|---|---|
| 修改本仓库允许文件 | 已授权 | 限定第 12 节白名单 |
| 读取外部素材目录 | 已授权 | 只读原素材 |
| 写 `/tmp/browser-harness-bilibili-9226-tdd/` | 已授权 | 仅测试封面和脱敏证据 |
| 连接 `127.0.0.1:9226` | 已授权 | 使用 Browser Harness 租约 |
| Bilibili 真实定时投稿 | 已明确授权 | 遵守第 4 节和 3 次上限 |
| Git commit | 已明确授权 | 不 push；Auto Review 仍可审核 |
| 写入 `~/.local` 生产版本 | 已明确授权 | 只用生产管理脚本；Auto Review 仍可审核 |
| 删除、立即发布、push | 未授权 | 禁止执行 |

## 7. 建立可恢复执行账本

在每个阶段结束时，把以下内容追加到 Goal 进度或执行上下文；不要创建新的仓库状态文件：

- 当前阶段与已完成验收项
- 当前 Git HEAD 和 `git status --short`
- 已使用的真实提交次数及对应标题
- 9226 当前租约状态
- 最新证据文件路径
- 下一个唯一动作

任何恢复执行都先读此计划、Goal 状态、Git 状态和浏览器池状态，禁止从头重复真实投稿。

## 8. 阶段 A：只读基线与环境验证

在 `/Users/yelin/Developer/agent-tools/browser-harness` 执行：

```bash
pwd
which rtk
rtk --version
rtk git status --short --branch
rtk git log -1 --oneline
rtk codegraph status
rtk uv run --with pytest pytest -q tests/unit/test_bilibili_publishing.py
rtk uv run --with pytest pytest -q
rtk python3 scripts/verify_domain_skills.py
python3 "/Users/yelin/.codex/skills/production-toolchain-manager/scripts/toolchain.py" verify --tool browser-harness
./browser-harness agent-pool status
```

预期基线：

- 分支 `main`。
- 起始 HEAD 可能为 `0b6dcba chore: record local operating boundaries`；若不同，记录真实值，不擅自 reset。
- 专项测试约 20 个通过，全量测试约 304 个通过，Domain Skill registry 校验通过。
- 当前生产版本在计划编写时是 v1、release `0b6dcbafa45a-1d7943ae`、source `0.1.9`。执行时以 `verify` 的真实输出为准。
- 如果工作树存在用户变更，先确认是否与允许文件重叠。不得覆盖；重叠且无法安全绕开时按阻塞规则处理。

CodeGraph 已有索引。执行 `status` 后如允许则 `sync`，再查询 `submit_once`、`manager_evidence`、`submission_diagnostics` 的 callers/callees/impact。直接源码永远是行号与行为的最终依据。

## 9. 阶段 B：素材验证与封面生成

只读取素材，所有派生封面写入固定临时目录：

```bash
mkdir -p "/tmp/browser-harness-bilibili-9226-tdd"
/opt/homebrew/bin/ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration,size -of json "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787889530091-715515343/output.mp4"
/opt/homebrew/bin/ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration,size -of json "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787618151999-352662935/output.mp4"
/opt/homebrew/bin/ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration,size -of json "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787709497729-601582932/output.mp4"
/opt/homebrew/bin/ffmpeg -y -ss 00:00:01 -i "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787889530091-715515343/output.mp4" -frames:v 1 "/tmp/browser-harness-bilibili-9226-tdd/baseline-cover.png"
/opt/homebrew/bin/ffmpeg -y -ss 00:00:01 -i "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787618151999-352662935/output.mp4" -frames:v 1 "/tmp/browser-harness-bilibili-9226-tdd/acceptance-cover.png"
/opt/homebrew/bin/ffmpeg -y -ss 00:00:01 -i "/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787709497729-601582932/output.mp4" -frames:v 1 "/tmp/browser-harness-bilibili-9226-tdd/fallback-cover.png"
```

用 `ffprobe` 或已安装 Pillow 验证三张 PNG 均为 `1920x1080`。已知视频基线：

- Job 98：约 321.749 秒，H.264/AAC，约 119 MB。
- 验收：约 312.768 秒，1920x1080，约 105 MB。

任何文件缺失或不可解码时，不得用未知素材替代；记录并进入阻塞处理。

## 10. 阶段 C：Browser Harness 正确发现与租约

先用一次独立短租约做发现，脚本必须从 stdin 传入：

```bash
printf 't = new_tab("https://member.bilibili.com/platform/upload/video/frame")\nprint(page_info())\nclose_tab(t)\n' | env BU_NAME=agent BU_CDP_URL=http://127.0.0.1:9226 ./browser-harness
```

检查 `page_info()`，确认页面属于 Bilibili，并完整读取返回的全部 `domain_skill_files` 后，才允许申请第二次写操作租约。

执行前确认浏览器身份：

- 资源名：`SAU-自媒体运营-2号-9226`
- CDP：`http://127.0.0.1:9226`
- MID：`518800384`
- 显示账号：`水蜜桃英语`

身份不匹配立即停止，不得尝试登录、切号或迁移 Profile。

## 11. 阶段 D：Job 98 精确真实复现

### 11.1 固定输入

- 视频：`/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787889530091-715515343/output.mp4`
- 封面：`/tmp/browser-harness-bilibili-9226-tdd/baseline-cover.png`
- 标题：`《卫报》：从约会到影视，接吻为何在英国社会逐渐消失？｜外刊播客｜中英+文稿`
- 简介：`本期英语新闻播客讨论英国社会与影视作品中接吻逐渐减少的现象，提供中英双语文稿与英语听力练习。`
- 标签：`英语学习`、`英语听力`、`英语新闻`、`外刊精读`、`英语播客`
- 分区：`知识`
- 声明：`内容无需标注`
- 排期：`2026-09-03 22:00`

先调用现有只读回查，确认精确标题当前不存在。若已存在，禁止点击提交，记录冲突并按阻塞规则处理。

### 11.2 提交前观测

复用 `publishing.py` 现有方法准备上传、封面、字段和排期。必须连续取得两次稳定快照，两次都满足：

- 视频上传完成
- 自定义封面已设置
- 标题、分区、简介、标签、声明、排期完全匹配
- 提交按钮可用
- `validation_errors` 为空
- 无拦截 modal

点击前额外记录：

1. 提交按钮中心坐标。
2. `document.elementFromPoint(centerX, centerY)` 的 tag、可识别 class 和可见文本。
3. `drain_events()` 清空历史事件。

允许在测试进程中临时包装 `_click_visible` 采集命中元素，但包装器不得改变点击次数、等待时序或生产文件。

### 11.3 唯一真实点击

⚠️ 危险操作检测！  
操作类型：在 Bilibili 9226 生产账号创建真实定时投稿  
影响范围：生成一条计划于 2026-09-03 22:00 发布的稿件记录  
风险评估：可能真实进入审核/排期；重复点击会产生重复稿件  
授权状态：用户已于 2026-08-28 明确确认；仍须接受 Auto Review，不得绕过拒绝

调用现有 `submit_once(..., timeout=60)`，只调用一次。调用结束后立刻再次 `drain_events()`，只保存以下脱敏字段：

- HTTP method
- 去掉 query string 的 URL
- resource type
- response status 或 failure reason

禁止保存或输出 request headers、response headers、cookies、authorization、postData、csrf、token。将脱敏结果写入 `/tmp/browser-harness-bilibili-9226-tdd/job98-network-sanitized.json`。

### 11.4 证据分流

严格按观测选一个分支，不得预设 Hermes 结论：

| 证据 | 根因方向 | 下一步测试 |
|---|---|---|
| 没有相关非 GET 请求，且 `elementFromPoint` 不是提交按钮 | 点击被 overlay/命中元素拦截 | 为点击前可点击性或遮挡检测写一个 RED 测试 |
| 已发非 GET 请求，返回非 2xx 或明确业务拒绝 | 平台校验/协议/风控未被 UI 快照捕获 | 为具体拒绝信号的解析与返回状态写一个 RED 测试 |
| 请求成功或 2xx，但很快导航至稿件管理仍无卡片/API | 受理后 settle/reconciliation 窗口不足 | 为提交页诊断与首次管理页导航的调用顺序写一个 RED 测试 |
| `verified` 且标题、排期、manager、archive 全部匹配 | 当前不可复现 | 不改代码、不 commit、不 promote；转第 16 节收尾 |
| `accepted_but_schedule_unverified` | 已受理但排期证据未收敛 | 只调用 `manager_evidence`/`archive_matches` 多轮回读；禁止第二次点击 |

若结果不明，优先只读回查，不得用第二次提交来“确认”。

## 12. 阶段 E：严格 TDD 最小修复

允许改动的文件只有：

- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.py`
- `/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/bilibili/publishing.md`（仅当对外行为契约变化）
- `/Users/yelin/Developer/agent-tools/browser-harness/tests/unit/test_bilibili_publishing.py`
- `/Users/yelin/Developer/agent-tools/browser-harness/docs/plans/2026-08-28-bilibili-9226-submit-tdd-production.md`

关键源码锚点：

- `publishing.py::_click_visible`
- `publishing.py::submission_diagnostics`
- `publishing.py::archive_matches`
- `publishing.py::submission_snapshot`
- `publishing.py::manager_evidence`
- `publishing.py::submit_once`
- `helpers.py::drain_events`（只复用，不修改）
- `helpers.py::wait_for_network_idle`（只复用，不修改）

### 12.1 RED

先只改测试文件，添加 **一个** 与第 11.4 节实际证据对应的最小回归测试。运行该测试并保存完整输出：

```bash
rtk proxy uv run --with pytest pytest -q tests/unit/test_bilibili_publishing.py -k "新测试的精确名称" -vv
```

必须看到预期断言失败。若测试一开始就通过，说明没有覆盖缺陷，先改测试；不得进入 GREEN。

若证据属于 settle/reconciliation 分支，最小测试应表达以下行为而不是硬编码睡眠时间：首次 `submission_diagnostics` 返回 `click_not_accepted` 后，`submit_once` 必须在第一次跳转稿件管理页前，继续在上传页取得至少一次能判定受理/拒绝的本地诊断或有界 settle 结果。现有行为若是“诊断一次 → 立即 manager 导航”，测试应因调用顺序错误而 RED。

### 12.2 GREEN

只在 `publishing.py` 修改一个共享根因点，使新测试通过。优先复用现有 `submission_diagnostics`、`archive_matches`、`manager_evidence` 和循环；禁止新增框架、类、依赖、配置系统或通用重试抽象。

运行：

```bash
rtk uv run --with pytest pytest -q tests/unit/test_bilibili_publishing.py -k "新测试的精确名称"
rtk uv run --with pytest pytest -q tests/unit/test_bilibili_publishing.py
```

### 12.3 REFACTOR

仅删除测试或实现中的明显重复；行为不变。若已经足够简单，不做重构。只有对外状态或操作顺序契约改变时，才同步修改 `publishing.md`。

### 12.4 静态与全量回归

```bash
rtk uv run --with pytest pytest -q
rtk python3 scripts/verify_domain_skills.py
git diff --check
RTK_DISABLED=1 git diff -- agent-workspace/domain-skills/bilibili/publishing.py agent-workspace/domain-skills/bilibili/publishing.md tests/unit/test_bilibili_publishing.py
```

任何测试失败都先修复，不得带失败进入真实验收。

## 13. 阶段 F：真实验收与最多一次补丁闭环

### 13.1 第一验收输入

- 视频：`/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787618151999-352662935/output.mp4`
- 封面：`/tmp/browser-harness-bilibili-9226-tdd/acceptance-cover.png`
- 标题：`湖南店主扶人不担责｜外刊播客｜中英+文稿【链路验收0904】`
- 简介：`本期英语新闻播客讨论湖南店主扶老人后遭索赔、最终确认不担责的事件，提供中英双语文稿与英语听力练习。`
- 标签、分区、声明：同第 11.1 节
- 排期：`2026-09-04 22:00`

先检查标题长度不超过 80，且 manager/archive 无精确标题。然后重复第 10、11.2、11.3 节流程；本标题只点击一次。

⚠️ 危险操作检测！  
操作类型：在 Bilibili 9226 生产账号创建第二条真实定时验收稿件  
影响范围：生成一条计划于 2026-09-04 22:00 发布的稿件记录  
风险评估：真实进入审核/排期；重复操作会产生重复稿件  
授权状态：用户已于 2026-08-28 明确确认；仍须接受 Auto Review，不得绕过拒绝

验收必须同时满足第 2 节第 5 项。通过后转第 14 节。

### 13.2 验收仍失败时的唯一闭环

若第一验收失败：

1. 保存新的 hit-test、快照、脱敏网络、manager/archive 证据。
2. 判断它是否与原 RED 同根因。
3. 新增一个最小 RED，确认失败。
4. 做第二个最小补丁，重新跑专项和全量测试。
5. 使用备用素材和标题做第三次、也是最后一次真实点击：
   - 视频：`/Users/yelin/Documents/english-media-materials/hyperframes/render-workspace/videoFile-1787709497729-601582932/output.mp4`
   - 封面：`/tmp/browser-harness-bilibili-9226-tdd/fallback-cover.png`
   - 标题：`中国机器人跑赢博尔特｜外刊播客｜中英+文稿【链路验收0905】`
   - 简介：`本期英语新闻播客讨论中国机器人速度突破及其技术意义，提供中英双语文稿与英语听力练习。`
   - 排期：`2026-09-05 22:00`

第三次仍失败：禁止继续投稿。保存证据，恢复/关闭自己的标签页并释放租约；若同一阻塞条件达到 Goal 的三次连续判定门槛，则标记 `blocked`，否则继续做不产生外部写入的诊断，直到可合法更新 Goal 状态。

## 14. 阶段 G：清理与变更审计

每次真实测试后立即：

1. 关闭本任务用 `new_tab` 创建的标签页。
2. 正常结束 Browser Harness 进程以释放租约。
3. 执行 `./browser-harness agent-pool status`，只检查 9226 对应资源；其他账号存在租约不算失败。
4. 只读查询精确标题，确认每个标题至多一条。
5. 不删除已创建的定时稿件；用户已用远期排期隔离影响。

审计工作树：

```bash
rtk git status --short
RTK_DISABLED=1 git diff --stat
RTK_DISABLED=1 git diff --check
```

若出现白名单外变更，停止提交；辨认是否为用户已有改动，绝不覆盖或删除。

## 15. 阶段 H：Git 提交与生产版本发布

只有真实验收成功、全部测试通过、工作树无白名单外变更时执行。

⚠️ 危险操作检测！  
操作类型：Git commit  
影响范围：在 `/Users/yelin/Developer/agent-tools/browser-harness` 当前 `main` 创建本地提交  
风险评估：固化代码历史；不得包含用户无关改动，不得 push  
授权状态：用户已于 2026-08-28 明确确认；仍须接受 Auto Review，不得绕过拒绝

逐个添加实际变更文件，不使用 `git add .`：

```bash
git add "agent-workspace/domain-skills/bilibili/publishing.py" "tests/unit/test_bilibili_publishing.py"
```

若 `publishing.md` 确有契约变化，再单独添加；计划文件也单独添加。提交前运行 `git diff --cached --check` 和完整 staged diff 审计，然后：

```bash
git commit -m "fix(bilibili): verify 9226 submission acceptance"
```

不得 push。

提交后再次运行：

```bash
rtk uv run --with pytest pytest -q
rtk python3 scripts/verify_domain_skills.py
rtk git status --short --branch
```

生产发布前必须是 `main`、工作树干净、HEAD 已提交。

⚠️ 危险操作检测！  
操作类型：发布 Browser Harness 新生产版本  
影响范围：写入 Browser Harness 版本化生产目录并更新 `/Users/yelin/.local/bin/browser-harness-prod` 稳定入口  
风险评估：后续生产任务将使用新版本；旧版本必须保留用于回滚  
授权状态：用户已于 2026-08-28 明确确认；仍须接受 Auto Review，不得绕过拒绝

只发布 Browser Harness，不发布 SAU 或 Peach：

```bash
python3 "/Users/yelin/.codex/skills/production-toolchain-manager/scripts/toolchain.py" promote --tool browser-harness --confirm-promote browser-harness
python3 "/Users/yelin/.codex/skills/production-toolchain-manager/scripts/toolchain.py" verify --tool browser-harness
```

记录新版本号、release id、source version、稳定入口和保留的前一版本。若 `promote` 或 `verify` 失败，不手工改 symlink，不伪造成功；保留完整原始输出并按阻塞规则处理。

## 16. 最终验收清单与报告模板

结束前逐项核对：

- [ ] Goal 状态与执行账本一致
- [ ] Job 98 基线的标题、素材、排期和点击次数准确
- [ ] 根因由实时证据确认，不是复述 Hermes 假设
- [ ] RED 的失败输出已记录
- [ ] GREEN 后专项、全量、Domain Skill 校验全部通过
- [ ] 真实验收 `verified`，且 manager/archive 证据闭环
- [ ] 每标题至多一条，每标题只点击一次
- [ ] 总真实提交点击不超过 3
- [ ] 所有排期在 2026-09-01 至 2026-09-07，且未使用立即发布；最新卡片显示 `审核中` 时，审核后的状态不属于本 Skill
- [ ] 9226 无本任务残留租约、写锁或标签页
- [ ] Git 只提交白名单文件，无 push
- [ ] 新生产版本 verify 成功，旧版本仍可回滚

最终报告必须用简体中文，包含：

1. 根因：一句话，附关键 hit-test/网络/manager/archive 证据。
2. TDD：RED 测试名称、原始失败原因、最小实现位置。
3. 真实稿件：标题、排期、`aid/bvid`、manager/archive 匹配结果、提交点击次数。
4. 回归：专项、全量、Domain Skill 校验结果。
5. Git：commit hash；明确“未 push”。
6. 生产：旧版、新版、稳定入口、verify 结果。
7. 清理：9226 租约和标签页状态。

如果当前不可复现，则报告必须明确：基线真实提交已成功、未改代码、未创建 commit、未发布新生产版本，以及为什么这是正确收口。

## 17. 执行账本（2026-08-28）

- 阶段：真实基线、TDD 修复、备用素材验收已完成；当前进入提交与生产发布。
- Git：执行前 HEAD 为 `0b6dcba chore: record local operating boundaries`；当前变更仅为本计划、`publishing.py`、`publishing.md` 和单元测试。
- 真实点击：基线标题 1 次；0904 验收进程在产出计数前退出且归档/管理页均无记录，未重试；0905 备用标题 1 次。未超过 3 次总上限。
- 基线证据：精确标题唯一归档记录 `aid=117172093391350`、`bvid=BV1oXtA6rEHa`；此前管理页最新卡片精确匹配并显示 `审核中`，按用户口径发布完成。
- 备用验收证据：精确标题唯一归档记录 `aid=117172143857355`、`bvid=BV1BUtA6LEBE`；管理页最新卡片精确匹配并显示 `定时发布 2026年09月05日 22:00`。
- 质量门禁：专项和全量测试 `306 passed`，Domain Skill `PASS registry=102`，`git diff --check` 通过。
- 9226：浏览器仍运行，最新 Agent Pool 状态 `leases=[]`、`write_locks={}`；本任务创建的标签页已关闭，未停止浏览器。
- 下一动作：逐文件暂存并提交；提交后运行全量验证，再用生产管理脚本 promote/verify Browser Harness。

完成所有必要工作后调用 `update_goal(status="complete")`。若 Goal 带有后端报告的实际 token 使用量，最终一并报告；本计划不设置 token budget。
