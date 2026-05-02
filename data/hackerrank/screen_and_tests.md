# HackerRank Screen — Support Articles

## Extend Test Duration for Candidates

HackerRank for Work allows you to extend the test duration for candidates in two ways:
- Add Time Accommodation (before or after invites, before candidate starts)
- Add Extra Time (during or after the test)

### Add Time Accommodation

The Add Time Accommodation feature allows you to extend test duration either before or after sending candidate invites, as long as the candidate has not yet started the test.

Prerequisites:
- You must have a published test in your HackerRank account.
- You must be the test owner or have editor access.

#### Adding time accommodation before sending invites
1. Log in to your HackerRank for Work account.
2. Go to the Tests tab.
3. Select the test you want to modify.
4. Click Invite.
5. Select Time Accommodation dropdown from the upper-right corner.
6. Choose 25%, 50%, 75%, 100% or Custom percentage (in multiples of five).
7. Select Save.
The system updates the invite template with the modified duration.

#### Adding time accommodation after sending invites
1. Log in to your HackerRank for Work account.
2. Go to the Tests tab.
3. Select the test you want to modify.
4. Go to the Candidates tab.
5. Select the checkbox next to the candidate(s).
6. Click More > Add Time Accommodation.
7. Enter the accommodation percentage in multiples of five.
8. Click Save.

After you apply time accommodation, the updated duration appears in the test invite email and on the test landing page before the candidate starts the test.

### Add Extra Time

The test timer runs continuously and does not pause for technical issues. If a candidate loses time due to connectivity or other issues, you can add extra time during the test, after submission, or after test ends.

1. Log in to your HackerRank for Work account.
2. Go to the Tests tab.
3. Select the test you want to modify.
4. Go to the Candidates tab.
5. Select the checkbox next to the candidate(s).
6. Click More > Add Time.
7. Enter the time in minutes.
8. Click Confirm.

Note: A candidate who is still in a test session must refresh the page to see the updated timer. A candidate who has completed the test must log in again to view the added time.

## Managing Tests

### Test Variants
- Create variants to adapt a single test to different candidate profiles (e.g., different tech stacks like React, Angular, Vue.js).
- Variants streamline assessments by showing candidates only relevant sections and generating role-specific reports.
- A test must have at least two variants to function; you cannot delete a variant if only two exist.
- Variants without logic are hidden from candidates until logic is added.

### Test Expiration
Tests in HackerRank remain active indefinitely unless a start and end time are set. Without these, tests do not expire automatically.
To set expiration:
1. Go to the test's Settings and select the General section.
2. Update the Start date & time and End date & time fields.
3. After expiration: invited candidates cannot access the test, and the Invite button is disabled.
4. To keep the test active indefinitely, clear these fields by clicking the clear icon (X).

### Clone a Test
To clone a test, go to Tests, find the test, click the three-dot menu, and select Clone.

### Lock a Test
Locking prevents changes. Go to Tests, find the test, click the three-dot menu, and select Lock.

### Grant Test Access / Revoke Test Access
Share tests with team members. Go to the test, click Share, and add collaborators. Revoke access from the same menu.

## Invite Candidates to a Test
1. Go to the Tests tab.
2. Select the test.
3. Click Invite.
4. Enter candidate email addresses.
5. Customize the invite email if needed.
6. Click Send Invites.

### Re-invite Candidates
To re-invite a candidate:
1. Go to the Candidates tab of the test.
2. Select the candidate.
3. Click More > Reinvite.
The candidate will receive a new invitation email.

## Test Integrity
- Proctoring features: Webcam, screen recording, tab-switching detection
- Plagiarism detection compares submissions across candidates
- IP restriction: limit test access to specific IP ranges

## Compatibility Check
Before taking a test, candidates can run a compatibility check to verify:
- Browser compatibility
- Webcam access (if proctoring is enabled)
- Screen sharing capability
- Internet connectivity
- Zoom connectivity (if applicable for interview)
All criteria must pass for the candidate to proceed. If any check fails, the candidate should:
- Update their browser to the latest version
- Allow camera/microphone permissions
- Disable VPN or proxy connections
- Check firewall settings
- Contact their IT administrator for help with connectivity tools

## Test Reports
- View candidate scores, code submissions, and proctoring data in the test report
- Reports can be downloaded as PDF or CSV
- Filter candidates by score range, status, or tags

## HackerRank Safelist/Allowlist URLs
To ensure candidates can access HackerRank tests without issues, allowlist the following:
- *.hackerrank.com
- *.hrank.io
- *.hackerrank-corp.com
Contact your IT team to add these to your firewall or proxy allowlist.

## Execution Environment
HackerRank provides a sandboxed execution environment for running code. Supported languages include C, C++, Java, Python, JavaScript, Ruby, Go, Kotlin, Swift, and many more. Each language has specific version and resource limits documented.
