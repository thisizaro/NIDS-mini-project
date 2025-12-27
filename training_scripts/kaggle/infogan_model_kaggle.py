"""
InfoGAN model for NIDS — Kaggle Version.

Adapted from infogan_model_optimized.py for Kaggle environment:
  - Imports nids_utils_kaggle instead of nids_utils
  - setup_kaggle() replaces setup_colab() with Kaggle-specific GPU config
  - All paths default to /kaggle/working/
  - Otherwise identical architecture and training logic
"""

import os
import json
import time
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ─── Preprocessing constants (unchanged) ─────────────────────────────────────

ZERO_FEATURES = [
    "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags", "CWE Flag Count",
    "Fwd Avg Bytes/Bulk", "Fwd Avg Packets/Bulk", "Fwd Avg Bulk Rate",
    "Bwd Avg Bytes/Bulk", "Bwd Avg Packets/Bulk", "Bwd Avg Bulk Rate",
]

IRRELEVANT_FEATURES = [
    "Flow ID", "Source IP", "Src IP", "Destination IP", "Dst IP",
    "Timestamp", "Source Port", "Src Port", "Destination Port",
]

LABEL_MAP = {
    "BENIGN": 0, "Bot": 1, "FTP-Patator": 2, "SSH-Patator": 2,
    "DoS slowloris": 3, "DoS Slowhttptest": 3, "DoS Hulk": 3,
    "DoS GoldenEye": 3, "Heartbleed": 3, "DDoS": 3,
    "Infiltration": 4, "PortScan": 5,
    "Web Attack \x96 Brute Force": 6, "Web Attack \x96 XSS": 6,
    "Web Attack \x96 Sql Injection": 6,
    "Web Attack – Brute Force": 6, "Web Attack – XSS": 6,
    "Web Attack – Sql Injection": 6,
}

CLASS_NAMES = ["Normal", "Botnet", "Brute Force", "DoS", "Infiltration", "PortScan", "Web Attack"]
NUM_CLASSES = len(CLASS_NAMES)
IMAGE_SHAPE = (11, 11, 1)
LABEL_COLUMN = "Label"


# ─── Kaggle setup helper ────────────────────────────────────────────────────

def setup_kaggle():
    """
    Call once at notebook start. Enables mixed precision, memory growth, prints GPU info.
    Works for both T4 and P100 on Kaggle.

    Note: MirroredStrategy is NOT used because TF's custom GAN training loops
    with BatchNormalization cause placeholder errors under MirroredStrategy.
    A single T4 with proper data pipeline is fast enough for this model size.
    """
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"GPU(s) detected: {len(gpus)}")
        for gpu in gpus:
            print(f"  {gpu.name}")
    else:
        print("WARNING: No GPU detected — training will be very slow.")
        print("Make sure you enabled GPU in: Settings → Accelerator → GPU T4 x2")

    # Mixed precision — works on both T4 (tensor cores) and P100 (lesser benefit)
    from tensorflow.keras import mixed_precision
    mixed_precision.set_global_policy("mixed_float16")
    print(f"Mixed precision policy: {mixed_precision.global_policy().name}")
    print(f"TF version: {tf.__version__}")


# ─── Network builders (he_normal init, float32 output heads) ────────────────

def build_shared_backbone():
    """Shared 3-layer Conv2D backbone. he_normal init on all Conv layers."""
    inp = layers.Input(shape=IMAGE_SHAPE, name="image_input")

    x = layers.Conv2D(64, 4, strides=2, padding="same", kernel_initializer="he_normal")(inp)
    x = layers.LeakyReLU(negative_slope=0.2)(x)

    x = layers.Conv2D(128, 4, strides=2, padding="same", kernel_initializer="he_normal")(x)
    x = layers.LeakyReLU(negative_slope=0.2)(x)

    x = layers.Conv2D(256, 4, strides=1, padding="same", kernel_initializer="he_normal")(x)
    x = layers.LeakyReLU(negative_slope=0.2)(x)

    x = layers.Flatten()(x)
    return keras.Model(inp, x, name="shared_backbone")


def build_discriminator(backbone):
    """Discriminator head. Output is float32 for numerical stability with mixed precision."""
    inp = layers.Input(shape=IMAGE_SHAPE, name="disc_input")
    features = backbone(inp)
    out = layers.Dense(1, name="disc_logit")(features)
    # Explicit float32 cast for mixed precision safety
    out = layers.Activation("sigmoid", dtype="float32", name="disc_out")(out)
    return keras.Model(inp, out, name="discriminator")


