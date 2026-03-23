"""
InfoGAN model for NIDS traffic classification.
Based on: "Unknown intrusion traffic detection method based on unsupervised
learning and open-set recognition" (Fang & Xie, 2025, Nature Scientific Reports)

Architecture from Fig. 6 of the paper:
- Shared Conv2D backbone for Discriminator and Classifier Q
- Generator uses Conv2DTranspose to produce 11x11x1 images
- Input: 69 network flow features, zero-padded to 121, reshaped to 11x11x1
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ─── Preprocessing constants ───────────────────────────────────────────────
# 10 all-zero features to remove (paper Section "Results and discussion")
ZERO_FEATURES = [
    "Bwd PSH Flags",
    "Fwd URG Flags",
    "Bwd URG Flags",
    "CWE Flag Count",
    "Fwd Avg Bytes/Bulk",
    "Fwd Avg Packets/Bulk",
    "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk",
    "Bwd Avg Packets/Bulk",
    "Bwd Avg Bulk Rate",
]

# Irrelevant features to remove (paper Section "Results and discussion")
# Note: These may not exist in all CSV variants; we drop them if present.
IRRELEVANT_FEATURES = [
    "Flow ID",
    "Source IP",
    "Src IP",
    "Destination IP",
    "Dst IP",
    "Timestamp",
    "Source Port",
    "Src Port",
    "Destination Port",
]

# CICIDS2017 attack label mapping → 7 classes
LABEL_MAP = {
    "BENIGN": 0,
    "Bot": 1,
    "FTP-Patator": 2,
    "SSH-Patator": 2,
    "DoS slowloris": 3,
    "DoS Slowhttptest": 3,
    "DoS Hulk": 3,
    "DoS GoldenEye": 3,
    "Heartbleed": 3,
    "Infiltration": 4,
    "PortScan": 5,
    "Web Attack \x96 Brute Force": 6,
    "Web Attack \x96 XSS": 6,
    "Web Attack \x96 Sql Injection": 6,
    "Web Attack – Brute Force": 6,
    "Web Attack – XSS": 6,
    "Web Attack – Sql Injection": 6,
    "DDoS": 3,
}

CLASS_NAMES = ["Normal", "Botnet", "Brute Force", "DoS", "Infiltration", "PortScan", "Web Attack"]
NUM_CLASSES = len(CLASS_NAMES)
IMAGE_SHAPE = (11, 11, 1)  # 69 features → zero-padded to 121 → 11x11x1


# ─── Network builders ──────────────────────────────────────────────────────

def build_shared_backbone():
    """
    Shared 3-layer Conv2D backbone (Fig. 6a).
    Input: 11x11x1 → Output: flattened feature vector.
    """
    inp = layers.Input(shape=IMAGE_SHAPE, name="image_input")

    # Conv2D(64, 4x4, stride 2, same) → LeakyReLU
    x = layers.Conv2D(64, 4, strides=2, padding="same")(inp)
    x = layers.LeakyReLU(negative_slope=0.2)(x)

    # Conv2D(128, 4x4, stride 2, same) → LeakyReLU
    x = layers.Conv2D(128, 4, strides=2, padding="same")(x)
    x = layers.LeakyReLU(negative_slope=0.2)(x)

    # Conv2D(256, 4x4, stride 1, same) → LeakyReLU
    x = layers.Conv2D(256, 4, strides=1, padding="same")(x)
    x = layers.LeakyReLU(negative_slope=0.2)(x)

    x = layers.Flatten()(x)
    return keras.Model(inp, x, name="shared_backbone")


def build_discriminator(backbone):
    """
    Discriminator head (Fig. 6a left).
    Shares the backbone, adds Dense(1) → Sigmoid.
    """
    inp = layers.Input(shape=IMAGE_SHAPE, name="disc_input")
    features = backbone(inp)
    out = layers.Dense(1, activation="sigmoid", name="disc_out")(features)
    return keras.Model(inp, out, name="discriminator")


def build_classifier(backbone, num_classes=NUM_CLASSES):
    """
    Classifier Q head (Fig. 6a right).
    Shares the backbone, adds Dense(128) → BN → LeakyReLU → Dense(c) → Softmax.
    """
    inp = layers.Input(shape=IMAGE_SHAPE, name="cls_input")
    features = backbone(inp)
    x = layers.Dense(128)(features)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(negative_slope=0.2)(x)
    out = layers.Dense(num_classes, activation="softmax", name="cls_out")(x)
    return keras.Model(inp, out, name="classifier")


def build_generator(noise_dim, num_classes=NUM_CLASSES):
    """
    Generator (Fig. 6b).
    Input: concatenated [noise_z, latent_c] → 11x11x1 output.

    Dimensions verified:
      Dense(4*4*512) → Reshape(4,4,512)
      Conv2DTranspose(256, 4x4, valid) → 7x7x256
      Conv2DTranspose(128, 3x3, valid) → 9x9x128
      Conv2DTranspose(64, 3x3, valid)  → 11x11x64
      Conv2DTranspose(1, 1x1, same)    → 11x11x1
    """
    noise_inp = layers.Input(shape=(noise_dim,), name="noise_z")
    label_inp = layers.Input(shape=(num_classes,), name="latent_c")

    x = layers.Concatenate()([noise_inp, label_inp])
    x = layers.Dense(4 * 4 * 512)(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Reshape((4, 4, 512))(x)

    # Conv2DTranspose(256, 4x4, valid) → 7x7
    x = layers.Conv2DTranspose(256, 4, strides=1, padding="valid")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    # Conv2DTranspose(128, 3x3, valid) → 9x9
    x = layers.Conv2DTranspose(128, 3, strides=1, padding="valid")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    # Conv2DTranspose(64, 3x3, valid) → 11x11
    x = layers.Conv2DTranspose(64, 3, strides=1, padding="valid")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    # Final: Conv2DTranspose(1, 1x1, same) → 11x11x1
    x = layers.Conv2DTranspose(1, 1, strides=1, padding="same", activation="tanh")(x)

    return keras.Model([noise_inp, label_inp], x, name="generator")


# ─── InfoGAN Trainer ───────────────────────────────────────────────────────

class InfoGANTrainer:
    """
    Trains the Info GAN with three losses:
      - D_loss: binary crossentropy (real vs fake)
      - G_loss: binary crossentropy (fool discriminator)
      - Q_loss: categorical crossentropy (recover latent vector c)

    Objective (Eq. 16): min_{G,Q} max_D V(D,G) - lambda * L1(G,Q)

    Hyperparameters from the paper:
      - Optimizer: Adam, lr=0.0002
      - lambda = 1 (weight for mutual information term)
      - latent c: one-hot, 7 categories
    """

    def __init__(self, generator, discriminator, classifier, backbone,
                 noise_dim=100, num_classes=NUM_CLASSES, lr=0.0002, lambda_info=1.0):
        self.generator = generator
        self.discriminator = discriminator
        self.classifier = classifier
        self.backbone = backbone
        self.noise_dim = noise_dim
        self.num_classes = num_classes
        self.lambda_info = lambda_info

        self.d_opt = keras.optimizers.Adam(learning_rate=lr, beta_1=0.5)
        self.g_opt = keras.optimizers.Adam(learning_rate=lr, beta_1=0.5)
        self.q_opt = keras.optimizers.Adam(learning_rate=lr, beta_1=0.5)

        self.bce = keras.losses.BinaryCrossentropy()
        self.cce = keras.losses.CategoricalCrossentropy()

    def _sample_noise_and_labels(self, batch_size):
        """Sample random noise z and one-hot encoded latent vector c."""
        z = tf.random.normal(shape=(batch_size, self.noise_dim))
        c_idx = tf.random.uniform(
            shape=(batch_size,), minval=0, maxval=self.num_classes, dtype=tf.int32
        )
        c = tf.one_hot(c_idx, self.num_classes)
        return z, c

    @tf.function
    def train_step(self, real_images):
        batch_size = tf.shape(real_images)[0]
        z, c = self._sample_noise_and_labels(batch_size)

        # ── Discriminator step ──
        fake_images = self.generator([z, c], training=True)

        with tf.GradientTape() as tape:
            real_out = self.discriminator(real_images, training=True)
            fake_out = self.discriminator(fake_images, training=True)
            d_loss_real = self.bce(tf.ones_like(real_out), real_out)
            d_loss_fake = self.bce(tf.zeros_like(fake_out), fake_out)
            d_loss = (d_loss_real + d_loss_fake) * 0.5

        d_vars = self.discriminator.trainable_variables
        d_grads = tape.gradient(d_loss, d_vars)
        self.d_opt.apply_gradients(zip(d_grads, d_vars))

        # ── Generator + Q (classifier) step ──
        z, c = self._sample_noise_and_labels(batch_size)

        with tf.GradientTape() as tape:
            fake_images = self.generator([z, c], training=True)
            fake_out = self.discriminator(fake_images, training=True)
            g_loss = self.bce(tf.ones_like(fake_out), fake_out)

            # Q loss: recover latent vector c from fake data
            c_pred = self.classifier(fake_images, training=True)
            q_loss = self.cce(c, c_pred)

            total_g_loss = g_loss + self.lambda_info * q_loss

        g_vars = self.generator.trainable_variables + self.classifier.trainable_variables
        g_grads = tape.gradient(total_g_loss, g_vars)
        self.g_opt.apply_gradients(zip(g_grads, g_vars))

        return d_loss, g_loss, q_loss

    def fit(self, X, epochs, batch_size):
        dataset = (
            tf.data.Dataset.from_tensor_slices(X)
            .shuffle(len(X))
            .batch(batch_size)
            .prefetch(tf.data.AUTOTUNE)
        )

        history = {"d_loss": [], "g_loss": [], "q_loss": []}

        for epoch in range(epochs):
            epoch_d, epoch_g, epoch_q = [], [], []

            for batch in dataset:
                dl, gl, ql = self.train_step(batch)
                epoch_d.append(dl.numpy())
                epoch_g.append(gl.numpy())
                epoch_q.append(ql.numpy())

            avg_d = float(tf.reduce_mean(epoch_d))
            avg_g = float(tf.reduce_mean(epoch_g))
            avg_q = float(tf.reduce_mean(epoch_q))

            history["d_loss"].append(avg_d)
            history["g_loss"].append(avg_g)
            history["q_loss"].append(avg_q)

            if (epoch + 1) % 50 == 0 or epoch == 0:
                print(
                    f"Epoch {epoch+1:4d}/{epochs} — "
                    f"D_loss={avg_d:.4f}  G_loss={avg_g:.4f}  Q_loss={avg_q:.4f}"
                )

        return history

    def get_activation_vectors(self, X, batch_size=1024):
        """
        Get penultimate layer activations (before softmax) for OpenMax.
        These are the 128-dim Dense layer outputs in the classifier.
        """
        # Build a model that outputs the penultimate layer
        penultimate = keras.Model(
            self.classifier.input,
            self.classifier.layers[-2].output,  # Dense(128) before softmax
            name="penultimate",
        )
        return penultimate.predict(X, batch_size=batch_size, verbose=1)


# ─── Data Preprocessing for InfoGAN ──────────────────────────────────────────

LABEL_COLUMN = "Label"


def load_and_clean_csv(csv_path):
    """
    Load a CICIDS2017 CSV and apply the paper's preprocessing:
      - Strip column whitespace
      - Handle duplicate 'Fwd Header Length' columns
      - Remove 10 all-zero features
      - Remove irrelevant features (IPs, ports, timestamps, Flow ID)
      - Map labels to 7-class scheme
      - Clean inf/NaN values

    Returns: (X_df, labels_int, label_names)
      - X_df: DataFrame of cleaned features (~69 columns)
      - labels_int: numpy array of integer labels (0–6)
      - label_names: original string labels
    """
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Handle duplicate "Fwd Header Length" columns
    dupes = df.columns[df.columns.duplicated()].unique().tolist()
    if "Fwd Header Length" in dupes:
        cols = list(df.columns)
        seen = False
        for i, c in enumerate(cols):
            if c == "Fwd Header Length":
                if seen:
                    cols[i] = "Fwd Header Length.1"
                seen = True
        df.columns = cols

    # Extract labels before dropping columns
    label_names = df[LABEL_COLUMN].values if LABEL_COLUMN in df.columns else None

    # Map string labels to integer classes
    labels_int = None
    if label_names is not None:
        labels_int = np.array([LABEL_MAP.get(l.strip(), -1) for l in label_names])

    # Drop label column and irrelevant/zero-value features
    drop_cols = [LABEL_COLUMN] + ZERO_FEATURES + IRRELEVANT_FEATURES
    drop_cols = [c for c in drop_cols if c in df.columns]
    X_df = df.drop(columns=drop_cols)

    # Clean inf/NaN
    X_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_df = X_df.fillna(X_df.median(numeric_only=True))

    return X_df, labels_int, label_names


def features_to_images(X_scaled):
    """
    Convert scaled feature vectors to 11x11x1 images.
    Paper method: 69 features → zero-pad to 121 → reshape to (11, 11, 1).

    Args:
        X_scaled: (N, D) numpy array where D <= 121

    Returns:
        images: (N, 11, 11, 1) float32 array
    """
    N, D = X_scaled.shape
    if D < 121:
        # Zero-pad to 121
        padded = np.zeros((N, 121), dtype=np.float32)
        padded[:, :D] = X_scaled
    else:
        padded = X_scaled[:, :121].astype(np.float32)

    return padded.reshape(N, 11, 11, 1)


def prepare_infogan_data(csv_paths, scaler=None):
    """
    End-to-end data preparation for InfoGAN training.

    Args:
        csv_paths: list of CSV file paths to load
        scaler: pre-fitted MinMaxScaler (if None, fits a new one)

    Returns:
        images: (N, 11, 11, 1) float32 array ready for InfoGAN
        labels_int: (N,) integer labels (0–6, or -1 for unmapped)
        scaler: fitted MinMaxScaler
        feature_cols: list of feature column names
    """
    all_X = []
    all_labels = []

    for path in csv_paths:
        X_df, labels_int, _ = load_and_clean_csv(path)
        all_X.append(X_df)
        if labels_int is not None:
            all_labels.append(labels_int)

    # Concatenate all DataFrames (use intersection of columns)
    feature_cols = all_X[0].columns.tolist()
    for x in all_X[1:]:
        feature_cols = [c for c in feature_cols if c in x.columns]

    X_combined = pd.concat([x[feature_cols] for x in all_X], ignore_index=True)
    labels_combined = np.concatenate(all_labels) if all_labels else None

    print(f"Combined dataset: {X_combined.shape[0]} samples, {X_combined.shape[1]} features")

    # Fit or apply scaler
    if scaler is None:
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X_combined).astype(np.float32)
    else:
        X_scaled = scaler.transform(X_combined).astype(np.float32)

    # Convert to images
    images = features_to_images(X_scaled)
    print(f"Image shape: {images.shape}")

    return images, labels_combined, scaler, feature_cols
