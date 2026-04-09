import api from "./client";

export const fetchWishlistRequest = () => api.get("/wishlist");
export const addWishlistRequest = (payload) => api.post("/wishlist/add", payload);
export const removeWishlistRequest = (bookId) => api.delete(`/wishlist/remove/${bookId}`);