def build_classifier(backbone, num_classes=NUM_CLASSES):
    """Classifier Q head. Output is float32 for loss stability."""
    inp = layers.Input(shape=IMAGE_SHAPE, name="cls_input")
    features = backbone(inp)
    x = layers.Dense(128)(features)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(negative_slope=0.2)(x)
    out = layers.Dense(num_classes, name="cls_logit")(x)
    out = layers.Activation("softmax", dtype="float32", name="cls_out")(out)
    return keras.Model(inp, out, name="classifier")


def build_generator(noise_dim, num_classes=NUM_CLASSES):
    """Generator. Output tanh is float32. he_normal init on ConvTranspose."""
    noise_inp = layers.Input(shape=(noise_dim,), name="noise_z")
    label_inp = layers.Input(shape=(num_classes,), name="latent_c")

    x = layers.Concatenate()([noise_inp, label_inp])
    x = layers.Dense(4 * 4 * 512, kernel_initializer="he_normal")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Reshape((4, 4, 512))(x)

    x = layers.Conv2DTranspose(256, 4, strides=1, padding="valid", kernel_initializer="he_normal")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    x = layers.Conv2DTranspose(128, 3, strides=1, padding="valid", kernel_initializer="he_normal")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    x = layers.Conv2DTranspose(64, 3, strides=1, padding="valid", kernel_initializer="he_normal")(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)

    x = layers.Conv2DTranspose(1, 1, strides=1, padding="same", kernel_initializer="he_normal")(x)
    x = layers.Activation("tanh", dtype="float32", name="gen_out")(x)

    return keras.Model([noise_inp, label_inp], x, name="generator")


# ─── InfoGAN Trainer (optimized) ─────────────────────────────────────────────

