# Nexus / The Seed 架构与 MVP 设计

> 状态：设计草案，尚未实现。本文同时定义长期架构边界与首个 MVP 的可交付范围。RPG Maker 的已验证适配经验归档于 [RPG Maker web-play Seed 文档](../seeds/rpgmaker-web-play/docs/rpgmaker-lan.md)。

## 1. 定位

**Nexus** 是生态系统：它让玩家、游戏资产、可运行的游戏世界与共同体在一个受控的连接点相遇。

**The Seed** 是 Nexus 的平台与代码库名称。它登记游戏、识别用户、调度运行负载，并提供游玩、开服和社区所需的基础能力。

**Seed** 是一个游戏引擎/发行形态的适配包。它把一类原本不能直接在 Nexus 中运行的资产，变成具有明确能力、输入、持久化边界和运行方式的对象。Seed 不是游戏资源本身，也不是某个玩家创建出来的实例。

这一命名借用了《刀剑神域》的 *The Seed* 意象：原作中它是用于创造与运行虚拟世界的开发框架。这里的映射是“平台通过可扩展 Seed 让不同游戏在统一生态中可用”；并不表示与该作品或其权利人存在关联。

## 2. 问题与目标

Nexus 面向三条会逐步汇合、但不应被强行混同的用户路径：

1. 玩家从目录选择一款受支持的游戏，在浏览器或其他客户端中立即游玩，并拥有自己的存档。
2. 服主从模板创建一台游戏服务器，取得连接地址和管理能力，并管理玩家、世界数据及生命周期。
3. 社区成员围绕游戏条目分享攻略、评价和心得；这些内容不依赖某台实例正在运行。

目标是让新游戏类型的接入集中在相应 Seed 内，而不是修改账号、目录、调度和社区等平台核心。

MVP 验证的不是某一种游戏的网页化，而是完整的最小路径：管理员登记一个可授权游玩的 **Game / Release** 并绑定满足能力合同的 **Seed**；玩家在 Portal 中发现该项目，经登录与授权后通过 **Gate** 进入运行负载；平台保留运行诊断与可恢复的个人进度。首期以一个经实际验证的 `web-play` Seed 为实现载体，可部署在单机或可信局域网。

首期的社区能力仅限于 Game / Release 的浏览、项目说明和受授权游玩入口；评论、攻略、评分、群组与审核仍是后续领域。服务器托管也不是 MVP 的交付条件，但必须由 Seed、Runtime 与持久化边界预留扩展位置。

非目标：

- 不把 Nexus 设计成游戏商店、破解分发渠道或通用模拟器前端。
- 不承诺任何桌面游戏都能自动转成网页游戏。
- 不在首期构建多租户公网站群、计费、联邦社交或通用集群编排。
- 不以单一的 `start()` 接口掩盖网页游玩和专用服务器之间不同的安全与数据语义。

## 3. 核心模型

```text
The Seed
├─ Nexus
│  ├─ Catalog        游戏条目、发行版、支持状态与资产来源
│  ├─ Identity       用户、会话、授权与个人资料
│  ├─ Seed Registry  Seed 清单、版本、能力与适配配置
│  ├─ Runtime        创建、暴露、观测、停止和回收运行负载
│  ├─ Persistence    存档、世界数据、实例配置与备份
│  └─ Community      攻略、评论、评分、讨论与群组
└─ Seed
   ├─ web-play          浏览器可玩的静态/转换运行时
   ├─ dedicated-server  有端口、管理面和世界数据的专用服务器
   ├─ emulator-play     （未来）经允许的模拟器运行时
   └─ remote-stream     （未来）远程渲染/串流运行时
```

### 3.1 领域对象与所有权

| 对象 | 含义 | 所有者 | 生命周期 |
| --- | --- | --- | --- |
| Game | 面向用户的游戏条目 | Catalog | 长期 |
| Release | 一个可运行版本及其授权/来源记录 | Catalog | 长期、可替换 |
| Seed | 对某类引擎或发行形态的适配实现 | Seed Registry | 可版本化 |
| Deployment | `Release + Seed + 配置` 的一次可运行声明 | Runtime | 可重建 |
| Play session | 某用户的一次游玩会话 | Runtime | 短暂 |
| Server instance | 服主创建的一台专用服务器 | 服主；平台托管 | 可停止、可重建 |
| Save | 某用户在某 Game/Release 下的存档 | 用户 | 长期 |
| World data | 某 Server instance 的地图与插件状态 | 服务器实例/服主 | 长期 |
| Community content | 攻略、评价、评论等 | 创作者，受社区规则约束 | 长期 |

