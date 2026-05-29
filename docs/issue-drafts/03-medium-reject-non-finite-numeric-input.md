# [Medium] Reject non-finite numeric input before decimal comparisons

**Labels:** `security`, `medium`, `backend`, `validation`

## Summary

Several forms and model paths compare decimal values without first rejecting non-finite numeric input.

## Evidence

- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/receiving/admin.py:387-400`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/receiving/forms.py:144-195`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/receiving/forms.py:303-335`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/distribution/forms.py:254-284`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/expired/forms.py:64-76`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/recall/forms.py:74-86`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/puskesmas/forms.py:81-85`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/stock/models.py:293-297`

## Problem

Code performs decimal comparisons directly, allowing crafted `NaN` or `Infinity`-like inputs to reach comparison logic.

## Impact

This can trigger `InvalidOperation` and return 500 errors instead of user-facing validation errors.

## Expected Changes

- Centralize finite-decimal validation.
- Apply it in relevant form and model clean paths before comparisons.
- Add regression tests for non-finite inputs.

## Acceptance Criteria

- [ ] Non-finite numeric values are rejected as validation errors.
- [ ] Decimal comparisons no longer raise 500s for malformed numeric input.
- [ ] Shared validation is reused across affected forms and models where appropriate.
- [ ] Regression tests cover `NaN`, `Infinity`, and similar invalid numeric cases.
