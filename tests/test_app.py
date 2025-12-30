"""
Tests for the Mergington High School Activities API
"""

import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        "Basketball": {
            "description": "Team sport focusing on basketball skills and competitive games",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu"]
        },
        "Soccer": {
            "description": "Outdoor soccer league and friendly matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 22,
            "participants": ["alex@mergington.edu", "nina@mergington.edu"]
        },
        "Art Club": {
            "description": "Explore painting, drawing, and mixed media techniques",
            "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 18,
            "participants": ["grace@mergington.edu"]
        },
    }
    
    # Clear and reset activities
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Reset again after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Basketball" in data
        assert "Soccer" in data
        assert "Art Club" in data
    
    def test_get_activities_contains_activity_details(self, client):
        """Test that activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        basketball = data["Basketball"]
        
        assert "description" in basketball
        assert "schedule" in basketball
        assert "max_participants" in basketball
        assert "participants" in basketball
    
    def test_get_activities_shows_participants(self, client):
        """Test that participant list is included"""
        response = client.get("/activities")
        data = response.json()
        
        assert "james@mergington.edu" in data["Basketball"]["participants"]
        assert "alex@mergington.edu" in data["Soccer"]["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball/signup?email=newemail@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newemail@mergington.edu" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant"""
        email = "newemail@mergington.edu"
        
        # Signup
        client.post(f"/activities/Basketball/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball"]["participants"]
    
    def test_signup_for_nonexistent_activity_returns_404(self, client):
        """Test signup for activity that doesn't exist"""
        response = client.post(
            "/activities/NonexistentActivity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_participant_returns_400(self, client):
        """Test that duplicate signup is rejected"""
        response = client.post(
            "/activities/Basketball/signup?email=james@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_multiple_participants(self, client):
        """Test signing up multiple different participants"""
        emails = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/Art Club/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all were added
        response = client.get("/activities")
        data = response.json()
        for email in emails:
            assert email in data["Art Club"]["participants"]


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        response = client.post(
            "/activities/Basketball/unregister?email=james@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "james@mergington.edu"
        
        # Unregister
        client.post(f"/activities/Basketball/unregister?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Basketball"]["participants"]
    
    def test_unregister_from_nonexistent_activity_returns_404(self, client):
        """Test unregister from activity that doesn't exist"""
        response = client.post(
            "/activities/NonexistentActivity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_non_participant_returns_400(self, client):
        """Test that unregistering a non-participant is rejected"""
        response = client.post(
            "/activities/Basketball/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_then_signup_again(self, client):
        """Test that a user can sign up again after unregistering"""
        email = "james@mergington.edu"
        
        # Unregister
        response = client.post(f"/activities/Basketball/unregister?email={email}")
        assert response.status_code == 200
        
        # Sign up again
        response = client.post(f"/activities/Basketball/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant is back
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball"]["participants"]


class TestIntegration:
    """Integration tests combining multiple endpoints"""
    
    def test_signup_and_unregister_flow(self, client):
        """Test complete signup and unregister flow"""
        email = "integration@mergington.edu"
        activity = "Soccer"
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Check count increased
        response = client.get("/activities")
        new_count = len(response.json()[activity]["participants"])
        assert new_count == initial_count + 1
        
        # Unregister
        response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Check count decreased
        response = client.get("/activities")
        final_count = len(response.json()[activity]["participants"])
        assert final_count == initial_count
    
    def test_multiple_activities_independent(self, client):
        """Test that signup to one activity doesn't affect others"""
        email = "test@mergington.edu"
        
        # Sign up to two different activities
        client.post(f"/activities/Basketball/signup?email={email}")
        client.post(f"/activities/Soccer/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        
        # Verify in both
        assert email in data["Basketball"]["participants"]
        assert email in data["Soccer"]["participants"]
        assert email not in data["Art Club"]["participants"]
