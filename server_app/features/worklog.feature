Feature: Work session logging
  As an authenticated employee
  I want to record work session events (START, PAUSE, STOP)
  So that my working hours are accurately tracked

  Background:
    Given the employee with personnel number "TAB-200" and password "pass5678" exists
    And the client is authenticated as "TAB-200" with password "pass5678"

  Scenario: Employee starts a work session
    When the employee sends a worklog event "START" with current timestamp
    Then the response status should be 201
    And a WorkLog entry with event "START" should exist for employee "TAB-200"

  Scenario: Employee can retrieve only their own logs
    Given another employee with personnel number "TAB-201" and password "pass0000" exists
    And employee "TAB-201" has an existing worklog entry
    When the employee "TAB-200" requests the worklog list
    Then the response status should be 200
    And the returned list should contain exactly 0 entries

  Scenario: Unauthenticated request to worklog is rejected
    When an unauthenticated client requests the worklog list
    Then the response status should be 401
