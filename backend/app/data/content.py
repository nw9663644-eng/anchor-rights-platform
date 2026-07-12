from __future__ import annotations


def opt(option_id: str, label: str, score: float) -> dict:
    return {"id": option_id, "label": label, "score": score}


def question(question_id: str, dimension: str, title: str, options: list[tuple[str, str, float]]) -> dict:
    return {
        "id": question_id,
        "dimension": dimension,
        "title": title,
        "type": "single",
        "options": [opt(*item) for item in options],
    }


QUESTIONS = [
    question("personal_1", "personal", "直播作息与考勤管理", [("a", "机构统一排班、考勤，请假需审批", 4), ("b", "机构提出排班要求，可协商调整", 2), ("c", "仅约定场次或时长，不考勤", 1), ("d", "完全自主安排", 0)]),
    question("personal_2", "personal", "直播开播关停管控", [("a", "开播、停播均由机构指令决定", 4), ("b", "关键场次由机构安排", 2), ("c", "仅需提前报备", 1), ("d", "完全自主决定", 0)]),
    question("personal_3", "personal", "直播内容策划权限", [("a", "脚本、选品、话术由机构审核决定", 4), ("b", "机构确定主题，主播可调整", 2), ("c", "机构仅提供建议", 1), ("d", "主播自主策划", 0)]),
    question("personal_4", "personal", "直播流程与风格管控", [("a", "机构持续监督流程、形象和表达", 4), ("b", "机构设置主要规范", 2), ("c", "仅有品牌合规要求", 1), ("d", "无统一管控", 0)]),
    question("personal_5", "personal", "日常工作指令调度", [("a", "需服从运营人员日常指令", 4), ("b", "重要事项接受调度", 2), ("c", "双方按项目协商", 1), ("d", "不存在日常指令", 0)]),
    question("personal_6", "personal", "线下事务统一管理", [("a", "培训、会议、活动均须参加", 4), ("b", "部分活动必须参加", 2), ("c", "活动自愿参加", 1), ("d", "无统一线下事务", 0)]),
    question("personal_7", "personal", "言行形象统一约束", [("a", "机构对日常言行、形象持续管理", 4), ("b", "对公开活动有较强约束", 2), ("c", "仅约定基本品牌规范", 1), ("d", "由主播自主决定", 0)]),
    question("personal_8", "personal", "违规处罚机制力度", [("a", "存在罚款、扣分、停播等纪律处分", 4), ("b", "存在明确整改或扣减规则", 2), ("c", "仅承担一般违约责任", 1), ("d", "无内部处罚机制", 0)]),
    question("personal_9", "personal", "工作排他性约束", [("a", "禁止与其他机构或平台合作", 4), ("b", "合作需经机构批准", 2), ("c", "特定项目存在排他", 1), ("d", "可自由选择合作方", 0)]),
    question("personal_10", "personal", "岗位层级管理体系", [("a", "纳入岗位、主管、汇报体系", 4), ("b", "有固定负责人和考核", 2), ("c", "仅有项目联系人", 1), ("d", "无管理层级", 0)]),
    question("economic_1", "economic", "收入薪资结构", [("a", "固定工资或保底加绩效提成", 5), ("b", "稳定保底加收益分成", 3), ("c", "主要按项目或场次结算", 1), ("d", "自主经营、自负盈亏", 0)]),
    question("economic_2", "economic", "薪资结算发放主体", [("a", "由机构按固定周期统一发放", 4), ("b", "平台结算后由机构分配", 3), ("c", "机构代收后按约转付", 1), ("d", "平台直接结算给主播", 0)]),
    question("economic_3", "economic", "福利补贴发放情况", [("a", "提供社保、餐补等员工型福利", 4), ("b", "提供部分固定补贴", 2), ("c", "仅有临时奖励", 1), ("d", "无福利补贴", 0)]),
    question("economic_4", "economic", "直播硬件设备供给", [("a", "主要设备由机构提供", 4), ("b", "机构提供部分设备", 2), ("c", "机构给予设备补助", 1), ("d", "设备由主播承担", 0)]),
    question("economic_5", "economic", "运营推广资源供给", [("a", "运营、投流、选品由机构持续提供", 4), ("b", "机构提供主要推广资源", 2), ("c", "偶尔提供资源支持", 1), ("d", "主播自行运营推广", 0)]),
    question("economic_6", "economic", "直播场地提供情况", [("a", "必须使用机构场地", 4), ("b", "主要使用机构场地", 2), ("c", "可按需使用机构场地", 1), ("d", "场地由主播解决", 0)]),
    question("economic_7", "economic", "成本费用分摊模式", [("a", "主要经营成本由机构承担", 3), ("b", "双方按比例分担", 2), ("c", "机构仅承担少量成本", 1), ("d", "主播承担全部成本", 0)]),
    question("economic_8", "economic", "经营盈亏风险承担", [("a", "机构承担主要经营风险", 3), ("b", "双方共同承担", 2), ("c", "主播承担主要风险但有保底", 1), ("d", "主播独立承担盈亏", 0)]),
    question("economic_9", "economic", "收入扣除项目规则", [("a", "机构可按内部规则扣减收入", 4), ("b", "扣减项目较多且由机构核定", 2), ("c", "仅按合同扣除明确成本", 1), ("d", "收入由主播自主支配", 0)]),
    question("organizational_1", "organizational", "业务隶属定位", [("a", "直播属于机构主营业务组成部分", 4), ("b", "属于机构重要业务项目", 3), ("c", "仅是外围合作业务", 1), ("d", "与机构业务相互独立", 0)]),
    question("organizational_2", "organizational", "账号所有权归属", [("a", "账号由机构注册并控制", 4), ("b", "账号共同管理", 3), ("c", "主播所有但机构可运营", 1), ("d", "主播独立所有和管理", 0)]),
    question("organizational_3", "organizational", "对外身份公示形式", [("a", "以机构成员或员工身份对外", 4), ("b", "以机构签约主播身份对外", 3), ("c", "部分场景使用机构身份", 1), ("d", "始终以个人身份对外", 0)]),
    question("organizational_4", "organizational", "团队编制纳入情况", [("a", "纳入部门或固定团队编制", 3), ("b", "纳入项目团队", 2), ("c", "仅与指定人员对接", 1), ("d", "不属于机构团队", 0)]),
    question("organizational_5", "organizational", "合作协议签订类型", [("a", "劳动合同或员工入职文件", 3), ("b", "经纪、合作协议但履行员工职责", 2), ("c", "普通劳务或项目协议", 1), ("d", "平等商业合作协议", 0)]),
    question("organizational_6", "organizational", "合作时长约束力度", [("a", "长期固定且退出限制严格", 4), ("b", "期限较长并有续约考核", 3), ("c", "阶段性项目合作", 1), ("d", "临时、松散合作", 0)]),
    question("organizational_7", "organizational", "晋升考核组织体系", [("a", "纳入统一绩效、晋升体系", 3), ("b", "有固定考核和等级", 2), ("c", "仅做项目复盘", 1), ("d", "无组织考核", 0)]),
    question("risk_social_insurance", "risk", "社会保险缴纳情况", [("a", "已足额缴纳", 0), ("b", "仅缴纳部分险种或以补贴替代", 1), ("c", "未缴纳任何社会保险", 1)]),
    question("risk_deduct", "risk", "收益扣减与罚款", [("a", "频繁发生且依据不清", 1), ("b", "偶尔发生或存在争议", 1), ("c", "从未发生", 0)]),
    question("risk_rest", "risk", "超时直播与休息", [("a", "长期强制超时或随时加播", 1), ("b", "偶尔超时且难以拒绝", 1), ("c", "可自主安排休息", 0)]),
    question("risk_contract", "risk", "合同条款公平性", [("a", "存在多项明显不公平条款", 1), ("b", "部分条款权责不清", 1), ("c", "条款清晰公平", 0)]),
    question("risk_ban", "risk", "封号、限流与停播", [("a", "频繁发生或被用于管理处罚", 1), ("b", "偶尔发生且申诉困难", 1), ("c", "从未发生", 0)]),
    question("risk_salary", "risk", "保底薪资兑现", [("a", "拖欠、少发或延迟发放", 1), ("b", "约定后从未兑现", 1), ("c", "已按约兑现或无保底约定", 0)]),
    question("risk_resign", "risk", "退出与自主择业限制", [("a", "违约金或限制明显过重", 1), ("b", "存在一定退出障碍", 1), ("c", "可合理退出并自主择业", 0)]),
    question("risk_contract_type", "risk", "实际履行与协议类型", [("a", "签订劳动合同", 0), ("b", "签经纪/合作协议但受较强管理", 1), ("c", "口头约定或无书面协议", 1)]),
    question("risk_overtime", "risk", "排班与加班补偿", [("a", "严格排班、频繁加班且无补偿", 1), ("b", "基本固定、偶尔加班", 1), ("c", "时间自主", 0)]),
    question("risk_welfare", "risk", "福利与职业保障", [("a", "无任何保障", 1), ("b", "仅有商业险或部分补贴", 1), ("c", "保障较完整", 0)]),
]

