/* Migration: 019_alarm_snooze_week.sql */
/* Adds snoozed_until column to track precise snooze timestamps for future UI use */

ALTER TABLE alerts ADD COLUMN snoozed_until DATETIME;
ALTER TABLE alerts ADD COLUMN snooze_count INTEGER DEFAULT 0;