class InfoGANTrainer:
    """
    Kaggle-optimized InfoGAN trainer.

    Features:
      - Gradient clipping (clipnorm=1.0) on all optimizers
      - Label smoothing: real labels = 0.9
      - tf.train.Checkpoint with auto-resume
      - Periodic sample generation + history save
      - Optional early stopping
    """

    def __init__(self, generator, discriminator, classifier, backbone,
                 noise_dim=100, num_classes=NUM_CLASSES, lr=0.0002, lambda_info=1.0,
                 checkpoint_dir=None):
        self.generator = generator
        self.discriminator = discriminator
        self.classifier = classifier
        self.backbone = backbone
        self.noise_dim = noise_dim
        self.num_classes = num_classes
        self.lambda_info = lambda_info

        # Gradient clipping
        self.d_opt = keras.optimizers.Adam(learning_rate=lr, beta_1=0.5, clipnorm=1.0)
        self.g_opt = keras.optimizers.Adam(learning_rate=lr, beta_1=0.5, clipnorm=1.0)

        self.bce = keras.losses.BinaryCrossentropy()
        self.cce = keras.losses.CategoricalCrossentropy()

        # Label smoothing constant
        self.real_label_val = 0.9

        # Checkpointing
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint = None
        self.ckpt_manager = None
        self._start_epoch = 0

        if checkpoint_dir:
            self.checkpoint = tf.train.Checkpoint(
                generator=self.generator,
                discriminator=self.discriminator,
                classifier=self.classifier,
                d_opt=self.d_opt,
                g_opt=self.g_opt,
            )
            self.ckpt_manager = tf.train.CheckpointManager(
                self.checkpoint, checkpoint_dir, max_to_keep=3
            )
            if self.ckpt_manager.latest_checkpoint:
                self.checkpoint.restore(self.ckpt_manager.latest_checkpoint)
                # Extract epoch number from checkpoint path
                ckpt_name = os.path.basename(self.ckpt_manager.latest_checkpoint)
                try:
                    self._start_epoch = int(ckpt_name.split("-")[-1])
                except ValueError:
                    self._start_epoch = 0
                print(f"Resumed from checkpoint: {self.ckpt_manager.latest_checkpoint} (epoch {self._start_epoch})")
            else:
                print(f"No checkpoint found in {checkpoint_dir} — training from scratch.")

    def _sample_noise_and_labels(self, batch_size):
        z = tf.random.normal(shape=(batch_size, self.noise_dim))
        c_idx = tf.random.uniform(shape=(batch_size,), minval=0, maxval=self.num_classes, dtype=tf.int32)
        c = tf.one_hot(c_idx, self.num_classes)
        return z, c

    @tf.function
    def train_step(self, real_images):
        batch_size = tf.shape(real_images)[0]

        # Label smoothing: real → 0.9, fake → 0.0
        real_labels = tf.fill([batch_size, 1], self.real_label_val)
        fake_labels = tf.zeros([batch_size, 1])

        # ── Discriminator step ──
        z, c = self._sample_noise_and_labels(batch_size)
        fake_images = self.generator([z, c], training=True)

        with tf.GradientTape() as tape:
            real_out = self.discriminator(real_images, training=True)
            fake_out = self.discriminator(fake_images, training=True)
            d_loss_real = self.bce(real_labels, real_out)
            d_loss_fake = self.bce(fake_labels, fake_out)
            d_loss = (d_loss_real + d_loss_fake) * 0.5

        d_grads = tape.gradient(d_loss, self.discriminator.trainable_variables)
        self.d_opt.apply_gradients(zip(d_grads, self.discriminator.trainable_variables))

        # ── Generator + Q step ──
        z, c = self._sample_noise_and_labels(batch_size)

        with tf.GradientTape() as tape:
            fake_images = self.generator([z, c], training=True)
            fake_out = self.discriminator(fake_images, training=True)
            g_loss = self.bce(tf.ones([batch_size, 1]), fake_out)

            c_pred = self.classifier(fake_images, training=True)
            q_loss = self.cce(c, c_pred)

            total_g_loss = g_loss + self.lambda_info * q_loss

        g_vars = self.generator.trainable_variables + self.classifier.trainable_variables
        g_grads = tape.gradient(total_g_loss, g_vars)
        self.g_opt.apply_gradients(zip(g_grads, g_vars))

        return d_loss, g_loss, q_loss

    def _generate_samples(self, n_per_class=4):
        """Generate sample images for each class."""
        all_imgs = []
        for cls in range(self.num_classes):
            z = tf.random.normal(shape=(n_per_class, self.noise_dim))
            c = tf.one_hot(tf.fill([n_per_class], cls), self.num_classes)
            fake = self.generator([z, c], training=False)
            all_imgs.append(fake.numpy())
        return all_imgs

    def _save_samples(self, epoch, save_dir):
        """Save generated sample grid."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        imgs = self._generate_samples(n_per_class=4)
        fig, axes = plt.subplots(self.num_classes, 4, figsize=(8, 2 * self.num_classes))
        for cls in range(self.num_classes):
            for j in range(4):
                ax = axes[cls, j] if self.num_classes > 1 else axes[j]
                ax.imshow(imgs[cls][j, :, :, 0], cmap="viridis", vmin=-1, vmax=1)
                ax.axis("off")
        fig.suptitle(f"Epoch {epoch}", fontsize=12)
        fig.tight_layout()
        os.makedirs(save_dir, exist_ok=True)
        fig.savefig(os.path.join(save_dir, f"samples_epoch_{epoch:04d}.png"), dpi=100)
        plt.close(fig)

    def fit(self, dataset, epochs, steps_per_epoch=None,
            save_dir=None, print_every=10, sample_every=10, ckpt_every=5,
            early_stop=False, early_stop_patience=10, early_stop_d_threshold=0.05):
        """
        Train the InfoGAN.

        Args:
            dataset:          tf.data.Dataset (already batched + prefetched)
            epochs:           total number of epochs to train
            steps_per_epoch:  if None, iterates full dataset each epoch
            save_dir:         directory for samples/history
            print_every:      print losses every N epochs
            sample_every:     generate + save samples every N epochs
            ckpt_every:       save checkpoint every N epochs
            early_stop:       enable early stopping
            early_stop_patience:  epochs of stable G loss before stopping
            early_stop_d_threshold: if D_loss < this for patience epochs, stop
        """
        history = {"d_loss": [], "g_loss": [], "q_loss": [], "epoch_time": []}

        # Resume support
        start_epoch = self._start_epoch

        # Early stopping state
        g_loss_window = []
        d_low_count = 0

        from tqdm.auto import tqdm

        for epoch in range(start_epoch, epochs):
            t0 = time.time()
            epoch_d = tf.keras.metrics.Mean()
            epoch_g = tf.keras.metrics.Mean()
            epoch_q = tf.keras.metrics.Mean()

            pbar = tqdm(
                enumerate(dataset),
                total=steps_per_epoch,
                desc=f"Epoch {epoch+1}/{epochs}",
                unit="step",
                leave=False,
            )
            for step, batch in pbar:
                dl, gl, ql = self.train_step(batch)
                epoch_d.update_state(dl)
                epoch_g.update_state(gl)
                epoch_q.update_state(ql)
                if step % 50 == 0:
                    pbar.set_postfix(D=f"{float(dl):.4f}", G=f"{float(gl):.4f}", Q=f"{float(ql):.4f}")
                if steps_per_epoch and step + 1 >= steps_per_epoch:
                    break
            pbar.close()

            avg_d = float(epoch_d.result())
            avg_g = float(epoch_g.result())
            avg_q = float(epoch_q.result())
            elapsed = time.time() - t0

            history["d_loss"].append(avg_d)
            history["g_loss"].append(avg_g)
            history["q_loss"].append(avg_q)
            history["epoch_time"].append(elapsed)

            # Print
            if (epoch + 1) % print_every == 0 or epoch == start_epoch:
                total_time = sum(history["epoch_time"])
                print(
                    f"Epoch {epoch+1:4d}/{epochs} — "
                    f"D={avg_d:.4f}  G={avg_g:.4f}  Q={avg_q:.4f}  "
                    f"({elapsed:.1f}s | total {total_time/60:.1f}m)"
                )

            # Checkpoint
            if self.ckpt_manager and (epoch + 1) % ckpt_every == 0:
                self.ckpt_manager.save(checkpoint_number=epoch + 1)

            # Sample generation
            if save_dir and (epoch + 1) % sample_every == 0:
                self._save_samples(epoch + 1, os.path.join(save_dir, "samples"))

            # Save history periodically
            if save_dir and (epoch + 1) % print_every == 0:
                os.makedirs(save_dir, exist_ok=True)
                pd.DataFrame(history).to_csv(
                    os.path.join(save_dir, "training_history_live.csv"), index=False
                )

            # Early stopping
            if early_stop:
                g_loss_window.append(avg_g)
                if len(g_loss_window) > early_stop_patience:
                    g_loss_window.pop(0)

                if len(g_loss_window) == early_stop_patience:
                    g_std = np.std(g_loss_window)
                    if g_std < 0.01:
                        print(f"Early stop: G_loss stable (std={g_std:.5f}) for {early_stop_patience} epochs.")
                        break

                if avg_d < early_stop_d_threshold:
                    d_low_count += 1
                    if d_low_count >= early_stop_patience:
                        print(f"Early stop: D_loss < {early_stop_d_threshold} for {early_stop_patience} epochs.")
                        break
                else:
                    d_low_count = 0

        # Final checkpoint
        if self.ckpt_manager:
            self.ckpt_manager.save(checkpoint_number=epochs)
            print(f"Final checkpoint saved at epoch {epochs}.")

        # Final history save
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            pd.DataFrame(history).to_csv(
                os.path.join(save_dir, "training_history_final.csv"), index=False
            )

        return history

    def get_activation_vectors(self, X, batch_size=1024):
        """Get 128-dim penultimate layer outputs for OpenMax."""
        penultimate = keras.Model(
            self.classifier.input,
            self.classifier.layers[-3].output,  # Dense(128) output, before the logit+softmax
            name="penultimate",
        )
        return penultimate.predict(X, batch_size=batch_size, verbose=0)

    def get_activation_vectors_from_dataset(self, dataset):
        """Get activation vectors from a tf.data.Dataset (memory-safe)."""
        penultimate = keras.Model(
            self.classifier.input,
            self.classifier.layers[-3].output,
            name="penultimate",
        )
        all_avs = []
        for batch in dataset:
            avs = penultimate(batch, training=False)
            all_avs.append(avs.numpy())
        return np.concatenate(all_avs, axis=0)


# ─── Memory-safe data pipeline ──────────────────────────────────────────────

def load_and_clean_csv(csv_path):
    """Load a CICIDS2017 CSV, clean it, return (X_df, labels_int). Same logic as original."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    # Handle duplicate "Fwd Header Length"
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

    label_names = df[LABEL_COLUMN].values if LABEL_COLUMN in df.columns else None
    labels_int = None
    if label_names is not None:
        labels_int = np.array([LABEL_MAP.get(str(l).strip(), -1) for l in label_names])

    drop_cols = [c for c in [LABEL_COLUMN] + ZERO_FEATURES + IRRELEVANT_FEATURES if c in df.columns]
    X_df = df.drop(columns=drop_cols)
    X_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    X_df = X_df.fillna(X_df.median(numeric_only=True))

    return X_df, labels_int


