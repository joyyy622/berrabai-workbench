# 部署与更新说明

## 当前运行方式

代码托管在 GitHub，公开演示已部署到 Cloudflare Pages，完整业务版仍在本机运行。完整业务版前后端由同一个 Python 服务提供；数据写入本机 SQLite，本地 AI 连接同机 Ollama。上传代码不会自动同步本机订单，也不会启动公开网站。

## Cloudflare Pages 的适用范围

[Cloudflare Pages](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/)可托管本项目的公开静态演示。需使用下文的构建命令生成 `public-demo`，以启用独立的浏览器数据模式。

完整业务版依赖 Python HTTP 服务、SQLite 与模型接口，当前没有 Workers / 云数据库适配。直接发布原始 `dist/` 仍会缺少 `/api/*` 接口；静态演示不承担管理员登录、共享数据库、真实 AI 问答或 RSS 获取。

## 完整在线服务需要准备

1. 可运行 Python 的主机或容器，以及 HTTPS 反向代理。服务仅监听 `127.0.0.1`，适合同机代理转发。
2. 持久化磁盘上的 `WORKBENCH_DB` 路径，不能依赖临时文件系统。
3. 平台环境变量中的管理员密码与模型配置；禁止提交本机 `.env`。
4. 同机 Ollama 与足够内存，或可访问的云端兼容模型接口。
5. 登录尝试限流、HTTPS 会话 Cookie、防跨站请求策略、进程管理、错误日志，以及备份恢复演练。当前会话在内存中，重启后需重新登录。

以上为完整业务服务的上线准备，当前未完成其云端部署。公开静态演示的已验证配置见下文。

## 更新代码

先备份数据并停止服务，在已克隆的仓库中执行：

```sh
git pull --ff-only
set -a
source .env
set +a
python3 server.py
```

有本地代码修改时先保存或提交再拉取。静态文件刷新可见；Python 或环境变量更新需重启。更新后验证登录、导入、报告、备份与模型连接；代码回退不会自动回退数据库。

## 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 登录提示未配置密码 | 启动终端是否加载 `ADMIN_PASSWORD`；加载后重启 |
| 本地模型未就绪 | Ollama 是否运行，模型是否下载，`LOCAL_MODEL` 是否匹配 |
| 云端模型 401 | 密钥所属平台与接口地址是否匹配；不要将密钥贴到 Issue |
| RSS 404 | 编辑来源并核对完整 RSS 地址，普通文章页不等于 RSS |
| 其他页面已更新数据 | 保留待录入内容，刷新最新版本后再提交 |
| 端口已占用 | 停止旧服务，或修改 `PORT` 后启动 |
| 文件模式和服务模式数据不同 | 两者分别存于浏览器与数据库，可用 JSON 备份迁移 |

## 与小程序后台的关系

当前数据路径是：小程序订单后台导出文件 → 工作台导入、字段映射与明细更新 → SQLite 分析数据 → 图表与报告。GitHub 托管代码，不负责订单同步。

直接接口接入尚未实现。后续对接微信云开发或自建后台时，需要确认实际订单表、访问授权、成交状态与退款字段，再实现服务端增量读取与同步记录。业务后台仍是交易数据来源，浏览器不保存数据库访问凭据。

## Cloudflare Pages 公开演示版

公开演示采用独立静态构建，不运行 Python、SQLite 或模型服务。访客数据保存在各自浏览器中；初次访问展示内置演示，导入订单时进入独立的个人工作区。首次访问的数据不会与导入的订单累加。

在 Cloudflare 控制台的 Workers & Pages 中，选择 Create application → Pages → Import an existing Git repository，授权 GitHub 仓库 `joyyy622/berrabai-workbench`，使用以下设置：

| 设置项 | 值 |
| --- | --- |
| Framework preset | None |
| Production branch | `main` |
| Root directory | 仓库根目录，留空 |
| Build command | `python3 scripts/build-public-demo.py` |
| Build output directory | `public-demo` |
| 环境变量 | 无需配置管理员密码或模型密钥 |

部署成功后，控制台会给出实际的 `*.pages.dev` 网址；在首次部署成功前，不把预测域名视为已上线。后续推送到 `main` 后，Pages 会自动重新构建。GitHub 仓库保持私有也能连接 Pages。

本地执行同一构建命令后，也可将 `public-demo` 目录内容打成 ZIP，在 Pages 的 Direct Upload 页面上传。Git 集成与直接上传是两种项目创建方式，本项目推荐 Git 集成以便持续更新。

构建只复制四个前端文件及响应头配置，排除数据库、订单备份、密钥和 Python 服务。在线模式强制使用浏览器存储，不请求 `/api/*`；AI 自由问答与 RSS 获取需要完整业务服务，不包含在此静态演示中。

## 当前公开演示

生产网址：https://berrabai-workbench.pages.dev/

已连接 GitHub 的 `main` 分支，启用自动构建。2026-11-26 已验证独立、未登录浏览器可直接打开总览与规则报告，不出现管理员登录或自由问答输入框。访客导入的数据保存在各自浏览器。

若部署状态成功但访问 404，先检查 Build command 与 Build output directory 是否被留空。两项分别应为 `python3 scripts/build-public-demo.py` 和 `public-demo`；保存后需重新构建，原有部署不会自动改为新目录。

## 查看访问统计

在 Cloudflare Pages 的 `berrabai-workbench` 项目中，打开 Metrics，在 Web Analytics 区域点击 Enable。Cloudflare 会在下一次部署时自动注入统计脚本；随后在 Web Analytics 中选择这个站点查看数据。

静态构建已允许官方脚本 `https://static.cloudflareinsights.com/beacon.min.js` 及统计上报地址。统计不会把访客在工作台中导入的订单作为业务数据上传；应用的订单、报告和待办仍保存在各自浏览器中。

Visits 表示访问次数，一次访问可能包含多次页面浏览；Page views 表示页面浏览量。两者都不能直接作为严格去重的访客人数。统计从启用并部署后开始，无法补回未收集的历史访问，广告拦截等因素也可能造成漏计。工作台内的侧栏切换不代表新的独立访客。

参考：[Pages 开启统计](https://developers.cloudflare.com/pages/how-to/web-analytics/)、[指标定义](https://developers.cloudflare.com/web-analytics/data-metrics/high-level-metrics/)。
