---
name: new-version
description: Release a new version (review commits and merged PRs since the last tag, recommend a semantic version bump when needed, and create an annotated release tag with a short change-focused message). Use when the user asks to release a version or invokes /new-version with or without a version.
compatibility: Requires git, gh, bash, and python3 in a git repository with tags and a GitHub remote.
---

# New Version

Use this skill only when the user explicitly wants to cut a release.

## Input

Expected input: an optional version argument such as `0.2.1` or `v0.2.1`.

If a version is provided, normalize it as:
- package version: `0.2.1`
- git tag: `v0.2.1`

If a version is provided but is ambiguous or not a simple `X.Y.Z` version, stop and ask.

If no version is provided:
- inspect the changes since the last tag first
- recommend one bump type to the user: `patch`, `minor`, or `major`
- ask the user to choose the bump type before making changes
- compute the next version from the previous tag only after the user answers

Use this recommendation rule:
- recommend `patch` for fixes, small polish, dependency or maintenance work, and behavior that stays backward compatible
- recommend `minor` for new user-visible features or additive capabilities that stay backward compatible
- recommend `major` only for breaking changes, removals, incompatible configuration changes, or behavior that would surprise existing users

When asking, be explicit about the recommendation, for example: `Recommended: minor, because this release adds a new user-visible feature and keeps compatibility.`

## Workflow

1. Verify release preconditions.
   - Run `git branch --show-current` and stop unless the result is `master`.
   - Run `git status --short --branch` and stop if the worktree is not clean.
   - Run `git fetch --tags origin`.
   - Confirm the branch tracks `origin/master` and is fully synced with it.
   - If `master` is behind upstream, run `git pull --ff-only`.
   - If the branch is still ahead, behind, or diverged after the pull attempt, stop and explain why.
2. Collect release context from the last tag.
   - Run `git describe --tags --abbrev=0` to find the previous tag.
   - Run `git tag -n` to inspect existing tag message style.
   - Run `git log --oneline --decorate <last-tag>..HEAD`.
   - Run `git log --merges --oneline <last-tag>..HEAD` to show merged PRs.
   - Run `git diff --stat <last-tag>..HEAD`.
   - Run `git diff --name-status <last-tag>..HEAD`.
   - If the merge log is not enough to understand the PRs, inspect the relevant PRs with `gh pr view <number> --json number,title,body,mergeCommit`.
3. Resolve the target version.
   - If the user already provided a valid version, use it.
   - If the user did not provide a version, recommend `patch`, `minor`, or `major` based on the collected changes and ask the user to choose one.
   - Compute the next version from the previous tag after the user chooses:
     - `patch`: increment `X.Y.Z` to `X.Y.(Z+1)`
     - `minor`: increment `X.Y.Z` to `X.(Y+1).0`
     - `major`: increment `X.Y.Z` to `(X+1).0.0`
   - Normalize the final value to package version `X.Y.Z` and tag `vX.Y.Z`.
4. Present the changes before cutting the release.
   - Summarize the main changes since the previous tag.
   - Mention the commits, merged PRs, and the main files or areas changed.
   - Stop if there are no commits since the previous tag.
5. Draft the tag message.
   - Match the short annotated-tag style already used in `git tag -n`.
   - Focus on the main user-visible changes, not the internal implementation details.
   - Prefer a concise sentence fragment such as `Add update indicator and improve OpenRouter support`.
6. Cut the release.
   - Run `bash .agents/skills/new-version/scripts/release-version.sh <version> "<tag-message>"`.
7. Verify the result.
   - Run `git status --short --branch`.
   - Run `git log --oneline --decorate -2`.
   - Run `git tag -n --list <tag>`.

## Stop conditions

- Not on `master`
- Dirty worktree
- No reachable prior tag
- No commits since the last tag
- Version already exists
- `git pull --ff-only` fails or leaves the branch not fully synced

## Notes

- Never use force pull, rebase, or amend.
- Never push unless the user explicitly asks.
- The helper script in `scripts/release-version.sh` updates `src/inkypal/__init__.py` and `pyproject.toml`, creates the release commit, and creates the annotated tag.
