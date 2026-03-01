import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score, precision_recall_fscore_support


class Evaluator:
    def __init__(self, model, data_loader, threshold):
        self.model = model
        self.data_loader = data_loader
        self.threshold = threshold
    
    def evaluate(self, benign_path, attack_paths):
        X_benign, _ = self.data_loader.load_and_preprocess(benign_path)
        X_benign = self.data_loader.transform(X_benign)
        
        benign_errors = self.model.compute_reconstruction_error(X_benign)
        
        results = []
        
        for attack_path in attack_paths:
            X_attack, _ = self.data_loader.load_and_preprocess(attack_path)
            X_attack = self.data_loader.transform(X_attack)
            
            attack_errors = self.model.compute_reconstruction_error(X_attack)
            
            y_true = np.concatenate([np.zeros(len(benign_errors)), np.ones(len(attack_errors))])
            y_scores = np.concatenate([benign_errors, attack_errors])
            y_pred = (y_scores > self.threshold).astype(int)
            
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_true, y_pred, average='binary', zero_division=0
            )
            
            auc = roc_auc_score(y_true, y_scores)
            cm = confusion_matrix(y_true, y_pred)
            tn, fp, fn, tp = cm.ravel()
            
            acc = (tp + tn) / (tp + tn + fp + fn)
            
            results.append({
                'Attack': attack_path.split('/')[-1],
                'Threshold': self.threshold,
                'Accuracy': acc,
                'Precision': precision,
                'Recall': recall,
                'F1': f1,
                'AUC': auc,
                'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn
            })
        
        return pd.DataFrame(results)
