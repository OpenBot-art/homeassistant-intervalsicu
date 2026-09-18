# Intervals.icu Integration for Home Assistant

[English](#english) | **简体中文**

一个将 [Intervals.icu](https://intervals.icu)（面向耐力运动员的训练分析平台）接入 Home Assistant 的自定义集成。

支持将训练负荷、体能状态、睡眠与心率变异性等数据接入 HA，用于自动化、看板与长期趋势统计。

## 功能特性

- **35 个静态传感器**：覆盖每日健康数据、最近活动、计划训练与运动员档案
- **按运动类型生成的传感器**：为每个运动项目（骑行、跑步、游泳……）分别生成 FTP、乳酸阈心率与最大心率传感器
- **配速最佳成绩传感器**：根据配速曲线自动生成各距离的最佳成绩
- **日历实体**：计划训练、目标、备注与比赛会出现在 HA 日历卡片中，可用于自动化
- **多语言**：内置英文、简体中文、繁体中文
- **稳健的数据处理**：显式排序、时区感知的时间比较、部分失败降级

## 安装

### HACS（推荐）

1. 在 HACS 中把本仓库添加为自定义仓库
2. 搜索「Intervals.icu」并安装
3. 重启 Home Assistant

### 手动安装

1. 将 `custom_components/intervals_icu` 目录复制到你的 Home Assistant `custom_components` 目录
2. 重启 Home Assistant

## 配置

1. 进入 **设置** > **设备与服务** > **添加集成**
2. 搜索「Intervals.icu」
3. 填入 **运动员 ID** 与 **API 密钥**
   - 可在 Intervals.icu 账号的 **设置** > **开发者设置** 中找到

## 传感器

### 每日健康数据

| 传感器 | 说明 | 单位 |
|--------|------|------|
| 体重 | 体重 | kg |
| 静息心率 | 静息心率 | bpm |
| 心率变异性 | HRV | ms |
| 心率变异性 SDNN | HRV SDNN | ms |
| 睡眠时长 | 总睡眠时长 | s |
| 睡眠评分 | 睡眠质量评分 | — |
| 准备度 | 准备度评分 | — |
| 血氧饱和度 | 血氧饱和度 | % |
| 步数 | 每日步数 | steps |
| 体能 (CTL) | 长期训练负荷 | — |
| 疲劳 (ATL) | 短期训练负荷 | — |
| 状态 (TSB) | 训练压力平衡（CTL − ATL），由集成计算 | — |
| 负荷变化率 | 训练负荷变化率 | — |
| 压力 | 主观压力水平 | — |
| 情绪 | 主观情绪 | — |
| 积极性 | 主观积极性 | — |
| 疲劳感 (主观) | 主观疲劳程度 | — |
| 肌肉酸痛 | 主观酸痛程度 | — |
| 摄入热量 | 摄入热量 | kcal |

### 最近活动

| 传感器 | 说明 | 单位 |
|--------|------|------|
| 最近活动 | 活动名称 | — |
| 最近活动类型 | 活动类型（骑行、跑步等） | — |
| 最近活动时长 | 移动时间 | s |
| 最近活动距离 | 距离 | m |
| 最近活动训练负荷 | 训练负荷 | — |
| 最近活动平均心率 | 平均心率 | bpm |
| 最近活动最大心率 | 最大心率 | bpm |
| 最近活动平均功率 | 平均功率 | W |
| 最近活动标准化功率 | 标准化功率 | W |
| 最近活动强度 | 强度系数 | — |
| 最近活动消耗热量 | 消耗热量 | kcal |
| 最近活动累计爬升 | 累计爬升 | m |

### 计划训练

| 传感器 | 说明 |
|--------|------|
| 下一个训练 | 下一个计划训练的名称 |
| 下一个训练日期 | 下一个计划训练的日期 |
| 下一个训练类型 | 下一个计划训练的类型 |

### 运动员档案

| 传感器 | 说明 | 单位 |
|--------|------|------|
| 静息心率 (档案) | 档案中的静息心率 | bpm |

### 按运动类型生成

对于 `sportSettings` 中的每个运动项目，集成会生成三个传感器：**阈值功率**、**乳酸阈心率**、**最大心率**。

例如同时配置了骑行与跑步时，会得到：

```
骑行 阈值功率      骑行 乳酸阈心率      骑行 最大心率
跑步 阈值功率      跑步 乳酸阈心率      跑步 最大心率
```

> 早期版本只读取第一项运动配置，多运动项目的用户会丢失其余运动的数据。

### 配速最佳成绩

根据跑步配速曲线为每个距离生成一个最佳成绩传感器（单位：秒），并在属性中附带创造该成绩的活动 ID。

### 日历

日历实体会展示 Intervals.icu 日历中的计划训练、目标、备注与比赛，可用于自动化。

## 语言

集成内置 **英文**、**简体中文**（`zh-Hans`）与 **繁体中文**（`zh-Hant`）。

Home Assistant 会在 **设置** > **系统** > **通用** 中自动选择语言，无需额外配置。

有两点值得说明：

- **实体 ID 始终为英文**，与界面语言无关。因此切换语言不会导致实体被重建，历史统计数据也不会丢失。
- **运动名称单独本地化**（例如 `Ride` 显示为「骑行」）。这是因为 Home Assistant 会原样插入占位符的值，不会对其再做翻译。

新增翻译后可用以下脚本自检：

```bash
./.venv/Scripts/python.exe tools/check_translations.py          # 各语言 key 结构一致性
./.venv/Scripts/python.exe tools/render_translations.py zh-Hans # 预览渲染结果
```

## 开发

### 运行测试

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install aiohttp pytest

./.venv/Scripts/python.exe -m pytest tests/ -q          # 85 passed
./.venv/Scripts/python.exe tools/smoke_check.py         # 端到端冒烟检查
```

测试**无需安装完整的 Home Assistant**：`tests/_ha_stubs.py` 会在 HA 缺失时提供所需的最小接口，让纯逻辑测试能在轻量环境中运行。

### 项目结构

```
custom_components/intervals_icu/
├── __init__.py       集成装配与实体 ID 迁移
├── api.py            Intervals.icu API 客户端
├── coordinator.py    数据轮询与排序
├── sensor.py         传感器（描述符驱动）
├── calendar.py       日历实体
├── config_flow.py    UI 配置流程
├── const.py          常量
└── translations/     语言文件
```

### 数据更新

数据每 **2 小时**轮询一次。日历在浏览日期区间时按需拉取事件。

---

## English

A custom Home Assistant integration for [Intervals.icu](https://intervals.icu), a training analytics platform for endurance athletes.

### Features

- **35 static sensors** covering daily wellness, the latest activity, planned workouts and the athlete profile
- **Per-sport sensors**: FTP, LTHR and max heart rate generated for every configured sport
- **Best-effort sensors**: one per distance from the running pace curve
- **Calendar entity** for planned workouts, targets, notes and races
- **Translations**: English, Simplified Chinese and Traditional Chinese
- **Robust data handling**: explicit ordering, timezone-aware comparisons, graceful partial failure

### Installation

**HACS (recommended)**

1. Add this repository as a custom repository in HACS
2. Search for "Intervals.icu" and install
3. Restart Home Assistant

**Manual**

1. Copy the `custom_components/intervals_icu` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

### Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "Intervals.icu"
3. Enter your **Athlete ID** and **API Key**
   - Find these in your Intervals.icu account under **Settings** > **Developer Settings**

### Sensors

**Wellness (daily)**

| Sensor | Description | Unit |
|--------|-------------|------|
| Weight | Body weight | kg |
| Resting heart rate | Resting HR | bpm |
| HRV | Heart rate variability | ms |
| HRV SDNN | HRV SDNN | ms |
| Sleep time | Total sleep duration | s |
| Sleep score | Sleep quality score | — |
| Readiness | Readiness score | — |
| SpO2 | Blood oxygen saturation | % |
| Steps | Daily step count | steps |
| Fitness (CTL) | Chronic training load | — |
| Fatigue (ATL) | Acute training load | — |
| Form (TSB) | Training stress balance (CTL − ATL), computed by the integration | — |
| Ramp rate | Training ramp rate | — |
| Stress | Subjective stress level | — |
| Mood | Subjective mood | — |
| Motivation | Subjective motivation | — |
| Fatigue (subjective) | Subjective fatigue | — |
| Soreness | Subjective soreness | — |
| Calories consumed | Calories consumed | kcal |

**Latest activity**

| Sensor | Description | Unit |
|--------|-------------|------|
| Last activity | Activity name | — |
| Last activity type | Activity type (Ride, Run, etc.) | — |
| Last activity duration | Moving time | s |
| Last activity distance | Distance | m |
| Last activity training load | Training load score | — |
| Last activity avg HR | Average heart rate | bpm |
| Last activity max HR | Max heart rate | bpm |
| Last activity avg power | Average power | W |
| Last activity normalized power | Normalized power | W |
| Last activity intensity | Intensity factor | — |
| Last activity calories | Calories burned | kcal |
| Last activity elevation gain | Total elevation gain | m |

**Planned workouts**

| Sensor | Description |
|--------|-------------|
| Next workout | Name of the next planned workout |
| Next workout date | Date of the next planned workout |
| Next workout type | Type of the next planned workout |

**Athlete profile**

| Sensor | Description | Unit |
|--------|-------------|------|
| Resting heart rate (profile) | Resting HR from the profile | bpm |

**Per sport**

For every sport in `sportSettings`, the integration creates three sensors: **FTP**, **LTHR** and **max heart rate**.

An athlete configured for both cycling and running gets:

```
Ride FTP        Ride LTHR        Ride max heart rate
Run FTP         Run LTHR         Run max heart rate
```

> Earlier versions read only the first `sportSettings` entry, so multi-sport athletes silently lost every sport but the first.

**Best efforts**

One sensor per distance from the running pace curve, in seconds, with the activity ID that set the effort exposed as an attribute.

**Calendar**

A calendar entity showing planned workouts, targets, notes and races from your Intervals.icu calendar.

### Languages

The integration ships with English, Simplified Chinese (`zh-Hans`) and Traditional Chinese (`zh-Hant`). Home Assistant picks the language from **Settings** > **System** > **General**; no configuration is needed.

Entity IDs stay in English regardless of the selected language, so switching languages never orphans existing entities or their long-term statistics. Sport names are localized separately (for example `Ride` renders as `骑行`) because Home Assistant inserts placeholder values verbatim and does not translate them.

### Development

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install aiohttp pytest

./.venv/Scripts/python.exe -m pytest tests/ -q          # 85 passed
./.venv/Scripts/python.exe tools/smoke_check.py         # end-to-end smoke check
```

The test suite does **not** require a full Home Assistant installation: `tests/_ha_stubs.py` provides the minimal surface the integration imports when HA is absent.

```bash
./.venv/Scripts/python.exe tools/check_translations.py          # translation key consistency
./.venv/Scripts/python.exe tools/render_translations.py zh-Hans # preview rendered names
```

### Data update

Data is polled from the Intervals.icu API every 2 hours. The calendar fetches events on demand when browsing date ranges.
