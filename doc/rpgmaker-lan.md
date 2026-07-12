# RPG Maker 局域网网页化：Seed 设计、适配记录与 Nexus 接入

> 本文是 RPG Maker MV/MZ `web-play` Seed 的专属设计与实测记录。Nexus 的社区、Catalog、Seed SDK、Runtime、Gate 与个人进度的通用架构见 [../arch.md](../arch.md)。

## Seed 定位与 Nexus 接入

该 Seed 将一份管理员有权使用的 RPG Maker MV/MZ 游戏 `www/` 资源目录转换为 Nexus 可运行的 `web-play` 项目。它不是“任意 RPG Maker 游戏自动修复”器：每个桌面版特化仍可能需要显式的游戏专属覆盖规则。

```text
管理员登记 Game + Release + RPG Maker Seed binding
  → Seed 检查 `www/index.html`、引擎版本与桌面依赖
  → 生成只读资源挂载与只读/派生覆盖层
  → 产出静态 HTTP RuntimeSpec
  → Nexus Runtime 启动负载，Gate 交付授权入口
  → 浏览器加载游戏；支持进度同步时由启动壳处理快照
```

### 输入与校验

Seed 接受 `www/` 路径、目标语言等有限配置。至少验证：

- 存在 `www/index.html`、`js/`、`data/`，以及游戏实际引用的资源目录。
- 已识别 MV/MZ 与必要版本信息。
- 对被加载的脚本扫描 `require(`、`fs`、`nw.gui`、`process.`、`child_process`、Steam/NW.js 插件和 `www/` 外路径引用。
- 对请求 URL 与实际文件路径检查大小写差异，例如 `fonts/Fonts`、`audio/Audio`、`movies/Movies`。

扫描结果分为“可直接运行”“需已知覆盖规则”“不支持并阻止启动”。对不确定的桌面依赖，宁可阻止自动发布并给出证据，也不要声称已经转换成功。

### 输出、隔离与运行规格

- 原始 `www/` 以只读卷提供给静态服务。
- 覆盖文件由 Seed 生成到独立目录，静态服务只对明确路径优先返回覆盖版本。
- 每一项覆盖应记录原因、所影响的游戏版本和回退方式，例如禁用 Node/NW.js 插件、将文件语言配置改为 URL 参数、或修正目录大小写映射。
- `RuntimeSpec` 只声明镜像、只读挂载、覆盖优先级、端口和健康检查；Seed 不直接启动 Docker、不读用户表、不写进度数据。
- 默认不在容器可写层保存游戏资产、数据库或存档。Nexus Runtime 负责执行、检查、停止和回收该规格，Gate 负责授权入口。

## 交付物

- 启动框架：[rpgmaker-lan](/tmp/tmp/rpgmaker-lan)
- 当前游戏资源根目录：`/tmp/tmp/3.8/data/www`
- 资源规模：约 4 GB；框架不复制资源，容器以只读卷映射。

## 当前游戏的适配结论

该游戏使用 RPG Maker MV 1.6.2，并被 NW.js 桌面运行时封装。`www/index.html`、`js`、`data`、`img`、`Audio` 构成完整网页运行时，但存在三项桌面版遗留：

| 问题 | 证据 | 框架处理 |
| --- | --- | --- |
| 语言由 Node `fs` 读取 | `js/rpg_managers.js` 的 `require('fs')` | 覆盖为固定 `LngMode`，默认 `tc` |
| Steam 插件依赖 Node/NW.js | 已启用 `JsScript15Set`，加载 `greenworks` | 覆盖 `plugins.js`，禁用该插件 |
| 字体路径大小写不一致 | HTML 为 `fonts/`，实际目录为 `Fonts/` | Nginx 将 `/fonts/` 映射到 `Fonts/` |
| 音频路径大小写不一致 | 运行时请求 `audio/`，实际目录为 `Audio/` | Nginx 将 `/audio/` 映射到 `Audio/` |
| 公共事件调用 Node `fs` | `CommonEvents.json` 内动态执行 `require("fs")` | 覆盖相应公共事件为空操作，避免创建桌面端标记文件 |
| 标题菜单切换语言写入本地文件 | `JsScript91Set` 写入 `lng.txt` | 使用 URL 参数与浏览器 localStorage 保存语言，随后刷新页面 |

