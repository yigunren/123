"""生成 Grad-CAM 热力图，并可选生成 6 类样例网格。"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    ROOT, SPLIT_CSV, MODEL_DIR, FIG_DIR, IMG_SIZE,
    CLASS_NAMES_EN, CLASS_NAMES_ZH,
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False
NAMES_ZH = [CLASS_NAMES_ZH[n] for n in CLASS_NAMES_EN]


def load_model_and_cam():
    """加载分类模型，并重新连一个“输入 → 最后卷积特征 + 类别概率”的模型。

    Keras 3 对嵌套 Functional 模型的中间层直接取 output 有时会报
    “not connected”，所以这里用 base(inputs) 重新走一遍前向图，
    再复用原模型的 GAP / Dropout / Dense 权重。
    """
    model_path = MODEL_DIR / "tomato_mobilenetv2.h5"
    if not model_path.exists():
        raise SystemExit(f"模型不存在：{model_path}，请先运行 train.py")
    model = keras.models.load_model(model_path, compile=False)
    base = model.get_layer("mobilenetv2_1.00_160")
    inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    conv_outputs = base(inputs, training=False)       # 5×5×1280 特征图
    x = model.get_layer("gap")(conv_outputs)
    x = model.get_layer("dropout")(x)
    predictions = model.get_layer("predictions")(x)
    grad_model = keras.Model(inputs, [conv_outputs, predictions])
    return model, grad_model


def preprocess(path):
    """与训练/预测完全一致的预处理：RGB、160×160、[-1,1]、加 batch 维。"""
    img = Image.open(path).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(img).astype("float32")
    arr = keras.applications.mobilenet_v2.preprocess_input(arr)
    return np.expand_dims(arr, axis=0), img


def make_cam(path, grad_model, pred_index=None):
    """计算 Grad-CAM：用目标类得分对最后卷积特征求梯度并加权求和。"""
    x, img = preprocess(path)
    x_tensor = tf.convert_to_tensor(x)
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(x_tensor)
        if pred_index is None:
            # 默认解释模型最看好的那一类
            pred_index = int(tf.argmax(predictions[0]))
        loss = predictions[:, pred_index]
    # 类别得分对特征图的梯度：每个通道的重要性
    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    # 通道加权求和，得到 5×5 的热力图
    heatmap = tf.reduce_sum(conv_outputs * pooled_grads, axis=-1)
    heatmap = tf.maximum(heatmap, 0)                   # 只保留正贡献
    heatmap = heatmap / (tf.reduce_max(heatmap) + 1e-8)  # 归一化到 0—1
    heatmap = tf.image.resize(heatmap[..., None], [IMG_SIZE, IMG_SIZE]).numpy().squeeze()
    return img, heatmap, predictions.numpy()[0], pred_index


def overlay(img, heatmap):
    """把热力图以 45% 透明度叠到原图上，返回 uint8 RGB 图像。"""
    jet = plt.get_cmap("jet")
    heat = jet(heatmap)[..., :3]
    base = np.asarray(img).astype("float32") / 255.0
    out = np.clip(0.55 * base + 0.45 * heat, 0, 1)
    return (out * 255).astype(np.uint8)


def save_single(image_path, out_path):
    """单张图片：左图原图、右图 Grad-CAM 叠加，保存为 PNG。"""
    model, grad_model = load_model_and_cam()
    img, heatmap, probs, pred_idx = make_cam(image_path, grad_model)
    vis = overlay(img, heatmap)
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    axes[0].imshow(img)
    axes[0].set_title("原始图像")
    axes[0].axis("off")
    axes[1].imshow(vis)
    axes[1].set_title(f"Grad-CAM：{NAMES_ZH[pred_idx]}（{probs[pred_idx]:.1%}）")
    axes[1].axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out_path}")


def save_grid():
    """6 类各挑一张“分类正确”的测试图，拼成 2×3 的 Grad-CAM 面板。"""
    model, grad_model = load_model_and_cam()
    df = pd.read_csv(SPLIT_CSV)
    test = df[df["split"] == "test"]
    picks = []
    for class_idx, name in enumerate(CLASS_NAMES_EN):
        sub = test[test["label"] == name]
        for _, row in sub.iterrows():
            path = str(ROOT / row["filepath"])
            img, heatmap, probs, pred_idx = make_cam(path, grad_model)
            # 只选预测正确的样本，避免图注里出现“预测错”的尴尬
            if pred_idx == class_idx:
                picks.append((name, path, img, heatmap, probs, pred_idx))
                break
        if len(picks) < class_idx + 1:
            raise SystemExit(f"测试集中没有正确分类的样本：{name}")

    fig, axes = plt.subplots(2, 3, figsize=(13, 8.4))
    for ax, (name, path, img, heatmap, probs, pred_idx) in zip(axes.ravel(), picks):
        vis = overlay(img, heatmap)
        ax.imshow(vis)
        ax.set_title(f"{NAMES_ZH[pred_idx]}（{probs[pred_idx]:.1%}）", fontsize=11)
        ax.axis("off")
    fig.suptitle("Grad-CAM：模型关注区域（每类取 1 张正确分类的测试图）", fontsize=14)
    fig.tight_layout()
    out = FIG_DIR / "gradcam_grid.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="单张图片路径")
    parser.add_argument("--out", default=str(FIG_DIR / "gradcam_single.png"))
    parser.add_argument("--grid", action="store_true", help="生成 6 类样例网格")
    args = parser.parse_args()
    if args.grid:
        save_grid()
    elif args.image:
        save_single(args.image, args.out)
    else:
        parser.print_help()
