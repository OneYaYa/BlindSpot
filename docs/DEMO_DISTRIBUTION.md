# Blindspot Relay Demo 发布方案

## 结论

Blindspot 可以部署为网页版，但当前仓库还不能直接部署到 Render。建议采用双入口：

1. **先发布 Windows ZIP**：现有发行脚本已经能打包 Godot 运行时、本地 AI 中继与启动器，这是最快、风险最低、表现最完整的公开试玩方式。
2. **再发布 Render 网页版**：作为无需下载的宣传入口，降低试玩摩擦；保留 Windows 包作为完整音频、稳定性能和离线体验版本。

Render 不能运行 Windows EXE。网页版必须由 Godot 单独导出为 `index.html`、WebAssembly、PCK 等静态资源。

## 当前状态

- 工程使用 Godot 4.6、GDScript 和 Compatibility 渲染器，具备 Web 导出的基础条件。
- `export_presets.cfg` 目前只有 `Windows Desktop`，没有 Web 预设。
- 本机尚未安装 Godot 4.6.3 Web 导出模板，因此现在无法做真实浏览器回归。
- Godot 客户端的 AI 地址仍是 `http://127.0.0.1:8787/api/npc/decide`。
- Python 服务默认只允许 localhost Origin，默认监听 `127.0.0.1:8787`，没有提供 Godot 静态文件。
- `HTTPRequest.use_threads` 当前固定开启；单线程 Web 导出需要按 `web` feature tag 关闭。
- 程序化 `AudioStreamWAV` 必须在 Chrome、Firefox 和 Safari 实测。Godot 官方文档指出默认 Web Sample 播放不支持程序化音频生成，必要时应在 Web 版禁用动态音层或改用预生成 OGG/WAV。
- GitHub 仓库当前没有公开 Release，现有 `build/` 产物也被正确忽略，没有上传。

## 阶段一：GitHub Release Windows Demo

这是当前推荐的立即发布路径。

1. 使用 `packaging/build_windows_release.ps1` 生成 `BlindspotRelay-Windows-v0.5.0.zip`。
2. **不要**使用个人高额度 Key 构建公开包，也不要使用 `-EmbedApiCredential`。
3. 运行 `packaging/smoke_test_release.py`，验证隔离解压、入口启动、哈希与进程清理。
4. 在 GitHub 创建 `v0.5.0-demo` Release，上传 ZIP 与 SHA-256。
5. README 的 Windows Demo 按钮指向 GitHub Releases。

优点：无需修改游戏架构，表现与本地测试一致，动态音频和文件系统行为最稳定。缺点：玩家需要下载并可能看到 Windows 未签名程序警告；没有托管密钥时使用本地 NPC 规则。

## 阶段二：Render Web Demo

推荐部署为**一个 Render Web Service**，由同一个域名同时提供 Godot 导出文件和 `/api/npc/decide`：

```text
Browser
  ├─ GET /                  -> Godot index.html / WASM / PCK
  └─ POST /api/npc/decide   -> Python relay -> OpenAI
```

单服务比“Render Static Site + 独立 API”更适合当前项目：它天然同源，减少 CORS、混合内容和环境地址注入问题，也能把 `OPENAI_API_KEY` 保存在 Render Secret 中。

### 必需改动

1. 安装与 Godot 4.6.3 完全匹配的导出模板。
2. 新增单线程 Web preset，导出入口必须命名为 `index.html`。
3. Web 平台下关闭 `HTTPRequest.use_threads`。
4. Web 平台把 API 地址解析为当前页面的 HTTPS origin，而不是 localhost。
5. 扩展 `server.py`：提供导出目录中的静态文件，支持 SPA 根路径，并继续处理现有 API 与 `/health`。
6. Render 环境下监听 `0.0.0.0:$PORT`；本地仍保持 `127.0.0.1:8787`。
7. 将 `OPENAI_API_KEY` 配置为 Render Secret，不写入仓库或浏览器资源。
8. 给公共 API 增加更严格的限流、请求大小、超时、预算和账单告警；当前按来源限流只能作为第一层保护。
9. 在 Chrome、Firefox、Safari 和移动端检查输入法、滚动、IndexedDB 设置持久化、音频解锁、动态音效与页面切后台行为。

### Render 配置方向

- 类型：Web Service，而不是只托管静态文件的 Static Site。
- Branch：`main`。
- Build：使用已提交的 Web 导出，或通过 Docker 安装固定版本 Godot 并在构建阶段导出。
- Start：`python server.py`，但服务必须读取 Render 的 `PORT` 并绑定 `0.0.0.0`。
- Secret：`OPENAI_API_KEY`。
- Health Check：`/health`。

免费 Web Service 会在空闲后休眠，首位试玩者可能遇到冷启动；公开宣传前应在页面上提示“首次连接可能需要几十秒”，或改用不休眠的实例。

## 为什么不只做 ZIP 或只做网页

| 方案 | 试玩摩擦 | AI 托管 | 表现完整度 | 当前工作量 |
|---|---:|---:|---:|---:|
| Windows ZIP | 中 | 默认本地规则 | 最高 | 低 |
| Render Web | 最低 | 可统一托管 | 需浏览器适配 | 中高 |
| 两者同时 | 覆盖最广 | 可选 | 最稳妥 | 分阶段可控 |

因此推荐顺序是：**先 Release ZIP 收集真实玩家反馈，再把稳定版本移植到 Render；网页入口负责传播，Windows 包负责完整体验。**

## 官方依据

- [Godot：Exporting for the Web](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html)
- [Render：Web Services](https://render.com/docs/web-services)
- [Render：Static Sites](https://render.com/docs/static-sites)
- [Render：Environment Variables and Secrets](https://render.com/docs/configure-environment-variables)