原始游戏资源不被写入。覆盖文件在启动时生成到 `rpgmaker-lan/overrides/`，Nginx 仅对已适配的请求路径替换响应。

语言选择现在可在标题菜单中完成。每台设备的选择保存在该浏览器的 `localStorage`，并反映在 URL 的 `lang` 参数；切换后页面自动重载。例如 `?lang=en`、`?lang=tc`。不同设备可以使用不同语言，不会修改游戏资源或影响其他设备。

## 目录和映射表

| 宿主机内容 | 容器路径 | 权限 | 用途 |
| --- | --- | --- | --- |
| 任意游戏的 `www` 目录 | `/usr/share/nginx/html` | 只读 | 游戏的 HTML、JS、数据、图片、音频与视频 |
| `rpgmaker-lan/overrides` | `/overrides` | 只读 | 本游戏生成的浏览器兼容覆盖文件 |
| `rpgmaker-lan/nginx.conf` | 镜像内 Nginx 配置 | 构建时复制 | 静态服务、覆盖规则、字体别名 |

容器端口为 `8080`；宿主机端口默认为 `8088`。启动脚本默认绑定 `0.0.0.0`，可被局域网设备访问。路由器未做端口转发时，不会因此暴露到互联网；仍应保留主机防火墙的局域网边界。

## 本次验证

- Docker Compose 已实际构建并启动 `rpgmaker-lan` 容器。
- `http://127.0.0.1:8088/` 和 `http://192.168.9.4:8088/` 均返回 `200 OK`。
- 无头 Chrome 已完成游戏首屏加载，创建了游戏 Canvas、加载数据库与全部已启用插件；控制台只有 Canvas 性能提示，未出现脚本异常或资源加载错误。
- 后续实机触发的公共事件曾调用 `require("fs")`；现已在五种语言数据覆盖中禁用两段仅创建桌面端标记文件的事件，并确认浏览器获取的繁中数据不再含该调用。
- 音效与游戏内 BGM 的加密文件现可经 `/audio/` 正确读取；系统配置指定的标题曲 `Theme6.rpgmvo` 不在当前游戏资源包中，因此标题界面仍不会播放该曲。

## 跨设备账号进度的 Nexus 协议

可以实现，但不能把 `StorageManager` 直接改为同步网络请求：RPG Maker MV 的读档流程要求同步返回值。正确做法是保留浏览器 `localStorage` 作为即时缓存，并在启动和保存的边界同步 Nexus 的个人进度服务：

```text
进入游戏：认证 → GET 当前快照 → 写入 localStorage → 启动游戏
游戏保存：写 localStorage → 防抖 PUT 快照(revision) → 服务端原子更新
冲突发生：返回冲突而非静默覆盖 → 客户端提示/保留可恢复副本
```

后端应至少保存 `user_id`、`game_id`、`release_id`、`slot_id`、`payload`、`revision`、`updated_at`；密码只保存 Argon2id 或 bcrypt 哈希。保存接口应使用乐观锁版本号，避免两个设备同时保存时静默覆盖。登录会话应为 `HttpOnly`、`Secure`、`SameSite=Lax` Cookie。生产化前，Save payload 的大小上限、速率限制、备份与恢复策略必须明确。

局域网账号认证仍应使用 HTTPS；纯 HTTP 会让同网段设备能够截获密码与会话。Nginx 可终止 TLS，并把 `/api/` 反向代理到一个最小的认证和 SQLite 服务。SQLite 数据库和备份目录应作为 Docker 命名卷或宿主机目录挂载，不能放在容器可写层。

## 当前游戏的启动方式

```bash
cd /tmp/tmp/rpgmaker-lan
./start.sh
```

启动后，在承载 Docker 的电脑上查询内网 IPv4 地址，然后由其他设备访问：

```text
http://<电脑内网IPv4>:8088/
```

可指定资源目录、端口、绑定地址和语言：

```bash
./start.sh --game-www /path/to/game/www --lang tc --port 8088 --bind 192.168.1.10
```

停止服务：

```bash
./stop.sh
```

