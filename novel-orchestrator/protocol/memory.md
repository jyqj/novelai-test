# memory.md — 摘要梯队规范（L3 上下文编译层）

> commit 时 `novel.py` 自动 rollup；编排者可在卷末 checkpoint 人工润色 recap。

## 1. 四层记忆金字塔

| 层 | 文件 | 生成 | 注入简报 |
|---|---|---|---|
| 章摘要 | `chapters/ch_NNNN.meta.json` → `summary_after` | 写手 writeback | §2 summary 链（前 3 章） |
| 弧文摘 | `state/digests/arc_NN_n.json` | commit 钩子 rollup | §2 本弧文摘（尾 8 条） |
| 卷文摘 | `state/digests/vol_NN.json` | commit 钩子 rollup | §2 本卷文摘（尾 5 条） |
| 书状态 | `ledgers/recap.md` | 卷末 checkpoint 人工 + 机器草稿 | §2 recap 尾 12 行 |

## 2. rollup 纪律

- 每次 `commit write/revise` 成功后，若 `summary_after` 非空，写入对应弧/卷 digest JSON。
- 同章重复 commit（revise）按 chapter 键替换，不追加重复条目。
- digest 条目格式：`{"chapter","summary","updated_at"}`。

## 3. recap 机器草稿（建议）

卷末 checkpoint 前，编排者可将本卷 digest 尾 N 条压缩为 3–6 行写入 `ledgers/recap.md`；
brief 只读尾 12 行，禁止通读全书。
