import api from "./client";

export const fetchReviewsByBookRequest = (bookId) => api.get(`/reviews/book/${bookId}`);
export const createReviewRequest = (payload) => api.post("/reviews", payload);
export const updateReviewRequest = (id, payload) => api.put(`/reviews/${id}`, payload);
export const deleteReviewRequest = (id) => api.delete(`/reviews/${id}`);

