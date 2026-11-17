"""In-process protocol tests use explicitly labelled fixtures, not live aircraft."""
import unittest
from unittest.mock import patch
from mcp.client import Client
from mcp_server import server
from sky_client import SkyReadError
from test_sky_client import ROW


class MCPReadOnlyTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_and_structured_result(self):
        with patch('mcp_server.get_aircraft',return_value=[ROW]):
            async with Client(server,read_timeout_seconds=5,cache=None) as client:
                result = await client.list_tools()
                self.assertEqual([t.name for t in result.tools],['list_aircraft'])
                tool = result.tools[0]
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.open_world_hint)
                self.assertEqual(tool.input_schema.get('properties',{}),{})
                value = await client.call_tool('list_aircraft',{})
                self.assertFalse(value.is_error)
                self.assertEqual(value.structured_content['count'],1)
                self.assertEqual(value.structured_content['aircraft'][0]['id'],'fixture-A1')
                self.assertTrue(value.structured_content['simulation'])

    async def test_auth_error_is_not_an_empty_success(self):
        with patch('mcp_server.get_aircraft',side_effect=SkyReadError('测试权限拒绝')):
            async with Client(server,read_timeout_seconds=5,cache=None) as client:
                result = await client.call_tool('list_aircraft',{})
                self.assertTrue(result.is_error)
                self.assertIsNone(result.structured_content)
                self.assertIn('测试权限拒绝', ' '.join(p.text for p in result.content if p.type == 'text'))


if __name__ == '__main__': unittest.main()
