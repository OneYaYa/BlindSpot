<p align="center">
  <strong>简体中文</strong> · <a href="README.md">English</a>
</p>

<div align="center">
  <img src="icon.svg" width="152" alt="盲区中继信号图标">
  <h1>盲区中继 / BLINDSPOT RELAY</h1>
  <p><strong>你看得见系统，他看得见现场。任何一方都无法独自逃生。</strong></p>
  <p>一款关于信任、信息差与受损通讯的单人 AI 对话惊悚解谜游戏。</p>
</div>

[![《盲区中继》游戏预告](assets/branding/blindspot-gameplay-preview.gif)](assets/branding/blindspot-gameplay-trailer.mp4)

<p align="center">
  <a href="assets/branding/blindspot-gameplay-trailer.mp4"><strong>▶ 观看 / 下载游戏预告</strong></a>
</p>

<p align="center">
  <a href="https://github.com/OneYaYa/BlindSpot/releases"><strong>⬇ WINDOWS DEMO / RELEASES</strong></a>
</p>

## 一个屏幕，两种真相

K-17 设施正在失效。你是远程调度员，能读取残缺的全局遥测；林岚是一名左肩受伤、被困在隔离舱门后的维护技术员，他只能报告眼前亲自确认的东西。

你的记录不完整，他面前的标签已经烧毁。你们必须在通讯盲区两端交叉核对信息，并决定哪些风险值得让另一个真人承担。

这不是摆在谜题旁边的聊天机器人——对话本身就是谜题。

## 你说过的话会留到结局

林岚记住的不只是玩家姓名。安抚、欺骗、鲁莽命令、谨慎修复、承诺与关键失误都会成为本局结构化事件，改变他的信任、危险行动意愿以及获救后的最后一句话。

五段个人经历会在不同房间自然浮现。完整撤离能够保存事故遥测并重启责任调查；应急撤离或许救得了人，却可能永久烧毁证据。失败后留下的只有持续载波。

## AI 可以说话，但不能改写现实

- **自然对话**：用自己的话询问伤势、环境、回忆、恐惧或下一步。
- **真实信息差**：调度员与技术员分别掌握关键线索的一半。
- **玩家授权**：AI 最多提出一个本地合法动作，没有你的确认就不能执行。
- **确定性后果**：房间、资源、谜题、信任、错误与结局始终由 Godot 管理。
- **无 Key 仍可玩**：在线模型不可用时，本地角色规则仍能完成整起事故。
- **可重玩证据**：线路读数、压力标定、路线与事故签名会在重开后变化。

## 五个房间，一道黑暗中的声音

1. 抢接受损中继，与林岚建立联系。
2. 恢复调度员独占遥测，同时避免把隐藏答案直接泄露给他。
3. 把烧毁的现场接头标签与远端电气记录交叉核对。
4. 从两个不完整视角重建冷却压力顺序。
5. 在完整修复与应急旁路之间选择，并承担被保全或被毁掉的证据后果。

每个房间都有独立视觉地标与无线电环境层。林岚会随氧气、信任、行动与结局切换基础、监听、受伤和释然姿态。

## 试玩 Demo

### Windows：目前最适合公开发布

公开 v0.5.2 Windows 试玩版已发布到 [GitHub Releases](https://github.com/OneYaYa/BlindSpot/releases/tag/v0.5.2)。下载 `BlindspotRelay-Windows-v0.5.2.zip`，完整解压后运行 `BlindspotRelay.exe`。发行包已经包含 Godot 运行时与本地代理，玩家不需要安装 Godot 或 Python。压缩包不包含开发者 API Key；没有在线模型时，本地规则仍可完整通关。未配置在线服务时，启动器会自动打开仅限本机的配置页，玩家可填入自己的 Key；凭据会使用 Windows DPAPI 加密并绑定当前系统账户。已经配置 Key 时，启动器会明确提示在线 AI 已启用；如果误开 `_runtime/BlindspotGame.exe`，游戏会引导玩家返回外层启动器。

### 浏览器：计划中的低门槛版本

Godot 可以把这个 GDScript 工程导出为 WebAssembly，Render 也可以承载它。但 Blindspot 还需要增加专用 Web 导出、同源 HTTPS API、浏览器安全的请求线程配置和音频降级，之后才适合公开宣传网址。推荐目标是一个 Render Web Service 同时提供 Godot 网页文件和 Python AI 中继，让模型密钥始终留在服务端。

经过核对的上线步骤与当前阻碍见 [Demo 发布方案](docs/DEMO_DISTRIBUTION.md)。

<details>
<summary><strong>从源码运行</strong></summary>

需要 Godot 4.6 或更高版本。

```powershell
git clone https://github.com/OneYaYa/BlindSpot.git
cd BlindSpot
& "C:\path\to\Godot_v4.6.3-stable_win64_console.exe" --path .
```

不启动 Python 服务时，游戏会自动使用本地 NPC 规则。要测试可选在线对话，可将 `.env.example` 复制为 `.env`，填入专用 `OPENAI_API_KEY`，运行 `python server.py` 后再启动 Godot。

</details>

<details>
<summary><strong>架构与验证</strong></summary>

Blindspot 使用 Godot 4.6 权威模拟器、最小权限 NPC 上下文编译器、本地规则回退，以及可选的 Python Responses API 中继。调度员独占遥测与隐藏谜题答案会在模型调用前过滤；模型返回的动作还必须通过 Python 校验、Godot 复验与玩家授权。

当前回归基线：

- Python：27 项测试
- Godot 权威模拟：250 项检查
- Godot 主流程集成：100 项检查
- 中文在线 AI 体验集：12 个用例，覆盖人格、事实、泄漏、动作、复读、延迟、请求、失败与回退

技术资料：[AI NPC 技术升级](docs/AI_NPC_TECH_UPGRADE.md) · [AI 与隐私](docs/AI_AND_PRIVACY.md) · [发布清单](docs/RELEASE_CHECKLIST.md)

</details>
