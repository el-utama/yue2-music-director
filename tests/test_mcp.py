import unittest
from yue2_music_director.mcp import endpoint,configured_endpoint,Client


class MCPTests(unittest.TestCase):
    def test_loopback(self):
        self.assertEqual(endpoint('http://localhost:1234/mcp'),'http://localhost:1234/mcp')
        self.assertEqual(endpoint('http://127.0.0.1:8791/mcp'),'http://127.0.0.1:8791/mcp')
        self.assertEqual(endpoint('http://[::1]:8791/mcp'),'http://[::1]:8791/mcp')
    def test_nonlocal_rejected(self):
        for address in ('https://example.com/mcp','http://localhost@evil.com/mcp',
                        'http://192.168.1.10/mcp','http://127.0.0.1/',
                        'http://localhost/mcp?token=private'):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):endpoint(address)
    def test_no_implicit_endpoint(self):
        import unittest.mock
        with unittest.mock.patch.dict('os.environ',{},clear=True):
            with self.assertRaises(ValueError):configured_endpoint(None)


if __name__=='__main__':unittest.main()
