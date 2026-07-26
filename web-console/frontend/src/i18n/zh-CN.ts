import { ApiError, ChatResponse } from "../api/types";

type Messages = Record<string, string>;

export const messages: Messages = {
  "header.title": "芝麻机器人模拟器",
  "header.subtitle": "本地模拟器 · 真实硬件已禁用",
  "header.api.online": "接口在线",
  "header.api.offline": "接口离线",
  "header.api.blocked": "接口已阻止",
  "header.runtime.simulator": "运行模式：模拟器",
  "header.provider.mock": "模型服务：模拟模式",
  "header.hardware.disabled": "真实硬件已禁用",
  "header.reconnect": "重新连接",

  "panel.chat": "AI 对话",
  "panel.robot": "机器人状态",
  "panel.controls": "模拟器控制",
  "panel.timeline": "运行记录",
  "panel.backendAllowlist": "最终支持项以后端安全规则为准",

  "button.clearChat": "清空对话",
  "button.inject": "注入故障",
  "button.clearAllFaults": "清除全部故障",
  "button.resetSimulator": "重置模拟器",
  "button.resetSession": "重置会话",
  "button.refresh": "刷新",
  "button.send": "发送",
  "button.sending": "发送中…",
  "button.cancel": "取消",
  "button.confirmAction": "确认执行",

  "chat.inputLabel": "AI 指令",
  "chat.placeholder": "输入机器人指令，例如“挥手”或“查看电量”…",
  "chat.remaining": "还可输入 {count} 字",
  "chat.empty": "当前对话只保存在本页面内存中。",
  "chat.initial": "已连接到本地芝麻机器人模拟器。真实硬件当前已禁用。",
  "chat.requestFailed": "指令发送失败。",
  "chat.confirmationRequired": "该动作需要在网页中确认后才会执行。",
  "chat.outcomeUnknown": "确认请求已提交，但未收到最终结果。请检查机器人状态和运行记录，不要直接重复执行。",
  "chat.confirmationCanceled": "本次网页确认已取消，机器人动作未执行。",
  "chat.sessionReset": "当前会话已重置。运行系统确认请求撤销：{value}",

  "quick.status": "查看状态",
  "quick.battery": "查看电量",
  "quick.wave": "挥手",
  "quick.walk": "向前走",
  "quick.stop": "停止",
  "quick.faults": "查看故障",
  "quick.timeline": "查看记录",
  "quick.safety": "安全检查",

  "robot.pose": "姿态",
  "robot.face": "表情",
  "robot.motion": "运动状态",
  "robot.command": "当前指令",
  "robot.charging": "充电状态",
  "robot.runtime": "运行模式",
  "robot.communication": "通信状态",
  "robot.emergencyStop": "紧急停止",
  "robot.faults": "故障状态",
  "robot.battery": "电量",
  "robot.notSynced": "尚未同步",
  "robot.noFaults": "当前没有模拟故障",

  "controls.faultInjection": "模拟故障注入",
  "controls.faultPlaceholder": "请输入故障代码，例如 battery_low",
  "controls.suggestions": "可用示例：电量过低（battery_low）、舵机卡住（servo_stuck）、通信中断（communication_lost）",
  "controls.simulatorFailed": "模拟器操作失败。",
  "controls.clearFault": "清除 {fault}",
  "controls.resetSimulatorConfirm": "确定要重置模拟器吗？\n\n这将：\n- 清空当前模拟器状态\n- 清空当前网页中的待确认动作\n- 使旧的确认请求失效\n- 保留长期记忆数据",
  "controls.resetSessionConfirm": "确定要重置当前会话吗？\n\n这将：\n- 清空当前对话\n- 清空短期记忆\n- 保留模拟器状态\n- 不会直接撤销运行系统中的确认请求",

  "timeline.title": "运行记录",
  "timeline.limit": "显示数量",
  "timeline.loading": "正在刷新运行记录…",
  "timeline.empty": "暂时没有运行记录",
  "timeline.recent": "最近",
  "timeline.event": "事件",
  "timeline.eventType": "事件类型",
  "timeline.action": "动作",
  "timeline.result": "结果",
  "timeline.reason": "原因",
  "timeline.runtime": "运行模式",
  "timeline.fault": "故障",
  "timeline.resultAvailable": "已有结果",
  "timeline.code": "代码：{code}",

  "confirmation.title": "确认机器人动作",
  "confirmation.action": "动作",
  "confirmation.originalRequest": "原始指令",
  "confirmation.reason": "确认原因",
  "confirmation.fingerprint": "安全指纹",
  "confirmation.fingerprintMissing": "未提供",
  "confirmation.help": "点击“确认执行”后，系统才会执行该动作。安全确认编号只保存在当前页面内存中，不会显示或保存。",
  "confirmation.submitting": "正在等待机器人运行系统返回最终结果，请勿关闭页面或重复提交。",
};

export function t(key: string, params: Record<string, string | number | boolean> = {}): string {
  let value = messages[key] ?? key;
  for (const [name, replacement] of Object.entries(params)) {
    value = value.split(`{${name}}`).join(String(replacement));
  }
  return value;
}

const emptyResultValues = new Set(["", "none", "null", "unknown", "false"]);

