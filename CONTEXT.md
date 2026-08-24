# CONTEXT

The vocabulary of this repository. Terms defined here are canonical — use them in code,
commit messages, and docs, and challenge anything that contradicts them.

## Upstream and derivation

**Upstream** — [`tsunglung/UberEats`](https://github.com/tsunglung/UberEats), the
MIT-licensed project this repository derives from. Commits authored by `tsunglung` keep
their original authorship *and their original commit hashes*, so the base can be verified
against upstream independently. The **divergence point** is `512c57f`; everything at or
below it is upstream's work.

This is not a GitHub fork — see
[`docs/adr/0001-standalone-repo-not-fork.md`](docs/adr/0001-standalone-repo-not-fork.md).

## What may not enter this repository

These four categories are distinct. They are confused easily and handled differently, and
the `.githooks/pre-commit` guard is built directly on them.

**Credential** — a secret that grants access: an Uber Eats `sid` cookie *value*, an API
token, a password. None has ever been committed here and none may be. Credentials live in
Home Assistant's config-entry storage at runtime, never in source.

A *reference* to a credential is not a credential. `CONF_COOKIE`, and the header format
string `f"sid={self._cookie}"` in `data.py`, are code — they name the thing without
carrying its value. Any scan that flags them is miscalibrated, not vigilant.

**Corporate identity** — an email address, username, or hostname belonging to the
maintainer's employer. It grants no access, which is exactly why it gets overlooked: it is
not a secret, it is a *link* between this personal project and an unrelated organisation.
It must not appear in file contents or in commit and tag metadata.

**Public alias** — `kalijason`, the maintainer's own public GitHub handle. Deliberately
public. It appears in `manifest.json`, `hacs.json`, and commit authorship, and is not
sensitive.

**Infrastructure exposure** — a factual description of one specific running system: a
hostname, an SSH username, a sudo policy, a network topology. It is not a credential, so
secret scanners ignore it entirely — but it is reconnaissance material, and it arrives
disguised as documentation. Deployment runbooks describing a particular Home Assistant
instance stay out of this repository; `.gitignore` keeps `.claude/` out for this reason.

## The guard, and what it cannot do

`.githooks/pre-commit` (enabled with `git config core.hooksPath .githooks`) rejects a
commit whose author identity, committer identity, or staged content matches a denied
pattern, or whose staged content contains something shaped like a real `sid` value.

The patterns themselves live in `.githooks/deny-patterns.local`, which is **gitignored**.
That split is deliberate: this repository is public, so writing the corporate domain into
a tracked regex would republish the very identity the guard exists to keep out.

Three limits, stated so no one over-trusts it:

- `git commit --no-verify` bypasses it completely.
- `core.hooksPath` is repo-local configuration. **A fresh clone does not inherit it** —
  it must be set again by hand.
- A fresh clone has no `deny-patterns.local`, so the identity and content checks do not
  run. The hook warns loudly on stderr rather than passing silently, but a warning is not
  a block.

It guards against accident. It does not guard against intent, and it is not a substitute
for looking at what you are committing.
