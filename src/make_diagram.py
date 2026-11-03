"""生成模型结构示意图。"""
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


def box(ax, x, y, w, h, title, sub, color, edge):
    p = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.3, edgecolor=edge, facecolor=color,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
            fontsize=11, color="#17241e", fontweight="bold")
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
            fontsize=8.5, color="#4b5a50")


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
        linewidth=1.2, color="#c7953f",
    ))


def main():
    fig, ax = plt.subplots(figsize=(13, 3.3))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 3.3)
    ax.axis("off")

    y, h = 1.05, 1.15
    boxes = [
        (0.25, 1.45, "输入图像", "160 × 160 × 3", "#eef5ee", "#2f7d5b"),
        (2.05, 2.00, "MobileNetV2", "ImageNet 预训练\n深度可分离卷积", "#dfece2", "#2f7d5b"),
        (4.45, 1.55, "全局平均池化", "5 × 5 × 1280 → 1280", "#f7f2e6", "#c7953f"),
        (6.40, 1.10, "Dropout", "丢弃率 0.25", "#f7f2e6", "#c7953f"),
        (8.05, 1.75, "全连接层", "1280 → 6", "#dcebed", "#2b6f77"),
        (10.25, 1.35, "Softmax", "6 类概率", "#0b3b2e", "#0b3b2e"),
    ]
    for item in boxes:
        x, w, title, sub, color, edge = item
        box(ax, x, y, w, h, title, sub, color, edge)

    # 最后一个深色框文字改为浅色
    ax.text(10.25 + 1.35 / 2, y + h * 0.62, "Softmax", ha="center", va="center",
            fontsize=11, color="#f4f0e2", fontweight="bold")
    ax.text(10.25 + 1.35 / 2, y + h * 0.28, "6 类概率", ha="center", va="center",
            fontsize=8.5, color="#c9d8cc")

    coords = [(1.70, y + h / 2), (4.05, y + h / 2), (6.00, y + h / 2),
              (7.50, y + h / 2), (9.80, y + h / 2), (11.60, y + h / 2)]
    for (x1, yy1), (x2, yy2) in zip(coords[:-1], coords[1:]):
        arrow(ax, x1, yy1, x2, yy2)

    ax.text(0.25, 2.68, "番茄叶片病害识别模型结构", fontsize=15,
            color="#0b3b2e", fontweight="bold")
    ax.text(0.25, 2.38, "迁移学习策略：先冻结骨干训练分类头，再解冻最后 20 层并以 1e-5 学习率微调；BN 层保持冻结。",
            fontsize=9.5, color="#5b685f")
    ax.text(2.05, 0.62, "参数量约 2.27 M", fontsize=8.5, color="#6c7a70")
    ax.text(10.25, 0.62, "输出：细菌性斑点病 / 早疫病 / 晚疫病 / 叶霉病 / 斑枯病 / 健康",
            fontsize=8.5, color="#6c7a70")

    fig.tight_layout()
    out = FIG_DIR / "model_architecture.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
