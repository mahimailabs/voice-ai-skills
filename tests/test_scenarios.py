"""Every skill carries behavioral scenarios, and their patterns are checked offline."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import scenarios


class ScenarioTests(unittest.TestCase):
    def test_every_skill_has_a_scenario_file(self):
        skills = {path.name for path in (ROOT / 'skills').iterdir() if path.is_dir()}
        self.assertEqual(skills, set(scenarios.load()))

    def test_scenarios_are_well_formed(self):
        seen = set()
        for skill, data in scenarios.load().items():
            self.assertEqual(data['skill'], skill)
            self.assertGreaterEqual(len(data['scenarios']), 2, f'{skill}: at least two scenarios')
            for scenario in data['scenarios']:
                with self.subTest(skill=skill, scenario=scenario.get('id')):
                    self.assertNotIn(scenario['id'], seen, 'scenario ids are unique')
                    seen.add(scenario['id'])
                    self.assertTrue(scenario['prompt'].strip())
                    for name in scenario.get('also_accept', []):
                        self.assertIn(name, scenarios.load(), 'also_accept names a real skill')
                    self.assertTrue(scenario['criteria'])
                    self.assertTrue(scenario['required'], 'at least one required pattern')
                    self.assertTrue(scenario['forbidden'], 'at least one forbidden pattern')
                    for rule in scenario['required'] + scenario['forbidden']:
                        re.compile(rule['pattern'])
                        self.assertTrue(rule['why'].strip())

    def test_examples_prove_the_patterns(self):
        for case in scenarios.cases():
            with self.subTest(scenario=case['id']):
                good = scenarios.grade(case, case['examples']['pass'])
                self.assertTrue(good['passed'], good)
                bad = scenarios.grade(case, case['examples']['fail'])
                self.assertFalse(bad['passed'], 'the failing example must trip a pattern')


if __name__ == '__main__':
    unittest.main()
