"""
Dice + BCE combined loss for binary segmentation.
Handles class imbalance (small objects vs large background).
"""
import tensorflow as tf

SMOOTH = 1e-6

def dice_bce_loss(y_true, y_pred):
    """
    Combined Dice + Binary Cross-Entropy loss.

    Dice loss addresses class imbalance — without it, the model
    learns to predict all-background when the target class is rare.
    BCE stabilises gradients early in training.
    """
    y_true_f = tf.reshape(y_true, [-1])
    y_pred_f = tf.reshape(y_pred, [-1])

    intersection = tf.reduce_sum(y_true_f * y_pred_f)
    dice_loss = 1.0 - (2.0 * intersection + SMOOTH) / (
        tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f) + SMOOTH)

    bce_loss = tf.keras.losses.binary_crossentropy(y_true, y_pred)
    return dice_loss + tf.reduce_mean(bce_loss)
