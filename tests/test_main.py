def test_root(client):
    """Test the health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "FastAPI Image Upload Server"}

def test_register_user(client):
    """Test successful user registration"""
    response = client.post(
        "/register",
        json={"username": "testuser", "password": "securepassword"}
    )
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}

def test_register_duplicate_user(client):
    """Test that duplicate usernames are rejected"""
    client.post("/register", json={"username": "testuser", "password": "securepassword"})
    
    response = client.post("/register", json={"username": "testuser", "password": "newpassword"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}

def test_login_success(client):
    """Test login and JWT token generation"""
    client.post("/register", json={"username": "testuser", "password": "securepassword"})
    
    # Note: OAuth2PasswordRequestForm expects form data (data=...), not JSON
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "securepassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
