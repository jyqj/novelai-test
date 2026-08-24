# templates/ — 项目模板库(novel.py init 母版)

novel.py 从本目录实例化项目文件。占位规约:`[方括号]`=待填,填后删除括号;枚举/数值字段已置合法默认值;md frontmatter 扁平(单行 `key: value`,内联 JSON 字段用合法值如 `aliases: []`),禁多行与嵌套。格式契约见 `protocol/formats.md`。

## 模板 → 项目路径映射

| 模板 | 实例化为 | 时机(落盘一律经 novel.py) |
|---|---|---|
| config.json | config.json | init 拷贝,向导改值 |
| book.md | tree/book.md | init 建空壳(status=empty);书庭 S1–S4 充实,commit 定稿 |
| style.md | tree/style.md | init 建空壳;书庭定文风;禁忌节预置黑名单即刻被 check --unit 取用 |
| world.md | tree/world.md | init 建空壳;书庭 S2 定稿 |
| volume.md | tree/vol_NN/volume.md | tree add volume 实例化;卷庭定稿 |
| arc.md | tree/vol_NN/arc_NN_n.md | tree add arc 实例化;弧简流程定稿 |
| chapter.md | chapters/ch_NNNN.md | write 任务 commit 落盘(status=drafted) |
| chapter.task.json | chapters/ch_NNNN.task.json | novel.py 自弧计划「章分配草案」抽骨架;编排者排批补 beats/hook |
| chapter.meta.json | chapters/ch_NNNN.meta.json | commit 自写手 writeback 块持久化 |
| entity-char.md | entities/char_{slug}.md | 设计庭/卷庭建卡;commit 追加事件日志;对账轮重写现状节 |
| entity-item.md | entities/item_{slug}.md | 同上 |
| entity-loc.md | entities/loc_{slug}.md | 同上 |
| entity-fac.md | entities/fac_{slug}.md | 同上 |
| thread.md | threads/thread_{slug}.md | 设计/写作中登记;commit 追加推进日志并迁移 state |
| decision.md | court/dec_NNN_{slug}.md | 每场庭后主编产出,编排者落盘;否决案台账拦截无证据重提 |
| review.md | reviews/ch_NNNN.light.md 或 .deep.md | 轻评/深评子代理产出,commit 落盘 |

## init 行为

1. `novel.py init <dir>`:生成 formats §1 全目录骨架 + git init + 首 commit。
2. 直接实例化:config.json 与 tree/{book,style,world}.md(status=empty,占位待填)。
3. 其余模板按需实例化:tree add(volume/arc)、排批(chapter 三件套)、建卡/登记(entity/thread)、庭后(decision)、评审(review)。
4. ledgers/、tasks/queue.json、state/、entities/aliases.json、briefs/、court/transcripts/、data/feedback/、corpus/ 由 novel.py 内置生成,不从模板拷贝。
5. 单写者纪律:项目内一切写入经 `novel.py commit`;状态迁移合法性见 formats §3,必需标题节机检见 formats §4/§17。
