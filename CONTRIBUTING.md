# 贡献指南

## 提 issue

- 缺陷：写清现象、复现步骤、运行环境与命令输出。
- 需求：写清使用场景与期望行为。

注意：状态输出里不要贴 `access_token` 或 `refresh_token`，贴之前自行打码。

## 提 PR

1. 从 `main` 拉分支，一个小改动一个 PR。
2. 保持单文件结构，不引入新的第三方依赖，HTTP 继续用标准库。
3. 面向终端与日志的输出一律 ASCII 英文，注释可用中文。
4. 提交前自行跑通 `list` 与 `claim --dry-run`，在 PR 描述里写清验证方式。

## 硬约定

- 脚本对凭据来源只读，任何改动不得写回。
- 不要提交任何含令牌的文件。
- 接口路径、超时、重试次数这类易变值集中放在常量区。

## 本地检查

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe codebuddy_claim.py --data examples/sample-accounts.json list

.\.venv\Scripts\python.exe -m pip install pre-commit
.\.venv\Scripts\python.exe -m pre_commit run --all-files
```

打包元数据在 `pyproject.toml`，动它之前先验证还能装能跑：

```powershell
.\.venv\Scripts\python.exe -m pip install .
codebuddy-claim --data examples\sample-accounts.json list
```

装完记得清掉 `build/` 与 `*.egg-info/` 两个目录，它们被忽略，但容易忘了清。
