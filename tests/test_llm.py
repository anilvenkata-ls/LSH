from __future__ import annotations

from rcm_change_platform.agents import MetadataDiscoveryAgent, RequestIntakeAgent
from rcm_change_platform.context import ChangeContext, RunOptions
from rcm_change_platform.llm import AnthropicLLM, NullLLM, OpenAILLM, complete_json, default_client


class FakeLLM:
    name = "fake"

    def __init__(self, reply: str | None):
        self.reply = reply
        self.prompts: list[str] = []

    def available(self) -> bool:
        return True

    def complete(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str | None:
        self.prompts.append(prompt)
        return self.reply


def test_default_client_is_deterministic_without_keys():
    client = default_client({})
    assert isinstance(client, NullLLM)
    assert not client.available()
    assert client.complete("anything") is None


def test_default_client_selects_the_configured_provider():
    assert isinstance(default_client({"ANTHROPIC_API_KEY": "k"}), AnthropicLLM)
    assert isinstance(default_client({"OPENAI_API_KEY": "k"}), OpenAILLM)
    assert isinstance(default_client({"ANTHROPIC_API_KEY": "k", "RCM_LLM_PROVIDER": "none"}), NullLLM)
    both = default_client({"ANTHROPIC_API_KEY": "k", "OPENAI_API_KEY": "k", "RCM_LLM_PROVIDER": "openai"})
    assert isinstance(both, OpenAILLM)


def test_provider_payloads_are_shaped_per_api():
    anthropic = AnthropicLLM("key", "claude-sonnet-4-5")._payload("hello", "sys", 32)
    assert anthropic["system"] == "sys" and anthropic["messages"][0]["content"] == "hello"
    openai = OpenAILLM("key", "gpt-4.1-mini")._payload("hello", "sys", 32)
    assert [message["role"] for message in openai["messages"]] == ["system", "user"]


def test_complete_json_extracts_an_embedded_object():
    payload = complete_json(FakeLLM('Sure!\n{"report": "AR Aging Report"}\nHope that helps'), "prompt")
    assert payload == {"report": "AR Aging Report"}
    assert complete_json(FakeLLM("no json here"), "prompt") is None
    assert complete_json(FakeLLM(None), "prompt") is None
    assert complete_json(NullLLM(), "prompt") is None


def test_intake_uses_the_llm_when_it_returns_a_valid_extraction(tmp_path):
    llm = FakeLLM(
        '{"report": "AR Aging Report", "requested_column": "patient financial class", '
        '"business_reason": "payer mix review", "change_type": "add_column"}'
    )
    context = ChangeContext.create(
        "we could really use financial class visibility somewhere in AR",
        options=RunOptions(output_dir=tmp_path),
        llm=llm,
    )
    RequestIntakeAgent().run(context)
    assert context.request.parser == "llm:fake"
    assert context.request.report == "AR Aging Report"
    assert context.request.business_reason == "payer mix review"
    assert "Known reports" in llm.prompts[0]


def test_intake_falls_back_when_the_llm_reply_is_unusable(tmp_path):
    context = ChangeContext.create(
        "Add Patient Financial Class to the AR Aging Report",
        options=RunOptions(output_dir=tmp_path),
        llm=FakeLLM('{"report": ""}'),
    )
    RequestIntakeAgent().run(context)
    assert context.request.parser == "rule_based"
    assert context.request.report == "AR Aging Report"


def test_metadata_uses_the_llm_to_break_a_tie(tmp_path, make_repo):
    def drop_dictionary(payload):
        payload["data_dictionary"]["terms"] = []

    llm = FakeLLM('{"table": "rcm.dim_patient", "column": "patient_financial_class"}')
    context = ChangeContext.create(
        "Add Patient Financial Class to the AR Aging Report",
        repo=make_repo(drop_dictionary),
        options=RunOptions(output_dir=tmp_path),
        llm=llm,
    )
    RequestIntakeAgent().run(context)
    MetadataDiscoveryAgent().run(context)
    assert context.metadata.column.physical_column == "patient_financial_class"
