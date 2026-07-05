import api from "./client";

export const fetchCartRequest = () => api.get("/cart");
export const addToCartRequest = (payload) => api.post("/cart/add", payload);
export const updateCartItemRequest = (payload) => api.put("/cart/update", payload);
export const removeCartItemRequest = (bookId) => api.delete(`/cart/remove/${bookId}`);
export const clearCartRequest = () => api.delete("/cart/clear");

