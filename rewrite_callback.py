# git-filter-repo will wrap this file's contents as the body of
# `def commit_callback(commit):` so this file should contain only
# the body (no function definition).
# Keep the initial commit unchanged — hex id recorded earlier.
# Only modify commits that are not the root (root commits have no parents).
if commit.parents:
    commit.author_name = b"Ryan Kenning"
    commit.author_email = b"rkenning2@gmail.com"
    commit.committer_name = b"Ryan Kenning"
    commit.committer_email = b"rkenning2@gmail.com"
