import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.base import BaseEstimator
from sentence_transformers import SentenceTransformer


class BertModelSingleton:
    _model = None

    @staticmethod
    def get_model(name="paraphrase-MiniLM-L3-v2") -> SentenceTransformer:
        if BertModelSingleton._model is None:
            BertModelSingleton._model = SentenceTransformer(name)
        return BertModelSingleton._model

class Message:
    def __init__(self, user_id: str, text: str, timestamp: float):
        self.user_id = user_id
        self.text = text
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "text": self.text,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Message':
        return Message(data['user_id'], data['text'], data['timestamp'])


def extract_features_for_single_message(message: Message) -> np.ndarray:
    text = message.text.strip()
    timestamp = message.timestamp
    length = len(text)
    entropy = 0

    if text:
        from collections import Counter
        from math import log2
        counter = Counter(text)
        probs = [c / length for c in counter.values()]
        entropy = -sum(p * log2(p) for p in probs)

    model = BertModelSingleton.get_model()
    bert_vector = model.encode([text])[0] if text else np.zeros(384)

    vector = np.concatenate([[length, entropy, timestamp], bert_vector])
    return vector


def analyze_message(message: Message, ml_model: BaseEstimator) -> Dict:
    features = extract_features_for_single_message(message)
    ml_result = ml_model.predict([features])[0]
    rule_based = 'bot' in message.user_id.lower()

    return {
        "user_id": message.user_id,
        "text": message.text,
        "timestamp": message.timestamp,
        "rule_based_bot": rule_based,
        "ml_bot": bool(ml_result),
        "final_is_bot": rule_based or bool(ml_result)
    }


def load_messages_from_file(path: str) -> List[Message]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "messages" in data:
        data = data["messages"]
    return [Message.from_dict(item) for item in data]


def load_or_train_model(model_path: str = "model.pkl") -> BaseEstimator:
    import joblib
    from glob import glob

    if Path(model_path).exists():
        return joblib.load(model_path)

    X, y = [], []
    for file in glob("training_data/*.json"):
        data = json.loads(Path(file).read_text(encoding="utf-8"))
        label = data["label"]
        messages = [Message.from_dict(m) for m in data["messages"]]
        for msg in messages:
            vector = extract_features_for_single_message(msg)
            X.append(vector)
            y.append(label)

    pipeline = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    pipeline.fit(X, y)
    joblib.dump(pipeline, model_path)
    return pipeline


def save_report(results: List[Dict]):
    Path("logs").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = f"logs/report_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"📄 Звіт збережено: {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("⚠️  Використання: python main.py file1.json [file2.json ...]")
        exit(1)

    file_paths = sys.argv[1:]
    model = load_or_train_model()
    all_results = []

    for file_path in file_paths:
        try:
            messages = load_messages_from_file(file_path)
            if not messages:
                continue

            print(f"\n📂 Аналізуємо файл: {file_path} ({len(messages)} повідомлень)")

            for i, msg in enumerate(messages, 1):
                result = analyze_message(msg, model)
                result["file"] = file_path
                all_results.append(result)
                print(f"{i:03}: {'🤖 BOT' if result['final_is_bot'] else '🙂 Human'} | {msg.text[:40]!r}")

        except Exception as e:
            print(f"❌ Помилка при обробці {file_path}: {e}")

    if all_results:
        save_report(all_results)
