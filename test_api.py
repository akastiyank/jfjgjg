import os
import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Remove database if it exists before importing app to avoid conflicts
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
if os.path.exists(db_path):
    try:
        os.remove(db_path)
    except Exception:
        pass

from main import app

class EduGenieTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.headers = {}
        cls.user_token = None

    def test_01_register_user(self):
        response = self.client.post("/api/auth/register", json={
            "username": "Test Learner",
            "email": "test@edugenie.edu",
            "password": "securepassword123"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("user_id", data)
        self.assertEqual(data["username"], "Test Learner")

    def test_02_register_duplicate_email(self):
        response = self.client.post("/api/auth/register", json={
            "username": "Duplicate Learner",
            "email": "test@edugenie.edu",
            "password": "anotherpassword"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_03_login_user(self):
        response = self.client.post("/api/auth/login", json={
            "email": "test@edugenie.edu",
            "password": "securepassword123"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], "Test Learner")
        
        # Save token for next tests
        EduGenieTestCase.user_token = data["token"]
        EduGenieTestCase.headers = {
            "Authorization": f"Bearer {data['token']}",
            "x-gemini-key": "mock-api-key-value"
        }

    def test_04_unauthorized_access(self):
        # Call QnA without headers
        response = self.client.post("/api/qna", json={"question": "What is 1+1?"})
        self.assertEqual(response.status_code, 401)

    @patch("main.generate_answer")
    def test_05_qna_endpoint(self, mock_qna):
        mock_qna.return_value = "The answer is 2."
        response = self.client.post(
            "/api/qna", 
            json={"question": "What is 1+1?"},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answer"], "The answer is 2.")
        self.assertIn("query_id", data)
        mock_qna.assert_called_once_with("What is 1+1?", api_key="mock-api-key-value")

    @patch("main.explain_concept")
    def test_06_explain_endpoint(self, mock_explain):
        mock_explain.return_value = "Photosynthesis is the process of converting light to chemical energy."
        response = self.client.post(
            "/api/explain",
            json={"concept": "Photosynthesis", "use_local": False},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["explanation"], "Photosynthesis is the process of converting light to chemical energy.")
        self.assertEqual(data["model"], "Gemini 1.5 Flash")
        mock_explain.assert_called_once_with("Photosynthesis", use_local=False, api_key="mock-api-key-value")

    @patch("main.generate_quiz")
    def test_07_quiz_endpoint(self, mock_quiz):
        mock_quiz.return_value = [
            {
                "QuestionText": "What is Python?",
                "OptionA": "A snake",
                "OptionB": "A programming language",
                "OptionC": "A database",
                "OptionD": "An IDE",
                "CorrectOption": "B"
            }
        ]
        response = self.client.post(
            "/api/quiz",
            json={"topic": "Python basics", "num_questions": 1},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["questions"]), 1)
        self.assertEqual(data["questions"][0]["QuestionText"], "What is Python?")
        self.assertEqual(data["questions"][0]["CorrectOption"], "B")
        mock_quiz.assert_called_once_with("Python basics", num_questions=1, api_key="mock-api-key-value")

    @patch("main.generate_summary")
    def test_08_summary_endpoint(self, mock_summary):
        mock_summary.return_value = "This is a summary of the long text."
        response = self.client.post(
            "/api/summary",
            json={"text": "Very long text that needs summarization for studying purposes."},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"], "This is a summary of the long text.")

    @patch("main.generate_learning_path")
    def test_09_learning_path_endpoint(self, mock_path):
        mock_path.return_value = {
            "Topic": "Machine Learning",
            "Level": "Beginner",
            "RecommendedTopics": ["1. Intro to Math", "2. Simple Regression", "3. Decision Trees"]
        }
        response = self.client.post(
            "/api/learning-path",
            json={"topic": "Machine Learning", "level": "Beginner"},
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["learning_path"]["Topic"], "Machine Learning")
        self.assertEqual(data["learning_path"]["Level"], "Beginner")
        self.assertEqual(len(data["learning_path"]["RecommendedTopics"]), 3)

    def test_10_history_retrieval(self):
        response = self.client.get("/api/history", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # We did QnA, Explain, Quiz, Summary, Learning-path (5 queries total)
        self.assertEqual(len(data), 5)
        # Check types
        types = [item["QueryType"] for item in data]
        self.assertIn("qa", types)
        self.assertIn("explain", types)
        self.assertIn("quiz", types)
        self.assertIn("summarize", types)
        self.assertIn("learn", types)

if __name__ == "__main__":
    unittest.main()
