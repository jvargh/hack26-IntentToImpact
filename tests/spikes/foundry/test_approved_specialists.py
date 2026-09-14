"""Approval boundaries fail before any agent mutation."""

import copy
import unittest
from unittest.mock import AsyncMock, patch

from approved_specialists import (
    ApprovalError, ENDPOINT, NAMES, create_initial, expected_definition,
    validate_definition, validate_invocation_body, validate_readback,
)


class ApprovalTests(unittest.TestCase):
    def test_all_three_exact_definitions(self):
        for name, role in NAMES.items():
            validate_definition(name, expected_definition(role))

    def test_unapproved_name(self):
        with self.assertRaisesRegex(ApprovalError, "allowlist"):
            validate_definition("unapproved-agent", expected_definition("synthesis"))

    def test_wrong_scope(self):
        with self.assertRaisesRegex(ApprovalError, "scope"):
            validate_definition("intent-to-impact-synthesis", expected_definition("synthesis"),
                                ENDPOINT + "-wrong")

    def test_tool_bearing_definition(self):
        definition = expected_definition("synthesis")
        definition["tools"] = [{"type": "web_search"}]
        with self.assertRaisesRegex(ApprovalError, "empty tools"):
            validate_definition("intent-to-impact-synthesis", definition)

    def test_connection_or_instruction_change(self):
        for change in ({"connections": ["unapproved"]}, {"instructions": "unapproved"}):
            with self.subTest(change=change), self.assertRaisesRegex(ApprovalError, "exactly match"):
                validate_definition("intent-to-impact-synthesis",
                                    {**expected_definition("synthesis"), **change})

    def test_readback_pinned_and_tool_free(self):
        name = "intent-to-impact-assurance"
        data = {"name": name, "version": "1", "definition": expected_definition("assurance")}
        validate_readback(name, "1", data)
        for bad in ({**data, "version": "2"}, {**data, "name": "unapproved"}):
            with self.assertRaisesRegex(ApprovalError, "identity"):
                validate_readback(name, "1", bad)
        unsafe = copy.deepcopy(data)
        unsafe["definition"]["tools"] = [{"type": "mcp"}]
        with self.assertRaisesRegex(ApprovalError, "differs"):
            validate_readback(name, "1", unsafe)

    def test_invocation_requires_exact_reference(self):
        name = "intent-to-impact-synthesis"
        body = {"agent_reference": {"type": "agent_reference", "name": name, "version": "1"},
                "store": False}
        validate_invocation_body(name, "1", body)
        for change in ({"store": True}, {"tools": [{"type": "mcp"}]},
                       {"model": "unapproved"}, {"agent_reference": {"name": name}}):
            with self.subTest(change=change), self.assertRaises(ApprovalError):
                validate_invocation_body(name, "1", {**body, **change})


class CreationTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_agent_never_creates(self):
        project = AsyncMock()
        project.agents.get.return_value = {"name": "intent-to-impact-synthesis"}
        with self.assertRaisesRegex(ApprovalError, "collision"):
            await create_initial(project, "intent-to-impact-synthesis",
                                 expected_definition("synthesis"), {}, lambda: None)
        project.agents.get.assert_awaited_once()
        project.agents.create_version.assert_not_awaited()

    async def test_unapproved_or_tools_fail_before_network(self):
        for name, definition in (
            ("unapproved", expected_definition("synthesis")),
            ("intent-to-impact-synthesis", {**expected_definition("synthesis"), "tools": [{}]}),
        ):
            project = AsyncMock()
            with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
                    self.assertRaises(ApprovalError):
                await create_initial(project, name, definition, {}, lambda: None)
            project.agents.get.assert_not_awaited()
            project.agents.create_version.assert_not_awaited()

    async def test_prior_creation_attempt_cannot_repeat(self):
        project = AsyncMock()
        with self.assertRaisesRegex(ApprovalError, "already attempted"):
            await create_initial(project, "intent-to-impact-synthesis", expected_definition("synthesis"),
                                 {"creationAttempted": True}, lambda: None)
        project.agents.get.assert_not_awaited()
        project.agents.create_version.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
