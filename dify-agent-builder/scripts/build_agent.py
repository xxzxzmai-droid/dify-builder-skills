#!/usr/bin/env python3
"""把一份 BlueprintSpec JSON 渲染成可导入的 Dify 0.3.0 Chatflow YAML。

用法：
    python3 build_agent.py <blueprint.json> <output.yml>

BlueprintSpec 的结构见 ../references/blueprint-spec.md。
本脚本是确定性引擎：你（设计者）只负责写好 blueprint，剩下的拼装/接线/校验交给它。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assembler as A


def main():
    if len(sys.argv) != 3:
        print("用法: python3 build_agent.py <blueprint.json> <output.yml>", file=sys.stderr)
        sys.exit(2)
    blueprint = json.load(open(sys.argv[1], encoding="utf-8"))
    app = A.assemble(blueprint)
    dsl = A.dump_yaml(app)
    val = A.validate(app, blueprint, dsl)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(dsl)
    g = app["workflow"]["graph"]
    print(f"✅ 已生成 {sys.argv[2]}")
    print(f"   节点 {len(g['nodes'])}、连线 {len(g['edges'])}；类型: {[n['data']['type'] for n in g['nodes']]}")
    if val.get("warnings"):
        print("   注意事项:")
        for w in val["warnings"]:
            print("   - " + w)
    if val.get("manual"):
        print("   导入后需手动配置:")
        for m in val["manual"]:
            print("   - " + m)


if __name__ == "__main__":
    main()
