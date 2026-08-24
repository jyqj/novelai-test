# adopt.md — 存量文稿/半途项目收编协议

> 场景：用户已有开头几章（或几十章）旧稿 / 从别的工具半途迁来，要求本 skill 接管续写。
> 原则：**先收编、后续写**——不在资产缺失的裸稿上直接排新章；但也不逼用户补齐全部
> 设计资产才开工（最小闭环见 §4）。CLI：`novel.py adopt <file> --as ch_NNNN`。

## 1. 盘点（收编前，编排者一次性完成）

1. 清点旧稿：章数、总字数、断更位置、有无既有大纲/人设文档。
2. `novel.py init <dir>` 建新项目（旧稿目录**不改动**，只读）。
3. 蓝图逆推：读旧稿 + 用户口述，按书庭**简化流程**（solo §3 三件套即可）补
   `tree/book.md`、`world.md`、`style.md` 到 committed——style 的口癖禁忌节可先只留
   预置黑名单，范文锚直接引旧稿最好的 2 段。
4. 建骨架：`tree add volume/arc`（按旧稿实际分段，粗分即可）；主要角色
   `entity new` + aliases.json 登记中文名；进行中的伏笔 `thread new`（state 按实情
   手工校正，plant_ch 填旧稿章号）。

## 2. 逐章导入

```
for 每章旧稿（按章号顺序）:
  novel.py adopt <旧稿文件> --as ch_NNNN --parent arc_NN_n --title <标题>
  # 落盘为 status=drafted + task.json 骨架 + meta.json stub（issues 标记 adopted）
  # 同时写入 ngram 指纹（后续新章即可查跨章重复）
```

- 已发布过的旧章：adopt 后依次 `task done --note "light=pass（存量既发）"` →
  `tree set-status approved` → `publish`，把游标推到真实断更位置
  （publish 连续性谓词要求从 ch_0001 开始依序补齐状态）。
- 未发布的存稿章：停在 drafted/approved，按 buffer 语义参与后续发布。

## 3. 补录（收编的核心账，宁缺勿假）

按优先级补 meta.json（可分批，每批跑 `check --project` 收敛）：

1. **summary_after**（每章 3–8 句）——简报 §2 的记忆链，缺了新章简报即断档。
2. **continuity_delta**——只补"后文还会用到"的事实（实体获得物/身份/位置/承诺），
   经一次性脚本或手工誊入后，对新事实统一走一遍 facts 登记：最简做法是把补录的
   delta 合入各章 meta.json 后，用 `retcon`/手工按 formats §9 写入
   `ledgers/facts/vol_NN.json`（id 递增不回填旧号）。拿不准的事实**不录**，
   宁可简报缺料让写手报 issues，也不录错账。
3. **thread_ops 追认**：threads/ 各线的推进日志手工补「- ch_NNNN: advance 一句话」
   到实情状态。
4. 实体现状节：跑一轮对账（serial-ops §5，资料员读旧稿产出现状节）。

## 4. 最小闭环（时间紧时的底线）

book/world/style committed + 主角实体卡 + aliases + 断更点前 3 章的 summary_after
+ 进行中 threads。**低于此线不排新章**——写手简报会大面积缺料，产出必然脑补。

## 5. 收编后自查

```
novel.py check --project      # 三件套/引用/facts 全绿
novel.py status               # 游标与 buffer 与实情一致
novel.py brief <断更点+1 章>  # 人工读一遍简报：§2 记忆链与 §6 事实是否够写
```

简报读起来"像给新写手的完整交接"即收编完成，进入正常产线（pipeline §1）。
