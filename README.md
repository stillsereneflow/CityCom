# 城脉·涟控（CityPulse）

**事件感知的交通数字孪生与离线决策保真度审计（实验室原型）**

English: [README.en.md](README.en.md)（早期 D1–D4 原型的英文说明）

本项目在一条按香港观塘道 / 观塘绕道走廊构建的合成路网上（SUMO 1.27.1），搭建了两个互相隔离的仿真世界：

- **代理世界（Proxy）**：隐藏的"真实世界"。采用 IDM 驾驶模型，并注入真实事故：`ktb_n1` 第 0–1 车道在 900 m 处被封堵，持续时间为 4,500–5,400 s。
- **孪生世界（Twin）**：被测系统。采用 Krauss 驾驶模型，与代理世界刻意保持结构性差异；需求来自独立的泊松稀疏化需求流，并做常规同化。孪生**只能**经 ZeroMQ 防火墙收到稀疏、带噪声的检测器消息（21 个检测器中的 14 个，30 s 粒度，含测量噪声与 5 % 丢包），从不读取代理世界的状态。

在决策时刻 t_d = 5,100 s，孪生通过**快照分支**对 5 个基础设施级动作做反事实推演，预测每个动作在未来 15 分钟内的总行程时间 J（车·时）：

| 动作 | 内容 |
|---|---|
| A0 | 不干预 |
| A1 | 事故信号预案 |
| A2 | VMS 诱导（假设遵从率 0.30） |
| A3 | A1 + A2 |
| A4 | 提示更强的 VMS 诱导 |

随后在代理世界中，从它自己的 t_d 状态出发执行同样 5 个动作（真实遵从率 0.35，真实事故），得到最优动作（oracle），以此**离线审计**孪生决策的保真度。同一复制内使用公共随机数（CRN），选择用的复制与评估用的复制分开，每个分支在全新进程中运行。方法细节见 [`final/METHOD.md`](final/METHOD.md)。

## 主要结果：冻结测试审计

设计于 2026-10-06 冻结。8 个从未使用过的测试种子（4501–4508）在冻结后**只运行一次**。孪生采用"持续点状封堵"的事故假设（belief B）。区间为 8 个种子上的 95 % t 区间，单位为车·时。

| 指标 | 冻结测试（4501–4508） | 开发集（4201–4208） |
|---|---|---|
| 孪生选择的动作 | A3 8/8 | A3 8/8 |
| 代理世界最优动作 | A3 7/8（4508 为 A4） | A3 7/8（4208 为 A4） |
| Top-1 一致 | 7/8 | 7/8 |
| 收益估计误差 BEE（预测收益 − 实现收益） | **+2.162 [1.738, 2.586]** | +1.632 [1.041, 2.222] |
| BEE 占 A0 总行程时间的比例 | 1.9 % | 1.4 % |
| 分拆遗憾 | −0.034 [−0.113, 0.046] | 0.029 [−0.040, 0.098] |
| Spearman / Kendall | 0.825 [0.738, 0.912] / 0.675 | 0.850 / 0.750 |
| 校准差异（以代理世界替代孪生） | 0.316 [0.134, 0.499] | 0.181 [0.080, 0.281] |
| 固定 A3 的收益：孪生预测 vs 代理实现 | 7.066 vs 4.904 | 6.757 vs 5.126 |
| **D300 对照**（告知真实清除时间）的 BEE | −2.870 [−4.914, −0.826] | −3.187 [−5.474, −0.899] |

- **常数基线**：代理世界的最优动作在 7/8 个种子上就是 A3，所以"始终选 A3"的常数策略同样能达到 7/8 的一致率。7/8 本身不能说明孪生的决策能力。
- **完整性**：960/960 个分支全部成功，没有重跑、重复或剔除；种子新鲜度与随机数隔离检查通过；采集前后代码哈希一致。
- **独立复核**：全部指标由三套实现分别复算：项目分析器，以及两份独立编写、不调用分析器的复算脚本。三者结果一致。
- **与开发集比较**：冻结测试**复现了同一场景下的规律**：选择 A3、7/8 一致、收益高估、排序强正相关、遗憾接近零。冻结集的点估计更大（BEE +2.16 vs +1.63，校准差异 0.32 vs 0.18），但这既不能确定精确幅度，也不能说明两组之间存在差异或等价。两组数据从不合并。

## 支撑研究（均预注册，并从原始数据复核）

