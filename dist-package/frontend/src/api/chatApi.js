import api from "./client";

export const sendAssistantMessageRequest = (payload) => api.post("/assistant/chat", payload);
export const confirmAssistantOrderRequest = (payload) => api.post("/assistant/confirm-order", payload);
