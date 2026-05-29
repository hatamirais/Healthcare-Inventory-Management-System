# [Medium] Add rate limiting to sensitive POST endpoints

**Labels:** `security`, `medium`, `backend`, `rate-limit`

## Summary

Sensitive POST actions outside login are not throttled.

## Evidence

- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/requirements.txt:1-34`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/config/urls.py:37-38`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/users/urls.py:7-23`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/users/views.py:377-516`

## Problem

`django-axes` protects login, but other sensitive POST flows such as bulk user actions and password reset remain unthrottled.

## Impact

These actions are easier to automate or abuse and do not meet the intended security baseline.

## Expected Changes

- Add `django-ratelimit`.
- Apply rate limiting to sensitive POST endpoints.
- Return appropriate responses when limits are exceeded.
- Add tests for throttled behavior.

## Acceptance Criteria

- [ ] Sensitive POST endpoints are rate limited.
- [ ] Login protections remain intact and unaffected.
- [ ] Rate-limit behavior is documented or configurable where needed.
- [ ] Tests cover both allowed and throttled requests.
