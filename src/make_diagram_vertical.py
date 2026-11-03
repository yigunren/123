"""生成适合报告排版的竖向模型结构图。"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FIG_DIR

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False


def box(ax, y, title, sub, color, edge, text_color="#17241e"):
    x, w, h = 0.45, 5.1, 1.05
    p = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=1.2, edgecolor=edge, facecolor=color,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center",
            fontsize=11, color=text_color, fontweight="bold")
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
            fontsize=8.2, color=text_color if text_color != "#17241e" else "#4b5a50")


def arrow(ax, y1, y2):
    ax.add_patch(FancyArrowPatch(
        (3.0, y1), (3.0, y2), arrowstyle="-|>", mutation_scale=13,
        linewidth=1.2, color="#c7953f",
    ))


def main():
    fig, ax = plt.subplots(figsize=(6, 9.2))
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    ax.text(0.45, 8.75, "番茄叶片病害识别模型结构", fontsize=14,
            color="#0b3b2e", fontweight="bold")
    ax.text(0.45, 8.42, "MobileNetV2 + 两阶段迁移学习", fontsize=9.2, color="#5b685f")

    ys = [7.15, 5.75, 4.35, 2.95, 1.55]
    box(ax, ys[0], "输入图像", "160 × 160 × 3，RGB", "#eef5ee", "#2f7d5b")
    box(ax, ys[1], "MobileNetV2 骨干", "ImageNet 预训练；深度可分离卷积；约 2.26 M 参数", "#dfece2", "#2f7d5b")
    box(ax, ys[2], "全局平均池化", "5 × 5 × 1280 → 1280 维特征向量", "#f7f2e6", "#c7953f")
    box(ax, ys[3], "Dropout", "丢弃率 0.25，抑制过拟合", "#f7f2e6", "#c7953f")
    box(ax, ys[4], "全连接 + Softmax", "1280 → 6 类概率", "#0b3b2e", "#0b3b2e", "#f4f0e2")

    for y1, y2 in zip(ys[:-1], ys[1:]):
        arrow(ax, y1, y2 + 1.05)

    ax.text(3.0, 1.12, "输出：细菌性斑点病 / 早疫病 / 晚疫病 / 叶霉病 / 斑枯病 / 健康",
            ha="center", fontsize=8.3, color="#6c7a70")
    ax.text(3.0, 0.78, "训练策略：冻结骨干 → 训练分类头 → 解冻最后 20 层微调（BN 冻结）",
            ha="center", fontsize=8.0, color="#5b685f")

    fig.tight_layout()
    out = FIG_DIR / "model_architecture_vertical.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
