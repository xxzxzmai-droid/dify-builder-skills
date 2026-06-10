# 离线安装说明

这个离线包包含两个可直接安装的 Codex/Claude skill：

- `dify-agent-builder`：从自然语言需求生成可导入 Dify Chatflow `.yml`
- `dify-plugin-builder`：从自然语言需求生成并打包 Dify 工具插件 `.difypkg`

## 推荐安装方式

解压后进入离线包目录，直接运行：

```bash
./install_offline.sh --target codex
```

如果同时想安装到 Claude：

```bash
./install_offline.sh --target both
```

然后重启 Codex/Claude。

如果你的 agent 只收到 zip 附件，请先让它解压附件，再在解压目录执行上面的命令。

## 手动安装到 Codex

也可以把两个目录复制到本机 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R dify-agent-builder ~/.codex/skills/
cp -R dify-plugin-builder ~/.codex/skills/
```

## 安装到 Claude

把两个目录复制到 Claude skills 目录，例如：

```bash
mkdir -p ~/.claude/skills
cp -R dify-agent-builder ~/.claude/skills/
cp -R dify-plugin-builder ~/.claude/skills/
```

复制后重启 Claude。

## 验证

```bash
python3 ~/.codex/skills/dify-agent-builder/scripts/build_agent.py \
  ~/.codex/skills/dify-agent-builder/examples/knowledge_qa.json \
  /tmp/dify-knowledge-qa.yml
```

如果看到生成 `.yml` 且节点连线统计正常，说明智能体生成 skill 可用。

插件 skill 可用这个命令快速验证：

```bash
python3 ~/.codex/skills/dify-plugin-builder/scripts/scaffold_plugin.py /tmp/dify-plugin-smoke \
  --name dify_plugin_smoke \
  --author codex \
  --label-zh "插件测试" \
  --label-en "Plugin Smoke" \
  --description-zh "离线安装后的插件脚手架测试" \
  --description-en "Plugin scaffold smoke test"

bash ~/.codex/skills/dify-plugin-builder/scripts/pack_plugin.sh \
  /tmp/dify-plugin-smoke /tmp/dify-plugin-smoke.difypkg
```

打包输出里 `目录条目=0` 且 `manifest在根=1` 即为正常。
