import pandas as pd
from engine.pipeline import run_detection_pipeline

# Create sample gameplay data for 10 players
data = pd.DataFrame({
    "player_id": [f"p{i}" for i in range(10)],
    "score": [100, 120, 110, 130, 90, 115, 125, 105, 95, 5000],
    "kills": [5, 6, 5, 7, 4, 6, 7, 5, 4, 100],
    "deaths": [2, 3, 2, 3, 2, 2, 3, 2, 2, 1],
    "play_time": [15] * 10,
    "actions": [20, 22, 21, 25, 18, 23, 24, 20, 19, 500],
    "action_interval": [2.5, 2.2, 2.4, 2.1, 2.8, 2.3, 2.0, 2.6, 2.7, 0.1]
})

# Run the complete pipeline
results = run_detection_pipeline(data)

# Display results
print("\nFAIRPLAY RADAR RESULTS")
print(results.to_string(index=False))

# Verify expected output columns
expected_columns = [
    "anomaly_label",
    "anomaly_score",
    "risk_score",
    "risk_reasons",
    "risk_level"
]

for column in expected_columns:
    assert column in results.columns, f"Missing column: {column}"

print("\nSUCCESS: All pipeline stages completed!")