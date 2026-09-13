import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('validator', ROOT/'scripts/validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class PackagingTests(unittest.TestCase):
    def test_each_skill_works_as_the_only_installed_skill(self):
        for source in sorted((ROOT/'skills').iterdir()):
            if not source.is_dir():
                continue
            with self.subTest(skill=source.name), tempfile.TemporaryDirectory() as folder:
                installed = Path(folder)/source.name
                shutil.copytree(source, installed)
                failures = []
                validator.check_skill(str(installed), failures)
                self.assertEqual(failures, [])
                helper = installed/'scripts/latency_budget.py'
                if helper.exists():
                    result = subprocess.run([sys.executable, str(helper), '--shape','cascade','--eot','700',
                                             '--ttft','620','--ttfb','240','--e2e','1560'], cwd=folder, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('620', result.stdout)

    def test_nested_references_and_escapes_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            installed = Path(folder)/'voice-prompting'
            shutil.copytree(ROOT/'skills/voice-prompting', installed)
            (installed/'references/broken.md').write_text('[missing](missing.md)\n[escape](../../outside.md)')
            failures = []
            validator.check_skill(str(installed), failures)
            self.assertTrue(any('does not resolve' in f for f in failures))
            self.assertTrue(any('escapes' in f for f in failures))

    def test_duplicate_metadata_is_rejected(self):
        with self.assertRaises(validator.Failure):
            validator.parse_frontmatter('---\nname: first\nname: second\n---\n', 'test')