**资产、用户存档、世界数据三者必须分离。** 游戏资产应可复用且尽可能只读；Save 按用户隔离；World data 仅属于其服务器实例。任何 Seed 都不得把它们混入一个可写目录。

## 4. Seed 合同

Seed 由平台加载的不是任意脚本，而是一份受版本控制的清单和实现。清单至少应声明：适用的游戏/引擎版本、资源检查方式、所提供的能力、所需持久卷、网络暴露面、管理接口和健康检查。

```text
Seed
  validate(asset) -> 适配性报告
  prepare(read-only asset, configuration) -> 运行产物/覆盖层
  capabilities -> web-play | dedicated-server | ...
  runtime specification -> 镜像、命令、挂载、资源限制、健康检查
  persistence schema -> save | world | instance-config
  exposure -> HTTP 入口或游戏协议端口
  administration -> 可选；明确的管理协议与权限模型
```

`validate` 必须在创建负载前失败并给出原因；`prepare` 应优先生成覆盖层或派生产物，不能原地修改用户提供的游戏资产。Seed 只能访问平台显式授予的卷、环境变量和网络，不获得宿主机任意目录或 Docker 控制面权限。

### 4.1 两类首要能力

| 能力 | 面向对象 | 关键输出 | 持久化 | 典型 Seed |
| --- | --- | --- | --- | --- |
| `web-play` | 玩家 | 受认证保护的 HTTP 入口 | 用户 Save | RPG Maker MV/MZ 网页适配 |
| `dedicated-server` | 服主与玩家 | 地址、协议端口、状态、管理员入口 | World data、实例配置 | Minecraft、Source/L4D2 |

二者共享运行创建、权限检查和审计，但不能共享错误的数据合同。网页游戏需要浏览器兼容性和存档同步；专用服务器需要端口声明、白名单、管理员通道、备份与资源上限。一款游戏可以同时由不同 Seed 或同一多能力 Seed 提供这两类能力。

## 5. 组件边界与依赖规则

```text
Web/UI ─┐
API ────┼──> Application services ──> Domain contracts
Worker ─┘           │                       │
                     ├──> Seed Registry <───┘
                     └──> Ports: database / object storage / runtime executor

Seed implementation ──> Seed SDK contracts
Runtime executor ─────> container or process infrastructure
```

- Catalog、Identity、Community 不依赖某个特定 Seed。
- Runtime 只依赖 Seed SDK 的声明和受限执行接口，不导入具体引擎实现。
- Seed 可依赖 SDK 与自身的适配工具，不能直接读写用户库、社区库或其他 Seed 的数据。
- Community 通过稳定的 `game_id` / `release_id` 关联目录，不调用实例生命周期。
- 运行时基础设施（Docker、反向代理、SQLite 等）置于端口之后；领域和 Seed 清单不应嵌入供应商专有调用。

首期可以是单体应用加一个本地运行 worker；此处的边界是代码和数据所有权，不要求微服务。

## 6. 生命周期

### 6.1 浏览器游玩

```text
用户选择 Game
  → Portal 展示 Release 的支持状态与访问条件
  → Identity 授权，Catalog 找到受支持 Release 与 web-play Seed
  → Link Start 以幂等键编排 Seed validate / prepare
  → Runtime 创建或复用受限 HTTP 负载
  → Gate 发布短期、受控入口
  → 客户端拉取自己的 Save 快照，写入本地即时缓存
  → 游戏运行；保存时先写本地缓存，再同步服务端
```

### 6.2 专用服务器

```text
服主选择 Game 与服务器模板
  → Seed validate / prepare
  → Runtime 分配受限网络、持久 World data 与实例配置
  → 创建实例并通过健康检查
  → 返回连接地址与受权限保护的管理入口
  → 服主操作白名单/备份/停止；审计关键操作
  → 停止后保留 World data，实例可恢复或删除
```

## 7. MVP 实现边界

### 7.1 用户故事与范围