export function normalizeDisplayCode(value: unknown): string {
  return String(value ?? "").trim();
}

export function isMeaningfulConfirmationResult(value: unknown): boolean {
  if (value === null || value === undefined || value === false) return false;
  return !emptyResultValues.has(normalizeDisplayCode(value).toLowerCase());
}

export function confirmationResultLabel(value: unknown): string | null {
  if (!isMeaningfulConfirmationResult(value)) return null;
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    accepted: "已确认并执行",
    ok: "已执行",
    already_used: "此确认已使用",
    action_mismatch: "确认动作与当前动作不一致",
    context_changed: "机器人状态已变化，请重新发起",
    expired: "确认已过期，请重新发起",
    unknown_id: "找不到该确认请求",
    stale_confirmation: "当前确认内容已失效",
  };
  return labels[code] ?? code;
}

export function actionLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    wave: "挥手",
    walk_forward: "向前移动",
    stop: "停止",
    inject: "注入故障",
    reset: "重置",
  };
  return labels[code] ?? (code || "无");
}

export function motionStateLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    idle: "空闲",
    moving: "运动中",
    stopped: "已停止",
    unknown: "未知",
  };
  return labels[code] ?? (code || "未知");
}

export function commandLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    wave: "挥手",
    walk_forward: "向前移动",
    stop: "停止",
    none: "无",
    unknown: "未知指令",
  };
  return labels[code] ?? (code || "无");
}

export function faceLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    default: "默认",
    happy: "开心",
    sad: "难过",
    alert: "警觉",
    unknown: "未知",
  };
  return labels[code] ?? (code || "未知");
}

export function robotPoseLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    standing: "站立",
    sitting: "坐下",
    lying: "躺下",
    unknown: "未知",
  };
  return labels[code] ?? (code || "未知");
}

export function chargingStateLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    not_charging: "未充电",
    charging: "充电中",
    full: "已充满",
    unknown: "未知",
  };
  return labels[code] ?? (code || "未知");
}

export function runtimeModeLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    simulator: "模拟器",
    mock: "模拟模式",
    real: "真实硬件模式",
    unknown: "未知模式",
  };
  return labels[code] ?? (code || "未知模式");
}

export function communicationLabel(timedOut: boolean | null | undefined): string {
  return timedOut ? "通信超时" : "通信正常";
}

export function emergencyStopLabel(active: boolean | null | undefined): string {
  return active ? "已触发" : "未触发";
}

export function faultLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    battery_low: "电量过低",
    servo_stuck: "舵机卡住",
    communication_lost: "通信中断",
  };
  return labels[code] ? `${labels[code]}（${code}）` : code || "未知故障";
}

export function eventTypeLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    fault: "故障",
    runtime: "运行系统",
    command: "指令",
    simulator: "模拟器",
    event: "事件",
  };
  return labels[code] ?? (code || "事件");
}

export function resultLabel(value: unknown): string {
  const code = normalizeDisplayCode(value);
  const labels: Record<string, string> = {
    ok: "已执行",
    done: "已完成",
    failed: "失败",
    rejected: "已拒绝",
    result_available: "已有结果",
  };
  if (labels[code]) return labels[code];
  const confirmation = confirmationResultLabel(code);
  if (confirmation) return confirmation;
  return labels[code] ?? (code || "已有结果");
}

export function chatRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    system: "系统",
    assistant: "助手",
    user: "你",
  };
  return labels[role] ?? role;
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const labels: Record<string, string> = {
      abort: "请求已取消。",
      timeout: "请求超时，请检查本地模拟器是否仍在运行。",
      offline: "无法连接到本地模拟器接口。",
      invalid_json: "接口返回的数据格式不正确。",
      invalid_response: "接口返回内容无法识别。",
      invalid_api_base: "接口地址配置不安全，已阻止请求。",
      unsafe_mode: "当前后端不是安全的本地模拟器模式。",
      invalid_request: "请求参数不正确。",
      stale_confirmation: "当前确认内容已失效。",
      unknown_fault: "后端不支持该故障代码。",
      request_too_large: "请求内容过长。",
      not_found: "找不到请求的资源。",
      internal_error: "本地模拟器内部错误。",
      api_error: "接口请求失败。",
    };
    return labels[error.code] ?? "接口请求失败。";
  }
  return "请求失败。";
}

export function chatResponseText(response: ChatResponse): string {
  const runtime = response.structured?.runtime;
  const runtimeRecord = typeof runtime === "object" && runtime !== null ? runtime : null;
  const runtimeConfirmation = runtimeRecord && "confirmation" in runtimeRecord ? runtimeRecord.confirmation : null;
  const state =
    typeof runtimeConfirmation === "object" && runtimeConfirmation !== null && "state" in runtimeConfirmation
      ? (runtimeConfirmation as { state?: unknown }).state
      : null;
  const confirmation = confirmationResultLabel(state);
  if (confirmation) return `确认结果：${confirmation}`;
  if (response.status === "confirmation_required") return t("chat.confirmationRequired");
  if (response.status === "ok" && response.action) return `已执行：${actionLabel(response.action)}`;
  if (response.message) return response.message;
  if (response.userMessage) return response.userMessage;
  return resultLabel(response.status);
}
