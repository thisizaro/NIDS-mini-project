import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


@keras.saving.register_keras_serializable()
class BaseAutoencoder(tf.keras.Model):
    """Base class for all autoencoder models"""
    
    def prepare_data(self, X):
        """Override this to reshape data for specific model architecture"""
        return X
    
    def compute_reconstruction_error(self, X):
        """Compute MSE between input and reconstruction"""
        X_prep = self.prepare_data(X)
        recon = self.predict(X_prep, verbose=0)
        return tf.reduce_mean(tf.square(X_prep - recon), axis=tuple(range(1, len(recon.shape)))).numpy()


@keras.saving.register_keras_serializable()
class Encoder(tf.keras.Model):
    def __init__(self, input_shape, latent_dim, **kwargs):
        super().__init__(**kwargs)
        self.input_shape_ = input_shape
        self.latent_dim = latent_dim
        self.conv1 = layers.Conv1D(32, 3, padding="same", activation="relu")
        self.conv2 = layers.Conv1D(latent_dim, 3, padding="same", activation="relu")
        self.maxpool = layers.MaxPooling1D(2, padding="same")

    def call(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        return self.maxpool(x)

    def get_config(self):
        return {"input_shape": self.input_shape_, "latent_dim": self.latent_dim}


@keras.saving.register_keras_serializable()
class Decoder(tf.keras.Model):
    def __init__(self, latent_dim, **kwargs):
        super().__init__(**kwargs)
        self.latent_dim = latent_dim
        self.deconv1 = layers.Conv1D(latent_dim, 3, padding="same", activation="relu")
        self.upsample = layers.UpSampling1D(2)
        self.output_layer = layers.Conv1D(1, 3, padding="same", activation="linear")

    def call(self, x):
        x = self.deconv1(x)
        x = self.upsample(x)
        return self.output_layer(x)

    def get_config(self):
        return {"latent_dim": self.latent_dim}


@keras.saving.register_keras_serializable()
class ConvAutoencoder(BaseAutoencoder):
    def __init__(self, input_dim, latent_dim=16, **kwargs):
        super().__init__(**kwargs)
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.encoder = Encoder((input_dim, 1), latent_dim)
        self.decoder = Decoder(latent_dim)

    def call(self, x):
        return self.decoder(self.encoder(x))
    
    def prepare_data(self, X):
        """Reshape for 1D CNN: (batch, features, 1)"""
        if len(X.shape) == 2:
            return X.reshape(-1, X.shape[1], 1)
        return X

    def get_config(self):
        return {"input_dim": self.input_dim, "latent_dim": self.latent_dim}


@keras.saving.register_keras_serializable()
class DenseAutoencoder(BaseAutoencoder):
    def __init__(self, input_dim, latent_dim=32, **kwargs):
        super().__init__(**kwargs)
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.encoder_layers = [
            layers.Dense(64, activation='relu'),
            layers.Dense(latent_dim, activation='relu')
        ]
        self.decoder_layers = [
            layers.Dense(64, activation='relu'),
            layers.Dense(input_dim, activation='linear')
        ]
    
    def call(self, x):
        for layer in self.encoder_layers:
            x = layer(x)
        for layer in self.decoder_layers:
            x = layer(x)
        return x
    
    def get_config(self):
        return {"input_dim": self.input_dim, "latent_dim": self.latent_dim}
