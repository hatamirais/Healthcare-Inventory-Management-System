# [Rule Gap] Resolve Redis/Celery usage against the stated no-broker/no-Redis constraint

**Labels:** `security`, `architecture`, `ops`, `tech-debt`

## Summary

The repository still includes Redis and Celery related runtime and documentation despite a stated no-broker/no-Redis constraint.

## Evidence

- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/requirements.txt:1-34`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/docker-compose.yml:15-26`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/docs/infrastructure_plan.md:17-23`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/docs/infrastructure_plan.md:68-71`

## Problem

The current dependency and runtime baseline conflicts with the stated architecture constraint.

## Impact

This adds unnecessary attack surface and creates operational and documentation drift.

## Expected Changes

- Either remove unused Redis and Celery dependencies and docs,
- or explicitly document and justify the exception.

## Acceptance Criteria

- [ ] Redis and Celery usage is either removed or formally justified.
- [ ] Runtime, dependency, and docs are aligned with the intended architecture.
- [ ] Any remaining broker dependency is clearly documented with rationale.
- [ ] Obsolete infrastructure references are cleaned up.
