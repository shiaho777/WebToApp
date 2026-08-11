# 贡献指南 (简体中文)

感谢你参与改进 WebToApp!本指南说明改动如何合入本项目。

**English** · 简体中文

## 交付流程

每一次有意识的改动 —— 新功能、修复或文档 —— 都遵循同一条流程:

```
Issue → 向 main 提 PR → CI 通过 → 合并 → Issue 自动关闭
```

1. **从 Issue 开始。** 如果还没有对应 Issue,[新建一个](https://github.com/shiaho777/WebToApp/issues/new),描述问题和改动范围。
2. **从 `main` 切分支。** 用清晰的命名(`fix/...`、`feat/...`、`docs/...`)。
3. **实施改动。** 保持提交聚焦。不要提交密钥、`generated/`、`certs/*.keystore` / `*.pem` 或 IDE/系统垃圾文件 —— 它们已被 git 忽略。
4. **本地跑测试:**
   ```bash
   pip install -r server/requirements.txt
   pip install pytest
   pytest tests/
   ```
5. **向 `main` 提 Pull Request。** 按模板填写:
   - **Summary** —— 改了什么、为什么。
   - **Fixes #N**(或 `Closes #N`) —— 让 Issue 在 PR 合并时自动关闭。
   - **Test plan** —— 你是怎么验证的。
6. **等 CI。** `ci / test` 会在 Python 3.10 / 3.11 / 3.12 上跑测试套件,必须全绿才能合并。
7. **合并。** CI 绿之后,维护者合并 PR,Issue 会自动关闭。

## 规则

- **基线分支是 `main`。** 功能 PR 只能合进 `main`。
- **CI 是合并门槛。** 不要合并红色检查。CI 绝不自动关闭 Issue —— Issue 通过 `Fixes #N` / `Closes #N` 在合并时关闭。
- **一个 PR 对应一个主 Issue。** 其他 Issue 用链接引用,不要带额外的关闭关键词。
- **前端改动:** 改 `css/` 或 `js/` 时,记得 bump `index.html` 里的 `?v=` 缓存戳。

## 报告 Bug

开 Issue 时请包含:
- 期望的行为 vs 实际发生的情况。
- 你测试的 URL(WebToApp 本身的网址,或你封装的目标网站)。
- 复现步骤,以及你的平台 / 浏览器。

## 行为准则

友善、建设性。我们都是为了做出一个好用的工具。
