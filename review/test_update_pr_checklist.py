import copy
import unittest
from update_pr_checklist import checked_body, ITEM

class ChecklistTests(unittest.TestCase):
    def setUp(self):
        self.pr = {"number": 123, "state": "open", "head": {"ref": "auto-update/pkg-2.0",
                   "sha": "a"*40, "repo": {"full_name": "alice/nixpkgs"}},
                   "base": {"sha": "b"*40}, "body": "Human text\r\n"+ITEM+"\r\n- [ ] Other\r\n"}
        self.reviewed = copy.deepcopy(self.pr)
        self.inputs = {"pr": "123", "aarch64-darwin": "yes_sandbox_relaxed"}
        self.reports = [{"head": "a"*40, "base": "b"*40, "system": "aarch64-darwin",
                         "result": {"failed": [], "still_failing": []}}]
    def render(self):
        return checked_body(self.pr, self.reviewed, self.reports, self.inputs)
    def test_only_review_item_changes_and_repeat_is_noop(self):
        result = self.render()
        self.assertEqual(result, self.pr["body"].replace(ITEM, ITEM.replace("[ ]", "[x]")))
        self.pr["body"] = result
        self.assertIsNone(self.render())
    def test_failed_and_still_failing_results_do_not_check(self):
        for field in ("failed", "still_failing"):
            self.reports[0]["result"][field] = ["pkg"]
            self.assertIsNone(self.render())
            self.reports[0]["result"][field] = []
    def test_missing_empty_duplicate_and_wrong_system_reports_fail(self):
        for reports in ([], self.reports*2, [dict(self.reports[0], system="x86_64-linux")]):
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                checked_body(self.pr, self.reviewed, reports, self.inputs)
    def test_changed_pr_head_and_report_commits_fail(self):
        self.pr["head"]["sha"] = "c"*40
        with self.assertRaises(ValueError): self.render()
        self.pr = copy.deepcopy(self.reviewed)
        for field in ("head", "base"):
            self.reports[0][field] = "c"*40
            with self.assertRaises(ValueError): self.render()
            self.reports[0][field] = self.reviewed[field]["sha"]
    def test_missing_failure_fields_fail(self):
        self.reports[0]["result"] = {}
        with self.assertRaises(ValueError): self.render()
    def test_missing_or_duplicate_checkbox_fails(self):
        for body in ("Human text", ITEM+"\n"+ITEM):
            self.pr["body"] = body
            with self.assertRaises(ValueError): self.render()
    def test_non_updater_pr_unchanged(self):
        self.reviewed["head"]["ref"] = "manual-update"
        self.assertIsNone(self.render())

if __name__ == "__main__":
    unittest.main()
