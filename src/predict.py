"""单张番茄叶片图片预测。"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from tensorflow import keras

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import MODEL_DIR, IMG_SIZE, CLASS_NAMES_EN, CLASS_NAMES_ZH


def load_image(path):
    """读取图片 → RGB → 缩放到训练尺寸 → MobileNetV2 预处理 → 增加 batch 维。"""
    img = Image.open(path).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(img).astype("float32")
    # 与训练时完全一致：像素值映射到 [-1, 1]
    arr = keras.applications.mobilenet_v2.preprocess_input(arr)
    # 模型输入要求 (batch, height, width, channels)
    return np.expand_dims(arr, axis=0)


def main():
    parser = argparse.ArgumentParser(description="单张番茄叶片图片预测")
    parser.add_argument("image", help="待预测图片路径")
    parser.add_argument("--topk", type=int, default=3, help="显示概率最高的前 k 类")
    args = parser.parse_args()

    model_path = MODEL_DIR / "tomato_mobilenetv2.h5"
    if not model_path.exists():
        raise SystemExit(f"模型不存在：{model_path}，请先运行 train.py")
    # compile=False：只做推理，不需要优化器和损失函数
    model = keras.models.load_model(model_path, compile=False)
    names = [CLASS_NAMES_ZH[n] for n in CLASS_NAMES_EN]

    x = load_image(args.image)
    probs = model.predict(x, verbose=0)[0]       # 6 类的概率
    order = np.argsort(probs)[::-1][: args.topk]  # 从高到低排序

    print(f"图片：{args.image}")
    for rank, idx in enumerate(order, 1):
        print(f"{rank}. {names[idx]:<10s} {probs[idx]:.2%}")


if __name__ == "__main__":
    main()