| 研究 | 结果 |
|---|---|
| 缺失排队诊断（种子 4301–4304） | 结论为"支持"。把事故历史回放进孪生后，在真实清除时间下，固定 A3 的收益绝对误差从 4.16 降到 0.90 车·时（配对变化 −4.58 / −3.25 / −3.06 / −2.17）。t_d 时的排队车辆：代理世界 55 / 7 / 40 / 25，常规孪生 0，回放历史后的孪生 14–19。对事故持续时间的敏感度从 6.0–7.7 降到 1.4–3.0。完整动作排序没有改善。 |
| 回放诊断（3 条记录的事故数据流） | 点状封堵加上真实起始时间，使假设性的"会采纳"评估从 0/13 升到 6/13；在 9 次合成的无事故评估上全部为负。这些是相互依赖的离线评估，不是控制器轨迹，也不是误采纳率。 |
| 事件开发运行（48 次运行） | 13 个疑似事件片段、25 次假设库评估，自然采纳 0/6。事件感知孪生与常规孪生的预测完全相同（事故场景的 MAE 在 5 / 15 分钟分别为 20.6 / 18.8 辆停驶车辆）。无事故、需求冲击、传感器故障场景均未报警；需求冲击实际只带来 5–8 % 的额外走廊流量，故障检测器停在正常读数上。 |
| 事件引擎机制覆盖 | 触发、假设库评估与预测：在实时运行中验证。采纳、状态替换、清除与恢复：仅在强制运行中验证（清除过早 3/3，恢复正常完成 1/4）。DEGRADED 状态的定时退出：仅有单元测试。 |

以下是**解释**，不是已证实的结论：

- 结果与"误差相互抵消"一致：持续封堵的假设部分抵消了孪生缺失的事故历史。
- 恢复历史状态的实验支持用"继承状态"来解释孪生对持续时间假设的敏感性。
- 动作选择一致而收益估计偏乐观，提示决策一致与收益估计准确可能出现分离。

## 局限，以及本项目不作的声明

局限：

- 只有一条合成走廊、一种事故类型、一个决策时刻、一套动作菜单；测试种子为 8 个。
- 冻结审计评估的是**被给定事故假设的常规孪生**，不是在线事故推断。
- 事件引擎从未自然采纳事故假设；常规同化（NA-300）未通过资格检验，后验温度（β = 0.25）与各阈值未经校准。
- 缺失排队诊断的证据只有 N = 4，属于描述性证据；回放历史改变的是孪生的全部继承状态，不只是排队。
- 校准差异是蒙特卡洛经验水平，不是可证明的下界，也从不从 BEE 中扣除。
- 分拆遗憾的参照是在 M₁ 上选出、在 M₂ 上评估的最优动作；负遗憾不代表孪生胜过真正的最优。

本项目**不**声称：可靠的事故推断、可直接部署、在真实道路上有效、事件同化优于常规同化、收益预测普遍准确，也不报告任何合并开发集与测试集的统计量。

允许使用的全部表述见 [`final/CLAIMS.md`](final/CLAIMS.md)（英文，附中文摘要）；完整报告见 [`final/FINAL_REPORT.md`](final/FINAL_REPORT.md)。

## 目录结构

| 路径 | 作用 |
|---|---|
| `final/` | 最终证据包：报告、允许表述、方法、图、表、决策卡演示 |
| `submission/` | 提交材料：项目简表、作品说明书、答辩 PPT、演讲稿、演示视频、匿名化源码包及检查脚本 |
| `release/` | 发布版 `competition-submission-v1.0`，附逐文件 SHA256 校验，内容不再修改 |
| `docs/` | 设计冻结记录、各阶段决策文档与预注册计划 |
| `results/` | 支撑结论的实验数据与汇总，冻结审计在 `results/frozen_audit/` |
| `citypulse/hkdata/` | 香港运输署检测器数据：解析、实时记录、历史回填 |
| `citypulse/network/` | OSM → SUMO 路网、检测器映射、事故信号预案 |
| `citypulse/demand/` | 由香港流量数据分别生成代理世界与孪生世界的独立需求（routeSampler） |
| `citypulse/proxy/` | 代理世界服务、传感器模拟、事故注入；`truth_config.py` 是只属于代理世界的真值 |
| `citypulse/twin/` | 孪生服务、泊松稀疏化需求流 |
| `citypulse/bus/messages.py` | 防火墙：两个世界之间仅有的两种消息类型 |
| `citypulse/control/actions.py` | 基础设施级动作：信号预案、VMS 与遵从模型 |
| `citypulse/branching/engine.py` | 快照 → 并行分支 → KPI |
| `citypulse/experiments/` | 实验驱动、审计分析、检查与作图 |
| `tests/` | pytest 测试 |
| `deep-research-report2.md` | 设计方案 |

## 环境配置（Windows，Git Bash）

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

以下命令都在仓库根目录运行，运行前先设置环境变量：

