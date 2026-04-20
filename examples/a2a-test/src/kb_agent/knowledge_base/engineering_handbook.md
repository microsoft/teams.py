# Engineering Handbook

This handbook covers how engineering teams at Northwind Co. ship software. It is a living document;
propose changes via PR to the `engineering-docs` repo.

## Code Review

All production code requires review by at least one other engineer before merge. Reviews focus on
correctness, readability, and whether tests cover the change. Reviewers should respond within one
business day; if blocked, the author escalates in the team channel.

## Testing

- **Unit tests:** required for any logic with branching behavior. Aim for clear test names and one
  assertion per test where practical.
- **Integration tests:** required for any feature that crosses a service boundary.
- **Manual verification:** document the manual test steps in the PR description for UI changes.

## Deploys

Production deploys happen twice a day: 10:00 AM and 3:00 PM Pacific. Deploys are blocked on
Fridays after 12:00 PM, during company-wide freezes, and whenever the on-call flags an active
incident. Emergency hotfixes require manager approval and a follow-up postmortem.

## On-call

Engineers rotate on-call in one-week shifts. On-call is compensated at a rate of $500/week plus
$100 per after-hours page. The on-call runbook is in the `oncall` repo; review it before your shift.

## Incidents

Any customer-visible outage is a P1 incident and requires an immediate #incident channel, a
designated incident commander, and a postmortem within 5 business days of resolution.
