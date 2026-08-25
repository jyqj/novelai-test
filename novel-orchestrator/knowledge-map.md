# knowledge-map.md — 111 块知识的归属台账（按块的视图）

knowledge/ 是深读库，**运行期默认零加载**。本表回答唯一问题：某块知识在 v2 体系里从哪进入
工作流。**按场/按阶段检索不走本表**——阶段视图在 `protocol/stages/` 各包（每场庭审的 K 池），
装载规则 SSOT=`protocol/knowledge-orchestration.md`；本表是块级归属的对账基准
（stages/ 包 K 池 ≡ 本表场次标注，由 `tools/tests/test_stage.py` 机检）。三种归属：

| 归属 | 含义 | 进入方式 |
|---|---|---|
| **蒸馏→rubric** | 可操作判据已提炼进某张判据卡（含阈值） | 运行期只读该 rubric，**不回读原块**；仅当判据存疑/需改卡时经 `knowledge-blocks.md` 锚点回读 |
| **庭审附件** | 设计期输入：编排者在对应庭审场次把该块列入 R0 投递白名单 | 场次代号：书庭 S1/S2/S3/S4、卷庭、弧/细纲（弧规划与 traditional 细纲工序）、卷末（checkpoint 深评） |
| **仅 learn** | 学理基座/诊断素材，不进任何常规流程 | 只在「诊断疑难/用户求教/改判据卡」时按块深读，读完即弃 |

## 运行期防膨胀规则（硬约束）

1. **写作产线零知识**：写手/轻评/深评永不加载 knowledge/——写手只见简报，评审只见 rubrics。
2. **庭审附件白名单制**：本表的场次标注是**可选池**，不是必读清单——按场整理好的池
   （K-ID+名称+何时挑）见 `protocol/stages/` 对应阶段包；每场庭审由编排者按本场争点从池中挑
   **≤4 块**投递，且**每块只取锚点段**（锚点与 L1–L4 读法见 `knowledge-blocks.md` 检索协议）；
   附件进设计简报，不进章简报。
3. **诊断预算**：一次诊断 ≤2 块；先查本表定位，再经 knowledge-blocks 锚点取段，禁整文件读。
4. **改卡回流**：深读结论若有普适价值，改的是 rubrics/（并在卡的 K-ID 脚注登记来源），
   不是把原文抄进协议；knowledge/ 原文永远只读。

## K-CONCEPT 构思类（22）

| K-ID | 名称 | 归属 | 说明 |
|---|---|---|---|
| K-CONCEPT-001 | 高概念提问法 | 庭审附件·S1 | 概念提案生成 |
| K-CONCEPT-002 | 高概念元素拆解 | 庭审附件·S1 | 同上 |
| K-CONCEPT-003 | 元素等级划分（四档制） | 庭审附件·S1 | 元素评估 |
| K-CONCEPT-004 | 元素排列组合创新 | 庭审附件·S1 | 差异化提案 |
| K-CONCEPT-005 | 元素大纲规划法 | 庭审附件·S1 | 概念→分卷草案过渡 |
| K-CONCEPT-006 | 高概念与元素区分 | 仅 learn | 概念辨析 |
| K-CONCEPT-007 | 前提概念 | 庭审附件·S1 | 前提陈述句打磨 |
| K-CONCEPT-008 | 前提与高概念区分 | 仅 learn | 概念辨析 |
| K-CONCEPT-009 | 多维主线理论 | 庭审附件·S1 | 主线电缆素材 |
| K-CONCEPT-010 | 电缆理论 | 蒸馏→rubrics/structure.md | 主线电缆判据 |
| K-CONCEPT-011 | 引线系统 | 蒸馏→rubrics/structure.md | 线索纪律判据 |
| K-CONCEPT-012 | 支线系统 | 蒸馏→rubrics/structure.md | 支线配比判据 |
| K-CONCEPT-013 | 主控思想公式 | 蒸馏→rubrics/theme.md | 主控思想公式判据（S1 改附 rubric 卡） |
| K-CONCEPT-014 | 思想与反思想辩证 | 蒸馏→rubrics/theme.md | 思想-反思想对抗判据 |
| K-CONCEPT-015 | 三种结局模式 | 庭审附件·S4 | 分卷草案收束设计 |
| K-CONCEPT-016 | 规避说教 | 蒸馏→rubrics/theme.md | 说教检测判据 |
| K-CONCEPT-017 | 类型常规提炼法 | 庭审附件·S1 | 题材定位 |
| K-CONCEPT-018 | 类型混合策略 | 庭审附件·S1 | 题材定位 |
| K-CONCEPT-019 | 网文类型体系 | 庭审附件·S1 | 平台/赛道选择 |
| K-CONCEPT-020 | 免费流读者模型与短剧化节奏 | 庭审附件·S1 | 平台策略；data-analyst 可深读 |
| K-CONCEPT-021 | 题材红线与内容安全 | 蒸馏→rubrics/redline.md | 六域判定清单 |
| K-CONCEPT-022 | 书名与简介工程 | 庭审附件·S1 | 开书商业包装 |