def fit_scaler_streaming(csv_paths, feature_range=(-1, 1)):
    """
    Two-pass scaler fit without holding all data in RAM.
    Returns: scaler, feature_cols
    """
    # Determine shared columns from first file
    first_df, _ = load_and_clean_csv(csv_paths[0])
    feature_cols = first_df.columns.tolist()
    del first_df

    for path in csv_paths[1:]:
        df, _ = load_and_clean_csv(path)
        feature_cols = [c for c in feature_cols if c in df.columns]
        del df

    # Compute global min/max
    global_min = None
    global_max = None

    for path in csv_paths:
        print(f"  Scanning {os.path.basename(path)} for min/max...")
        df, _ = load_and_clean_csv(path)
        X = df[feature_cols].values.astype(np.float32)
        batch_min = np.nanmin(X, axis=0)
        batch_max = np.nanmax(X, axis=0)

        if global_min is None:
            global_min = batch_min
            global_max = batch_max
        else:
            global_min = np.minimum(global_min, batch_min)
            global_max = np.maximum(global_max, batch_max)
        del df, X

    # Build scaler manually
    scaler = MinMaxScaler(feature_range=feature_range)
    scaler.fit(np.vstack([global_min.reshape(1, -1), global_max.reshape(1, -1)]))

    return scaler, feature_cols


