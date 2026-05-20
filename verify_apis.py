import sys
import requests

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /health...")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    return True

def test_validation_error():
    print("\nTesting validation error response shape...")
    try:
        # POST with missing keys to /jobs/explain-match
        r = requests.post(f"{BASE_URL}/jobs/explain-match", json={})
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        assert r.status_code == 422
        res = r.json()
        assert res.get("error") is True
        assert "message" in res
        assert res.get("code") == 422
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    return True

def test_404_error():
    print("\nTesting 404 error response shape...")
    try:
        r = requests.get(f"{BASE_URL}/invalid-route-xyz")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        assert r.status_code == 404
        res = r.json()
        assert res.get("error") is True
        assert "message" in res
        assert res.get("code") == 404
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    return True

def test_profile_not_found():
    print("\nTesting 404 profile not found error response shape...")
    try:
        r = requests.get(f"{BASE_URL}/profile/999999")
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        assert r.status_code == 404
        res = r.json()
        assert res.get("error") is True
        assert "message" in res
        assert res.get("code") == 404
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    return True

if __name__ == "__main__":
    tests = [test_health, test_validation_error, test_404_error, test_profile_not_found]
    success = True
    for t in tests:
        if not t():
            success = False
    if success:
        print("\nALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED!")
        sys.exit(1)
