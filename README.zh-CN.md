# codebuddy-claim

[English](README.md) | 简体中文

一条命令批量领取 CodeBuddy 账号的积分福利（活动补偿、欢迎礼包）。单文件脚本，唯一第三方依赖 `cryptography`，HTTP 走标准库。对凭据来源只读，不写回。

## 一、前置条件：准备一份凭据文件

脚本不会调用任何账号管理工具的导入导出功能，它只读一份 JSON 凭据文件。无论你用什么工具管理账号，把数据整理成下面的格式即可，模板见 `docs/credentials-template.json`。

文件为 UTF-8 编码的 JSON 数组，每个元素一个账号。字段要求：

| 字段 | 必填 | 说明 |
| :-- | :-- | :-- |
| access_token | 是 | 登录态 JWT，请求以 Bearer 方式携带 |
| domain | 是 | 账号所属站点域名，如 www.codebuddy.cn 或 www.codebuddy.ai |
| id | 否 | 账号标识。用于去重与 `--account` 过滤，优先级最高 |
| uid | 否 | 账号标识。id 缺失时用它去重与过滤 |
| email | 否 | 显示名（手机号或邮箱），用于展示与过滤 |
| expires_at | 否 | token 过期时间，毫秒时间戳。缺省时列表显示 UNKNOWN |
| refresh_token | 否 | 刷新令牌。access_token 失效时脚本会用它尝试续期一次 |
| status | 否 | 仅作展示 |
| nickname | 否 | 脚本当前不读取，可留可删 |

只有 access_token 与 domain 是硬性必需。缺任一个或值为空串，该账号被静默跳过，输出里不会出现，也不影响其他账号。数字类型的 id 与 uid 会自动转成字符串，多余字段一律忽略。

如果导出源里没有 domain 字段，手动补一个即可。取值只有 www.codebuddy.cn 与 www.codebuddy.ai 两种，按账号实际所属站点选。

带随机数值的完整样例见 `examples/sample-accounts.json`，可直接拿来试跑。

如果你用的恰好是 Cockpit Tools：它的账号导出功能导出的就是这个格式，直接可用；本机装有它时也可以跳过导出，让脚本自动读取本地数据（见下文第二节）。

## 二、怎么用

