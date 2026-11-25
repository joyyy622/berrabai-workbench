"""Import the observed catalog into the editable knowledge table once."""
import csv
from collections import defaultdict
from pathlib import Path

SNAPSHOT_DATE = "2026-11-23"
CATALOG_FILE = Path(__file__).with_name("catalog_snapshot.tsv")
PREFIX = "小程序实读 " + SNAPSHOT_DATE + " · "


def entries():
    groups = defaultdict(list)
    with CATALOG_FILE.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            price = int(row["列表起价（元）"])
            groups[row["品类"]].append((row["商品名称"], price, row["页面备注"]))
    result = []
    boundary = (
        "来源：2026-11-23直接查看Berrabai莓莓兔小程序的商品列表。"
        "以下金额仅为当时列表展示的起价，不是实时库存、完整购买价或最终报价。"
        "部分最低价可能对应寄改而不含娃，不可将起价直接当成娃＋钻价格。"
        "只有备注明确核对的规格才能给出相应规格价格，其他规格须人工确认。"
        "未标注尺寸、材质、是否含娃、工期时不得推测。\n"
    )
    for category, rows in groups.items():
        content = boundary + "品类：" + category + "\n" + "\n".join(
            f"{name}：列表¥{price}起。" + (note + "。" if note else "")
            for name, price, note in rows
        )
        result.append((PREFIX + category, content))
    result.append((PREFIX + "目录读取范围与回答规则",
        "商品列表已逐类查看，共21个商品品类；另有购前须知分类，含生日贺卡（列表0元起）及四份服务说明。"
        "0元展示不代表顾客可免费单独购买或服务没有收费。星星人幸运马有两条同名同价记录，暂按一个款式列入目录。"
        "本次完成分类列表读取，只抽查了克拉拉的规格；其余商品的规格选项、尺寸、详情图说明未逐项穷尽。"
        "可据此介绍有哪些款式与页面标明的工期，但顾客问含娃价格、具体规格、实时库存和准确交期时应引导人工确认。"
        "同名商品要先确认品类，例如拉布布美乐蒂与Melody美乐蒂系列不同。"
        "先回答顾客正在问的款式，避免一次罗列所有商品。"))
    result.extend([
        (PREFIX + "购前与款式确认", "来源：小程序购前须知分类及用户提供的同版清晰资料图。品牌说明只对正品娃娃进行贴钻改造；下单后请添加客服微信并保持联系畅通，款式确认无误后开始制作。一般手工制作3–5天，以客服告知及具体商品标注为准；发货前拍摄实物照片或视频，确认后安排发货。目录中还有生日贺卡，列表0元起；不能据此承诺免费单独购买。"),
        (PREFIX + "定制与寄改流程", "来源：用户提供的小程序DIY定制与寄改资料图，当前分类列表仍展示此说明。可沟通贴钻位置、配色与风格、图案元素、蝴蝶结和配饰、个性化设计。价格按款式、工艺和复杂程度单独核算。寄改前先联系客服确认是否可改造；流程为寄娃、沟通需求、评估报价、设计确认、制作、寄回。确认方案后开始制作，完成后提供照片或视频确认再寄回；最终价格以确认设计方案为准。不能承诺所有娃娃均能改造。"),
        (PREFIX + "闪钻日常养护", "来源：用户提供的闪钻养护资料图，当前小程序分类列表仍展示此说明。每颗钻为手工贴上。建议减少硬物摩擦，避免频繁揉搓、拉扯钻饰，单独收纳，长期不用可放入防尘袋。避免水洗或长时间浸水、酒精香水消毒液等化学品、高温暴晒、与钥匙饰品等硬物长期摩擦，以及用力拉扯或抠钻。"),
        (PREFIX + "售后资料与人工核实", "来源：用户提供的售后须知资料图，当前小程序分类列表仍展示此说明。页面写明：收到娃娃7天内发现明显掉钻，应拍照或拍视频联系客服，可寄回免费补钻，寄回邮费由品牌承担；7天后邮费由客户承担。页面另写免费补钻6个月、6个月后收费，具体资格和费用由人工核实。明显质量问题请提供订单信息、照片或视频及问题描述。资料中的定制退换与责任认定须人工确认；AI不直接拒绝顾客诉求、不判定责任或承诺赔付。")
    ])
    return result


def import_catalog(conn):
    added = 0
    for title, content in entries():
        if not conn.execute("SELECT 1 FROM knowledge WHERE title=?", (title,)).fetchone():
            conn.execute("INSERT INTO knowledge(title,content) VALUES(?,?)", (title, content))
            added += 1
    return added
