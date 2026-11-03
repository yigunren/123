"""训练 MobileNetV2 番茄叶片病害分类模型，并输出指标与图表。"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    ROOT, SPLIT_CSV, MODEL_DIR, FIG_DIR, METRIC_DIR,
    IMG_SIZE, BATCH_SIZE, SEED, NUM_CLASSES,
    CLASS_NAMES_EN, CLASS_NAMES_ZH,
)

# CPU 线程数，避免训练时把机器占满
try:
    tf.config.threading.set_intra_op_parallelism_threads(4)
    tf.config.threading.set_inter_op_parallelism_threads(2)
except Exception:
    pass

keras.utils.set_random_seed(SEED)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

LABEL_TO_IDX = {name: i for i, name in enumerate(CLASS_NAMES_EN)}
ZH_NAMES = [CLASS_NAMES_ZH[name] for name in CLASS_NAMES_EN]


def load_split():
    """读取 splits.csv，并把类别名字转换成 0—5 的整数标签。"""
    df = pd.read_csv(SPLIT_CSV)
    df["label_idx"] = df["label"].map(LABEL_TO_IDX)
    return df


def decode_image(path, label, training):
    """读取一张 JPEG，做缩放/增强，再转成 MobileNetV2 需要的 [-1, 1] 输入。

    训练阶段先放大到 180×180，再随机裁到 160×160，相当于一次轻量的
    随机缩放 + 平移；验证/测试阶段只做确定性的 160×160 缩放。
    """
    img = tf.io.read_file(path)                       # 读原始字节
    img = tf.image.decode_jpeg(img, channels=3)        # 统一解码为 RGB
    if training:
        # 训练增强：随机裁剪、翻转、亮度/对比度/饱和度扰动
        img = tf.image.resize(img, [IMG_SIZE + 20, IMG_SIZE + 20])
        img = tf.image.random_crop(img, [IMG_SIZE, IMG_SIZE, 3])
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_brightness(img, 0.12)
        img = tf.image.random_contrast(img, 0.90, 1.10)
        img = tf.image.random_saturation(img, 0.90, 1.10)
    else:
        # 验证/测试不做随机增强，保证评估结果可复现
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
    img = tf.cast(img, tf.float32)
    # MobileNetV2 预训练权重要求输入在 [-1, 1]
    img = keras.applications.mobilenet_v2.preprocess_input(img)
    return img, label


def make_dataset(df, training=False, shuffle=False):
    """把 DataFrame 转成 tf.data.Dataset，负责打乱、并行读取、批处理和预取。"""
    paths = df["filepath"].map(lambda p: str(ROOT / p)).values
    labels = df["label_idx"].values.astype(np.int32)
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if shuffle:
        # 只在训练集打乱；验证/测试保持顺序，方便和 DataFrame 对齐
        ds = ds.shuffle(len(df), seed=SEED, reshuffle_each_iteration=True)
    ds = ds.map(
        lambda p, y: decode_image(p, y, training),
        num_parallel_calls=tf.data.AUTOTUNE,
    )
    # prefetch 让 CPU 在读图的同时训练，减少等待
    return ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)


def build_model():
    """构建 MobileNetV2 + 分类头；返回完整模型和骨干，便于第二阶段解冻。"""
    base = keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,          # 去掉 ImageNet 的 1000 类分类头
        weights="imagenet",         # 使用预训练权重，加速小数据集收敛
    )
    base.trainable = False          # 第一阶段先冻结骨干
    inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="leaf_image")
    x = base(inputs, training=False)
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dropout(0.25, name="dropout")(x)
    outputs = layers.Dense(NUM_CLASSES, activation="softmax", name="predictions")(x)
    model = keras.Model(inputs, outputs, name="tomato_mobilenetv2")
    return model, base


def plot_history(stage1_csv, stage2_csv):
    """把第一阶段与微调阶段的 CSV 日志拼在一起，画准确率/损失曲线。"""
    h1 = pd.read_csv(stage1_csv)
    h2 = pd.read_csv(stage2_csv)
    epochs1 = len(h1)
    acc = list(h1["accuracy"]) + list(h2["accuracy"])
    val_acc = list(h1["val_accuracy"]) + list(h2["val_accuracy"])
    loss = list(h1["loss"]) + list(h2["loss"])
    val_loss = list(h1["val_loss"]) + list(h2["val_loss"])
    x = np.arange(1, len(acc) + 1)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].plot(x, acc, marker="o", label="训练准确率", color="#2f7d5b")
    axes[0].plot(x, val_acc, marker="s", label="验证准确率", color="#c7953f")
    axes[0].axvline(epochs1 + 0.5, color="#8a948c", linestyle="--", linewidth=1)
    axes[0].set_title("准确率曲线")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Accuracy")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].plot(x, loss, marker="o", label="训练损失", color="#2f7d5b")
    axes[1].plot(x, val_loss, marker="s", label="验证损失", color="#c7953f")
    axes[1].axvline(epochs1 + 0.5, color="#8a948c", linestyle="--", linewidth=1)
    axes[1].set_title("损失曲线")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Loss")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    fig.suptitle("MobileNetV2 迁移学习训练过程（虚线后为微调阶段）", fontsize=13)
    fig.tight_layout()
    out = FIG_DIR / "training_curves.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}", flush=True)


def evaluate(model, test_df):
    """在测试集上统一预测一次，计算指标并保存混淆矩阵、预测样例。"""
    # 不打乱顺序，保证 probs[i] 与 test_df.iloc[i] 一一对应
    test_ds = make_dataset(test_df, training=False, shuffle=False)
    probs = model.predict(test_ds, verbose=0)
    y_pred = probs.argmax(axis=1)
    y_true = test_df["label_idx"].values

    acc = accuracy_score(y_true, y_pred)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    weighted_p, weighted_r, weighted_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    # Top-3：真实类别只要落在概率最高的 3 个候选里就算命中
    top3 = float(np.mean([
        y_true[i] in np.argsort(probs[i])[-3:] for i in range(len(y_true))
    ]))

    # classification_report 会输出每一类的 precision/recall/F1
    report = classification_report(
        y_true, y_pred, target_names=ZH_NAMES, digits=4, zero_division=0
    )
    (METRIC_DIR / "classification_report.txt").write_text(report, encoding="utf-8")

    metrics = {
        "test_accuracy": float(acc),
        "top3_accuracy": top3,
        "macro_precision": float(macro_p),
        "macro_recall": float(macro_r),
        "macro_f1": float(macro_f1),
        "weighted_precision": float(weighted_p),
        "weighted_recall": float(weighted_r),
        "weighted_f1": float(weighted_f1),
        "test_size": int(len(test_df)),
        "classes": ZH_NAMES,
    }
    (METRIC_DIR / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 混淆矩阵
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8.2, 6.8))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Greens", cbar=False,
        xticklabels=ZH_NAMES, yticklabels=ZH_NAMES, ax=ax,
    )
    ax.set_xlabel("预测类别")
    ax.set_ylabel("真实类别")
    ax.set_title("测试集混淆矩阵")
    plt.xticks(rotation=28, ha="right")
    plt.yticks(rotation=0)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "confusion_matrix.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 预测样例
    rng = np.random.default_rng(SEED)
    idxs = rng.choice(len(test_df), size=12, replace=False)
    fig, axes = plt.subplots(3, 4, figsize=(13, 9.2))
    for ax, idx in zip(axes.ravel(), idxs):
        row = test_df.iloc[idx]
        img = Image.open(ROOT / row["filepath"]).convert("RGB").resize((160, 160))
        pred = int(y_pred[idx])
        true = int(y_true[idx])
        conf = float(probs[idx, pred])
        ax.imshow(img)
        ax.axis("off")
        color = "#2f7d5b" if pred == true else "#b3402f"
        ax.set_title(
            f"真实：{ZH_NAMES[true]}\n预测：{ZH_NAMES[pred]}（{conf:.1%}）",
            fontsize=9, color=color,
        )
    fig.suptitle("测试集预测样例", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "sample_predictions.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(report, flush=True)
    print(json.dumps(metrics, ensure_ascii=False, indent=2), flush=True)
    return metrics


def main():
    """完整训练入口：数据加载 → 冻结训练 → 微调 → 保存 → 评估。"""
    parser = argparse.ArgumentParser(description="番茄叶片病害 MobileNetV2 训练脚本")
    parser.add_argument("--stage1-epochs", type=int, default=12, help="第一阶段最大 epoch 数")
    parser.add_argument("--stage2-epochs", type=int, default=6, help="微调阶段最大 epoch 数")
    args = parser.parse_args()

    # 分别取出训练/验证/测试三个子集，并加上整数标签
    train_df = pd.read_csv(SPLIT_CSV)
    train_df["label_idx"] = train_df["label"].map(LABEL_TO_IDX)
    train_df = train_df[train_df["split"] == "train"].reset_index(drop=True)
    val_df = pd.read_csv(SPLIT_CSV)
    val_df["label_idx"] = val_df["label"].map(LABEL_TO_IDX)
    val_df = val_df[val_df["split"] == "val"].reset_index(drop=True)
    test_df = pd.read_csv(SPLIT_CSV)
    test_df["label_idx"] = test_df["label"].map(LABEL_TO_IDX)
    test_df = test_df[test_df["split"] == "test"].reset_index(drop=True)

    print(f"train={len(train_df)} val={len(val_df)} test={len(test_df)}", flush=True)
    # 训练集打乱并增强；验证集只缩放，不打乱
    train_ds = make_dataset(train_df, training=True, shuffle=True)
    val_ds = make_dataset(val_df, training=False, shuffle=False)

    model, base = build_model()
    model.summary()

    stage1_csv = METRIC_DIR / "history_stage1.csv"
    stage2_csv = METRIC_DIR / "history_finetune.csv"
    for p in (stage1_csv, stage2_csv):
        if p.exists():
            p.unlink()

    # 第一阶段：骨干冻结，只训练分类头；学习率可以稍大
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    callbacks1 = [
        # 只保存验证准确率最好的权重，避免最后一轮过拟合
        keras.callbacks.ModelCheckpoint(
            MODEL_DIR / "best_stage1.h5",
            monitor="val_accuracy", save_best_only=True, verbose=1,
        ),
        # 验证准确率连续 4 轮不提升就停止，并恢复最佳权重
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=4, restore_best_weights=True, verbose=1,
        ),
        # 验证损失平台期时把学习率降为 0.3 倍
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.3, patience=2, min_lr=1e-6, verbose=1,
        ),
        keras.callbacks.CSVLogger(stage1_csv),
    ]
    model.fit(
        train_ds, validation_data=val_ds, epochs=args.stage1_epochs,
        callbacks=callbacks1, verbose=1,
    )

    # 第二阶段：只解冻最后 20 层，并冻结 BN，避免小数据集上统计量漂移
    base.trainable = True
    for layer in base.layers[:-20]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
    # 微调学习率要比第一阶段小两个数量级，避免破坏预训练特征
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-5),
        loss=keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    callbacks2 = [
        keras.callbacks.ModelCheckpoint(
            MODEL_DIR / "best_finetune.h5",
            monitor="val_accuracy", save_best_only=True, verbose=1,
        ),
        # 微调阶段耐心值略小，防止在验证集上反复震荡
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=3, restore_best_weights=True, verbose=1,
        ),
        keras.callbacks.CSVLogger(stage2_csv),
    ]
    model.fit(
        train_ds, validation_data=val_ds, epochs=args.stage2_epochs,
        callbacks=callbacks2, verbose=1,
    )

    # 保存完整模型（结构 + 权重），后续 predict.py / gradcam.py 直接加载
    final_path = MODEL_DIR / "tomato_mobilenetv2.h5"
    model.save(final_path)
    print(f"saved model: {final_path}", flush=True)

    # 画训练曲线，并在测试集上做最终评估
    plot_history(stage1_csv, stage2_csv)
    evaluate(model, test_df)


if __name__ == "__main__":
    main()
