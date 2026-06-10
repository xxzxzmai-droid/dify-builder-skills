import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "dify-agent-builder"
EXAMPLES_DIR = AGENT_DIR / "examples"


def load_assembler():
    path = AGENT_DIR / "scripts" / "assembler.py"
    spec = importlib.util.spec_from_file_location("dify_agent_assembler", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = load_assembler()


def load_example(name):
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def graph_parts(app):
    graph = app["workflow"]["graph"]
    nodes = graph["nodes"]
    edges = graph["edges"]
    return nodes, edges


def node_types(app):
    return [node["data"]["type"] for node in graph_parts(app)[0]]


def assert_graph_is_wired(testcase, app):
    nodes, edges = graph_parts(app)
    ids = {node["id"] for node in nodes}
    testcase.assertEqual(len(ids), len(nodes), "node ids must be unique")
    for item in edges:
        testcase.assertIn(item["source"], ids)
        testcase.assertIn(item["target"], ids)


class AgentBuilderExamplesTest(unittest.TestCase):
    def test_examples_render_without_broken_edges(self):
        for path in sorted(EXAMPLES_DIR.glob("*.json")):
            with self.subTest(path=path.name):
                blueprint = json.loads(path.read_text(encoding="utf-8"))
                app = A.assemble(blueprint)
                dsl = A.dump_yaml(app)
                validation = A.validate(app, blueprint, dsl)
                assert_graph_is_wired(self, app)
                self.assertFalse(
                    [w for w in validation["warnings"] if "断线" in w or "重复节点" in w],
                    validation["warnings"],
                )
                self.assertNotIn("生成时的原始需求", dsl)

    def test_knowledge_example_has_expected_shape(self):
        app = A.assemble(load_example("knowledge_qa.json"))
        self.assertEqual(
            node_types(app),
            ["start", "knowledge-retrieval", "llm", "answer"],
        )
        self.assertFalse(app["workflow"]["features"]["file_upload"]["enabled"])
        self.assertTrue(app["workflow"]["features"]["retriever_resource"]["enabled"])

    def test_document_export_enables_upload_and_file_answer(self):
        app = A.assemble(load_example("document_report_export.json"))
        dsl = A.dump_yaml(app)
        self.assertEqual(
            node_types(app),
            ["start", "document-extractor", "llm", "code", "answer"],
        )
        self.assertTrue(app["workflow"]["features"]["file_upload"]["enabled"])
        self.assertIn(".markdown_link#}}", dsl)
        code_nodes = [n for n in graph_parts(app)[0] if n["data"]["title"] == "代码生成文件"]
        self.assertEqual(len(code_nodes), 1)
        compile(code_nodes[0]["data"]["code"], "<file-export-code>", "exec")

    def test_http_example_declares_env_vars_and_avoids_secret_values(self):
        app = A.assemble(load_example("http_ticket_query.json"))
        dsl = A.dump_yaml(app)
        envs = {env["name"]: env for env in app["workflow"]["environment_variables"]}
        self.assertEqual(node_types(app), ["start", "http-request", "llm", "answer"])
        self.assertEqual(envs["API_BASE_URL"]["value_type"], "string")
        self.assertEqual(envs["API_TOKEN"]["value_type"], "secret")
        self.assertIn("{{#env.API_TOKEN#}}", dsl)
        self.assertIn("keyword={{#sys.query#}}", dsl)
        self.assertNotIn("Bearer sk-", dsl)

    def test_classifier_example_has_independent_route_answers(self):
        blueprint = load_example("classifier_office_assistant.json")
        app = A.assemble(blueprint)
        nodes, edges = graph_parts(app)
        self.assertEqual(node_types(app).count("answer"), 2)
        handles = {edge["sourceHandle"] for edge in edges if edge["source"] == "node_classifier"}
        self.assertEqual(handles, {"policy_qa", "ticket_query"})
        validation = A.validate(app, blueprint, A.dump_yaml(app))
        self.assertTrue(any("多路由结构检查通过" in item for item in validation["checks"]))

    def test_condition_example_has_else_branch_and_none_hardened_router(self):
        blueprint = load_example("condition_file_or_chat.json")
        app = A.assemble(blueprint)
        nodes, edges = graph_parts(app)
        self.assertIn("if-else", node_types(app))
        ifelse = [node for node in nodes if node["data"]["type"] == "if-else"][0]
        self.assertEqual({case["case_id"] for case in ifelse["data"]["cases"]}, {"doc"})
        handles = {edge["sourceHandle"] for edge in edges if edge["source"] == ifelse["id"]}
        self.assertEqual(handles, {"doc", "false"})
        router = [node for node in nodes if node["id"] == "node_router"][0]
        self.assertIn("str(file_text or '').strip()", router["data"]["code"])

    def test_vision_example_enables_upload_without_document_extractor(self):
        app = A.assemble(load_example("vision_receipt_ocr.json"))
        nodes, _ = graph_parts(app)
        self.assertEqual(node_types(app), ["start", "llm", "answer"])
        self.assertTrue(app["workflow"]["features"]["file_upload"]["enabled"])
        llm = [node for node in nodes if node["data"]["type"] == "llm"][0]
        self.assertTrue(llm["data"]["vision"]["enabled"])
        self.assertEqual(llm["data"]["vision"]["configs"]["variable_selector"], ["node_start", "upload_file"])

    def test_cli_builds_importable_yaml_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "agent.yml"
            result = subprocess.run(
                [
                    sys.executable,
                    str(AGENT_DIR / "scripts" / "build_agent.py"),
                    str(EXAMPLES_DIR / "knowledge_qa.json"),
                    str(out_path),
                ],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=True,
            )
            text = out_path.read_text(encoding="utf-8")
            self.assertIn("version: \"0.3.0\"", text)
            self.assertIn("knowledge-retrieval", text)
            self.assertIn("节点 4、连线 3", result.stdout)


if __name__ == "__main__":
    unittest.main()