管理员可以登记 Game、一个或多个 Release、资产引用、授权来源和支持状态；为 Release 选择兼容的 Seed；在启动前取得“可运行、需适配或不支持”的检查报告；并查看游玩负载的入口、状态与失败诊断。Seed 处理的原始资产与平台数据相互隔离，运行期不把资产、数据库或个人进度混入临时容器层。

玩家可以在 Portal 中浏览可见的 Game 与 Release，了解游玩方式、支持状态和访问条件；登录后只能通过 Gate 进入被授权项目。对声明支持个人进度的 `web-play` 项目，进度先在客户端正常保存，再按项目协议同步和恢复，其他用户不能读取或覆盖它。

MVP 包含：

- Portal 中最小的 Game / Release 浏览页、项目说明与受授权游玩入口。
- 最小账户、登录会话、Game 授权和 Catalog 管理能力。
- Seed Registry、Seed 能力合同，以及一个经过验证的 `web-play` Seed。
- Runtime、Gate 与运行诊断；实现可以是一个应用进程、SQLite 与 Docker Compose。
- 对 Seed 声明支持的项目提供个人进度快照、冲突处理、备份说明和本地/局域网 HTTPS 部署路径。
- 对一个真实、经授权的 Seed 输入进行端到端验证。

MVP 不包含：开放投稿的公共游戏目录、评论/攻略、好友、Guild、商业支付与 Steam 登录；任意游戏或引擎的自动兼容；Minecraft/L4D2 一键开服；多节点调度、自动扩缩、公开互联网多租户隔离或计费；以及绕过 DRM、托管未获授权资源或承诺浏览器已取得的资产仍可保密。

### 7.2 MVP 模块与调用方向

MVP 采用**模块化单体**：Web、API 和本地 worker 可以部署在同一台机器，领域模块也可以暂时运行在同一进程，但代码、数据所有权和调用方向必须明确。模块不是微服务；只有出现独立扩缩、故障隔离或团队所有权需求时，才考虑拆成独立进程。MVP 可共用一个 SQLite 数据库，但表、迁移和 Repository 仍由相应模块拥有。

| 模块（代码名） | Nexus 语义名 | 责任 | 拥有的数据/状态 | MVP 程度 |
| --- | --- | --- | --- | --- |
| `portal` | **Nexus** | 玩家与管理员 Web 界面；组合 API 返回的数据 | 仅前端状态 | 必须 |
| `identity` | Player Identity | 注册/登录、会话、角色、授权判断 | 用户、凭据、会话、角色 | 必须 |
| `catalog` | **World Index** | Game / Release、资产引用、授权来源、支持状态与展示元数据 | 游戏、发行版、资产引用 | 必须 |
| `seed_registry` | **Seed Registry** | Seed 清单、版本、能力和兼容条件；Seed SDK 合同 | Seed 元数据、版本、能力 | 必须 |
| `launch` | **Link Start** | 编排选择 World、校验权限、选择 Seed、创建 Deployment、返回 Gate | 启动请求及幂等键；不拥有容器 | 必须 |
| `runtime` | Runtime | 创建、检查、停止和回收运行负载；隐藏 Docker | Deployment、运行状态、诊断 | 必须 |
| `gate` | **Gate** | 将授权用户路由到正确负载，签发/校验短期入口 | 路由、入口有效期、访问审计 | 必须 |
| `progress` | Progress Archive | 为支持该能力的项目保存版本化个人快照、检测冲突、恢复历史版本 | progress、revision、同步记录 | 最小实现 |
| `infrastructure` | 无对外名称 | 实现 SQLite、Docker、反向代理、文件系统和时钟端口 | 技术配置，不拥有领域规则 | 必须 |

```text
portal
  └─> application API
       ├─> identity
       ├─> catalog
       ├─> launch (Link Start)
       │    ├─> identity authorization port
       │    ├─> catalog query port
       │    ├─> seed_registry
       │    ├─> runtime port
       │    └─> gate port
       └─> progress
            ├─> identity authorization port
            └─> catalog identity/reference port

seed implementations ──> Seed SDK contracts
runtime ────────────────> Runtime Executor port <── infrastructure/docker
gate ───────────────────> Route Publisher port  <── infrastructure/reverse-proxy
domain modules ─────────> Repository ports      <── infrastructure/sqlite
```

