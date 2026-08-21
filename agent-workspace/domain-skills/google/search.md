# Google Search Domain Skill (google.com / *.google.com)

## Scope

通用搜索层：对**已消歧**的中文新闻实体，机械拉取 Google 公开搜索结果，
供调用 Agent 横向阅读判断官方英文名、权威通行译名或规范拼音。本 Skill
只负责“搜索层”：

- 只机械返回结构化结果，**不翻译、不判断哪个英文名正确、不判断新闻真假**；
- 无官方译名证据时，由调用方业务 Skill 回退规范拼音（本层不负责）；
- 覆盖当前/未来新闻、地点、机构、台风、人名、作品等长尾实体，前提是
  调用方先确定实体具体指代（例如先确定“武汉天桥”指哪座桥，再搜索）。

Hosts: `google.com` / `*.google.com`。

## 使用边界

- 输入必须是已消歧的具体实体，建议查询模板：
  `"<实体> official english name"` 或 `"<实体> english name site:.gov.cn"`。
- 模糊词组（如 `武汉天桥`、`新台风`）不是本层有效输入，调用方必须先消歧。
- 只读：打开 google.com/search，提取结果块；不点击进入结果页，不提交表单，
  不发布任何内容。
- 限速：连续查询默认间隔 `MIN_QUERY_DELAY = 4s`；批量上限
  `MAX_BATCH_QUERIES = 20` 次/调用，超出需调用方分块。
- 验证码/consent：遇到 `/sorry/` 或 consent 页，**抛 RuntimeError 并停止**，
  这是 human blocker，不要在循环里重试。
- 浏览器：通过 source wrapper 的 `agent-pool run/exec` 进入；pool 按当前
  Profile 和账号分配共享或临时会话并负责清理。调用方不得指定 CDP endpoint、
  选择 CDP 端口或手工选择/复制/删除浏览器 Profile。

## UI facts（2026-08-12 实测）

Google SERP（`/search?hl=en&num=8`）：

- 结果块：`div[data-snc]` 内包含 `a h3`（标题锚点）。class 名轮换
  （`N54PNb BToiNc`、`srKDX` 等），因此按结构选择，不按 class 选择。
- 标题：`a h3` 的 textContent。
- URL：最近的 `a` 的 href。
- 摘要：`.VwiC3b` 文本（部分块/图片块可能缺失）。
- rank：SERP 上前 N 个 `a h3` 锚点的 1 起始顺序。
- consent/验证码页特征：`#consent-bump`、`form[action*="consent"]`、
  `/sorry/` URL、`#captcha-form`。
- `num=8` 为实用默认：Google 对 `num>10` 多数 SERP 仍只给约 8-10 条。

## Functions

### `search(query, num_results=8, min_delay=4.0)`

返回结构化结果列表，每项：

```python
{
  "query": str,            # 原查询
  "rank": int,             # 1 起始
  "title": str,            # 标题
  "url": str,              # 结果 URL
  "snippet": str,          # 摘要（可能为空字符串）
  "source_domain": str,    # 规范化域名（去 www.）
}
```

- 抛 `RuntimeError`：验证码/consent 墙（human blocker）、无结果锚点（SERP 结构变更）。
- 查询前 `sleep(min_delay)`，供循环调用限速。

### `search_many(queries, num_results=8, min_delay=4.0)`

串行批量查询（带限速），返回每个查询的结果列表；超过 20 个查询抛
`ValueError`（调用方分块）。遇到验证码立即停止（不循环重试）。

### `run(query, num_results=8)`

`exec(open(...).read())` 下的 CLI 入口：打印 `rank. title | url | source_domain`。

## Example

```bash
/Users/yelin/Developer/agent-tools/browser-harness/browser-harness agent-pool run \
  --site google.com --account default --mode read <<'PY'
new_tab("https://www.google.com/search?hl=en&num=8")
print(page_info())
exec(open("/Users/yelin/Developer/agent-tools/browser-harness/agent-workspace/domain-skills/google/search.py").read())
run("武汉天兴洲长江大桥 official english name", 8)
PY
```

## Verification checklist

- [ ] `search("武汉天兴洲长江大桥 official english name", 8)` 返回
      ≥6 条结果，每项含非空 title/url/source_domain，rank 1 起始连续。
- [ ] 结果包含权威来源（Wikipedia / english.wuhan.gov.cn / baike.baidu.com 等）。
- [ ] 连续两次查询间隔 ≥ `MIN_QUERY_DELAY` 秒。
- [ ] `/sorry/` 或 consent 页时抛 `RuntimeError` 且不重试。
- [ ] `verify_domain_skills.py` 通过（注册一致）。
