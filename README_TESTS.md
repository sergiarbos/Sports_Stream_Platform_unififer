# Testing Guide for Sports Stream Platform

This document outlines the testing infrastructure and the specific unit tests implemented for the Sports Stream Platform, focusing primarily on the `schedule` application.

## Overview

The test suite ensures the reliability of the core business logic, specifically around event visibility, status categorization, and timezone-aware date filtering.

To run the tests locally, use the following command from the root directory:
```bash
python manage.py test schedule
```

To run the tests with coverage (requires `coverage` package):
```bash
coverage run manage.py test schedule
coverage report -m
```

## Test Suites

The tests are located in `schedule/tests.py` and cover several crucial aspects of the platform:

### 1. `StatusLabelTest`
Validates the `status_label` property of the `Event` model.
* **Live Events**: Ensures events with `STATUS_LIVE` return the `"LIVE"` label.
* **Finished Events**: Ensures events with `STATUS_FINISHED` return the `"ON DEMAND"` label.
* **Scheduled Events**: Ensures upcoming events with `STATUS_SCHEDULED` return the `"UPCOMING"` label.

### 2. `HomeViewTest`
Tests the behavior and context of the main dashboard (`schedule:home`).
* **HTTP 200 OK**: Verifies the home page loads successfully.
* **Upcoming Events Context**: Ensures that correctly scheduled events appear within the `upcoming_events` context variable.
* **30-Day Forward Window**: Validates the core business rule that prevents infinite scrolling. Scheduled events occurring beyond the 30-day horizon (`UPCOMING_WINDOW_DAYS`) are automatically excluded from the schedule view.

### 3. `DateTimeFilterTest` (Timezone & Date Logic)
This is the most critical suite for handling global users. It tests the helper functions (`categorize_event` and `filter_events` in `utils.py`) that categorize events into `"Live"`, `"Today"`, and `"Tomorrow"`.

#### Key Features Tested:
* **Timezone Consistency**: Prevents bugs where live events (e.g., late-night Champions League matches) are miscategorized.
* **Timezone Overrides**: Simulates different user locations using `timezone.override`. The tests explicitly check the behavior in:
  * `UTC` (Coordinated Universal Time)
  * `Europe/Madrid` (CET)
  * `America/New_York` (EST)
* **Time Mocking**: Uses `unittest.mock.patch` to freeze `timezone.now()`. This guarantees that tests remain deterministic and will not fail regardless of the local machine's configuration or the time of day the test suite is executed.

---
*Note: All tests have been designed to achieve 100% coverage on the targeted date/time utility functions.*