- `identity` 不依赖 Catalog、Seed、Runtime 或 Portal。
- `catalog` 可以保存 Seed binding 的标识，但不加载具体 Seed 实现。
- `launch` 只做跨模块用例编排；它不能包含某个引擎特例或 Docker 命令。
- `runtime` 只接受 Seed 产出的通用 Runtime specification；它不知道具体游戏或引擎。
- `gate` 只负责访问入口和路由，不负责密码校验，也不成为第二套权限数据库。
- `progress` 使用稳定的 `user_id`、`game_id`、`release_id`，不依赖某次短暂 Deployment；不支持该能力的 Seed 不调用它。
- `infrastructure` 实现领域定义的端口，领域模块不能反向依赖 Docker SDK、SQLite 查询细节或代理配置格式。

### 7.3 最小合同、状态机与目录草案

模块之间首期只需要以下对象，不预先建立通用事件总线：

| 提供方 | 最小合同 | 消费方 |
| --- | --- | --- |
| `identity` | `Actor`、`authorize(actor, action, resource)` | `launch`、`gate`、`progress` |
| `catalog` | `Game`、`Release`、`AssetRef`、`SeedBinding`、`Visibility` | `launch`、`progress`、Portal 查询 |
| `seed_registry` | `validate`、`prepare`、`RuntimeSpec`、`InspectionReport` | `launch`、具体 Seed |
| `runtime` | `create`、`inspect`、`stop`、`DeploymentStatus` | `launch`、Portal 管理视图 |
| `gate` | `publish`、`resolve`、`revoke`、`AccessEndpoint` | `launch`、浏览器入口 |
| `progress` | `getSnapshot`、`putSnapshot(expectedRevision)`、`ProgressConflict` | 声明支持同步的项目启动壳 |

运行状态使用显式状态机，避免通过“容器是否存在”猜测业务状态：

```text
Draft → Validating → Prepared → Starting → Ready
          │             │          │         │
          └─────────────┴──────────┴────────> Failed

Ready → Stopping → Stopped
```

重复的 Link Start 请求通过幂等键返回同一 Deployment，或明确创建新会话；不能因为浏览器重试而生成多份不受管理的负载。只有 `Ready` 状态可以发布 Gate；进入 `Failed`、`Stopping` 或 `Stopped` 后撤销入口。

目录只是逻辑边界草案，具体语言与框架确定后可以调整：

```text
apps/
├─ web/                    # Nexus Portal
├─ api/                    # HTTP API 与用例入口
└─ worker/                 # 本地运行任务；首期可与 api 同进程
modules/
├─ identity/
├─ catalog/
├─ seed-registry/
├─ launch/
├─ runtime/
├─ gate/
└─ progress/
seed-sdk/                  # 清单、能力和 RuntimeSpec 合同
seeds/                     # 各游戏/引擎适配
infrastructure/
├─ sqlite/
├─ docker/
├─ reverse-proxy/
└─ filesystem/
```

## 8. SAO 语义层（可选，非技术耦合）

下表只为命名与界面语言提供约束；底层代码仍使用清晰的通用术语，避免把粉丝术语变成难懂的协议。

| 名称 | 来源事实 | 在 Nexus 中的建议范围 | 不应承担的职责 |
| --- | --- | --- | --- |
| **The Seed** | SAO 中的虚拟世界开发框架意象 | 平台/代码库总名 | 单个游戏或容器实例 |
| **Nexus** | 通用“连接点”一词，并非声称为 SAO 专有名词 | 对外生态、目录与体验层 | 单一技术服务 |
| **Seed** | 与 The Seed 的“世界创造工具”意象相连 | 引擎适配包 | 游戏资源、用户存档 |
| **World** | SAO 叙事中的可进入虚拟世界是稳定概念 | 用户可进入的 Game/Release 体验 | 容器或服务器进程 |
| **Gate** | SAO 中常见的世界间移动/入口意象 | 受授权的访问入口、连接信息 | 身份系统本身 |
| **Cardinal** | SAO 中管理虚拟世界的系统名 | 未来的运维/策略子系统候选 | MVP 核心、用户社区 |
| **Guild** | 多人线上游戏中的稳定组织概念，SAO 亦使用 | 社区群组或服务器成员组织 | 认证、资源调度 |
| **Avatar** | 虚拟世界中的玩家化身意象 | 可选的游戏内展示资料 | 账户主键或权限模型 |

