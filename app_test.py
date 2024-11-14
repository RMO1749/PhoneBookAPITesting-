from fastapi.testclient import TestClient
from app import app
import json
from sqlalchemy.orm import sessionmaker
from app import engine, User

client = TestClient(app)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def load_test_data():
    with open("test_data.json", "r") as file:
        return json.load(file)

def register_user(username, password, role="READ_WRITE"):
    response = client.post(
        "/register",
        json={"username": username, "password": password, "role": role}
    )
    if response.status_code != 200:
        print(f"Failed to register user '{username}': {response.json()}")
    return {"username": username, "password": password, "role": role}

def get_access_token(username, password):
    response = client.post(
        "/token",
        data={"username": username, "password": password}
    )
    if response.status_code != 200:
        print("Failed to obtain token")
    else:
        return f"Bearer {response.json().get('access_token')}"

def add_person(headers, name, phone):
    response = client.post(
        "/PhoneBook/add",
        headers=headers,
        json={"full_name": name, "phone_number": phone}
    )
    return response
def test_phonebook_operations():
    user_credentials = register_user("testuser3", "ValidPass123", "READ_WRITE")
    token = get_access_token(user_credentials["username"], user_credentials["password"])
    headers = {"Authorization": token} if token else {}

    test_data = load_test_data()
    all_tests_passed = True  # Track if all tests pass

    # Test valid entries
    for test_case in test_data["valid_entries"]:
        response = add_person(headers, test_case["name"], test_case["phone"])
        if response.status_code != 200:
            print(f"Failed to add valid entry: {response.json()}")
            all_tests_passed = False

    # Test invalid names with valid phone numbers
    for test_case in test_data["invalid_names"]:
        response = add_person(headers, test_case["name"], test_case["phone"])
        if response.status_code != 400:
            print(f"Expected validation error for invalid name '{test_case['name']}' with valid phone '{test_case['phone']}', but got: {response.json()}")
            all_tests_passed = False

    # Test invalid phones with valid names
    for test_case in test_data["invalid_phones"]:
        response = add_person(headers, test_case["name"], test_case["phone"])
        if response.status_code != 400:
            print(f"Expected validation error for valid name '{test_case['name']}' with invalid phone '{test_case['phone']}', but got: {response.json()}")
            all_tests_passed = False

    # Test duplicate entries
    for test_case in test_data["duplicate_entries"]:
        response1 = add_person(headers, test_case["name"], test_case["phone"])
        response2 = add_person(headers, test_case["name"], test_case["phone"])
        if response2.status_code != 400:
            print(f"Expected duplicate entry error for '{test_case['name']}', but got: {response2.json()}")
            all_tests_passed = False

    # Summary of test results
    if all_tests_passed:
        print("All test cases passed successfully.")
    else:
        print("Some test cases did not pass. Check the output above for details.")

if __name__ == "__main__":
    test_phonebook_operations()
