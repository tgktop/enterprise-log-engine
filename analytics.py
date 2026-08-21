import pandas as pd
import numpy as np

class AnomalyEngine:
    def __init__(self, z_threshold: float = 2.0):
        self.metrics_history = []
        self.z_threshold = z_threshold

    def evaluate_latency(self, latency_ms: float) -> dict:
        self.metrics_history.append(latency_ms)
        
        if len(self.metrics_history) < 5:
            return {"is_anomaly": False, "z_score": 0.0, "reason": "Insufficient baseline data"}

        series = pd.Series(self.metrics_history[-50:])
        mean = series.mean()
        std = series.std()

        if std == 0:
            return {"is_anomaly": False, "z_score": 0.0, "reason": "Zero variance"}

        z_score = (latency_ms - mean) / std
        is_anomaly = z_score > self.z_threshold

        return {
            "is_anomaly": bool(is_anomaly),
            "z_score": float(round(z_score, 2)),
            "rolling_mean": float(round(mean, 2)),
            "rolling_std": float(round(std, 2))
        }