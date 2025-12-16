# ===================================================================
# ENHANCED RACE CONDITION TESTS (WITH PARENT-LEVEL VERSIONING)
# ===================================================================

# Setup: Create plan for race condition testing
POST {{host}}/api/travel-plans
Content-Type: application/json
{
  "title": "Race Condition Test Plan",
  "description": "Testing concurrent operations",
  "budget": 1000.00
}

HTTP 201
[Captures]
race_plan_id: jsonpath "$.id"
initial_version: jsonpath "$.version"

# Strategy 1: Rapid Sequential Updates (simulates race condition)
# Update 1: Should succeed
PUT {{host}}/api/travel-plans/{{race_plan_id}}
Content-Type: application/json
{
  "title": "First Update",
  "budget": 1100.00,
  "version": {{initial_version}}
}

HTTP 200
[Captures]
updated_version_1: jsonpath "$.version"

[Asserts]
jsonpath "$.version" == 2
jsonpath "$.title" == "First Update"

# Update 2: Using old version (should fail with 409)
PUT {{host}}/api/travel-plans/{{race_plan_id}}
Content-Type: application/Json
{
  "title": "Second Update (Should Fail)",
  "budget": 1200.00,
  "version": {{initial_version}}
}

HTTP 409
[Asserts]
jsonpath "$.error" contains "Conflict"
jsonpath "$.current_version" == 2

# Strategy 2: Location operations with parent versioning
# Get current plan version before adding locations
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Captures]
current_version: jsonpath "$.version"

# Add Location A with current version
POST {{host}}/api/travel-plans/{{race_plan_id}}/locations
Content-Type: application/json
{
  "name": "Location A",
  "budget": 100.00,
  "plan_version": {{current_version}}
}

HTTP 201
[Captures]
location_a_id: jsonpath "$.id"
location_a_order: jsonpath "$.visit_order"

# Get updated version after Location A
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Captures]
version_after_a: jsonpath "$.version"

# Add Location B with OLD version (should fail)
POST {{host}}/api/travel-plans/{{race_plan_id}}/locations
Content-Type: application/json
{
  "name": "Location B FAIL",
  "budget": 150.00,
  "plan_version": {{current_version}}
}

HTTP 409
[Asserts]
jsonpath "$.error" contains "Conflict"

# Add Location B with CORRECT version (should succeed)
POST {{host}}/api/travel-plans/{{race_plan_id}}/locations
Content-Type: application/json
{
  "name": "Location B",
  "budget": 150.00,
  "plan_version": {{version_after_a}}
}

HTTP 201
[Captures]
location_b_id: jsonpath "$.id"
location_b_order: jsonpath "$.visit_order"

# Get updated version after Location B
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Captures]
version_after_b: jsonpath "$.version"

# Add Location C with correct version
POST {{host}}/api/travel-plans/{{race_plan_id}}/locations
Content-Type: application/json
{
  "name": "Location C",
  "budget": 200.00,
  "plan_version": {{version_after_b}}
}

HTTP 201
[Captures]
location_c_id: jsonpath "$.id"
location_c_order: jsonpath "$.visit_order"

# Verify proper ordering
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Asserts]
jsonpath "$.locations" count == 3
jsonpath "$.locations[0].name" == "Location A"
jsonpath "$.locations[0].visit_order" == 1
jsonpath "$.locations[1].name" == "Location B"
jsonpath "$.locations[1].visit_order" == 2
jsonpath "$.locations[2].name" == "Location C"
jsonpath "$.locations[2].visit_order" == 3

# Strategy 3: Concurrent location updates
# Get current version
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Captures]
version_before_update: jsonpath "$.version"

# Update Location A with correct version
PUT {{host}}/api/locations/{{location_a_id}}
Content-Type: application/json
{
  "budget": 125.00,
  "plan_version": {{version_before_update}}
}

HTTP 200

# Try to update Location B with OLD version (should fail)
PUT {{host}}/api/locations/{{location_b_id}}
Content-Type: application/json
{
  "notes": "This should fail",
  "plan_version": {{version_before_update}}
}

HTTP 409
[Asserts]
jsonpath "$.error" contains "Conflict"

# Strategy 4: Delete with version check
# Get current version
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Captures]
version_before_delete: jsonpath "$.version"

# Try to delete with old version (should fail)
DELETE {{host}}/api/locations/{{location_c_id}}?plan_version={{version_before_update}}

HTTP 409
[Asserts]
jsonpath "$.error" contains "Conflict"

# Delete with correct version (should succeed)
DELETE {{host}}/api/locations/{{location_c_id}}?plan_version={{version_before_delete}}

HTTP 204

# Verify location deleted
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 200
[Asserts]
jsonpath "$.locations" count == 2

# Strategy 5: Cascade Delete Race Condition Test
DELETE {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 204

# Verify complete deletion (locations should be gone too)
GET {{host}}/api/travel-plans/{{race_plan_id}}

HTTP 404