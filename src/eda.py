"""数据概览：类别分布与样例图。"""
import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ROOT, SPLIT_CSV, FIG_DIR, CLASS_NAMES_EN, CLASS_NAMES_ZH

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False


def main():
    """打印类别分布，并从训练集每类取 1 张图生成数据样例图。"""
    df = pd.read_csv(SPLIT_CSV)
    # 行是类别，列是 train/val/test，方便检查是否分层均衡
    print(df.groupby(["label", "split"]).size().unstack(fill_value=0))

    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    for ax, name in zip(axes.ravel(), CLASS_NAMES_EN):
        # 每类只取训练集第一张，避免把测试图放进报告
        sub = df[(df["label"] == name) & (df["split"] == "train")].head(1)
        if len(sub) == 0:
            continue
        img = Image.open(ROOT / sub.iloc[0]["filepath"]).convert("RGB")
        ax.imshow(img)
        ax.set_title(
            f"{CLASS_NAMES_ZH[name]}\n训练样本数：{len(df[(df['label'] == name) & (df['split'] == 'train')])}",
            fontsize=11,
        )
        ax.axis("off")
    fig.suptitle("六类番茄叶片样例", fontsize=15)
    fig.tight_layout()
    out = FIG_DIR / "dataset_samples.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