```bash
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 CITYPULSE_NET=blite CITYPULSE_BLITE_REV=5 CITYPULSE_REROUTE=0
```

## 复核结果

只读复核（不改动任何结果文件）：

```bash
.venv/Scripts/python.exe -m pytest -q tests        # 提交 4fe70e0 时：222 通过，3 跳过
.venv/Scripts/python.exe results/frozen_audit/crosscheck_claude/indep_audit.py results/frozen_audit/raw.parquet belief=B
.venv/Scripts/python.exe final/demo/decision_card.py --seed 4501
```

重新生成图与表（会覆盖 `final/figures/` 和 `final/tables/` 中的文件）：

```bash
.venv/Scripts/python.exe final/figures/generate_figures.py
.venv/Scripts/python.exe final/tables/build_tables.py
```

> **注意**：不要对 `results/frozen_audit` 运行 `python -m citypulse.experiments.frozen_audit_analyze`，它会改写 `metrics.json`。只读复核请用上面的 `indep_audit.py`。

完整重新采集使用 `python -m citypulse.experiments.frozen_audit prepare|twoworld|rngcheck|branches|statehistory --out <新目录>`，并且需要新的种子：4501–4508 已经用过。

## 从原始数据构建场景（早期 D1–D4 原型流程）

### 香港运输署检测器数据

记录实时数据（只记录走廊上的检测器，追加写入 `data/hk/raw/YYYY-MM-DD.csv`）：

```bash
.venv/Scripts/python.exe -m citypulse.hkdata.recorder live --interval 60
```

从 data.gov.hk 历史档案回填（档案时间戳比数据所属时段早约 1 小时）：

```bash
.venv/Scripts/python.exe -m citypulse.hkdata.recorder backfill --start 20260929 --end 20260929 --hours 7 11
```

### 构建路网与需求

```bash
.venv/Scripts/python.exe -m citypulse.network.build_network
```

这一步下载 OSM 数据并生成 `scenarios/kwuntong/net_full.net.xml`（加 `--skip-download` 可复用 `data/osm/` 中已下载的数据）。然后裁剪出实际使用的走廊路网（高速公路 / 干道，以及走廊上的具名道路）：

```bash
.venv/Scripts/python.exe -c "import sumolib; n=sumolib.net.readNet('scenarios/kwuntong/net_full.net.xml'); open('scenarios/kwuntong/keep_trunk.txt','w').write('\n'.join(e.getID() for e in n.getEdges() if any(k in e.getType() for k in ['motorway','trunk']) or any(k in (e.getName() or '') for k in ['Kwun Tong Road','Kai Fuk','Kwun Tong Bypass'])))"
```

```bash
.venv/Lib/site-packages/sumo/bin/netconvert.exe -s scenarios/kwuntong/net_full.net.xml --keep-edges.input-file scenarios/kwuntong/keep_trunk.txt --keep-edges.components 1 -o scenarios/kwuntong/net.net.xml
```

下载检测器位置，映射到路网，再生成需求和预定义的信号预案：

```bash
curl -s -o data/hk/detector_locations.csv https://static.data.gov.hk/td/traffic-data-strategic-major-roads/info/traffic_speed_volume_occ_info.csv
.venv/Scripts/python.exe -m citypulse.network.map_detectors
.venv/Scripts/python.exe -m citypulse.demand.make_demand --day 2026-09-29 --h0 8 --h1 9 --scale 0.6
.venv/Scripts/python.exe -m citypulse.network.make_tls_plans
```

### 运行

双世界运行，代理世界中发生事故，在 t = 1500 s 保存快照（约 75 s 实际耗时）：

```bash
.venv/Scripts/python.exe -m citypulse.experiments.run_two_worlds --run incident --t-end 3000 --port 5561 --twin-snapshot 1500 --proxy-snapshot 1500
.venv/Scripts/python.exe -m citypulse.experiments.run_two_worlds --run baseline --t-end 3000 --port 5562 --no-incident
```

快照持久化测试（约 2.5 分钟）：

```bash
.venv/Scripts/python.exe -m citypulse.experiments.snapshot_tests
```

分支与运行时间基准（需要先完成上面的事故运行，约 3 分钟）：

```bash
.venv/Scripts/python.exe -m citypulse.experiments.branch_benchmark
```

生成图到 `docs/figures/`：

```bash
.venv/Scripts/python.exe -m citypulse.experiments.make_figures
```

## 数据来源

路网数据 © OpenStreetMap 贡献者（ODbL 许可）。交通数据来自香港特别行政区政府运输署，经 DATA.GOV.HK 提供。大部分生成数据（`data/` 下的原始数据、路由文件等）不纳入版本库；`results/` 中只收录了支撑结论的部分。