GAP_RULES = [
    {"id": "social", "question": "risk_social_insurance", "trigger": ["b", "c"], "title": "社会保险保障缺口", "detail": "核查用工实质、参保记录及机构是否以补贴替代法定义务。"},
    {"id": "pay", "question": "risk_deduct", "trigger": ["a", "b"], "title": "收入扣减风险", "detail": "保存结算单、流水和扣款通知，要求机构说明计算依据。"},
    {"id": "rest", "question": "risk_rest", "trigger": ["a", "b"], "title": "休息休假风险", "detail": "固定排班、开播时长和临时加播指令，核算实际工作强度。"},
    {"id": "contract", "question": "risk_contract", "trigger": ["a", "b"], "title": "合同公平风险", "detail": "重点审查高额违约金、单方解释权、账号处置和竞业限制。"},
    {"id": "platform", "question": "risk_ban", "trigger": ["a", "b"], "title": "账号处置风险", "detail": "保存封禁、限流、停播通知及申诉过程，区分平台规则与机构处分。"},
    {"id": "salary", "question": "risk_salary", "trigger": ["a", "b"], "title": "保底兑现风险", "detail": "对照合同、聊天承诺和银行流水核算欠付金额。"},
    {"id": "exit", "question": "risk_resign", "trigger": ["a", "b"], "title": "退出限制风险", "detail": "评估违约金与实际损失是否相称，并核查竞业范围和补偿。"},
    {"id": "form", "question": "risk_contract_type", "trigger": ["b", "c"], "min_total": 80, "title": "协议形式错配", "detail": "总分已呈现劳动关系特征，但书面协议与实际履行不一致。"},
    {"id": "overtime", "question": "risk_overtime", "trigger": ["a", "b"], "min_personal": 30, "title": "加班补偿风险", "detail": "在较强管理控制下，应重点核查延时、休息日直播及补偿。"},
    {"id": "welfare", "question": "risk_welfare", "trigger": ["a", "b"], "min_economic": 26, "title": "福利保障不足", "detail": "经济依附较强但保障不足，应核查社保、职业伤害和固定补贴。"},
]

CASES = []
RIGHTS_PACKAGES = {}