`stop.sh` 不需要游戏资源目录或语言参数；它仅停止既有容器。Compose 为停止场景提供空默认挂载，而 `start.sh` 仍会在启动前验证实际 `www/index.html`。

浏览器存档使用 `localStorage`，因此每个浏览器和设备各自保存，清理浏览器站点数据会删除相应存档。它不等同于原桌面版 `Save/` 中的文件存档，也不会自动同步。

## 通用流程

1. 定位游戏内的 `www/index.html`。没有该目录或入口文件时，此框架不适用。
2. 将该 `www` 作为只读资源目录传给 `start.sh --game-www`。
3. 在浏览器开发者工具检查首屏报错与网络 404。
4. 搜索 JS 中的 `require(`、`nw.gui`、`process.`、`child_process`、`fs`。仅为被实际加载的桌面 API 制作覆盖或禁用相应插件。
5. 检查 URL 与磁盘文件名的大小写，尤其是 `Fonts/fonts`、`Audio/audio`、`Movies/movies`。
6. 用手机、平板和另一台电脑分别测试首屏、音频、输入、存档和重开后的读档。

## `www` 目录与桌面版文件边界

对于多数 RPG Maker MV/MZ 游戏，`www/` 是网页运行主体：其中应有 `index.html`、`js/`、`data/`、`img/`、`Audio/`，以及按需存在的 `Movies/`、`Fonts/`。部署时应将整个 `www/` 作为资源根目录，而不是只挑选其中部分子目录。

Windows 游戏根目录中的 `.exe`、`nw.dll`、`node.dll`、`.pak`、`locales/` 等通常属于 NW.js/Chromium 桌面运行时；网页静态部署不需要它们。桌面 `Save/`、`ndata/` 也不会被浏览器自动使用，网页默认保存到浏览器 `localStorage`。

仍需逐游戏检查 `www/` 外部依赖。本游戏原先的 `data/lng.txt`、Steam/NW.js 插件和公共事件中的 Node `fs` 调用就是例外；它们不能随 `www/` 原样在浏览器工作，需要改成浏览器兼容逻辑或禁用。新游戏适配前应搜索 `require(`、`fs`、`nw.gui`、`process.`、`child_process` 与 `../` 外部路径引用。

## 适用范围与边界

RPG Maker MV/MZ 原生 Web 导出通常无需覆盖，只需挂载 `www` 并启动静态服务。桌面版常见的 NW.js 特化、Steam 插件、文件选择器、系统调用、外挂 EXE、第三方视频编解码器和桌面存档插件不能一概自动转换；应按运行报错逐项适配。

加密素材仍会下发到浏览器，由运行时解密。这种方式适合私有局域网使用，不提供资源保密或在线账号能力。

## Nexus 接入交付与完成条件

1. 将已有 `rpgmaker-lan` 验证框架整理为 Seed 原型，保留只读资产与覆盖层机制。
2. 实现该 Seed 的 `validate`、`prepare`、`InspectionReport` 与静态 HTTP `RuntimeSpec`，并将其登记进 Seed Registry。
3. 由 Nexus 控制面创建和停止负载，通过 Gate 返回仅受控入口；Seed 不越过其边界调用 Runtime。
4. 接入账户、Release 授权与版本化个人进度 API；在客户端启动/保存边界执行快照同步。
5. 用两台设备验证登录、首屏、音频、输入、保存、恢复、账户隔离与冲突处理。
6. 保留一个不支持的桌面特化样本，验证失败诊断与回滚，而不只验证成功路径。

满足以下条件时，这个 Seed 才可作为 Nexus 的首个 `web-play` 接入完成：

- 管理员能以受支持的 RPG Maker Release 创建并停止网页游玩服务，且不修改原始资源。
- 两个账户在两个设备上可进入同一游戏，互不可见彼此进度。
- 保存后的页面重开、服务重启和设备切换均可恢复最近一次成功同步的数据。
- 不受支持的 Node/NW.js 依赖会在启动前或明确的适配步骤中被报告，而非在玩家页面静默失败。
- 容器没有宿主机任意目录访问权、没有 Docker socket，持久数据不位于容器可写层。
- 所有用于验收的游戏资源均有明确的使用/托管授权记录。