## K-STRUCT 结构类（22）

| K-ID | 名称 | 归属 | 说明 |
|---|---|---|---|
| K-STRUCT-001 | 故事三角 | 蒸馏→rubrics/scene-value.md | 场景=价值变化单位（判据化） |
| K-STRUCT-002 | 五级单元 | 仅 learn | 理论基座 |
| K-STRUCT-003 | 23序列法总论 | 庭审附件·S4/卷庭 | 操作面已进 rhythm/classic24.md |
| K-STRUCT-004 | 序列0–6详解 | 庭审附件·S4/卷庭 | 同上 |
| K-STRUCT-005 | 序列7–12详解 | 庭审附件·S4/卷庭 | 同上 |
| K-STRUCT-006 | 序列13–18详解 | 庭审附件·S4/卷庭 | 同上 |
| K-STRUCT-007 | 序列19–23详解 | 庭审附件·S4/卷庭 | 同上 |
| K-STRUCT-008 | 激励事件设计 | 庭审附件·S1 | 开局设计 |
| K-STRUCT-009 | 故事五部分结构 | 仅 learn | 理论基座 |
| K-STRUCT-010 | 场景转折点 | 蒸馏→rubrics/scene-value.md | 价值翻转/turn 验收判据 |
| K-STRUCT-011 | 鸿沟机制 | 仅 learn | 深评诊断素材 |
| K-STRUCT-012 | 回报递减定理 | 庭审附件·卷庭 | 跨卷升级预算 |
| K-STRUCT-013 | 场景设计五步法 | 蒸馏→rubrics/scene-value.md | 场景五步完整性判据（弧/细纲改附 rubric 卡） |
| K-STRUCT-014 | 危机设计 | 庭审附件·弧/细纲 | 高潮前铺排 |
| K-STRUCT-015 | 高潮设计 | 庭审附件·卷庭 | 卷高潮设计 |
| K-STRUCT-016 | 结局设计 | 庭审附件·卷庭 | 卷末/全书收束 |
| K-STRUCT-017 | 故事脊椎 | 仅 learn | 理论基座 |
| K-STRUCT-018 | 节拍与潜文本 | 仅 learn | 深评诊断素材 |
| K-STRUCT-019 | 幕节奏公式 | 庭审附件·S4/卷庭 | 节拍间隔参数 |
| K-STRUCT-020 | 爽点类型学与密度 | 蒸馏→rubrics/payoff.md | 七类爽点+窗口阈值 |
| K-STRUCT-021 | 期待感链条 | 蒸馏→rubrics/payoff.md | promise 账户判据 |
| K-STRUCT-022 | 卷级0–23嵌套法 | 庭审附件·卷庭 | rhythm/classic24 卷内套用 |

## K-CHAR 人物类（14）

