"""Usage:
  train.py [options]

Options:
  -e NUM, --epochs NUM  : Number of epochs [default: 100:int]
  -p NUM, --patience NUM  : Early stopping epochs [default: 20:int]
  -s NUM, --seed NUM  : Random seed [default: 123:int]
"""
# You can try fixing incorrect labels, adding data for side case tuning, apply
# data augmentation techniques, or use any other method to improve the data.
# You may also find it helpful to take a look at the training script to get a
# better sense of the preprocessing and model (these are held fixed). The script
# will resize all images to (256, 256) and run them through a cut off ResNet50

import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
import json
import sys

import numpy as np
import tensorflow as tf
from argopt import argopt
from keras import callbacks
from tensorflow import keras
from tqdm.keras import TqdmCallback

directory = "./data"
user_data = directory
test_data = (
    directory + "/labelbook"
)  # this can be the labelbook, or any other test set you create

### DO NOT MODIFY BELOW THIS LINE, THIS IS THE FIXED MODEL ###
batch_size = 8


if __name__ == "__main__":
    args = argopt(__doc__).parse_args()
    tf.random.set_seed(args.seed)
    train = tf.keras.preprocessing.image_dataset_from_directory(
        user_data + "/train",
        labels="inferred",
        label_mode="categorical",
        class_names=["cat", "dog", "muffin", "croissant"],
        shuffle=True,
        seed=args.seed,
        batch_size=batch_size,
        image_size=(256, 256),
        crop_to_aspect_ratio=True,
    )

    valid = tf.keras.preprocessing.image_dataset_from_directory(
        user_data + "/val",
        labels="inferred",
        label_mode="categorical",
        class_names=["cat", "dog", "muffin", "croissant"],
        shuffle=True,
        seed=args.seed,
        batch_size=batch_size,
        image_size=(256, 256),
    )

    total_length = ((train.cardinality() + valid.cardinality()) * batch_size).numpy()
    if total_length > 10_000:
        raise IndexError(
            f"Dataset size larger than 10,000. Got {total_length} examples"
        )

    test = tf.keras.preprocessing.image_dataset_from_directory(
        test_data,
        labels="inferred",
        label_mode="categorical",
        class_names=["cat", "dog", "muffin", "croissant"],
        shuffle=False,
        seed=args.seed,
        batch_size=batch_size,
        image_size=(256, 256),
    )

    base_model = tf.keras.applications.ResNet50(
        input_shape=(256, 256, 3),
        include_top=False,
        weights=None,
    )
    base_model = tf.keras.Model(
        base_model.inputs, outputs=[base_model.get_layer("conv2_block3_out").output]
    )

    inputs = tf.keras.Input(shape=(256, 256, 3))
    x = tf.keras.applications.resnet.preprocess_input(inputs)
    x = base_model(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dense(4, activation="sigmoid")(x)
    model = tf.keras.Model(inputs, x)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
        loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True),
        metrics=["accuracy"],
    )
    model.summary()
    loss_0, acc_0 = model.evaluate(valid)
    print(f"loss {loss_0}, acc {acc_0}")

    cbks = []
    cbks.append(
        callbacks.ModelCheckpoint(
            "best_model",
            monitor="val_accuracy",
            mode="max",
            verbose=0,
            save_best_only=True,
            save_weights_only=True,
        )
    )
    cbks.append(TqdmCallback())
    if args.patience >= 0:
        cbks.append(
            callbacks.EarlyStopping(
                monitor="val_accuracy",
                patience=args.patience,
                mode="max",
                restore_best_weights=True,
            )
        )

    history = model.fit(
        train,
        validation_data=valid,
        epochs=args.epochs,
        callbacks=cbks,
        verbose=0,
    )

    model.load_weights("best_model")

    loss, acc = model.evaluate(valid)
    print(f"final loss {loss}, final acc {acc}")

    test_loss, test_acc = model.evaluate(test)
    print(f"test loss {test_loss}, test acc {test_acc}")
