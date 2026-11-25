import copy
import io
import json
import socket
import sqlite3
import unittest
import urllib.error
from unittest.mock import patch

from business import check_url, fetch_feed, init_business, read_workspace, save_workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        init_business(self.conn)
        self.state = read_workspace(self.conn)['state']

    def tearDown(self):
        self.conn.close()

    def test_roundtrip_and_stale_writer_do_not_overwrite(self):
        self.state['tasks'].append({'id':'test','title':'Synthetic task','done':False,'due':''})
        self.assertEqual(save_workspace(self.conn, 0, self.state), 1)
        stale = copy.deepcopy(self.state)
        stale['tasks'] = []
        with self.assertRaisesRegex(ValueError, '其他页面'):
            save_workspace(self.conn, 0, stale)
        self.assertEqual(read_workspace(self.conn)['state'], self.state)

    def test_invalid_refund_and_duplicate_lines_rejected(self):
        row = dict(id='A-1', orderId='A',date='2026-11-25',product='Synthetic',color='粉色',status='已支付',qty=1,refundQty=2,paid=10000,refund=0)
        self.state['orders'] = [row]
        with self.assertRaises(ValueError):
            save_workspace(self.conn, 0, self.state)
        row['refundQty'] = 0
        row['refund'] = 10001
        with self.assertRaises(ValueError):
            save_workspace(self.conn, 0, self.state)
        row['refund'] = 0
        self.state['orders'].append(copy.deepcopy(row))
        with self.assertRaisesRegex(ValueError, '重复'):
            save_workspace(self.conn, 0, self.state)
        self.assertEqual(read_workspace(self.conn)['version'], 0)

    def test_schema_and_integer_amounts_required(self):
        with self.assertRaises(ValueError):
            save_workspace(self.conn, 0, {})
        self.state['orders'] = [dict(id='A',orderId='A',date='2026-11-25',product='Synthetic',color='粉色',status='已支付',qty=1,refundQty=0,paid=1.5,refund=0)]
        with self.assertRaises(ValueError):
            save_workspace(self.conn, 0, self.state)


PUBLIC_DNS = [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]


class FeedTests(unittest.TestCase):
    @patch('business.socket.getaddrinfo', return_value=PUBLIC_DNS)
    @patch('business.urllib.request.build_opener')
    def test_markdown_url_cleanup_and_rss(self, opener, dns):
        opener.return_value.open.return_value = io.BytesIO(b'<rss><channel><item><title>Test</title><link>https://example.com/story</link><pubDate>Wed, 25 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>')
        result = fetch_feed(' https://example.com/feed/` ')
        self.assertEqual(result[0]['title'], 'Test')
        self.assertEqual(opener.return_value.open.call_args.args[0].full_url, 'https://example.com/feed/')

    @patch('business.socket.getaddrinfo', return_value=PUBLIC_DNS)
    @patch('business.urllib.request.build_opener')
    def test_atom_and_unsafe_links(self, opener, dns):
        opener.return_value.open.return_value = io.BytesIO(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title><link href="https://example.com/a"/><updated>2026-11-25</updated></entry><entry><title>Unsafe</title><link href="javascript:alert(1)"/></entry></feed>')
        self.assertEqual(len(fetch_feed('https://example.com/feed')), 1)

    @patch('business.socket.getaddrinfo', return_value=PUBLIC_DNS)
    @patch('business.urllib.request.build_opener')
    def test_404_and_xml_entities(self, opener, dns):
        opener.return_value.open.side_effect = urllib.error.HTTPError('https://example.com/feed',404,'Not Found',{},None)
        with self.assertRaisesRegex(ValueError,'404'):
            fetch_feed('https://example.com/feed')
        opener.return_value.open.side_effect = None
        opener.return_value.open.return_value = io.BytesIO(b'<!DOCTYPE rss [<!ENTITY x "test">]><rss/>')
        with self.assertRaisesRegex(ValueError, 'XML'):
            fetch_feed('https://example.com/feed')

    def test_private_and_non_https_sources_rejected(self):
        with self.assertRaises(ValueError):
            check_url('http://example.com/feed')
        with patch('business.socket.getaddrinfo', return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):
                check_url('https://example.com/feed')


if __name__ == '__main__':
    unittest.main()