| K-ID | 名称 | 归属 | 说明 |
|---|---|---|---|
| K-CHAR-001 | 塑造vs深层性格 | 仅 learn | 理论基座 |
| K-CHAR-002 | 压力揭示法 | 仅 learn | 深评诊断素材 |
| K-CHAR-003 | 动机三层设计 | 庭审附件·S3 | 实体卡种子 |
| K-CHAR-004 | 洋葱式性格模型 | 庭审附件·S3 | 实体卡「设定」节参考结构 |
| K-CHAR-005 | 人物弧光五步法 | 庭审附件·S3 | 主角弧设计；卷庭复检 |
| K-CHAR-006 | 情境化表现 | 仅 learn | 深评诊断素材 |
| K-CHAR-007 | 关系镜像 | 庭审附件·S3 | 阵容关系设计 |
| K-CHAR-008 | 反差张力 | 庭审附件·S3 | 同上 |
| K-CHAR-009 | 关系演变 | 庭审附件·S3 | relationship 线设计 |
| K-CHAR-010 | 屁股决定脑袋 | 庭审附件·S3 | 动机一致性 |
| K-CHAR-011 | 配角生命周期状态机 | 庭审附件·卷庭 | 群像运营（阵容变化节） |
| K-CHAR-012 | 反派梯队与轮换 | 庭审附件·S3 | 反派梯队节；卷庭复检 |
| K-CHAR-013 | 角色声纹卡方法 | 蒸馏→rubrics/voice.md | 遮名指认判据 |
| K-CHAR-014 | 主角讨喜度与代入感工程 | 庭审附件·S3 | 主角设计 |

## K-CONFLICT 冲突类（6）

| K-ID | 名称 | 归属 | 说明 |
|---|---|---|---|
| K-CONFLICT-001 | 冲突三层面 | 庭审附件·S3 | 对抗结构设计 |
| K-CONFLICT-002 | 思想vs反思想 | 庭审附件·S3 | 反派=反论证 |
| K-CONFLICT-003 | 战败狗原则 | 庭审附件·S3 | 深评亦可引用 |
| K-CONFLICT-004 | 反面人物五步法 | 庭审附件·S3 | 反派梯队节 |
| K-CONFLICT-005 | 负面价值四层递进 | 仅 learn | 理论基座 |
| K-CONFLICT-006 | 对抗力量总和设计 | 庭审附件·S3 | 对抗预算 |

## K-WORLD 世界观类（24）

| K-ID | 名称 | 归属 | 说明 |
|---|---|---|---|
| K-WORLD-001 | 双重分裂模型 | 仅 learn | 理论基座 |
| K-WORLD-002 | 三层同心圆 | 仅 learn | 理论基座 |
| K-WORLD-003 | 隐喻本体论 | 仅 learn | 理论基座 |
| K-WORLD-004 | 背景四维度 | 庭审附件·S2 | world 四节素材 |
| K-WORLD-005 | Sanderson三大法则 | 庭审附件·S2 | 体系设计底线 |
| K-WORLD-006 | 短路现象 | 仅 learn | 设定审计诊断素材 |
| K-WORLD-007 | 身体现象学 | 仅 learn | 理论基座 |
| K-WORLD-008 | 历史推定法 | 庭审附件·S2 | 势力格局推演 |
| K-WORLD-009 | 两极分化原则 | 庭审附件·S2 | 势力设计 |
| K-WORLD-010 | 日常生活构建 | 仅 learn | 深评诊断素材 |
| K-WORLD-011 | 符号在场理论 | 仅 learn | 理论基座 |
| K-WORLD-012 | 解释效率体系 | 庭审附件·S2 | 核心规则条数纪律 |
| K-WORLD-013 | 代价机制设计 | 庭审附件·S2 | hard 规则代价 |
| K-WORLD-014 | 六种升级模式 | 庭审附件·S2 | 力量体系选型 |
| K-WORLD-015 | 技能分级（隐喻层级） | 庭审附件·S2 | 位阶表设计 |
| K-WORLD-016 | 修炼境界设计 | 庭审附件·S2 | 位阶表设计 |
| K-WORLD-017 | 技能体系构建流程 | 庭审附件·S2 | 体系落地步骤 |
| K-WORLD-018 | 三体交互核心原理 | 仅 learn | 理论基座 |
| K-WORLD-019 | 六大创作原则 | 庭审附件·S2 | 体系自查 |
| K-WORLD-020 | 层级应用（大中小） | 仅 learn | 理论基座 |
| K-WORLD-021 | 三体博弈叙事功能 | 仅 learn | 理论基座 |
| K-WORLD-022 | 战力锚定表与卷级增幅预算 | 蒸馏→rubrics/power.md | 锚定表+增幅预算判据 |
| K-WORLD-023 | 越阶战斗合法性配额 | 蒸馏→rubrics/power.md | 越阶配额判据 |
| K-WORLD-024 | 金手指边际递减设计 | 蒸馏→rubrics/power.md | 金手指审计判据 |

