from __future__ import annotations

from app.data.content import GAP_RULES, QUESTIONS

DIMENSION_MAX = {"personal": 40, "economic": 35, "organizational": 25}

RIGHTS_PACKAGES = {
    "labor": {
        "label": "标准劳动关系",
        "summary": "80-100 分。三从属性较完整，符合法定要件，应重点审查劳动合同、工资支付、社保缴纳、休息休假、加班工资和违法解除等劳动法权益。",
        "rights": ["未签劳动合同双倍工资差额", "拖欠底薪、绩效奖金与直播提成", "延时直播及法定节假日加班工资", "在职期间社会保险补缴", "违法解除或单方停播的补偿赔偿", "追回违规扣款与罚款"],
        "legal_basis": ["《中华人民共和国劳动法》第2、36、44、50条", "《中华人民共和国劳动合同法》第7、10、30、38、46、82条", "《关于确立劳动关系有关事项的通知》(劳社部发〔2005〕12号)第1条", "《中华人民共和国社会保险法》第58、60条"],
        "actions": ["整理排班、考勤、处罚、工作指令和收益结算证据", "向机构提出书面权益诉求", "协商不成时向劳动监察部门投诉", "向劳动人事争议仲裁委员会申请仲裁", "对仲裁结果不服时依法提起诉讼"],
    },
    "ambiguous": {
        "label": "新业态模糊混合用工关系",
        "summary": "50-79 分。双方存在部分管理依附，但未完全达到标准劳动关系。应按新就业形态规则进行倾斜性保护，兼顾劳动权益与合同权益。",
        "rights": ["保底薪资与收益结算兑现", "恶意限流、停播或资源打压的补偿", "不公平格式条款调整", "职业伤害与灵活就业保障", "拒绝单方加重直播时长和管理约束", "合理解约与违约金调整"],
        "legal_basis": ["《关于维护新就业形态劳动者劳动保障权益的指导意见》（人社部发〔2021〕56号）第2、3、5条", "《最高人民法院关于为稳定就业提供司法服务和保障的意见》（法发〔2022〕36号）第6、7、8、9条", "《中华人民共和国民法典》第6、577、1165条"],
        "actions": ["固定日常管理约束事实与权益受损凭证", "协商修正合作条款和保障安排", "向直播平台或行业监管部门投诉协调", "通过人民调解委员会进行民事调解", "调解无效时提起合同纠纷诉讼"],
    },
    "service": {
        "label": "劳务依附型合作关系",
        "summary": "30-49 分。有一定管理约束和资源依赖，但主要按民事劳务或合作关系履行。重点关注报酬结算、合同公平、账号归属、资源扶持和违约责任。",
        "rights": ["追索劳务报酬与直播分成", "对故意打压造成损失主张赔偿", "追究流量、场地、运营扶持未兑现责任", "拒绝超出合同范围的高强度管控", "依据协议办理解约并维护经营自由"],
        "legal_basis": ["《中华人民共和国民法典》第119、1165条", "《劳动和社会保障部关于确立劳动关系有关事项的通知》（劳社部发〔2005〕12号）第1条"],
        "actions": ["核对合作协议并梳理违约事实", "发起对账并索要未结清劳务报酬", "通过平台客服或行业渠道居中协调", "协商无果后向基层人民法院提起民事诉讼"],
    },
    "business": {
        "label": "纯平等民事商务合作关系",
        "summary": "0-29 分。双方地位较平等，无明显人身、经济、组织依附，主要依据商业合作合同确定权责。重点处理合同履行、违约金、账号资源和公平交易问题。",
        "rights": ["拒绝远超合理标准的天价违约金", "对单方终止合作主张实际损失", "追究虚假包装、虚假引流和虚假扶持承诺", "自由选择合作平台与直播模式", "拒绝合同外额外附加义务"],
        "legal_basis": ["《中华人民共和国民法典》第4、5、577、585条"],
        "actions": ["对照合作合同确认履约情况", "依法协商解约与赔偿事宜", "协商无果时向被告所在地法院提起合同纠纷诉讼"],
    },
}


def _option_score(question_id: str, option_id: str) -> float:
    question = next(item for item in QUESTIONS if item["id"] == question_id)
    option = next(item for item in question["options"] if item["id"] == option_id)
    return float(option["score"])


def classify(total_score: float) -> str:
    if total_score >= 80:
        return "labor"
    if total_score >= 50:
        return "ambiguous"
    if total_score >= 30:
        return "service"
    return "business"


def evaluate_answers(answers: dict[str, str]) -> dict:
    dimension_values: dict[str, list[float]] = {key: [] for key in DIMENSION_MAX}

    for question in QUESTIONS:
        question_id = question["id"]
        dimension = question["dimension"]
        if dimension not in DIMENSION_MAX or question_id not in answers:
            continue
        dimension_values[dimension].append(_option_score(question_id, answers[question_id]))

    dimension_scores = {
        dimension: round(sum(values), 1) if values else 0
        for dimension, values in dimension_values.items()
    }
    dimension_percentages = {
        dimension: round((score / DIMENSION_MAX[dimension]) * 100, 1)
        for dimension, score in dimension_scores.items()
    }
    total_score = round(sum(dimension_scores.values()), 1)
    relation_type = classify(total_score)
    rights_package = RIGHTS_PACKAGES[relation_type]

    gaps = []
    for rule in GAP_RULES:
        selected = answers.get(rule["question"])
        eligible = (
            selected in rule["trigger"]
            and total_score >= rule.get("min_total", 0)
            and dimension_scores["personal"] >= rule.get("min_personal", 0)
            and dimension_scores["economic"] >= rule.get("min_economic", 0)
        )
        if eligible:
            gaps.append({"id": rule["id"], "title": rule["title"], "detail": rule["detail"]})

    bands = {
        "personal": ("管理控制较强" if dimension_scores["personal"] >= 30 else "存在部分管理" if dimension_scores["personal"] >= 15 else "自主性较高"),
        "economic": ("经济依附明显" if dimension_scores["economic"] >= 26 else "收益合作并存" if dimension_scores["economic"] >= 13 else "独立经营特征明显"),
        "organizational": ("深度纳入组织" if dimension_scores["organizational"] >= 19 else "浅层业务融入" if dimension_scores["organizational"] >= 8 else "组织相对独立"),
    }
    evidence = [
        "合作协议、补充协议及签约过程记录",
        "排班考勤、开播通知、工作指令和处罚记录",
        "工资、保底、提成、扣款明细及银行流水",
        "账号归属、后台权限、限流停播和申诉截图",
        "社保缴费记录、商业保险及福利补贴凭证",
    ]

    return {
        "dimensionScores": dimension_scores,
        "dimensionMax": DIMENSION_MAX,
        "dimensionPercentages": dimension_percentages,
        "totalScore": total_score,
        "relationType": relation_type,
        "relationLabel": rights_package["label"],
        "summary": rights_package["summary"],
        "rights": rights_package["rights"],
        "legalBasis": rights_package["legal_basis"],
        "actions": rights_package["actions"],
        "gaps": gaps,
        "dimensionInsights": bands,
        "evidenceChecklist": evidence,
        "modelVersion": "2026.07",
        "answeredCount": len([item for item in QUESTIONS if item["id"] in answers]),
        "disclaimer": "本报告基于问卷和规则模型生成，仅供学习、咨询和初步风险识别使用，不构成司法认定或正式法律意见。",
    }
