# Implement the ticket

You implement one ticket in your own copy of the repository. The ticket, the requirements it implements and the acceptance criteria that verify them are in your context, pinned at the revisions this task was created from.

1. Change only what the ticket needs, within its declared paths. A change to any other file is held for the test reviewer, who must acknowledge it explicitly; a change to CI configuration, `.grindstone/` or a lockfile without its manifest waits for a person's permission.
2. Write or change tests so that each acceptance criterion with method `test` is verified, and annotate each such test with `@verifies <criterion ID>` in a comment just after the line that defines the test, for example `# @verifies AC-0101-1`. Only annotations in the committed source count: a test that prints a criterion ID claims nothing.
3. Run the tests while you work. Your runs are working notes: the check station runs the suite again on the commit Grindstone makes from your workspace, and the test reviewer judges the tests independently.
4. Do not commit, push or open a pull request. Grindstone collects your workspace as files and delivers the result.
5. When you are done, call `report` once with your implementation report: a summary of the change, the criteria you addressed, the test files you added or changed, and any notes for the reviewer.