## K-WRITE 写作类（23）

| K-ID | 名称 | 归属 | 说明 |
|---|---|---|---|
| K-WRITE-001 | 展示不要告诉 | 仅 learn | 深评诊断素材 |
| K-WRITE-002 | 解说转化为弹药 | 仅 learn | 同上 |
| K-WRITE-003 | 解说进度金字塔 | 仅 learn | 同上 |
| K-WRITE-004 | 幕后故事使用 | 仅 learn | 同上 |
| K-WRITE-005 | 闪回正确运用 | 仅 learn | 同上 |
| K-WRITE-006 | 叙述者旁白检验 | 仅 learn | 同上 |
| K-WRITE-007 | 叙述视角与解说 | 庭审附件·S4 | style 叙述基准选型 |
| K-WRITE-008 | 作家六问 | 仅 learn | 理论基座 |
| K-WRITE-009 | 从内向外写作 | 仅 learn | 理论基座 |
| K-WRITE-010 | 步骤大纲法 | 庭审附件·弧/细纲 | traditional 细纲工序参考 |
| K-WRITE-011 | 网文连载流程 | 仅 learn | 操作面已进 protocol/serial-ops.md |
| K-WRITE-012 | 长篇分段创作 | 仅 learn | 操作面已进卷/弧协议 |
| K-WRITE-013 | 读者兴趣三策略 | 庭审附件·弧/细纲 | 期待操作表设计 |
| K-WRITE-014 | 惊奇与巧合处理 | 仅 learn | 深评诊断素材 |
| K-WRITE-015 | 意象系统（形象系统） | 蒸馏→rubrics/imagery.md | 意象系统纪律判据（S4 style 定稿改附 rubric 卡） |
| K-WRITE-016 | 对话写作技巧 | 仅 learn | 写手不读库；深评诊断用 |
| K-WRITE-017 | 描写写作技巧 | 蒸馏→rubrics/imagery.md | 描写六要诀/感官锚判据 |
| K-WRITE-018 | 口癖与句式重复防治 | 蒸馏→rubrics/prose-disease.md | 黑名单机制（机检已实现） |
| K-WRITE-019 | 打斗场面技法 | 蒸馏→rubrics/prose-disease.md | 打斗判据 |
| K-WRITE-020 | 章内微结构 | 蒸馏→rubrics/prose-disease.md | 500字信息密度/章尾钩 |
| K-WRITE-021 | 正文级水字数判据与修法 | 蒸馏→rubrics/prose-disease.md | 水字数判据 |
| K-WRITE-022 | 毒点防治与负面节拍降档 | 蒸馏→rubrics/toxicity.md | 毒点七问 |
| K-WRITE-023 | 防抄袭与融梗边界 | 蒸馏→rubrics/anti-plagiarism.md | 三级边界判据 |

## 统计与对账

- 合计 111 块：蒸馏→rubric **24**（11 张卡）；庭审附件 **54**（S1×13、S2×11、S3×14、
  S4×8（含标注"S4/卷庭"的 6 块）、卷庭×5、弧/细纲×3）；仅 learn **33**。
  （rev 2 变更：K-CONCEPT-013/014/016→theme、K-STRUCT-001/010/013→scene-value、
  K-WRITE-015/017→imagery——traditional 路线补齐自有判据卡；原庭审附件场次改附对应 rubric 卡。）
- 对账口径：本表行数与 `knowledge-blocks.md` 登记处一致；rubrics 卡脚注的 K-ID 引用
  （全 ID 逐个列出，不用斜杠缩写）与「蒸馏」列一致；场次标注与 `protocol/stages/` 各包
  K 池一致——三项对账全部由 `python3 tools/tests/test_stage.py` 机检。
- 新增知识块时：knowledge/ 原文加锚 → 登记 knowledge-blocks.md → 本表补归属行 →
  （若归属=庭审附件）同步 stages/ 对应包 K 池 → test_stage 绿（knowledge-orchestration §6.3）；
  无归属的块不得引用。