def preprocess_csvs_to_numpy(csv_paths, scaler, feature_cols, known_classes=None,
                              save_dir="/kaggle/working/preprocessing"):
    """
    One-time preprocessing: convert all CSVs to numpy arrays saved on disk.
    Returns paths to the saved .npy files and total sample count.
    Subsequent epochs load from numpy — no CSV re-reading.
    """
    os.makedirs(save_dir, exist_ok=True)
    images_path = os.path.join(save_dir, "train_images.npy")
    labels_path = os.path.join(save_dir, "train_labels.npy")

    # If already preprocessed, just load metadata
    if os.path.exists(images_path) and os.path.exists(labels_path):
        labels = np.load(labels_path)
        n = len(labels)
        print(f"Pre-processed data found: {n:,} samples")
        return images_path, labels_path, n

    num_features = len(feature_cols)
    pad_width = 121 - num_features

    label_remap = None
    if known_classes is not None:
        label_remap = {old: new for new, old in enumerate(known_classes)}

    all_images = []
    all_labels = []

    for path in csv_paths:
        print(f"  Processing {os.path.basename(path)}...")
        df, labels = load_and_clean_csv(path)
        X = df[feature_cols].values.astype(np.float32)
        X_scaled = scaler.transform(X).astype(np.float32)
        del df, X

        if pad_width > 0:
            X_padded = np.pad(X_scaled, ((0, 0), (0, pad_width)), mode="constant")
        else:
            X_padded = X_scaled[:, :121]
        del X_scaled

        imgs = X_padded.reshape(-1, 11, 11, 1)
        del X_padded

        if known_classes is not None and labels is not None:
            mask = np.isin(labels, list(known_classes))
            imgs = imgs[mask]
            labels = labels[mask]
            labels = np.array([label_remap[int(l)] for l in labels])

        all_images.append(imgs)
        if labels is not None:
            all_labels.append(labels)
        del imgs, labels

    images = np.concatenate(all_images, axis=0)
    del all_images
    labels_out = np.concatenate(all_labels) if all_labels else np.zeros(len(images), dtype=np.int32)
    del all_labels

    np.save(images_path, images)
    np.save(labels_path, labels_out)
    n = len(images)
    del images, labels_out
    print(f"Saved {n:,} samples to {save_dir}")
    return images_path, labels_path, n


def build_dataset_from_numpy(images_path, labels_path, batch_size, shuffle_buffer=50000):
    """
    Build a fast tf.data.Dataset from pre-processed numpy files.
    Loads fully into RAM (~1.3GB for CICIDS2017) — no mmap random I/O bottleneck.
    """
    print("Loading numpy arrays into RAM...")
    images = np.load(images_path)   # full load into RAM, NOT mmap
    labels = np.load(labels_path)
    n = len(images)
    print(f"  Loaded {n:,} samples ({images.nbytes / 1e9:.2f} GB)")

    dataset = tf.data.Dataset.from_tensor_slices((images, labels))
    dataset = (
        dataset
        .cache()                                    # cache in TF memory after first pass
        .shuffle(shuffle_buffer)
        .batch(batch_size, drop_remainder=True)
        .prefetch(tf.data.AUTOTUNE)
    )
    del images, labels  # numpy copies are now in TF's cache
    return dataset, n


