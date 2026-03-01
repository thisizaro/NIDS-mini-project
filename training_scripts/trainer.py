import numpy as np
from tensorflow.keras import callbacks


class Trainer:
    def __init__(self, model, data_loader):
        self.model = model
        self.data_loader = data_loader
        self.threshold = None
    
    def train(self, train_path, epochs=100, batch_size=64, validation_split=0.1, patience=10):
        X_train, _ = self.data_loader.load_and_preprocess(train_path)
        
        if self.data_loader.scaler is None:
            X_train = self.data_loader.fit_scaler(X_train)
        else:
            X_train = self.data_loader.transform(X_train)
        
        X_train_prep = self.model.prepare_data(X_train)
        
        early_stop = callbacks.EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)
        
        history = self.model.fit(
            X_train_prep, X_train_prep,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            shuffle=True,
            callbacks=[early_stop]
        )
        
        train_errors = self.model.compute_reconstruction_error(X_train)
        self.threshold = np.percentile(train_errors, 95)
        
        return history
    
    def save(self, model_path, scaler_path):
        self.model.save(model_path)
        self.data_loader.save_scaler(scaler_path)
        np.save(model_path.replace('.keras', '_threshold.npy'), self.threshold)
