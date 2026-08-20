# Blindspot Relay Demo 发布方案

## 当前可用入口

- **网页试玩**：<https://blindspot-relay.onrender.com>。无需下载或填写 API Key。
- **Windows Demo**：<https://github.com/OneYaYa/BlindSpot/releases/tag/v0.5.2>。完整音频、本地规则回退，也允许玩家配置自己的 Key。

网页版与 Windows 版来自同一套 Godot 4.6 工程与权威模拟逻辑，不是旧 HTML 原型。Render 同一个 Web Service 同时提供 Godot WebAssembly 文件和 Python AI 中继：

```text
Browser
  ├─ GET /                  -> Godot index.html / WASM / PCK
  ├─ GET /api/health        -> service status
  └─ POST /api/npc/decide   -> Python relay -> OpenAI
```

这种同源部署避免了混合内容和跨域配置，也确保 `OPENAI_API_KEY` 只存在于 Render Secret 中，不会进入 HTML、JavaScript、WASM、PCK 或 GitHub 仓库。

## Web 构建

仓库中的 `export_presets.cfg` 已包含单线程 `Web` preset。使用与工程匹配的 Godot 4.6.3 Web 导出模板后运行：

```powershell
& "C:\path\to\Godot_v4.6.3-stable_win64_console.exe" `
  --headless --path . --export-release "Web" "web/index.html"
```

生成的 `web/` 目录会提交到仓库，因此 Render 不需要在免费构建环境中额外下载 Godot。Python 服务以分块方式提供大型 WASM/PCK 文件，并继续处理原有 API。

## Render 配置

`render.yaml` 定义了 Web Service、启动命令和 `/api/health` 健康检查。Render 环境至少需要：

- `OPENAI_API_KEY`：Secret，禁止同步到仓库。
- `BLINDSPOT_MODEL`：当前线上模型名。
- `BLINDSPOT_RATE_LIMIT`：每个来源 IP 每分钟请求上限。

服务读取 Render 的 `PORT` 并监听 `0.0.0.0`；本地启动仍默认监听 `127.0.0.1:8787`。免费实例休眠后会出现冷启动，因此宣传页应保留首次连接等待提示。

## 浏览器适配

- Web 平台关闭 `HTTPRequest` 工作线程，使用单线程 WebAssembly 模板。
- 客户端从 `window.location.origin` 解析同源 `/api/npc/decide`，不再访问玩家电脑的 localhost。
- 内置 Noto Sans Mono CJK SC，避免浏览器缺少中文系统字体时出现方框。
- Windows 下载包的 `_runtime` 误启动保护不会在 Web 平台触发。
- 程序化无线电音频在 Web 平台暂时关闭；Windows 版保留完整动态音频。
- 在线模型超时、断网或响应非法时，Godot 仍会降级到本地 NPC 规则，权威任务状态不依赖模型。

## 发布前验证基线

- Python：37 项测试。
- Godot 权威模拟：254 项检查。
- Godot 主场景集成：100 项检查。
- Chrome Headless：真实加载 HTML、JS、WASM、PCK 和字体；中文画面正常，无浏览器严重错误。
- 浏览器真实 AI 链路：Godot Canvas 发出同源请求，Python relay 成功返回中文角色回复，页面切换为 `ONLINE`。
- 安全检查：Web 导出中不得包含 `.env`、玩家凭据或 Render Secret。

正式宣传前仍建议补做 Firefox、Safari、移动端输入法和长局内存回归。桌面 Chrome 是当前经过自动化验证的浏览器。

## 官方依据

- [Godot：Exporting for the Web](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html)
- [Render：Web Services](https://render.com/docs/web-services)
- [Render：Environment Variables and Secrets](https://render.com/docs/configure-environment-variables)
- [Noto CJK：SIL Open Font License 1.1](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE)
