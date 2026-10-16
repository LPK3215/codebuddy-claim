# CodeBuddy 账号奖励领取工具 项目分析

日期：2026-10-16
分析对象：d:/Develop/SourceCode/pythoncode/codebuddy-claim
分析方式：通读全部源码，真实运行验证。

## 一、项目定位

批量领取 CodeBuddy 账号活动奖励的本地命令行工具，覆盖 DeepSeek 补偿与新人礼包两类。账号来自 Cockpit Tools 的本地加密存储，或手工导出的 JSON 文件。

## 二、组成与规模

- codebuddy_claim.py：全部逻辑，单文件。
- requirements.txt：cryptography>=42.0，唯一第三方依赖，注明需要 Python 3.9 及以上。
- .gitignore：排除 .venv、__pycache__ 与 data 目录。
- data/workbuddy_accounts_2026-10-16.json：8 个账号的导出，含明文 access_token 与 refresh_token，已被 .gitignore 排除。
- .venv：Python 3.11.8 虚拟环境。
- docs/PROJECT-ANALYSIS.md：本文档。
- 无 git 仓库，无 README，无测试。

## 三、运行链路

1. 凭证加载。在 Cockpit 根目录读 secure-account-storage.key，对 codebuddy_accounts 与 workbuddy_accounts 下每个 json 的 nonce 与 ciphertext 做 AES-256-GCM 解密；同一账号取 JWT iat 最新的一条。也可以用 --data 直接指定导出文件。
2. token 状态。用 expires_at 与当前时间比较，输出 VALID、EXPIRED 或 UNKNOWN。
3. 业务调用。每个账号依次调两组端点，先查后领。第一组是 compensation-status 与 claim-compensation，第二组是 check-gift-claimed 与 claim-gift。
4. 鉴权。请求带 Bearer token 与 X-Client-Platform: web。遇到 401 时用 refresh_token 走 Keycloak realm copilot、client_id console 刷新一次，随后重试。
5. 落账。结果写入 %LOCALAPPDATA%\codebuddy-claim\claim-history.jsonl，按次追加。
6. 网络。构建 opener 时挂空 ProxyHandler，强制直连不走代理；User-Agent 伪装为 Chrome。

## 四、设计上成立的地方

- 对 Cockpit 存储只读，不回写任何内容。
- 端点、超时、重试次数、调用间隔、UA、历史文件上限全部提为常量。
- 全部输出为 ASCII 英文。
- 提供 dry-run，可在不触发领取的前提下查看状态。
- 统计失败条目，有失败时以 exit code 2 退出，便于外部脚本判断。
- HTTP 只用标准库，依赖面很小。
- 全局选项在命令名之前与之后都能解析。

## 五、修复记录

2026-10-16 完成，逐条给出验证方式。

1. 使用示例与实现不符。原 docstring 示例写成 claim --account user@example.com，报 unrecognized arguments。修复方式是让 --cockpit-root、--data、--account 同时注册到顶层解析器与子命令解析器，子命令侧使用 argparse.SUPPRESS 保留父级取值。验证：选项写在命令前、命令后、两处混用，三种写法都正确命中目标账号。
2. 空 id 账号会被合并。新增 account_key，去重键依次取 id、uid、access_token。验证：构造一份加密存储副本，两条空 id 且 uid 不同的账号全部保留，账号总数由修复前的 3 变为 4。
3. id 与 uid 类型未归一。account_from_obj 现在把 id、uid、email、nickname、refresh_token、status 一律转为字符串，domain 与 access_token 校验必须是字符串。验证：id 为数字、uid 为数字的账号正常列出，--account 用数字 id 过滤正确命中。
4. 明文凭证入库风险。新增 .gitignore，排除 data 目录与 .venv。项目当前不是 git 仓库，真正提交时再初始化即可。
5. Python 版本未声明。requirements.txt 增加版本说明，脚本启动时检查 sys.version_info，低于 3.9 直接以状态码 1 退出。
6. 历史文件只增不减。新增 rotate_history，文件超过 5 MiB 时重命名为 claim-history.jsonl.1，旧 .1 被覆盖，随后写新文件。同时修掉首次写入时文件不存在产生的无效告警。验证：把阈值调到 200 字节连写三次，第三次触发轮转，备份保留前两条，当前文件保留最后一条。
7. 冗余判断与统计文案。删掉永不成立的 .bak 分支，summary 行的失败字段改为 failed_items，明确它统计的是条目数。

## 六、遗留观察

- token_state 只依据本地 expires_at，本机时钟偏差会造成 VALID 与 EXPIRED 误判。真实有效性以接口返回为准。属设计取舍，未改动。
- 三个账号的 access_token 已失效，查询返回 401，刷新令牌也未能续期。工具行为正确，问题在账号侧状态。

## 七、真实运行结论

- list 走 Cockpit 解密链路，10 个账号全部解析成功。
- claim --dry-run 覆盖全部 10 个账号、20 个条目。3 个账号因令牌失效返回 401，其余返回 ALREADY-CLAIMED 或 INACTIVE。
- 退出码符合预期：存在失败条目时为 2，全部正常时为 0。
