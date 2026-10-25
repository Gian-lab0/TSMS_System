# TSMS update: admin-only editing and sick-leave coverage

## Changes
- Schedule edit form in Admin Dashboard now changes only the assigned teacher. The backend ignores submitted changes to all other schedule fields.
- Editing is admin-only. Teachers cannot add to or delete entries from a section timetable after it has been approved. Teachers may continue submitting schedules to unapproved/draft sections.
- Sick Leave / Wellness Break requests now include the teacher's name so the matching scheduled classes can be flagged.
- A red `!` appears beside classes assigned to a teacher whose leave request is not declined and whose date range includes today.
- Admins can click a class card on the timetable to open the cover-teacher availability page for that day and time. The page excludes teachers who already have a saved class at that period or have an active leave request on the selected date.
- Database migration adds `teacher_name` to existing leave_requests tables automatically.

## Notes
- The leave form asks the user to select the teacher name. Verify the selected name matches the teacher's scheduled name.
- The active red warning reflects the current date. Future leave requests are flagged when their start date arrives.
- Availability is based on saved schedule entries and leave requests; admin should confirm any substitute assignment before editing the timetable.

## Run
Install dependencies with `pip install -r requirements.txt`, then run `python app.py`.
