# 工具链与验证

Python 3.10+ 标准库实现。入口是 novel.py；在小说目录外固定工具绝对路径，见上级 README。协议为 ../protocol/formats.md，当前可靠性与迁移为 ../protocol/reliability.md。

## 模块边界

| 模块 | 职责 |
|---|---|
| common / project | 文本格式、项目路径、队列、共享读写 |
| transactions | 单主机锁、逐文件前镜像、异常回滚、崩溃恢复；Git 不是回滚替代品 |
| structure / commitflow / bootstrap | 唯一创建、首次写入/返修、消费指纹、初始化和收编 |
| review / receipts | 当前版本 checklist、逐项证据、内容哈希、冲突票与历史归档 |
| narrative / knowledge | 叙事记忆、历史知情/读者揭示、关系与状态选择 |
| brief / dependencies | 按依赖装包、字符预算、manifest 内容失效判断 |
| journal / rollup / extract | 账本、摘要索引、文本与自报对账；rollup 仍为全量重算 |
| checks / gate / serial_ops | 机械断言、统一批准/发布检查、连载状态 |
| stagectl / consult / court | 阶段导航、按症状有界借阅、设计工作区 |
| status / cli | 仪表盘与参数分发 |

## 关键命令

`init`、`tree`、`task`、`entity`、`thread`、`brief`、`check`、`commit`、`publish`、`retcon`、`checkpoint`、`ledger`、`facts`、`extract`、`gate`、`court`、`status` 沿用原有入口，参数以 --help 为准。

新契约：

```bash
python3 "$NOVEL" review checklist ch_0001 > /tmp/review.json
# 真正评审后填写，pending 不接受。
python3 "$NOVEL" review add ch_0001 --depth light --verdict pass --evidence /tmp/review.json
python3 "$NOVEL" knowledge grant fact_000001 --to char_a --ch ch_0005
python3 "$NOVEL" knowledge query --at ch_0004
python3 "$NOVEL" stage consult K-CONCEPT-001 --target ch_0001 --reason "核心冲突缺乏可展开性"
python3 "$NOVEL" recover
python3 "$NOVEL" recover --rollback
```

--note 是 review --issue 别名，不是评审证据。旧无哈希 pass 不自动迁移为新票；必须重新评审。发布本地状态不等于外部平台上传。

## 断言分级

FAIL 阻止机械契约违规：非法输入/路径/状态、覆盖已存在资产或 published、任务重复换载荷、未登记引用、无证据回执、待裁定/冲突阻塞、必需记忆缺失、简报强制内容超预算。项目 style 已登记黑名单仍是硬规则；修改需先修订 style。

WARN 表示风险：排比同首句、段落重复、指纹相似、节奏/战力频率等。NEEDS_REVIEW 是必须逐项裁定的主观问题；有 quote 不等于解释自动正确，有 pass 不等于已证明好看。

## 测试

```bash
for suite in tools/tests/test_*.py; do python3 "$suite" || exit 1; done
```

- test_smoke / test_refactor：已有端到端和返修账本覆盖，补充新证据夹具、预算拒绝与安全工作区语义。
- test_longrun：35 章合成生命周期，测试发布、修订、事实 ID、台账和缓存。不是文学 benchmark。
- test_matrix / test_stage：历史授予/圈成员、阶段闸门、默认知识池与引用对账。默认池仍保持不重不漏，但不禁止有记录的跨阶段使用。
- test_integrity：故障注入、真实进程死亡恢复、并发锁、篡改/重放、评审绕过负例、历史泄漏、关系/情绪记忆与预算。
- test_quickstart：直接抽取 README 的初始化代码，在空目录执行，不依赖 shell 当前目录暗约定。

support.py 隔离工作目录与测试 Git 身份，合成回执明确标记 synthetic。旧场景使用此夹具仅为测试流程；负例直接使用公开 CLI，不自动补票。每个 suite 可独立运行，CI 保留完整日志和精确源码快照。

## 当前边界

项目主写入受单主机 CLI 事务保护；init 在新空目录脚手架创建阶段尚无项目事务。恢复拒绝覆盖作者后来修改；没有前镜像的旧 journal 只能人工协调。Git 无身份时不自动暂存。直接手改不属于权限隔离沙箱，published_hash 只检测正文变更。

历史无证据数据会降级而非编造。深评机械票仅章级，历史返修未自动完成下游语义修复。简报检索是结构/关键词规则，依赖扫描与 rollup 尚非索引化增量引擎。真实读者、模型创作对照和百万字性能实验未执行；不能把测试绿等同优秀作品保证。