def build_dataset_from_csv(csv_paths, batch_size, scaler, feature_cols,
                           known_classes=None, shuffle_buffer=10000):
    """
    Memory-safe tf.data pipeline.
    Reads CSVs one at a time, scales, pads, reshapes to 11x11, yields (image, label).
    """
    num_features = len(feature_cols)
    pad_width = 121 - num_features  # zero-pad to 121

    label_remap = None
    if known_classes is not None:
        label_remap = {old: new for new, old in enumerate(known_classes)}

    def generator_fn():
        for path in csv_paths:
            df, labels = load_and_clean_csv(path)
            X = df[feature_cols].values.astype(np.float32)
            X_scaled = scaler.transform(X).astype(np.float32)
            del df, X  # free raw data immediately

            for i in range(len(X_scaled)):
                lab = int(labels[i]) if labels is not None else -1

                # Filter by known classes
                if known_classes is not None and lab not in label_remap:
                    continue

                # Zero-pad to 121 and reshape
                row = X_scaled[i]
                if pad_width > 0:
                    row = np.pad(row, (0, pad_width), mode="constant", constant_values=0.0)
                img = row.reshape(11, 11, 1)

                remapped = label_remap[lab] if label_remap and lab in label_remap else lab
                yield img, remapped

            del X_scaled, labels

    # Count total samples (needed for steps_per_epoch)
    total_samples = 0
    for path in csv_paths:
        df, labels = load_and_clean_csv(path)
        if known_classes is not None and labels is not None:
            total_samples += int(np.isin(labels, list(known_classes)).sum())
        else:
            total_samples += len(df)
        del df, labels

    output_sig = (
        tf.TensorSpec(shape=(11, 11, 1), dtype=tf.float32),
        tf.TensorSpec(shape=(), dtype=tf.int32),
    )

    dataset = tf.data.Dataset.from_generator(generator_fn, output_signature=output_sig)
    dataset = (
        dataset
        .shuffle(shuffle_buffer)
        .batch(batch_size, drop_remainder=True)
        .prefetch(tf.data.AUTOTUNE)
    )

    return dataset, total_samples, label_remap


def build_images_only_dataset(full_dataset):
    """Strip labels from a (image, label) dataset — for InfoGAN training which is unsupervised."""
    return full_dataset.map(lambda img, lab: img, num_parallel_calls=tf.data.AUTOTUNE)


def build_image_label_arrays_streamed(csv_paths, scaler, feature_cols, known_classes=None, chunk_size=50000):
    """
    Load data into numpy arrays in chunks for evaluation (OpenMax, sklearn metrics).
    Returns: images (N,11,11,1), labels (N,)
    """
    num_features = len(feature_cols)
    pad_width = 121 - num_features

    label_remap = None
    if known_classes is not None:
        label_remap = {old: new for new, old in enumerate(known_classes)}

    all_images = []
    all_labels = []

    for path in csv_paths:
        print(f"  Loading {os.path.basename(path)}...")
        df, labels = load_and_clean_csv(path)
        X = df[feature_cols].values.astype(np.float32)
        X_scaled = scaler.transform(X).astype(np.float32)
        del df, X

        if pad_width > 0:
            X_padded = np.pad(X_scaled, ((0, 0), (0, pad_width)), mode="constant")
        else:
            X_padded = X_scaled[:, :121]
        del X_scaled

        imgs = X_padded.reshape(-1, 11, 11, 1)
        del X_padded

        if known_classes is not None and labels is not None:
            mask = np.isin(labels, list(known_classes))
            imgs = imgs[mask]
            labels = labels[mask]
            labels = np.array([label_remap[int(l)] for l in labels])

        all_images.append(imgs)
        if labels is not None:
            all_labels.append(labels)
        del imgs, labels

    images = np.concatenate(all_images, axis=0)
    del all_images
    labels_out = np.concatenate(all_labels) if all_labels else None
    del all_labels

    return images, labels_out
