-- Migration: Add call_name to sales_calls
-- Description: Human-readable call title; populated from calendar
--              event title (bot calls) or LLM during analysis.
-- Created: 2026-04-21

ALTER TABLE sales_calls ADD COLUMN IF NOT EXISTS call_name TEXT;