推荐当前就固定前三个：**Nexus**（生态）、**The Seed**（平台）、**Seed**（适配包）。`World` 与 `Gate` 可以作为面向用户的通用名词。`Cardinal`、`Guild`、`Avatar` 留到它们对应的真实子域出现时再启用；不要为了凑世界观预先建模块。

## 9. 安全、授权与运维底线

- 平台只登记用户拥有、获授权或可合法托管的资产；“支持”不等于代为分发游戏。
- 每个负载采用最小权限：只读资产、独立可写卷、非 root 用户、资源限制、受控网络和显式端口。不要把 Docker socket 暴露给 Seed。
- 所有公网入口使用 HTTPS；会话 Cookie 使用 `HttpOnly`、`Secure` 与合适的 `SameSite` 策略。局域网也不应把密码和会话裸露在 HTTP 上。
- Save 写入使用版本号或等价的冲突检测；Server world 在停止、升级和删除前应有可恢复备份。
- 对实例创建、管理员操作、公开暴露端口和数据删除保留审计记录。

## 10. MVP 交付、完成定义与后续演进

MVP 按以下顺序交付：

1. 定义 `Game`、`Release`、`AssetRef`、`SeedBinding` 与社区展示所需的最小 Catalog；完成管理员登记流程和玩家浏览页。
2. 定义 Seed SDK 的能力、校验报告、准备产物和 `RuntimeSpec` 合同；将一个已验证的 `web-play` Seed 接入 Registry。
3. 从平台控制面启动和停止该 Seed 的运行负载，完成鉴权、幂等 Link Start 与仅受控 Gate 入口。
4. 对该 Seed 声明支持的项目接入本地账户、授权与版本化个人进度 API；验证启动、保存与恢复边界。
5. 以两台设备完成发现、登录、入口、首屏、输入、保存、恢复、账户隔离和冲突处理的端到端验证。
6. 用一个不支持的输入样本验证失败诊断与回滚，而不只验证成功路径。

满足以下条件时，MVP 才算完成：

- 玩家能在 Portal 中看到一个有明确版本与访问条件的 Game，并通过登录和授权进入受控游玩入口。
- 管理员能创建、检查、启动和停止一个 Seed 绑定的 Release；原始资产、持久数据和运行临时层保持隔离。
- 两个账户在两台设备上可进入同一支持个人进度的项目，互不可见彼此的数据；重开、服务重启与设备切换均能恢复最近一次成功同步的数据。
- 不支持的资产或环境依赖会在启动前或明确的适配步骤中被报告，不在玩家页面静默失败。
- Runtime 没有宿主机任意目录访问权、没有 Docker socket；所有用于验收的游戏资源都有明确的使用/托管授权记录。
- 首个 Seed 的专属限制、适配规则与实测证据独立记录在其文档中，不反向污染平台核心合同。

MVP 完成后，再按以下顺序演进：

1. 为当前 Minecraft 或 L4D2 资源选择一个 `dedicated-server` Seed，验证端口、世界卷和服主管理边界。
2. 抽取稳定的 Seed SDK 和登记机制，再增加更多引擎适配。
3. 在 Game 条目稳定后接入攻略、评分与讨论；群组/服务器社区随后独立演进。

后续模块只保留扩展位置，不在 MVP 中创建空表、空服务或占位 API：

| 后续模块 | 责任 | 与 MVP 的连接点 |
| --- | --- | --- |
| `community` | 攻略、心得、评分、评论与审核 | 只引用 `catalog` 的 `game_id`；不依赖 Runtime |
| `guilds` | 玩家群组、服务器成员与共同体权限 | 依赖 Identity；可关联 Game/Server instance |
| `server_rooms` | 服主创建、邀请、成员管理与连接信息 | 复用 Launch、Gate、Runtime，使用 `dedicated-server` Seed |
| `cardinal` | 配额、调度策略、自动恢复、多节点与运行治理 | 位于 Runtime specification 与执行器之间或之上 |
| `seed_exchange` | Seed 的发现、签名、兼容性与分发 | 扩展 Seed Registry；必须先解决信任与供应链安全 |
| `moderation` | 举报、审核、封禁与内容治理 | 服务 Community/Guild，不进入运行控制面 |

每一步至少验证：未经授权的用户不能访问入口或数据；停止和重启不会丢失应持久的数据；替换 Seed/Release 不会静默污染原始资产；失败时能给出 Seed、版本和资源检查阶段的诊断。
