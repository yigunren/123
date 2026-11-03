"""项目统一配置：路径、类别映射和训练超参数。

所有脚本都从本文件取路径，避免把绝对路径写死在代码里；
换电脑或换项目目录时，只需要保证目录结构一致即可。
"""
from pathlib import Path

# 项目根目录（src 的上一级）
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "plantvillage_subset"   # 6 类番茄图片
SPLIT_CSV = ROOT / "data" / "splits.csv"           # 分层切分结果
OUTPUT_DIR = ROOT / "outputs"
MODEL_DIR = OUTPUT_DIR / "models"
FIG_DIR = OUTPUT_DIR / "figures"
METRIC_DIR = OUTPUT_DIR / "metrics"

# 训练超参数：160×160 在 CPU 速度和病斑细节之间比较平衡
IMG_SIZE = 160
BATCH_SIZE = 32
SEED = 42
NUM_CLASSES = 6

# 目录名 -> 中文展示名
CLASS_NAMES_ZH = {
    "Tomato___Bacterial_spot": "番茄细菌性斑点病",
    "Tomato___Early_blight": "番茄早疫病",
    "Tomato___Late_blight": "番茄晚疫病",
    "Tomato___Leaf_Mold": "番茄叶霉病",
    "Tomato___Septoria_leaf_spot": "番茄斑枯病",
    "Tomato___healthy": "番茄健康叶片",
}

CLASS_NAMES_EN = list(CLASS_NAMES_ZH.keys())
IDX_TO_ZH = {i: CLASS_NAMES_ZH[name] for i, name in enumerate(CLASS_NAMES_EN)}
IDX_TO_EN = {i: name for i, name in enumerate(CLASS_NAMES_EN)}

for d in (MODEL_DIR, FIG_DIR, METRIC_DIR):
    d.mkdir(parents=True, exist_ok=True)
