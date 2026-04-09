import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models

def build_model(num_classes):
    base_model = tf.keras.applications.EfficientNetB0(
        include_top=False, weights='imagenet', input_shape=(128, 256, 3)
    )
    base_model.trainable = False
    
    model = models.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

def train_baseline():
    print("=== 🦜 BIRDCLEF 2026: TENSORFLOW BASELINE ===")
    
    # Check GPU
    print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
    
    try:
        df = pd.read_csv("/kaggle/input/birdclef-2026/train_metadata.csv")
        num_classes = df['primary_label'].nunique()
    except:
        print("Using dummy data.")
        num_classes = 2

    model = build_model(num_classes)
    model.summary()
    
    # Mock training
    x_train = np.random.random((16, 128, 256, 3))
    y_train = np.random.randint(num_classes, size=(16,))
    
    model.fit(x_train, y_train, epochs=1)
    print("Training complete.")
    model.save("birdclef_tf_baseline.h5")

if __name__ == "__main__":
    train_baseline()
