import api from "./client";

export const checkoutRequest = () => api.post("/orders/checkout");
export const fetchMyOrdersRequest = () => api.get("/orders/my");
export const fetchOrderDetailsRequest = (id) => api.get(`/orders/${id}`);
export const fetchAdminOrdersRequest = () => api.get("/admin/orders");
export const updateOrderStatusRequest = (id, status) =>
  api.put(`/admin/orders/${id}/status`, { status });
export const fetchAdminStatsRequest = (params = {}) => api.get("/admin/stats", { params });
