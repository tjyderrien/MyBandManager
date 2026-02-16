# Email2Deadline Thunderbird Add-on

This add-on extracts deadline dates from selected emails and generates an `.ics` calendar file you can import into Google Calendar.

## Features
- Works on currently selected emails in Thunderbird.
- Detects common deadline patterns such as:
  - `deadline: 2026-03-30`
  - `due by 14/04/2026 17:00`
  - `submit before March 22, 2026 at 09:30`
- Produces an iCalendar (`.ics`) export file.
- Exported file can be imported into Google Calendar (Google Agenda).

## Install (Temporary Add-on for development)
1. Open Thunderbird.
2. Go to **Add-ons and Themes**.
3. Click the gear icon → **Debug Add-ons**.
4. Choose **Load Temporary Add-on...**.
5. Select `manifest.json` from this folder.

## Usage
1. In Thunderbird, select one or multiple email messages.
2. Click the add-on toolbar button **Export deadlines to ICS**.
3. Choose where to save the generated `.ics` file.
4. Import this `.ics` file in Google Calendar:
   - Google Calendar → Settings → Import & export → Import.

## Notes
- If no deadline-like date is detected, the add-on shows a notification.
- Timed events are exported in UTC; date-only deadlines are exported as all-day events.
