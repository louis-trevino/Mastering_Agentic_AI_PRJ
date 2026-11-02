from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def evaluate(df: pd.DataFrame, label: str):
    y_true = df["true_category"]
    y_pred = df["predicted_category"]
    print(f"=== {label} ===")
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.2%}  ({df['correct'].sum()}/{len(df)} correct)\n")
    print("Per-class precision / recall / F1:")
    print(classification_report(y_true, y_pred, labels=CATEGORIES, zero_division=0))
    print("Confusion matrix (rows = true, cols = predicted):")
    cm = pd.DataFrame(
        confusion_matrix(y_true, y_pred, labels=CATEGORIES),
        index=CATEGORIES, columns=CATEGORIES,
    )
    print(cm)
    return accuracy_score(y_true, y_pred)

acc_v1 = evaluate(results_v1, "Run 1 — baseline prompt")

