# 1. A standalone repository, not a GitHub fork

Date: 2026-08-24

## Status

Accepted.

## Context

This project began as a GitHub fork of
[`tsunglung/UberEats`](https://github.com/tsunglung/UberEats). Six commits of local work
were added on top of upstream's eleven, five of which were pushed publicly.

Those six commits were authored with an email address belonging to the maintainer's
employer. That address grants no access to anything — it is not a credential — but it
links a personal side project to an unrelated organisation, publicly and permanently. It
should not have been there.

Removing it required rewriting commit metadata, which changes commit hashes. That much is
routine. The problem is what a rewrite does *not* achieve on GitHub: objects pushed to a
fork stay reachable by hash from every repository in the fork network, including upstream.
Force-pushing rewritten history over the old commits would have hidden them from the
branch view while leaving them retrievable by anyone who knew, or guessed, a hash. That is
the appearance of a fix rather than a fix — arguably worse than doing nothing, because it
invites the belief that the problem is solved.

Deleting the fork outright is the only mitigation GitHub offers that actually removes the
objects. But deleting a fork also destroys the "forked from" badge, which is how GitHub
expresses derivation, and derivation from an MIT-licensed project is something this
repository has an obligation — and a wish — to state clearly.

So the decision was a trade between two things that could not both be kept: the platform's
built-in attribution, and the removal of an identity that was already public.

At the time of the decision the repository had **0 stars and 0 forks**, and the exposure
was roughly three months old. The cost of deleting was therefore close to zero, and rising
with every day it was deferred.

## Decision

Delete the fork and publish the work as a standalone public repository under the same
name, carrying rewritten history.

Only the six local commits are rewritten. Upstream's eleven are left completely untouched
— same authorship, **same commit hashes** — so the divergence point `512c57f` is
byte-identical to upstream's `512c57f` and anyone can verify the base independently.

Attribution moves from the platform to the content: a credit section at the top of both
READMEs, the divergence point stated explicitly, the original `LICENSE` and copyright
notice preserved unchanged, and this record.

## Consequences

**What is gained.** The corporate identity is gone from commit and tag metadata, and the
old objects are no longer reachable through a fork network. Attribution is arguably
clearer than the badge was: a reader now learns not only that this derives from upstream,
but exactly where it diverged and what changed after.

**What is lost.** GitHub no longer shows the relationship. Upstream is not notified of
this repository's existence through the fork graph, and this repository does not appear in
upstream's fork list. Contributing changes back would mean opening a pull request from an
unrelated repository rather than a fork — more friction, though still possible.

**What remains uncertain.** Deleting a fork is the best mitigation available, not a
guarantee. There have been reports of fork-network objects surviving deletion. The
residual risk here is small given the repository's negligible exposure, but it is not
zero, and it would have been larger had the decision been deferred further.

**What this obliges.** Because the platform no longer carries the attribution, the README
credit and the `LICENSE` are now load-bearing. Neither may be dropped or diluted in future
edits.
