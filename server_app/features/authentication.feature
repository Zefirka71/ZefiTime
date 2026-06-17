Feature: Employee authentication via personnel number
  As an employee of the organisation
  I want to log in using my personnel number and password
  So that I can access my personal time tracking data

  Background:
    Given the employee with personnel number "TAB-100" and password "pass1234" exists

  Scenario: Successful authentication returns user profile
    When the client requests GET "/api/users/me/" with credentials "TAB-100" and "pass1234"
    Then the response status should be 200
    And the response JSON should contain key "personnel_number"

  Scenario: Wrong password returns 401
    When the client requests GET "/api/users/me/" with credentials "TAB-100" and "wrongpass"
    Then the response status should be 401

  Scenario: Unknown personnel number returns 401
    When the client requests GET "/api/users/me/" with credentials "TAB-999" and "pass1234"
    Then the response status should be 401

  Scenario: Request without credentials returns 401
    When the client requests GET "/api/users/me/" without credentials
    Then the response status should be 401