以下命令均在项目根目录下执行。Windows 用 `.\.venv\Scripts\python.exe`，macOS/Linux 用 `.venv/bin/python`：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe codebuddy_claim.py list             # 看有哪些账号、token 是否有效
.\.venv\Scripts\python.exe codebuddy_claim.py claim --dry-run  # 只查谁可以领，不领取
.\.venv\Scripts\python.exe codebuddy_claim.py claim            # 正式领取
```

日常只需要最后一条。有新活动时跑一次即可，已领过的账号自动跳过，重复跑没有副作用。

凭据来源两种方式：

1. `--data <文件路径>` 指定凭据文件，通用方式，推荐。
2. 本机装有 Cockpit Tools 时可不导出，脚本自动解密其本地账号库：默认探测用户主目录下的 `.cockpit_tools` 与 `.antigravity_cockpit`，可用环境变量 `COCKPIT_TOOLS_HOME` 指定其他位置。

过滤与限定参数：`--account 关键词` 按 email、id、uid 子串过滤，`--cockpit-root 路径` 手动指定 Cockpit 数据根。这些参数写在子命令前面或后面都可以。

结果状态对照：

| 状态 | 含义 | 要做什么 |
| :-- | :-- | :-- |
| CLAIMED credit=N | 领取成功，到账 N 积分 | 无 |
| ALREADY-CLAIMED | 之前已领过 | 无 |
| INACTIVE | 当前没有可领的活动 | 无。国际站账号无对应活动时显示这个，属正常 |
| CHECK-FAILED http=401 | 该账号 token 被服务端吊销 | 重新登录获取新凭据后重跑 |
| CLAIM-FAILED | 查询正常但领取被拒 | 记下响应内容，稍后重试 |

退出码：0 表示全部正常，2 表示存在失败条目，便于外部脚本判断。

## 三、让 AI 操作

把下面整段复制发给 AI，在项目根目录下启动会话，替换尖括号内容即可：

```text
帮我领取 CodeBuddy 账号的积分福利。本会话工作目录就是本工具的项目根目录，先读 ./README.md 了解用法与注意事项，然后执行：
1. 运行 codebuddy_claim.py claim --dry-run --data <凭据文件路径>，把每个账号的状态汇总给我。
2. dry-run 无异常后去掉 --dry-run 正式领取。
3. 最后汇报：哪些账号领到了多少积分、哪些已领过、哪些失败及原因。
约束：CHECK-FAILED http=401 的账号是凭据失效，如实报告即可，由我人工重新获取凭据；不要修改凭据来源应用的任何数据文件；不要把 token 或凭据内容输出到对话之外。
```

说明：凭据文件路径填你自己的存放位置，相对或绝对均可；本机装有 Cockpit Tools 时可去掉 `--data`，脚本自动探测本机数据根。

## 四、工作原理

### 接口

```
POST https://<domain>/billing/meter/compensation-status   # 查补偿状态
POST https://<domain>/billing/meter/claim-compensation    # 领补偿
POST https://<domain>/billing/meter/check-gift-claimed    # 查礼包状态
POST https://<domain>/billing/meter/claim-gift            # 领礼包
```

请求头带 `Authorization: Bearer <access_token>` 与 `X-Client-Platform: web`。响应 `code=0` 且 `data.active=true` 且 `data.claimed=false` 才调用领取接口。端点来自 codebuddy.cn 个人中心前端 bundle 的反查，页面为 /profile/plans-usage。

### Cockpit Tools 本地存储（可选捷径）

脚本不会调用该工具，只直接读取其本地数据文件，全程只读：

- 数据根下有 `secure-account-storage.key`，内容是明文 base64 的 32 字节 AES-256 密钥
- `codebuddy_accounts\*.json` 与 `workbuddy_accounts\*.json` 为加密账号对象，`nonce` 与 `ciphertext` 是 base64，AES-256-GCM 解密后即凭据 JSON
- 同一账号在两个目录都有文件时，按 access_token 的 JWT iat 取最新一份
- 用其他账号管理工具的用户可忽略本节，走 `--data` 凭据文件即可

### 网络与安全

- 必须直连不走系统代理，脚本已内置禁代理；换 HTTP 客户端时要显式禁代理
- 账号之间有固定间隔，不要并发
- 对 Cockpit 存储一律只读
- 凭据文件含登录态，不要提交到任何仓库或同步到公开位置
- 领取历史写入系统用户数据目录下的 `codebuddy-claim/claim-history.jsonl`（Windows 在 %LOCALAPPDATA%，其他平台回退到用户主目录）

## 五、已知限制

- access_token 失效时脚本会用 refresh_token 尝试续期一次，实测官方对第三方刷新请求返回 401，因此失效账号仍需重新登录获取新凭据
- access_token 的 JWT exp 只是签发声明，服务端吊销后 list 仍显示 VALID，401 才是真实判据
- 接口端点来自前端 bundle 反查，官方改版可能导致端点变化，届时重新抓包更新

## 六、文件结构

```
codebuddy-claim/
├── codebuddy_claim.py            # 主脚本（单文件）
├── README.md                     # 英文说明（GitHub 默认展示）
├── README.zh-CN.md               # 中文说明（本文件）
├── LICENSE                       # MIT
├── CONTRIBUTING.md               # 贡献指南
├── CHANGELOG.md                  # 版本变更记录
├── FAQ.md                        # 常见问题
├── SECURITY.md                   # 安全策略
├── AUTHORS                       # 作者
├── pyproject.toml                # 打包元数据
├── requirements.txt              # cryptography>=42.0，Python 3.9+
├── .gitignore                    # 排除 .venv、__pycache__、data
├── .gitattributes                # 行尾与 diff 规则
├── .pre-commit-config.yaml       # 本地文本规范钩子
├── .github/
│   ├── ISSUE_TEMPLATE/           # 缺陷与需求模板
│   └── pull_request_template.md  # PR 模板
├── examples/
│   └── sample-accounts.json      # 凭据文件格式样例，值为随机数
├── docs/                         # 分析与运行记录
└── data/                         # 凭据文件存放处（勿提交仓库）
```
