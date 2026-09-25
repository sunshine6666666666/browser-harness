# Issue: ChatGPT 2026-09-25 前端改版导致 chatgpt Domain Skill 发布链路失效

- 状态：**已修复并经生产验证**（本 fork main 分支，未向上游 browser-use/browser-harness 提 PR）
- 影响文件：`agent-workspace/domain-skills/chatgpt/basic_ops.py`
- 发现时间：2026-09-25 早晨，English Review 定时任务三个会话发布全部失败
- 本文件用途：本地排障入口。任何依赖 chatgpt Domain Skill 的调用方（english-review-publish、english-shadowing 等）发布失败时先读本文件核对 UI 假设是否过期。

## 现象（2026-09-25 实测）

1. 首页 composer 定位失败：`form[data-type="unified-composer"]` 不存在，新 UI 改用 `form[data-chatgpt-composer]`。
2. `?q=` 预填后全文已在 ProseMirror 编辑框中，但发送按钮保持 `disabled`——必须派发一次 `input` 事件 React 才重新注册草稿。
3. 发送按钮按 aria-label（发送提示/发送提示词/Send prompt）匹配不到，新按钮可靠特征是 `type=submit`。
4. 侧边栏会话行不再含 `<a href>`：当前打开会话的行是 `div[role="button"][aria-current="page"]`，标题在 `[data-thread-title]`，行内操作按钮 aria-label 为「聊天操作」（英文 Chat options）。
5. `rename_chat` 旧的 value-setter + blur + 对 composer form 派发事件全部失效；Enter 与 blur 均不提交。新版提交方式：聚焦标题输入框 → `press_key("a", 4)` 全选 → `type_text` 键入 → 对标题框所在 `form` 的 `button[type=submit]` 派发完整 pointer/mouse 序列。
6. localStorage 草稿（`oai/apps/conversationDrafts`）会把探测期间输入的文字反复恢复进输入框；探测/实验后必须用 `execCommand` 清空并走清空保存往返，否则残留文本污染下一次发送。

## 修复内容（代码内均带 `2026-09-25 UI` 注释）

1. 全部 composer 定位改为旧选择器优先、`form[data-chatgpt-composer]` 兜底（`observe_chatgpt_state`、`_composer_state`、`_find_composer_picker`、`new_chat`、`_activate_composer_picker`、`_prefill_via_qparam`、`send_message`、`send_and_wait` 等约 12 处）。
2. 新增 `_nudge_composer_after_prefill()`：`?q=` 预填全文校验一致后 focus + 派发 `InputEvent('input')`，随后 15 秒轮询发送按钮可用；不可用直接抛错，不点击。
3. `send_message` / `send_and_wait` 的发送按钮匹配追加 `type=submit` 兜底。
4. `_open_exact_conversation_options`：`<a>` 匹配唯一时走原路径；否则要求当前页 URL 即该会话（`/c/<id>`），对 `div[role="button"][aria-current="page"]` 做带坐标的 hover 序列后点击「聊天操作/Chat options」按钮。
5. `_read_exact_conversation_row`：无 `<a>` 时同样仅信任当前会话页上的 aria-current 行，从 `[data-thread-title]` 读标题。
6. `_rename_chat_once` 重写为上述「聚焦 → 全选 → 键入 → form submit」序列。
7. 兼容策略：全部为「旧选择器优先、新选择器兜底」，未删除旧路径；若 ChatGPT 再回滚 UI，旧逻辑仍可用。

## 2026-09-26 追加：侧边栏行回退为 `<a href>`，但行内结构混合

English Shadowing 09-26 轮实测：侧边栏会话行**恢复为 `<a href="/c/<id>">`**（`[data-thread-title]` 在行内 `<span>` 上），但与旧版不同：

1. 行内操作按钮**没有** `history-item-\d+-options` testid，只有 `aria-label="聊天操作"/Chat options`；
2. 该按钮不是 `<a>` 的子节点，而是 `<a>` 的**兄弟节点**（行容器 `div` 下 `<a>` + `<button>` 并列），`a.closest('li')` 内找不到按钮；
3. 合成 `btn.click()` 打不开菜单，必须像 aria-current 分支一样派发带坐标的完整 pointer/mouse 序列。

修复（同日，仍收敛在 `_open_exact_conversation_options` 的 `<a>` 分支）：`<a>` 唯一命中后，从锚点向上最多爬 4 层找 `aria-label=聊天操作` 按钮，并改用完整指针事件序列点击。`rename_chat` 内部流程（菜单→重命名→聚焦→全选→键入→form submit）与行读回校验未改，实测通过。另注意：`full_conversation()` 返回值**不含 `title` 键**，调用方校验重命名结果应使用 `_read_exact_conversation_row()`，不要用 `conv.get("title")`。

## 验证

- `python3 -m py_compile` 通过。
- 2026-09-25 08:52 生产冒烟：English Review 09-25 三个会话 **3/3 发布 + 重命名 + 规范 URL 核对成功**（发布脚本：english-review-publish/scripts/publish_review.py，浏览器 AgentPool-共享主浏览器-9223）。

## 调用方影响

- english-review-publish / english-shadowing 的调用方式**不变**（仍走 `send_message` 单发 + 轮询规范 URL + `full_conversation` 核对 + `rename_chat`），修复完全收敛在 Domain Skill 内部。
