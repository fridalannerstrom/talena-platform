# Sova: Talena Modern Projects as the template source

## Scope

For **new** Talena test processes, Sova templates are read exclusively from client **TALENA**, account **Talena Modern Projects**. The Sova project named **Test pictures** is intentionally excluded (case-insensitive comparison).

The setting `SOVA_TEMPLATE_ACCOUNT_NAME` defaults to `Talena Modern Projects`. The source is selected by the account's API `name`, but the actual API `code` and project `code` are stored on each new `TestProcess`. We do **not** assume or hard-code the account code.

If this account cannot be found exactly once, or lacks a code, creating or changing templates must fail clearly. There is **no fallback** to Talena Main Account.

## Existing test processes

Do **not** bulk-update `TestProcess.account_code`, `project_code`, invitation `sova_project_id`, or Sova order IDs. Existing/pending candidates and invitations retain their original Sova references, including Talena Main Account. The unfiltered API lookup remains available in `SovaClient.get_accounts_with_projects()` and is used when processing existing invitations.

ProjectMeta is keyed on `(provider, account_code, project_code)`. A Modern Projects account might not have corresponding ProjectMeta rows yet. The wizard falls back to extracting the selected assessments from Sova's project name. Review and populate metadata if names cannot be interpreted unambiguously.

## Pre-release validation

1. In the target Azure environment, with its real Sova API credentials, run:
   ```bash
   python manage.py audit_sova_template_coverage
   ```
   This is **read only** and must report exactly **31** distinct combinations, each with one project, without `Test pictures`. Investigate all missing, duplicate or unrecognized combinations before rollout.
2. In stage, open **Skapa ny testprocess** and verify that each relevant assessment combination chooses the right Modern Projects project.
3. Order a test only for an **internal test candidate**, then verify Sova response, invitation URL, webhook and result display.
4. Verify that an **older process** from Talena Main Account still displays its results and can continue its pending invitations.
5. Deploy after successful validation. No database migration or Sova project changes are needed for the account switch.

## Rollback

Revert the switch commit/PR if needed; do **not** rewrite existing process references. Any processes created while Modern Projects was active must keep those Modern Projects references. The old and new accounts must both remain accessible to Sova credentials while historical invitations can still be processed.
