# [High] Add server-side file validation and audit logging for uploads/imports

**Labels:** `security`, `high`, `backend`, `uploads`, `audit`

## Summary

Upload and import flows accept files without sufficient server-side validation and do not provide reliable audit logging.

## Evidence

- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/receiving/admin.py:67-75`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/receiving/admin.py:111-146`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/receiving/models.py:220-230`
- `/tmp/workspace/hatamirais/dinkes-farmalkes-ims/backend/apps/core/forms.py:30-34`

## Problem

CSV import and document/logo uploads currently lack:

- MIME whitelist
- extension whitelist
- size limits
- filename/path-traversal checks

The CSV import flow also catches broad exceptions without adequate audit/security logging.

## Impact

Unexpected or oversized files may be accepted and stored. Import activity is also hard to audit.

## Expected Changes

- Add server-side validation for MIME type, extension, size, and filename safety.
- Ensure uploaders and importers are explicitly restricted.
- Add structured logging for upload and import success and failure events.

## Acceptance Criteria

- [ ] Upload and import endpoints reject unsupported MIME types and extensions.
- [ ] Upload and import endpoints enforce file size limits.
- [ ] Unsafe filenames and path traversal attempts are rejected.
- [ ] Relevant upload and import actions are audit logged.
- [ ] Broad exception handling is narrowed or logged appropriately.
- [ ] Regression tests cover allowed and rejected file cases.
