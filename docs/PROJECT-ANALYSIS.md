# CodeBuddy 账号奖励领取工具 设计说明

本文说明工具的运行链路、设计取舍与已知边界。用法与字段要求见 [README.zh-CN.md](../README.zh-CN.md)，版本变更见 [CHANGELOG.md](../CHANGELOG.md)。

## 一、项目定位

批量领取 CodeBuddy 账号活动奖励的本地命令行工具，覆盖活动补偿与欢迎礼包两类。凭据来自手工导出的 JSON 文件，或 Cockpit Tools 的本地加密存储。

## 二、文件构成

- `codebuddy_claim.py`：全部逻辑，单文件。
- `requirements.txt`：`cryptography>=42.0`，唯一第三方依赖，要求 Python 3.9 及以上。
- `pyproject.toml`：打包元数据，提供 `codebuddy-claim` 命令。
- `examples/sample-accounts.json`：凭据文件样例，也可当模板照填。
- `data/`：本机凭据文件的存放处，已被 `.gitignore` 排除。

## 三、运行链路

1. 凭据加载。在 Cockpit 根目录读 `secure-account-storage.key`，对 `codebuddy_accounts` 与 `workbuddy_accounts` 下每个 json 的 `nonce` 与 `ciphertext` 做 AES-256-GCM 解密；同一账号取 JWT `iat` 最新的一条。也可以用 `--data` 直接指定导出文件。
2. token 状态。用 `expires_at` 与当前时间比较，输出 VALID、EXPIRED 或 UNKNOWN。
3. 业务调用。每个账号依次调两组端点，先查后领。第一组是 `compensation-status` 与 `claim-compensation`，第二组是 `check-gift-claimed` 与 `claim-gift`。
4. 鉴权。请求带 Bearer token 与 `X-Client-Platform: web`。遇到 401 时用 `refresh_token` 走 Keycloak realm copilot、client_id console 刷新一次，随后重试。
5. 落账。结果写入用户数据目录下的 `claim-history.jsonl`，按次追加。
6. 网络。构建 opener 时挂空 ProxyHandler，强制直连不走代理。

## 四、设计取舍

- 对凭据来源只读，不回写任何内容。这是工具的底线，避免破坏他人的账号管理工具。
- 先查后领。只有服务端明确返回可领才调领取接口，因此重复运行不会多领。
- 端点、超时、重试次数、调用间隔、UA、历史文件上限全部提为常量，官方改版时只改一处。
- 输出一律 ASCII 英文，避免终端编码问题。
- 失败条目计数，有失败时以 exit code 2 退出，便于外部脚本判断。
- HTTP 只用标准库，唯一依赖只用于解密，依赖面刻意保持很小。
- 全局选项在命令名之前与之后都能解析，两种写法都不会报错。
- 写操作不重试，避免超时发生在服务端已处理之后造成重复提交。

## 五、已知边界

- `token_state` 只依据本地 `expires_at`，本机时钟偏差会造成 VALID 与 EXPIRED 误判。真实有效性以接口返回为准，401 才是权威信号。
- 令牌被服务端吊销后，本地存储里仍是上一条凭据，只能重新登录获取新的。脚本会尝试用 `refresh_token` 续期一次，实测官方对第三方刷新请求返回 401。
- 接口端点来自前端 bundle 反查，官方改版可能导致端点变化。

## 六、验证记录

2026-10-16 实测，全部走真身脚本：

- `list` 走 Cockpit 解密链路，本机 10 个账号全部解析成功。
- `claim --dry-run` 覆盖全部 10 个账号、20 个条目，其中 3 个账号因令牌失效返回 401，其余返回 ALREADY-CLAIMED 或 INACTIVE。
- `claim` 正式运行结果一致，无重复领取，符合先查后领的设计。
- 退出码符合预期：存在失败条目时为 2，全部正常时为 0。
- 换新机器流程验证：新建虚拟环境装依赖后可直接运行；`pip install .` 安装后 `codebuddy-claim` 命令可用。
- 空 id 去重与类型归一验证：构造加密存储副本，两条空 id 且 uid 不同的账号全部保留；数字类型的 id 与 uid 正常列出并可过滤。
- 历史轮转验证：把阈值调小后连写三次，第三次触发轮转，备份保留前两条，当前文件保留最后一条。
