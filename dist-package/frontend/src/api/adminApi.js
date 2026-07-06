import api from "./client";

export const fetchAdminUsersRequest = () => api.get("/admin/users");
export const updateAdminUserRoleRequest = (id, role) => api.put(`/admin/users/${id}/role`, { role });
export const deleteAdminUserRequest = (id) => api.delete(`/admin/users/${id}`);

export const fetchAdminSessionsRequest = () => api.get("/admin/sessions");
export const deleteAdminSessionRequest = (id) => api.delete(`/admin/sessions/${id}`);

export const sendAdminChatRequest = (payload) => api.post("/admin/assistant/chat", payload);
