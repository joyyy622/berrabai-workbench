import runpy
import tempfile
import unittest
from pathlib import Path


class PublicBuildTests(unittest.TestCase):
    def test_public_output_contains_only_client_assets_and_no_runtime_data(self):
        root = Path(__file__).resolve().parents[1]
        module = runpy.run_path(str(root / 'scripts/build-public-demo.py'))
        build = module['build']
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'public-demo'
            build.__globals__['OUTPUT'] = output
            build()
            self.assertEqual({p.name for p in output.iterdir()}, {'index.html','owner.js','owner.css','catalog-data.js','_headers'})
            self.assertIn('window.BERRABAI_PUBLIC_DEMO=true', (output/'index.html').read_text())
            self.assertNotIn('BERRABAI_PUBLIC_DEMO=true', (root/'dist/index.html').read_text())
            self.assertIn("connect-src 'none'", (output/'_headers').read_text())
            # Rebuilding replaces stale output, including accidentally placed runtime files.
            (output/'private.sqlite3').write_text('must not publish')
            build()
            self.assertFalse((output/'private.sqlite3').exists())
